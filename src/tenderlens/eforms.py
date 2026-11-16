"""Parse one eForms notice (UBL XML) into flat records: notice, lots, organisations, awards.

eForms spreads one award across several linked parts: a LotResult (per lot) points at LotTenders and
SettledContracts; a LotTender points at a TenderingParty; a TenderingParty lists Tenderers, which are
Organisation ids. `parse` resolves those links so each award row says which organisation won which
lot, for how much, and when.

Privacy: contact people, e-mails, phone numbers and ultimate beneficial owners are never read. An
organisation flagged as a natural person (e.g. a sole trader, whose Swedish "org number" is a personal
identity number) keeps only its country and size.
"""

import json
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "efac": "http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1",
    "efbc": "http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1",
    "efext": "http://data.europa.eu/p27/eforms-ubl-extensions/1",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}
EXT = "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension"
SUPPORTED = {"ContractNotice", "ContractAwardNotice", "PriorInformationNotice"}


class Unsupported(ValueError):
    """Not an eForms notice we model (legacy TED schema, business registration notices)."""


def _text(el, path):
    found = el.find(path, NS) if el is not None else None
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


def _all(el, path):
    return [t for f in el.findall(path, NS) if f.text and (t := f.text.strip())] if el is not None else []


PLACEHOLDER_DATE = "2000-01-01"  # some senders fill required dates with this instead of a real one


def _date(value):
    """'2024-11-12Z' / '2025-01-02+01:00' → '2024-11-12'; not a date, or the placeholder → None."""
    if not value or len(value) < 10 or value[4] != "-" or value[7] != "-":
        return None
    day = value[:10]
    ok = day[:4].isdigit() and day[5:7].isdigit() and day[8:10].isdigit()
    return day if ok and day != PLACEHOLDER_DATE else None


def _amount(el, path):
    """(amount as a decimal string, currency) or (None, None). Strings, so Spark casts without float error."""
    found = el.find(path, NS) if el is not None else None
    if found is None or not found.text:
        return None, None
    try:
        value = Decimal(found.text.strip())
    except InvalidOperation:
        return None, None
    if not value.is_finite() or value < 0:
        return None, None
    return str(value), found.get("currencyID")


def _localised(el, path, lang):
    """Text in the notice language if there are several translations, else the first."""
    options = el.findall(path, NS) if el is not None else []
    for o in options:
        if o.get("languageID") == lang and o.text and o.text.strip():
            return o.text.strip()
    return next((o.text.strip() for o in options if o.text and o.text.strip()), None)


def _code(el, path, list_name):
    for f in el.findall(path, NS) if el is not None else []:
        if f.get("listName") == list_name and f.text:
            return f.text.strip()
    return None


def _bool(value):
    return {"true": True, "false": False, "1": True, "0": False}.get((value or "").lower())


def _organisations(ext, buyers):
    rows = []
    for org in ext.findall("efac:Organizations/efac:Organization", NS):
        company = org.find("efac:Company", NS)
        ref = _text(company, "cac:PartyIdentification/cbc:ID")
        if ref is None:
            continue
        person = _bool(_text(org, "efbc:NaturalPersonIndicator")) is True
        rows.append({
            "org_ref": ref,
            "name": None if person else _text(company, "cac:PartyName/cbc:Name"),
            "company_id": None if person else _text(company, "cac:PartyLegalEntity/cbc:CompanyID"),
            "country": _text(company, "cac:PostalAddress/cac:Country/cbc:IdentificationCode"),
            "nuts": _text(company, "cac:PostalAddress/cbc:CountrySubentityCode"),
            "city": None if person else _text(company, "cac:PostalAddress/cbc:CityName"),
            "size": _text(company, "efbc:CompanySizeCode"),
            "is_natural_person": person,
            "is_buyer": ref in buyers,
        })
    return rows


def _lots(root, lang):
    rows = []
    for lot in root.findall("cac:ProcurementProjectLot", NS):
        lot_id = _text(lot, "cbc:ID")
        project = lot.find("cac:ProcurementProject", NS)
        period = project.find("cac:PlannedPeriod", NS) if project is not None else None
        duration = period.find("cbc:DurationMeasure", NS) if period is not None else None
        value, currency = _amount(project, "cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount")
        process = lot.find("cac:TenderingProcess", NS)
        rows.append({
            "lot_id": lot_id,
            "title": _localised(project, "cbc:Name", lang),
            "main_cpv": _text(project, "cac:MainCommodityClassification/cbc:ItemClassificationCode"),
            "contract_nature": _text(project, "cbc:ProcurementTypeCode"),
            "estimated_value": value,
            "estimated_currency": currency,
            "nuts": _text(project, "cac:RealizedLocation/cac:Address/cbc:CountrySubentityCode"),
            "start_date": _date(_text(period, "cbc:StartDate")),
            "end_date": _date(_text(period, "cbc:EndDate")),
            "duration_value": duration.text.strip() if duration is not None and duration.text else None,
            "duration_unit": duration.get("unitCode") if duration is not None else None,
            "max_renewals": _text(project, "cac:ContractExtension/cbc:MaximumNumberNumeric"),
            "framework": _code(process, "cac:ContractingSystem/cbc:ContractingSystemTypeCode",
                               "framework-agreement"),
            "tender_deadline": _date(_text(process, "cac:TenderSubmissionDeadlinePeriod/cbc:EndDate")),
        })
    return rows


def _awards(root, ext):
    result = ext.find("efac:NoticeResult", NS)
    if result is None:
        return []
    tenders = {_text(t, "cbc:ID"): t for t in result.findall("efac:LotTender", NS)}
    parties = {_text(p, "cbc:ID"): p for p in result.findall("efac:TenderingParty", NS)}
    contracts = {_text(c, "cbc:ID"): c for c in result.findall("efac:SettledContract", NS)}
    contract_of = {_text(t, "cbc:ID"): cid for cid, c in contracts.items()
                   for t in c.findall("efac:LotTender", NS)}
    notice_award_date = _date(_text(root, "cac:TenderResult/cbc:AwardDate"))

    rows = []
    for lr in result.findall("efac:LotResult", NS):
        lot_id = _text(lr, "efac:TenderLot/cbc:ID")
        status = _text(lr, "cbc:TenderResultCode")
        received = None
        for stat in lr.findall("efac:ReceivedSubmissionsStatistics", NS):
            if _text(stat, "efbc:StatisticsCode") == "tenders":
                received = _text(stat, "efbc:StatisticsNumeric")
        for tender_id in _all(lr, "efac:LotTender/cbc:ID"):
            tender = tenders.get(tender_id)
            contract_id = contract_of.get(tender_id)
            contract = contracts.get(contract_id)
            value, currency = _amount(tender, "cac:LegalMonetaryTotal/cbc:PayableAmount")
            party = parties.get(_text(tender, "efac:TenderingParty/cbc:ID"))
            tenderers = party.findall("efac:Tenderer", NS) if party is not None else []
            winner = contract_id is not None and status == "selec-w"
            for tenderer in tenderers or [None]:
                rows.append({
                    "result_id": _text(lr, "cbc:ID"),
                    "lot_id": lot_id,
                    "result_status": status,
                    "tenders_received": received,
                    "tender_id": tender_id,
                    "tender_value": value,
                    "tender_currency": currency,
                    "rank": _text(tender, "cbc:RankCode"),
                    "is_winner": winner,
                    "org_ref": _text(tenderer, "cbc:ID"),
                    "group_lead": _bool(_text(tenderer, "efbc:GroupLeadIndicator")),
                    "contract_id": contract_id,
                    "award_date": (_date(_text(contract, "cbc:AwardDate")) or notice_award_date) if winner else None,
                    "signed_date": _date(_text(contract, "cbc:IssueDate")) if winner else None,
                })
    return rows


def parse(xml: str) -> dict:
    """Records for one notice. Raises Unsupported for notice kinds we don't model, ET.ParseError for
    broken XML, ValueError if a required field is missing."""
    root = ET.fromstring(xml)
    kind = root.tag.rsplit("}", 1)[-1]
    if kind not in SUPPORTED or not root.tag.startswith("{urn:oasis:names:specification:ubl:schema:xsd:"):
        raise Unsupported(kind)
    ext = root.find(EXT, NS)
    if ext is None:
        raise ValueError("no eForms extension")
    lang = _text(root, "cbc:NoticeLanguageCode")
    project = root.find("cac:ProcurementProject", NS)
    buyers = set(_all(root, "cac:ContractingParty/cac:Party/cac:PartyIdentification/cbc:ID"))
    total, total_currency = _amount(ext, "efac:NoticeResult/cbc:TotalAmount")
    estimated, estimated_currency = _amount(project, "cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount")
    notice = {
        "notice_id": _text(root, "cbc:ID"),
        "version": _text(root, "cbc:VersionID"),
        "procedure_id": _text(root, "cbc:ContractFolderID"),
        "notice_type": kind,
        "subtype": _text(ext, "efac:NoticeSubType/cbc:SubTypeCode"),
        "form_type": _text(root, "cbc:NoticeTypeCode"),
        "issue_date": _date(_text(root, "cbc:IssueDate")),
        "publication_date": _date(_text(ext, "efac:Publication/efbc:PublicationDate")),
        "language": lang,
        "title": _localised(project, "cbc:Name", lang),
        "main_cpv": _text(project, "cac:MainCommodityClassification/cbc:ItemClassificationCode"),
        "contract_nature": _text(project, "cbc:ProcurementTypeCode"),
        "procedure_type": _text(root, "cac:TenderingProcess/cbc:ProcedureCode"),
        "estimated_value": estimated,
        "estimated_currency": estimated_currency,
        "awarded_total": total,
        "awarded_currency": total_currency,
        "buyer_refs": sorted(buyers),
        "changed_notice": _text(ext, "efac:Changes/efbc:ChangedNoticeIdentifier"),
        "change_reason": _text(ext, "efac:Changes/efac:ChangeReason/cbc:ReasonCode"),
    }
    if not notice["notice_id"]:  # procedure_id is legitimately absent on planning-only notices
        raise ValueError("missing notice id")
    return {
        "notice": notice,
        "lots": _lots(root, lang),
        "organisations": _organisations(ext, buyers),
        "awards": _awards(root, ext),
    }


PARSED_COLUMNS = ["publication_number", "package_id", "status", "error", "parsed"]


def parse_batches(batches, chunk: int = 500):
    """mapInPandas body for silver: one row per notice with status ok / unsupported / error and the
    parse result as JSON. Lives here, not in the pipeline file, so Spark can ship it to workers by value."""
    import pandas as pd

    rows = []
    for b in batches:
        for pub, pkg, xml in zip(b["publication_number"], b["package_id"], b["xml"], strict=True):
            row = {"publication_number": pub, "package_id": pkg, "status": "ok", "error": None, "parsed": None}
            try:
                row["parsed"] = json.dumps(parse(xml), ensure_ascii=False)
            except Unsupported as e:
                row.update(status="unsupported", error=f"notice kind {e}")
            except Exception as e:  # noqa: BLE001 (any parse failure is quarantined with its reason)
                row.update(status="error", error=f"{type(e).__name__}: {e}"[:500])
            rows.append(row)
            if len(rows) == chunk:
                yield pd.DataFrame(rows, columns=PARSED_COLUMNS)
                rows = []
    if rows:
        yield pd.DataFrame(rows, columns=PARSED_COLUMNS)
