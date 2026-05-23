from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.allegro import endpoints
from app.allegro.client import AllegroClient, NotAuthorized
from app.db import repo
from app.repricer import description, images

STATIC_DIR = Path(__file__).parent / "web" / "static"

app = FastAPI(title="Allegro Arbitrage")
client = AllegroClient()


@app.on_event("startup")
def _startup() -> None:
    repo.init_db()


# ---- Watchlists -------------------------------------------------------------
class WatchlistIn(BaseModel):
    name: str
    phrase: str | None = None
    category_id: str | None = None
    ean: str | None = None
    price_from: float | None = None
    price_to: float | None = None
    condition: str = "all"
    scan_interval: int = 1800


@app.get("/api/watchlists")
def list_watchlists():
    with repo.get_conn() as conn:
        rows = conn.execute("SELECT * FROM watchlists ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/watchlists")
def create_watchlist(wl: WatchlistIn):
    with repo.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO watchlists(name, phrase, category_id, ean, price_from, price_to, "
            "condition, scan_interval) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
            (wl.name, wl.phrase, wl.category_id, wl.ean, wl.price_from, wl.price_to,
             wl.condition, wl.scan_interval),
        )
        new_id = cur.fetchone()["id"]
    return {"id": new_id}


@app.delete("/api/watchlists/{wl_id}")
def delete_watchlist(wl_id: int):
    with repo.get_conn() as conn:
        conn.execute("DELETE FROM watchlists WHERE id = ?", (wl_id,))
    return {"ok": True}


# ---- Opportunities ----------------------------------------------------------
@app.get("/api/opportunities")
def list_opportunities(status: str | None = None):
    sql = (
        "SELECT op.id, op.buy_total, op.ref_price, op.est_commission, op.net_profit, "
        "op.roi, op.status, op.created_at, p.name, p.allegro_product_id, "
        "o.allegro_offer_id, o.url, o.price, o.delivery_cost, o.seller, o.condition "
        "FROM opportunities op "
        "JOIN products p ON p.id = op.product_id "
        "JOIN offers o ON o.id = op.buy_offer_id "
    )
    params: tuple = ()
    if status:
        sql += "WHERE op.status = ? "
        params = (status,)
    sql += "ORDER BY op.roi DESC LIMIT 500"
    with repo.get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


class StatusIn(BaseModel):
    status: str


@app.post("/api/opportunities/{opp_id}/status")
def set_opportunity_status(opp_id: int, body: StatusIn):
    with repo.get_conn() as conn:
        conn.execute("UPDATE opportunities SET status = ? WHERE id = ?", (body.status, opp_id))
    return {"ok": True}


@app.get("/api/products/{product_id}/price-history")
def price_history(product_id: int):
    with repo.get_conn() as conn:
        rows = conn.execute(
            "SELECT ts, ref_price, sample_size FROM price_history "
            "WHERE product_id = ? ORDER BY ts",
            (product_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---- Settings ---------------------------------------------------------------
@app.get("/api/settings")
def get_settings_api():
    with repo.get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    return {r["key"]: r["value"] for r in rows}


@app.put("/api/settings")
def update_settings(values: dict[str, str]):
    for key, value in values.items():
        repo.set_setting(key, value)
    return {"ok": True}


# ---- Listing preview & images ----------------------------------------------
class PreviewIn(BaseModel):
    name: str
    image_urls: list[str] = []
    overrides: dict | None = None


@app.post("/api/preview")
def preview_listing(body: PreviewIn):
    desc = description.default_description(body.name, body.image_urls, body.overrides)
    return {"html": description.sections_to_preview_html(desc["sections"])}


@app.post("/api/images")
async def upload_image(file: UploadFile):
    data = await file.read()
    try:
        url = images.upload_binary(client, data, file.content_type or "image/jpeg")
    except NotAuthorized as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return {"location": url}


# ---- Auth -------------------------------------------------------------------
@app.get("/api/auth/status")
def auth_status():
    return {"connected": client.has_seller_token()}


@app.get("/auth/connect")
def auth_connect():
    return RedirectResponse(client.authorize_url())


@app.get("/auth/callback")
def auth_callback(code: str | None = None, error: str | None = None):
    if error or not code:
        return HTMLResponse(f"<p>Authorization failed: {error or 'no code'}</p>", status_code=400)
    client.exchange_code(code)
    return RedirectResponse("/?connected=1")


# ---- Static dashboard -------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
