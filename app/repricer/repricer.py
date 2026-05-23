"""App-side repricing (Allegro has no native pricing-rules API).

Undercut the cheapest competitor by a small epsilon, but never drop below the
operator's floor (cost basis + minimum margin).
"""
from app.allegro import endpoints
from app.allegro.client import AllegroClient


def compute_new_price(competitor_totals: list[float], floor_price: float,
                      undercut: float) -> float:
    """Cheapest competitor minus `undercut`, clamped at `floor_price`."""
    if not competitor_totals:
        return round(floor_price, 2)
    target = min(competitor_totals) - undercut
    return round(max(target, floor_price), 2)


def reprice_offer(client: AllegroClient, *, allegro_offer_id: str, current_price: float,
                  competitor_totals: list[float], floor_price: float,
                  undercut: float) -> float | None:
    """Update the offer's price if it should change. Returns the new price, else None."""
    new_price = compute_new_price(competitor_totals, floor_price, undercut)
    if abs(new_price - current_price) < 0.01:
        return None
    endpoints.update_offer_price(client, allegro_offer_id, new_price)
    return new_price
