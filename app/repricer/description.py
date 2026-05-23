"""Build an Allegro offer description from a branded template.

Allegro accepts only a structured description: a list of `sections`, each holding
1-2 `items` of type TEXT (a restricted HTML subset: h1, h2, p, ul/ol/li, b/strong,
i/em, a) or IMAGE (a URL of an image already uploaded via POST /sale/images).
We emit one item per section, which is always valid.
"""
import html

# A block is either {"type": "text", "html": "<h2>..</h2>"} with {placeholders},
# or {"type": "images"} which expands to one IMAGE section per uploaded photo.
DEFAULT_TEMPLATE: list[dict] = [
    {"type": "text", "html": "<h2>Stan przedmiotu</h2><p>{condition_text}</p>"},
    {"type": "images"},
    {"type": "text", "html": "<h2>Opis</h2><p>{name}</p>"},
    {"type": "text", "html": "<h2>Wysyłka i zwroty</h2>"
                             "<ul><li>{shipping}</li><li>{returns}</li></ul>"},
    {"type": "text", "html": "<p>{store_blurb}</p>"},
]

DEFAULT_CONTEXT = {
    "condition_text": "Używany, w pełni sprawny. Zdjęcia przedstawiają rzeczywisty egzemplarz.",
    "shipping": "Wysyłka w 24h od zaksięgowania wpłaty.",
    "returns": "14 dni na zwrot dla konsumentów.",
    "store_blurb": "Sprzedaż prowadzona przez sklep esej.",
}


def text_section(content_html: str) -> dict:
    return {"items": [{"type": "TEXT", "content": content_html}]}


def image_section(url: str) -> dict:
    return {"items": [{"type": "IMAGE", "url": url}]}


def _safe_context(context: dict) -> dict:
    """HTML-escape interpolated values so product names can't break the markup."""
    return {k: html.escape(str(v)) for k, v in context.items()}


def build_sections(template: list[dict], context: dict, image_urls: list[str]) -> list[dict]:
    ctx = _safe_context(context)
    sections: list[dict] = []
    for block in template:
        if block["type"] == "images":
            sections.extend(image_section(u) for u in image_urls)
        elif block["type"] == "text":
            sections.append(text_section(block["html"].format(**ctx)))
    return sections


def default_description(name: str, image_urls: list[str], overrides: dict | None = None) -> dict:
    context = {**DEFAULT_CONTEXT, "name": name, **(overrides or {})}
    return {"sections": build_sections(DEFAULT_TEMPLATE, context, image_urls)}


def sections_to_preview_html(sections: list[dict]) -> str:
    """Approximate how Allegro renders the description, for the dashboard preview."""
    parts: list[str] = []
    for section in sections:
        for item in section.get("items", []):
            if item["type"] == "TEXT":
                parts.append(item["content"])
            elif item["type"] == "IMAGE":
                parts.append(f'<img src="{html.escape(item["url"])}" alt="">')
    return "\n".join(parts)
