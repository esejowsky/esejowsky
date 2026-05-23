from collections import defaultdict
from dataclasses import dataclass

from app.allegro.endpoints import search_listing
from app.allegro.models import OfferCandidate, parse_listing
from app.db import repo
from app.scanner.reference import reference_price

MIN_SAMPLES = 3  # need at least this many comparable offers to trust a market price


@dataclass
class EngineParams:
    min_roi: float
    min_net_profit: float
    packaging_cost: float
    risk_buffer_pct: float
    resale_shipping_cost: float
    commission_rate_estimate: float
    reference_percentile: float

    @classmethod
    def from_settings(cls) -> "EngineParams":
        g = repo.get_float_setting
        return cls(
            min_roi=g("min_roi"),
            min_net_profit=g("min_net_profit"),
            packaging_cost=g("packaging_cost"),
            risk_buffer_pct=g("risk_buffer_pct"),
            resale_shipping_cost=g("resale_shipping_cost"),
            commission_rate_estimate=g("commission_rate_estimate"),
            reference_percentile=g("reference_percentile"),
        )


@dataclass
class Opportunity:
    candidate: OfferCandidate
    ref_price: float
    est_commission: float
    net_profit: float
    roi: float
    sample_size: int


def _product_key(c: OfferCandidate) -> str | None:
    return c.product_id or c.gtin


def evaluate(candidates: list[OfferCandidate], params: EngineParams) -> list[Opportunity]:
    """Pure opportunity detection: group comparable offers, score each as a buy.

    Comparable = same catalog product (or GTIN fallback) AND same condition.
    """
    groups: dict[tuple, list[OfferCandidate]] = defaultdict(list)
    for c in candidates:
        key = _product_key(c)
        if key is None or c.price <= 0:
            continue
        groups[(key, c.condition)].append(c)

    opportunities: list[Opportunity] = []
    for members in groups.values():
        if len(members) < MIN_SAMPLES:
            continue
        totals = [m.total for m in members]
        ref = reference_price(totals, params.reference_percentile)
        commission = round(ref * params.commission_rate_estimate, 2)
        risk = round(ref * params.risk_buffer_pct, 2)

        for c in members:
            net = round(
                ref - commission - params.resale_shipping_cost
                - c.total - params.packaging_cost - risk,
                2,
            )
            roi = round(net / c.total, 4) if c.total > 0 else 0.0
            if roi >= params.min_roi and net >= params.min_net_profit:
                opportunities.append(
                    Opportunity(
                        candidate=c,
                        ref_price=ref,
                        est_commission=commission,
                        net_profit=net,
                        roi=roi,
                        sample_size=len(members),
                    )
                )
    opportunities.sort(key=lambda o: o.roi, reverse=True)
    return opportunities


def scan_watchlist(client, watchlist: dict, params: EngineParams | None = None) -> int:
    """Fetch a watchlist's listings, evaluate, and persist opportunities. Returns count."""
    params = params or EngineParams.from_settings()
    candidates: list[OfferCandidate] = []
    offset = 0
    while offset < 1000:  # stay below the offset+limit ceiling; segment if you need more
        payload = search_listing(
            client,
            phrase=watchlist.get("phrase"),
            category_id=watchlist.get("category_id"),
            price_from=watchlist.get("price_from"),
            price_to=watchlist.get("price_to"),
            limit=100,
            offset=offset,
        )
        batch = parse_listing(payload)
        if not batch:
            break
        candidates.extend(batch)
        offset += 100

    want = watchlist.get("condition", "all")
    if want in ("new", "used"):
        candidates = [c for c in candidates if c.condition == want]

    opportunities = evaluate(candidates, params)

    with repo.get_conn() as conn:
        for opp in opportunities:
            c = opp.candidate
            product_id = repo.find_or_create_product(
                conn, c.product_id, c.gtin, c.name, c.category_id
            )
            offer_id = repo.upsert_offer(
                conn, c.offer_id, product_id, c.seller, c.price,
                c.delivery_cost, c.condition, c.url,
            )
            repo.record_price_history(conn, product_id, opp.ref_price, opp.sample_size)
            repo.upsert_opportunity(
                conn, product_id, offer_id, c.total, opp.ref_price,
                opp.est_commission, opp.net_profit, opp.roi,
            )
    return len(opportunities)
