PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS watchlists (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    phrase        TEXT,
    category_id   TEXT,
    ean           TEXT,
    price_from    REAL,
    price_to      REAL,
    condition     TEXT NOT NULL DEFAULT 'all',   -- new | used | all
    active        INTEGER NOT NULL DEFAULT 1,
    scan_interval INTEGER NOT NULL DEFAULT 1800,  -- seconds
    last_scan_at  TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    allegro_product_id TEXT UNIQUE,
    gtin              TEXT,
    name              TEXT,
    category_id       TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_products_gtin ON products(gtin);

CREATE TABLE IF NOT EXISTS offers (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    allegro_offer_id TEXT UNIQUE NOT NULL,
    product_id       INTEGER REFERENCES products(id),
    seller           TEXT,
    price            REAL NOT NULL,
    delivery_cost    REAL NOT NULL DEFAULT 0,
    condition        TEXT,
    url              TEXT,
    first_seen       TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen        TEXT NOT NULL DEFAULT (datetime('now')),
    active           INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_offers_product ON offers(product_id);

CREATE TABLE IF NOT EXISTS price_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    ts         TEXT NOT NULL DEFAULT (datetime('now')),
    ref_price  REAL NOT NULL,
    sample_size INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_id);

CREATE TABLE IF NOT EXISTS opportunities (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id     INTEGER NOT NULL REFERENCES products(id),
    buy_offer_id   INTEGER NOT NULL REFERENCES offers(id),
    buy_total      REAL NOT NULL,
    ref_price      REAL NOT NULL,
    est_commission REAL NOT NULL,
    net_profit     REAL NOT NULL,
    roi            REAL NOT NULL,
    status         TEXT NOT NULL DEFAULT 'new',  -- new|seen|bought|listed|sold|dismissed
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(buy_offer_id)
);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);

CREATE TABLE IF NOT EXISTS my_offers (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    allegro_offer_id TEXT UNIQUE,
    product_id       INTEGER REFERENCES products(id),
    opportunity_id   INTEGER REFERENCES opportunities(id),
    condition        TEXT NOT NULL DEFAULT 'used',  -- new | used
    list_price       REAL,
    cost_basis       REAL,
    min_price        REAL,
    repricing_enabled INTEGER NOT NULL DEFAULT 1,
    status           TEXT NOT NULL DEFAULT 'draft',  -- draft|published|ended
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS offer_images (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    my_offer_id      INTEGER NOT NULL REFERENCES my_offers(id) ON DELETE CASCADE,
    allegro_image_url TEXT NOT NULL,
    position         INTEGER NOT NULL DEFAULT 0,
    source           TEXT NOT NULL DEFAULT 'uploaded'  -- catalog | uploaded
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    grant_type    TEXT NOT NULL,   -- client_credentials | authorization_code
    scope_set     TEXT,
    access_token  TEXT NOT NULL,
    refresh_token TEXT,
    expires_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(grant_type)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
