"""Upload offer photos to Allegro and return hosted URLs.

For NEW items we reuse the catalog product photos (no upload). For USED items the
operator uploads real photos of the actual unit so the listing shows its true
condition rather than a stock catalog image.
"""
from app.allegro import endpoints
from app.allegro.client import AllegroClient


def upload_from_urls(client: AllegroClient, urls: list[str]) -> list[str]:
    return [endpoints.register_image(client, u) for u in urls]


def upload_binary(client: AllegroClient, data: bytes, content_type: str = "image/jpeg") -> str:
    return endpoints.register_image_binary(client, data, content_type)
