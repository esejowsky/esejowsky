from app.repricer.repricer import compute_new_price


def test_undercuts_cheapest_competitor():
    assert compute_new_price([100.0, 90.0, 95.0], floor_price=80.0, undercut=0.01) == 89.99


def test_respects_floor():
    assert compute_new_price([85.0], floor_price=90.0, undercut=0.01) == 90.0


def test_no_competitors_returns_floor():
    assert compute_new_price([], floor_price=50.0, undercut=0.01) == 50.0
