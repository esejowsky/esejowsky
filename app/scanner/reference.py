"""Reference resale price: a percentile of comparable offers with outliers removed."""


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile (p in 0..100). `values` need not be sorted."""
    if not values:
        raise ValueError("percentile of empty sequence")
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    rank = (p / 100.0) * (len(xs) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(xs) - 1)
    frac = rank - lo
    return xs[lo] + (xs[hi] - xs[lo]) * frac


def remove_outliers(values: list[float]) -> list[float]:
    """Drop values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]. Needs >=4 points to act."""
    if len(values) < 4:
        return list(values)
    q1 = percentile(values, 25)
    q3 = percentile(values, 75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    kept = [v for v in values if lo <= v <= hi]
    return kept or list(values)


def reference_price(totals: list[float], pct: float) -> float:
    """Realistic resale price = `pct` percentile of the de-noised market totals."""
    return round(percentile(remove_outliers(totals), pct), 2)
