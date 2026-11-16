import json
from pathlib import Path

import pandas as pd

from tenderlens import eforms, ted
from tenderlens.pipelines import silver

FIX = Path(__file__).parent / "fixtures"


def test_bronze_explode_yields_small_chunks():
    data = (FIX / "20250103_2025002.tar.gz").read_bytes()
    frames = list(ted.explode_packages([pd.DataFrame({"path": ["dbfs:/v/202500002.tar.gz"], "content": [data]})], chunk=1))
    assert len(frames) == 2 and all(len(f) == 1 for f in frames)
    assert set(pd.concat(frames).package_id) == {"202500002"}


def test_silver_parse_batches_sorts_ok_unsupported_and_error():
    xml = (FIX / "00002326_2025.xml").read_text(encoding="utf-8")
    batch = pd.DataFrame({"publication_number": ["2326-2025", "1-2024", "2-2024"], "package_id": ["p"] * 3,
                          "xml": [xml, "<TED_EXPORT/>", "<ContractNotice><broken>"]})
    out = pd.concat(list(eforms.parse_batches([batch], chunk=2)))
    assert list(out.status) == ["ok", "unsupported", "error"]
    assert json.loads(out.parsed.iloc[0])["notice"]["title"] == "Webbaserad upplysningsdatabastjänst"
    assert out.error.iloc[1] == "notice kind TED_EXPORT" and out.error.iloc[2].startswith("ParseError")


def test_silver_schema_covers_every_parsed_field():
    r = eforms.parse((FIX / "00002326_2025.xml").read_text(encoding="utf-8"))
    assert set(r["notice"]) == set(silver.NOTICE) | {"buyer_refs"}
    assert set(r["lots"][0]) == set(silver.LOT)
    assert set(r["organisations"][0]) == set(silver.ORG)
    assert set(r["awards"][0]) == set(silver.AWARD)
