"""Thin wrappers over the Allegro REST endpoints we use.

Verified shapes (developer.allegro.pl):
  GET  /offers/listing                  public search (client_credentials)
  GET  /sale/products                   catalog search (phrase + mode=GTIN)
  POST /pricing/offer-fee-preview        commission/fee quote (user token)
  POST /sale/product-offers              create catalog-linked offer (user token)
  PATCH /sale/product-offers/{offerId}   partial price/qty edit (user token)
  POST /sale/images                      register image from URL (user token)
"""
from app.allegro.client import AllegroClient


def search_listing(client: AllegroClient, *, phrase=None, category_id=None,
                   seller_id=None, price_from=None, price_to=None,
                   limit=60, offset=0) -> dict:
    params = {"limit": min(limit, 100), "offset": offset}
    if phrase:
        params["phrase"] = phrase
    if category_id:
        params["category.id"] = category_id
    if seller_id:
        params["seller.id"] = seller_id
    if price_from is not None:
        params["price.from"] = price_from
    if price_to is not None:
        params["price.to"] = price_to
    return client.get("/offers/listing", params=params)


def fee_preview(client: AllegroClient, *, category_id: str, price: float,
                marketplace="allegro-pl", currency="PLN") -> dict:
    body = {
        "offer": {
            "category": {"id": category_id},
            "sellingMode": {"price": {"amount": f"{price:.2f}", "currency": currency}},
            "marketplaces": {"base": {"id": marketplace}},
        }
    }
    return client.post("/pricing/offer-fee-preview", user=True, json=body)


def total_fee(quote: dict) -> float:
    """Best-effort sum of fee amounts from an offer-fee-preview response.

    Used for the precise check shown in the dashboard when a seller account is
    connected. The scanner itself estimates commission from a configurable rate
    because fee-preview requires a seller (billing:read) token.
    """
    total = 0.0
    for q in quote.get("quotes", []):
        fee_obj = q.get("fee", {})
        amount = fee_obj.get("amount")
        if amount is None:
            amount = fee_obj.get("commission", {}).get("amount")
        if amount is not None:
            total += float(amount)
    return round(total, 2)


def register_image(client: AllegroClient, image_url: str) -> str:
    """Register an image Allegro fetches from a public URL."""
    resp = client.post("/sale/images", user=True, json={"url": image_url})
    return resp["location"]


def register_image_binary(client: AllegroClient, data: bytes,
                          content_type: str = "image/jpeg") -> str:
    """Upload raw image bytes (used for the operator's own photos of used items)."""
    resp = client.request(
        "POST", "/sale/images", user=True, content=data,
        headers={"Content-Type": content_type},
    )
    return resp["location"]


def create_product_offer(client: AllegroClient, body: dict) -> dict:
    return client.post("/sale/product-offers", user=True, json=body)


def update_offer_price(client: AllegroClient, offer_id: str, price: float,
                       currency="PLN") -> dict:
    body = {"sellingMode": {"price": {"amount": f"{price:.2f}", "currency": currency}}}
    return client.patch(f"/sale/product-offers/{offer_id}", user=True, json=body)
