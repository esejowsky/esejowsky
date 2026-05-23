import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

DEFAULT_SETTINGS = {
    "min_roi": "0.25",            # 25 %
    "min_net_profit": "30",       # PLN
    "packaging_cost": "3",        # PLN
    "risk_buffer_pct": "0.05",    # 5 %
    "resale_shipping_cost": "0",  # PLN you subsidise on the resale side
    "commission_rate_estimate": "0.12",  # fallback commission when no seller token
    "reference_percentile": "40",
    "reprice_undercut": "0.01",   # PLN below cheapest competitor
}


def _connect() -> sqlite3.Connection:
    db_path = Path(get_settings().database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                (key, value),
            )


def get_setting(key: str, default: str | None = None) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else (DEFAULT_SETTINGS.get(key, default))


def get_float_setting(key: str) -> float:
    return float(get_setting(key))


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def upsert_product(conn, allegro_product_id, gtin, name, category_id) -> int:
    cur = conn.execute(
        "INSERT INTO products(allegro_product_id, gtin, name, category_id) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(allegro_product_id) DO UPDATE SET "
        "gtin=excluded.gtin, name=excluded.name, category_id=excluded.category_id "
        "RETURNING id",
        (allegro_product_id, gtin, name, category_id),
    )
    return cur.fetchone()["id"]


def find_or_create_product(conn, allegro_product_id, gtin, name, category_id) -> int:
    if allegro_product_id:
        return upsert_product(conn, allegro_product_id, gtin, name, category_id)
    if gtin:
        row = conn.execute(
            "SELECT id FROM products WHERE gtin = ? AND allegro_product_id IS NULL",
            (gtin,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE products SET name = ?, category_id = ? WHERE id = ?",
                (name, category_id, row["id"]),
            )
            return row["id"]
    cur = conn.execute(
        "INSERT INTO products(allegro_product_id, gtin, name, category_id) "
        "VALUES (?, ?, ?, ?) RETURNING id",
        (allegro_product_id, gtin, name, category_id),
    )
    return cur.fetchone()["id"]


def upsert_offer(conn, allegro_offer_id, product_id, seller, price, delivery_cost, condition, url) -> int:
    cur = conn.execute(
        "INSERT INTO offers(allegro_offer_id, product_id, seller, price, delivery_cost, condition, url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(allegro_offer_id) DO UPDATE SET "
        "product_id=excluded.product_id, price=excluded.price, "
        "delivery_cost=excluded.delivery_cost, last_seen=datetime('now'), active=1 "
        "RETURNING id",
        (allegro_offer_id, product_id, seller, price, delivery_cost, condition, url),
    )
    return cur.fetchone()["id"]


def record_price_history(conn, product_id, ref_price, sample_size) -> None:
    conn.execute(
        "INSERT INTO price_history(product_id, ref_price, sample_size) VALUES (?, ?, ?)",
        (product_id, ref_price, sample_size),
    )


def upsert_opportunity(conn, product_id, buy_offer_id, buy_total, ref_price,
                       est_commission, net_profit, roi) -> None:
    conn.execute(
        "INSERT INTO opportunities("
        "product_id, buy_offer_id, buy_total, ref_price, est_commission, net_profit, roi) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(buy_offer_id) DO UPDATE SET "
        "buy_total=excluded.buy_total, ref_price=excluded.ref_price, "
        "est_commission=excluded.est_commission, net_profit=excluded.net_profit, "
        "roi=excluded.roi",
        (product_id, buy_offer_id, buy_total, ref_price, est_commission, net_profit, roi),
    )
