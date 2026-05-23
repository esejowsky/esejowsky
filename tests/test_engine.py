import json
from pathlib import Path

from app.allegro.models import parse_listing
from app.scanner.engine import EngineParams, evaluate

FIXTURE = Path(__file__).parent / "fixtures" / "listing_sample.json"

PARAMS = EngineParams(
    min_roi=0.25,
    min_net_profit=30,
    packaging_cost=3,
    risk_buffer_pct=0.05,
    resale_shipping_cost=0,
    commission_rate_estimate=0.12,
    reference_percentile=40,
)


def _candidates():
    return parse_listing(json.loads(FIXTURE.read_text()))


def test_parse_listing_normalises_offers():
    candidates = _candidates()
    assert len(candidates) == 7
    deal = next(c for c in candidates if c.offer_id == "1005")
    assert deal.total == 715.0
    assert deal.product_id == "100"
    assert deal.gtin == "5901234123457"
    assert deal.condition == "used"


def test_evaluate_flags_only_the_underpriced_offer():
    opps = evaluate(_candidates(), PARAMS)
    assert len(opps) == 1
    opp = opps[0]
    assert opp.candidate.offer_id == "1005"
    assert opp.ref_price == 1317.0
    assert opp.est_commission == 158.04
    assert opp.net_profit == 375.11
    assert round(opp.roi, 4) == 0.5246
    assert opp.sample_size == 5


def test_group_below_min_samples_is_skipped():
    # product "200" has only two offers -> no market price -> no opportunity
    opps = evaluate(_candidates(), PARAMS)
    assert all(o.candidate.product_id != "200" for o in opps)


def test_high_threshold_yields_nothing():
    strict = EngineParams(
        min_roi=2.0, min_net_profit=30, packaging_cost=3, risk_buffer_pct=0.05,
        resale_shipping_cost=0, commission_rate_estimate=0.12, reference_percentile=40,
    )
    assert evaluate(_candidates(), strict) == []
