import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tenderlens import eforms

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return eforms.parse((FIX / name).read_text(encoding="utf-8"))


def test_award_notice_links_lots_tenders_and_winners():
    r = load("00002326_2025.xml")
    n = r["notice"]
    assert n["notice_type"] == "ContractAwardNotice"
    assert (n["language"], n["title"], n["main_cpv"]) == ("SWE", "Webbaserad upplysningsdatabastjänst", "72300000")
    assert (n["estimated_value"], n["estimated_currency"]) == ("14000000", "SEK")
    assert n["publication_date"] == "2025-01-03"

    orgs = {o["org_ref"]: o for o in r["organisations"]}
    winners = {(a["lot_id"], orgs[a["org_ref"]]["company_id"]) for a in r["awards"] if a["is_winner"]}
    assert ("LOT-0001", "5567968473") in winners  # Bureau van Dijk won lot 1
    assert ("LOT-0001", "5564363421") not in winners  # Dun & Bradstreet bid on it and lost
    assert all(orgs[ref]["is_buyer"] for ref in n["buyer_refs"])


def test_dates_only_on_winners_and_placeholder_dropped():
    r = load("00002326_2025.xml")
    losers = [a for a in r["awards"] if not a["is_winner"]]
    assert losers and all(a["award_date"] is None for a in losers)
    assert {a["award_date"] for a in r["awards"] if a["is_winner"]} <= {"2024-11-12", None}
    assert eforms._date("2000-01-01Z") is None
    assert eforms._date("2025-01-02+01:00") == "2025-01-02"
    assert eforms._date("tomorrow") is None


def test_contract_notice_lot_fields():
    r = load("00003632_2025.xml")
    assert r["notice"]["notice_type"] == "ContractNotice" and r["awards"] == []
    lot = r["lots"][0]
    assert lot["tender_deadline"] == "2025-02-03"
    assert (lot["estimated_value"], lot["estimated_currency"]) == ("55000000", "SEK")
    assert lot["contract_nature"] == "supplies"


def test_planning_notice_has_no_procedure_id():
    r = load("00001777_2025.xml")
    assert r["notice"]["notice_type"] == "PriorInformationNotice"
    assert r["notice"]["procedure_id"] is None


def _with_natural_person(xml: str) -> str:
    return xml.replace("<efac:Company>", "<efbc:NaturalPersonIndicator>true</efbc:NaturalPersonIndicator>"
                       "<efac:Company>", 1)


def test_natural_person_keeps_no_identity():
    r = eforms.parse(_with_natural_person((FIX / "00002326_2025.xml").read_text(encoding="utf-8")))
    person = next(o for o in r["organisations"] if o["is_natural_person"])
    assert person["name"] is None and person["company_id"] is None and person["city"] is None
    assert person["country"] == "SWE"


def test_amounts_are_exact_and_rejected_when_bad():
    el = ET.fromstring(f'<x xmlns:cbc="{eforms.NS["cbc"]}"><cbc:A currencyID="EUR">1234567.89</cbc:A>'
                       '<cbc:B currencyID="EUR">-5</cbc:B><cbc:C>n/a</cbc:C></x>')
    assert eforms._amount(el, "cbc:A") == ("1234567.89", "EUR")
    assert eforms._amount(el, "cbc:B") == (None, None)
    assert eforms._amount(el, "cbc:C") == (None, None)


def test_unsupported_and_broken():
    with pytest.raises(eforms.Unsupported):
        eforms.parse("<TED_EXPORT/>")
    with pytest.raises(ET.ParseError):
        eforms.parse("<ContractNotice><unclosed>")
