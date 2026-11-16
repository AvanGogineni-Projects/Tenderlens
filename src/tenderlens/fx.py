"""Monthly average ECB reference rates (units of currency per 1 EUR) as a dbt seed.

    python -m tenderlens.fx eurofxref-hist.csv dbt/seeds/fx_monthly.csv

shortcut: a seed refreshed by hand from the ECB history file; move to a scheduled ingest if gold needs
rates newer than the last refresh.
"""

import csv
import sys
from collections import defaultdict

FIXED = {"BGN": 1.95583}  # pegged; the ECB stopped publishing it when Bulgaria joined the euro (2026)


def monthly_rates(rows: list[dict], since: str = "2023-01") -> dict[tuple[str, str], float]:
    """{(month 'YYYY-MM', currency): mean rate} from ECB daily rows ({'Date': ..., 'USD': '1.08', ...})."""
    sums: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        month = row["Date"][:7]
        if month < since:
            continue
        for cur, val in row.items():
            if cur in ("Date", "") or cur in FIXED:
                continue
            try:
                rate = float(val)
            except (TypeError, ValueError):  # 'N/A' for currencies not quoted that day
                continue
            sums[(month, cur)].append(rate)
    rates = {k: round(sum(v) / len(v), 6) for k, v in sums.items()}
    for month in {m for m, _ in rates}:
        rates.update({(month, cur): rate for cur, rate in FIXED.items()})
    return rates


def main(src: str, dst: str) -> None:
    with open(src, newline="") as f:
        rates = monthly_rates(list(csv.DictReader(f)))
    with open(dst, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "currency", "per_eur"])
        for (month, cur), rate in sorted(rates.items()):
            w.writerow([f"{month}-01", cur, rate])
    print(f"{len(rates)} rates → {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
