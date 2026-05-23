from app.scanner.reference import percentile, reference_price, remove_outliers


def test_percentile_interpolates():
    assert percentile([10, 20, 30, 40], 50) == 25
    assert percentile([10, 20, 30, 40], 0) == 10
    assert percentile([10, 20, 30, 40], 100) == 40


def test_percentile_single_value():
    assert percentile([42], 40) == 42


def test_remove_outliers_keeps_cluster():
    values = [100, 102, 98, 101, 99, 700]
    kept = remove_outliers(values)
    assert 700 not in kept
    assert 100 in kept


def test_remove_outliers_small_sample_untouched():
    assert remove_outliers([5, 900, 7]) == [5, 900, 7]


def test_reference_price_ignores_the_cheap_outlier():
    totals = [1305, 1315, 1335, 1325, 715]
    assert reference_price(totals, 40) == 1317.0
