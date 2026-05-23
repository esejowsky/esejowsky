from app.repricer.description import (
    DEFAULT_TEMPLATE,
    build_sections,
    default_description,
    sections_to_preview_html,
)


def test_build_sections_interleaves_images():
    ctx = {
        "condition_text": "uzywany", "name": "Aparat", "shipping": "24h",
        "returns": "14 dni", "store_blurb": "esej",
    }
    sections = build_sections(DEFAULT_TEMPLATE, ctx, ["u1", "u2"])
    image_items = [it for s in sections for it in s["items"] if it["type"] == "IMAGE"]
    assert [it["url"] for it in image_items] == ["u1", "u2"]


def test_context_values_are_escaped():
    desc = default_description("Aparat <script>", ["u1"])
    html = sections_to_preview_html(desc["sections"])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_default_description_has_sections_and_image():
    desc = default_description("Aparat", ["https://img/1.jpg"])
    assert desc["sections"]
    assert any(
        it["type"] == "IMAGE" for s in desc["sections"] for it in s["items"]
    )


def test_preview_renders_images():
    desc = default_description("Aparat", ["https://img/1.jpg"])
    html = sections_to_preview_html(desc["sections"])
    assert 'src="https://img/1.jpg"' in html
