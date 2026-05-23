import argparse

from app.allegro.client import AllegroClient
from app.db import repo
from app.notifications.notify import notify
from app.repricer.repricer import reprice_offer
from app.scanner.engine import EngineParams, scan_watchlist


def cmd_init_db(_args) -> None:
    repo.init_db()
    print("database initialised")


def cmd_scan(args) -> None:
    client = AllegroClient()
    params = EngineParams.from_settings()
    with repo.get_conn() as conn:
        if args.watchlist:
            rows = conn.execute(
                "SELECT * FROM watchlists WHERE id = ?", (args.watchlist,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM watchlists WHERE active = 1").fetchall()
        watchlists = [dict(r) for r in rows]

    total = 0
    for wl in watchlists:
        found = scan_watchlist(client, wl, params)
        total += found
        print(f"watchlist '{wl['name']}': {found} opportunities")
        with repo.get_conn() as conn:
            conn.execute(
                "UPDATE watchlists SET last_scan_at = datetime('now') WHERE id = ?",
                (wl["id"],),
            )
    if total:
        notify(f"Allegro arbitrage: {total} okazji w ostatnim skanie.")
    client.close()


def cmd_reprice(_args) -> None:
    client = AllegroClient()
    undercut = repo.get_float_setting("reprice_undercut")
    with repo.get_conn() as conn:
        offers = conn.execute(
            "SELECT * FROM my_offers WHERE repricing_enabled = 1 "
            "AND status = 'published' AND allegro_offer_id IS NOT NULL"
        ).fetchall()
        offers = [dict(o) for o in offers]

    for mine in offers:
        with repo.get_conn() as conn:
            comp = conn.execute(
                "SELECT price, delivery_cost FROM offers "
                "WHERE product_id = ? AND active = 1 AND allegro_offer_id != ?",
                (mine["product_id"], mine["allegro_offer_id"]),
            ).fetchall()
        totals = [r["price"] + r["delivery_cost"] for r in comp]
        floor = mine["min_price"] or mine["cost_basis"] or 0
        new_price = reprice_offer(
            client,
            allegro_offer_id=mine["allegro_offer_id"],
            current_price=mine["list_price"] or 0,
            competitor_totals=totals,
            floor_price=floor,
            undercut=undercut,
        )
        if new_price is not None:
            with repo.get_conn() as conn:
                conn.execute(
                    "UPDATE my_offers SET list_price = ? WHERE id = ?",
                    (new_price, mine["id"]),
                )
            print(f"offer {mine['allegro_offer_id']}: repriced to {new_price}")
    client.close()


def cmd_refresh_tokens(_args) -> None:
    client = AllegroClient()
    client.get_public_token()
    if client.has_seller_token():
        client.get_user_token()
        print("tokens refreshed")
    else:
        print("public token ok; seller account not connected")
    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="arbitrage")
    sub = parser.add_subparsers(required=True)

    sub.add_parser("init-db").set_defaults(func=cmd_init_db)

    scan = sub.add_parser("scan")
    scan.add_argument("--watchlist", type=int, help="scan a single watchlist by id")
    scan.set_defaults(func=cmd_scan)

    sub.add_parser("reprice").set_defaults(func=cmd_reprice)
    sub.add_parser("refresh-tokens").set_defaults(func=cmd_refresh_tokens)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
