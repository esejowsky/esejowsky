from dataclasses import dataclass, field


@dataclass
class OfferCandidate:
    """Normalised view of one offer from /offers/listing."""

    offer_id: str
    name: str
    price: float
    delivery_cost: float
    condition: str            # "new" | "used" | "unknown"
    product_id: str | None
    gtin: str | None
    seller: str | None
    category_id: str | None
    url: str

    @property
    def total(self) -> float:
        return round(self.price + self.delivery_cost, 2)


def _to_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_listing(payload: dict) -> list[OfferCandidate]:
    """Flatten Allegro /offers/listing response (promoted + regular) into candidates."""
    items = payload.get("items", {})
    raw = list(items.get("promoted", [])) + list(items.get("regular", []))
    out: list[OfferCandidate] = []
    for o in raw:
        selling = o.get("sellingMode", {}).get("price", {})
        delivery = o.get("delivery", {}).get("lowestPrice", {})
        product = (o.get("productSet") or [{}])[0].get("product", {}) if o.get("productSet") else {}
        gtins = product.get("gtins") or product.get("eans") or []
        out.append(
            OfferCandidate(
                offer_id=str(o.get("id")),
                name=o.get("name", ""),
                price=_to_float(selling.get("amount")),
                delivery_cost=_to_float(delivery.get("amount")),
                condition=(o.get("condition") or "unknown").lower(),
                product_id=str(product["id"]) if product.get("id") else None,
                gtin=str(gtins[0]) if gtins else None,
                seller=str((o.get("seller") or {}).get("id") or "") or None,
                category_id=str((o.get("category") or {}).get("id") or "") or None,
                url=f"https://allegro.pl/oferta/{o.get('id')}",
            )
        )
    return out
