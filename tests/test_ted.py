import io
import tarfile
from pathlib import Path

import pytest

from tenderlens import ted
from tenderlens.ingest import ingest

FIX = Path(__file__).parent / "fixtures"
PACKAGE = (FIX / "20250103_2025002.tar.gz").read_bytes()


def make_package(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_package_id():
    assert ted.package_id(2025, 2) == "202500002"
    assert ted.package_url("202500002") == "https://ted.europa.eu/packages/daily/202500002"
    with pytest.raises(ValueError):
        ted.package_id(2025, 0)


def test_notices_from_real_package():
    rows = {r["publication_number"]: r for r in ted.notices(PACKAGE)}
    assert set(rows) == {"2326-2025", "3632-2025"}
    assert rows["2326-2025"]["notice_type"] == "ContractAwardNotice"
    assert rows["3632-2025"]["notice_type"] == "ContractNotice"
    assert "Ekobrottsmyndigheten" in rows["2326-2025"]["xml"]
    assert ted.validate(PACKAGE) == 2


def test_prefixed_root_and_broken_xml_are_kept():
    pkg = make_package({
        "d/00000001_2025.xml": b'<can:ContractAwardNotice xmlns:can="urn:x"/>',
        "d/00000002_2025.xml": b"not xml at all",
        "d/readme.txt": b"not a notice",
    })
    rows = {r["publication_number"]: r["notice_type"] for r in ted.notices(pkg)}
    assert rows == {"1-2025": "ContractAwardNotice", "2-2025": None}


def test_validate_rejects_truncated_and_empty():
    with pytest.raises((tarfile.TarError, EOFError)):
        ted.validate(PACKAGE[: len(PACKAGE) // 2])
    with pytest.raises(tarfile.TarError):
        ted.validate(make_package({"d/readme.txt": b"x"}))


def test_next_issues_skips_held_and_single_gaps_and_stops_at_today():
    published = {1, 2, 3, 5, 6}  # 4 is a gap, 7+ not out yet
    assert list(ted.next_issues(2025, {1, 2}, published.__contains__)) == [3, 5, 6]
    assert list(ted.next_issues(2025, published, published.__contains__)) == []


def test_ingest_writes_atomically_and_is_idempotent(tmp_path):
    calls = []

    def fake_fetch(pid):
        calls.append(pid)
        return PACKAGE if int(pid[4:]) <= 3 else None

    assert ingest(str(tmp_path), range(2025, 2026), fake_fetch) == ["202500001", "202500002", "202500003"]
    folder = tmp_path / "daily" / "2025"
    assert sorted(p.name for p in folder.iterdir()) == [f"20250000{i}.tar.gz" for i in (1, 2, 3)]
    calls.clear()
    assert ingest(str(tmp_path), range(2025, 2026), fake_fetch) == []
    assert calls == ["202500004", "202500005"]  # only probes past what it holds
