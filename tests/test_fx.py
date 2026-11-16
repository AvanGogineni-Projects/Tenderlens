from tenderlens.fx import monthly_rates


def test_monthly_mean_skips_na_and_adds_pegged_bgn():
    rows = [{"Date": "2026-01-02", "SEK": "11.0", "BGN": "N/A", "ROL": "N/A"},
            {"Date": "2026-01-05", "SEK": "12.0", "BGN": "N/A", "ROL": "N/A"},
            {"Date": "2022-12-30", "SEK": "99"}]
    r = monthly_rates(rows)
    assert r[("2026-01", "SEK")] == 11.5
    assert r[("2026-01", "BGN")] == 1.95583
    assert ("2026-01", "ROL") not in r and ("2022-12", "SEK") not in r
