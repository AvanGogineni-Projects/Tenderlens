"""Daily job: download every TED daily package we don't have yet into the raw volume.

Layout: {volume}/daily/{yyyy}/{package_id}.tar.gz. A package is written to `.part` and renamed, and
Auto Loader only picks up `*.tar.gz`, so bronze never reads a half-written file. Re-running is a no-op.
"""

import argparse
import datetime as dt
import os
from pathlib import Path

from tenderlens import ted


def ingest(volume: str, years: range, fetch=ted.fetch) -> list[str]:
    written = []
    for year in years:
        folder = Path(volume) / "daily" / str(year)
        folder.mkdir(parents=True, exist_ok=True)
        have = {int(p.name[4:9]) for p in folder.glob("*.tar.gz")}

        def save(issue: int, year: int = year, folder: Path = folder) -> bool:
            pid = ted.package_id(year, issue)
            data = fetch(pid)
            if data is None:
                return False
            part = folder / f"{pid}.part"
            part.write_bytes(data)
            os.replace(part, folder / f"{pid}.tar.gz")
            print(f"{pid}: {len(data) / 1e6:.1f} MB", flush=True)
            return True

        written += [ted.package_id(year, i) for i in ted.next_issues(year, have, save)]
    return written


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--volume", required=True, help="e.g. /Volumes/workspace/tenderlens/raw/ted")
    p.add_argument("--from-year", type=int, default=2024)
    a = p.parse_args(argv)
    got = ingest(a.volume, range(a.from_year, dt.date.today().year + 1))
    print(f"downloaded {len(got)} packages")


if __name__ == "__main__":
    main()
