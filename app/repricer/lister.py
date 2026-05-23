"""Create a resale offer linked to an existing catalog product.

Linking to `productId` (rather than creating a new catalog product) inherits the
title/parameters and keeps us on the right side of Allegro's no-duplicate-product
rules. We override the gallery with the operator's own photos for used items.
"""
from app.allegro import endpoints
from app.allegro.client import AllegroClient


def build_product_offer_body(*, product_id: str, price: float, name: str,
                             image_urls: list[str], description: dict,
                             shipping_rates_id: str | None, stock: int = 1,
                             currency: str = "PLN", publish: bool = False) -> dict:
    body: dict = {
        "productSet": [{"product": {"id": product_id}}],
        "name": name[:75],
        "sellingMode": {"format": "BUY_NOW",
                        "price": {"amount": f"{price:.2f}", "currency": currency}},
        "stock": {"available": stock},
        "images": image_urls,
        "description": description,
        # Create inactive by default — the operator reviews, then activates.
        "publication": {"status": "ACTIVE" if publish else "INACTIVE"},
    }
    # Delivery, payments and location otherwise fall back to the seller's
    # account defaults; a shipping-rate set is required to publish.
    if shipping_rates_id:
        body["delivery"] = {"shippingRates": {"id": shipping_rates_id}}
    return body


def create_listing(client: AllegroClient, *, product_id: str, price: float, name: str,
                   image_urls: list[str], description: dict,
                   shipping_rates_id: str | None = None, publish: bool = False) -> dict:
    body = build_product_offer_body(
        product_id=product_id, price=price, name=name, image_urls=image_urls,
        description=description, shipping_rates_id=shipping_rates_id, publish=publish,
    )
    return endpoints.create_product_offer(client, body)
