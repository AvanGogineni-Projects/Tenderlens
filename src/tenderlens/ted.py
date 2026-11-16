"""TED daily packages: where they live, how to fetch them, and how to unpack them into notice rows.

A daily package is `{yyyy}{issue:05d}` (issue = the Official Journal S issue, 1..~250 per year),
served as a tar.gz of one eForms XML file per notice named `{number:08d}_{yyyy}.xml`.
"""

import io
import re
import tarfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Iterator

BASE = "https://ted.europa.eu/packages/daily/"
MEMBER = re.compile(r"(?:^|/)(\d{8})_(\d{4})\.xml$")
NOTICE_TYPES = {"ContractNotice", "ContractAwardNotice", "PriorInformationNotice", "BusinessRegistrationInformationNotice"}


def package_id(year: int, issue: int) -> str:
    if not 1 <= issue <= 99999:
        raise ValueError(f"issue out of range: {issue}")
    return f"{year}{issue:05d}"


def package_url(pid: str) -> str:
    return BASE + pid


def fetch(pid: str, attempts: int = 4, timeout: int = 120) -> bytes | None:
    """Package bytes, or None if TED has not published it (400/404). Retries transient failures."""
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(package_url(pid), timeout=timeout) as r:
                data = r.read()
            validate(data)  # a truncated download raises here and is retried
            return data
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            err = e
        except (urllib.error.URLError, TimeoutError, ConnectionError, tarfile.TarError, EOFError) as e:
            err = e
        if attempt < attempts - 1:
            time.sleep(2 ** attempt * 5)
    raise RuntimeError(f"package {pid}: {err}")


def validate(data: bytes) -> int:
    """Number of notice files in a package; raises if the archive is corrupt or has none."""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        n = sum(1 for m in tar if m.isfile() and MEMBER.search(m.name))
    if n == 0:
        raise tarfile.TarError("package has no notice files")
    return n


def next_issues(year: int, have: set[int], exists, max_misses: int = 2) -> Iterator[int]:
    """Issues of `year` not in `have`, in order, while TED keeps publishing.

    Scans from issue 1 and stops after `max_misses` consecutive unpublished issues past the last one we
    hold, so a single gap is skipped but the scan ends at today's issue. `exists(issue)` answers whether
    TED has it.
    """
    issue, misses, last = 0, 0, max(have, default=0)
    while True:
        issue += 1
        if issue in have:
            continue
        if exists(issue):
            misses = 0
            yield issue
        elif issue > last:
            misses += 1
            if misses >= max_misses:
                return


def root_type(xml: bytes) -> str:
    """Local name of the root element (namespace and prefix stripped)."""
    for _, el in ET.iterparse(io.BytesIO(xml), events=("start",)):
        return el.tag.rsplit("}", 1)[-1].split(":")[-1]
    raise ValueError("empty document")


def notices(data: bytes) -> Iterator[dict]:
    """One dict per notice file: publication_number ('2326-2025'), notice_type, xml (str).

    Files that are not notices are skipped. A notice whose root element can't be read is still returned
    with notice_type=None, so bronze keeps it and an expectation flags it instead of losing it silently;
    full well-formedness is checked when silver parses the document.
    """
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for m in tar:
            match = MEMBER.search(m.name) if m.isfile() else None
            if not match:
                continue
            raw = tar.extractfile(m).read()
            try:
                kind = root_type(raw)
            except (ET.ParseError, ValueError):
                kind = None
            yield {
                "file_name": m.name,
                "publication_number": f"{int(match[1])}-{match[2]}",
                "notice_type": kind,
                "xml": raw.decode("utf-8", errors="replace"),
            }


NOTICE_COLUMNS = ["package_id", "file_name", "publication_number", "notice_type", "xml"]


def explode_packages(batches, chunk: int = 500):
    """mapInPandas body for bronze: packages in, notice rows out, in small frames so memory stays flat
    (a package is ~60 MB of XML once unpacked). Lives here, not in the pipeline file, so Spark can ship
    it to workers by value."""
    import pandas as pd

    for b in batches:
        for path, content in zip(b["path"], b["content"], strict=True):
            pid = path.rsplit("/", 1)[-1].removesuffix(".tar.gz")
            rows = []
            for n in notices(content):
                rows.append({"package_id": pid, **n})
                if len(rows) == chunk:
                    yield pd.DataFrame(rows, columns=NOTICE_COLUMNS)
                    rows = []
            if rows:
                yield pd.DataFrame(rows, columns=NOTICE_COLUMNS)
