"""Lakeflow pipeline, silver layer: parse each bronze notice once, then split into typed tables.

silver_parsed holds the parse result per notice (or why it failed); silver_notices / _lots /
_organisations / _awards are typed views of it; silver_quarantine keeps every notice that could not be
parsed, with the reason, so nothing is dropped silently.
"""

from pyspark import cloudpickle
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from tenderlens import eforms

# Workers can't import tenderlens; ship this pure module with the UDF instead (see bronze.py).
cloudpickle.register_pickle_by_value(eforms)

NOTICE = ["notice_id", "version", "procedure_id", "notice_type", "subtype", "form_type", "issue_date",
          "publication_date", "language", "title", "main_cpv", "contract_nature", "procedure_type",
          "estimated_value", "estimated_currency", "awarded_total", "awarded_currency", "changed_notice",
          "change_reason"]
LOT = ["lot_id", "title", "main_cpv", "contract_nature", "estimated_value", "estimated_currency", "nuts",
       "start_date", "end_date", "duration_value", "duration_unit", "max_renewals", "framework",
       "tender_deadline"]
ORG = ["org_ref", "name", "company_id", "country", "nuts", "city", "size", "is_natural_person", "is_buyer"]
AWARD = ["result_id", "lot_id", "result_status", "tenders_received", "tender_id", "tender_value",
         "tender_currency", "rank", "is_winner", "org_ref", "group_lead", "contract_id", "award_date",
         "signed_date"]

# Everything arrives as text and is cast below with try_cast, so one odd value nulls a field instead of
# failing the batch (the expectations then count it).
_struct = lambda fields: ", ".join(f"{f}: STRING" for f in fields)
PARSED_DDL = (f"STRUCT<notice: STRUCT<{_struct(NOTICE)}, buyer_refs: ARRAY<STRING>>, "
              f"lots: ARRAY<STRUCT<{_struct(LOT)}>>, organisations: ARRAY<STRUCT<{_struct(ORG)}>>, "
              f"awards: ARRAY<STRUCT<{_struct(AWARD)}>>>")

OUT = StructType([StructField(n, StringType()) for n in eforms.PARSED_COLUMNS])
MONEY, DATE, INT, BOOL = "DECIMAL(22,2)", "DATE", "INT", "BOOLEAN"
TYPES = {"estimated_value": MONEY, "awarded_total": MONEY, "tender_value": MONEY,
         "issue_date": DATE, "publication_date": DATE, "start_date": DATE, "end_date": DATE,
         "tender_deadline": DATE, "award_date": DATE, "signed_date": DATE,
         "duration_value": INT, "max_renewals": INT, "tenders_received": INT, "rank": INT,
         "is_natural_person": BOOL, "is_buyer": BOOL, "is_winner": BOOL, "group_lead": BOOL}


def typed(prefix: str, fields: list[str]):
    return [F.expr(f"try_cast({prefix}.{f} AS {TYPES[f]})").alias(f) if f in TYPES else F.col(f"{prefix}.{f}").alias(f)
            for f in fields]


@dp.table(name="silver_parsed", comment="Parse result per notice: status ok / unsupported / error.")
@dp.expect_or_fail("status_known", "status IN ('ok', 'unsupported', 'error')")
def silver_parsed():
    bronze = (spark.readStream.option("maxFilesPerTrigger", 4).table("bronze_notices")  # noqa: F821
              .select("publication_number", "package_id", "xml"))
    return (bronze.mapInPandas(eforms.parse_batches, OUT)
            .withColumn("parsed", F.from_json("parsed", PARSED_DDL)))


def _ok():
    return spark.readStream.table("silver_parsed").where("status = 'ok'")  # noqa: F821


@dp.table(name="silver_quarantine", comment="Notices that could not be parsed, and why.")
def silver_quarantine():
    return (spark.readStream.table("silver_parsed").where("status <> 'ok'")  # noqa: F821
            .select("publication_number", "package_id", "status", "error"))


@dp.table(name="silver_notices", comment="One row per notice.")
@dp.expect("has_publication_date", "publication_date IS NOT NULL")
@dp.expect("currency_code", "estimated_currency IS NULL OR length(estimated_currency) = 3")
def silver_notices():
    return _ok().select("publication_number", *typed("parsed.notice", NOTICE),
                        F.col("parsed.notice.buyer_refs").alias("buyer_refs"))


@dp.table(name="silver_lots", comment="One row per lot of a notice.")
@dp.expect("has_lot_id", "lot_id IS NOT NULL")
@dp.expect("dates_ordered", "start_date IS NULL OR end_date IS NULL OR start_date <= end_date")
def silver_lots():
    return (_ok().select("publication_number", F.explode("parsed.lots").alias("l"))
            .select("publication_number", *typed("l", LOT)))


@dp.table(name="silver_organisations", comment="Organisations named in a notice (buyers, bidders, review bodies).")
@dp.expect("person_has_no_identity", "NOT is_natural_person OR (name IS NULL AND company_id IS NULL)")
def silver_organisations():
    return (_ok().select("publication_number", F.explode("parsed.organisations").alias("o"))
            .select("publication_number", *typed("o", ORG)))


@dp.table(name="silver_awards", comment="One row per tender × tenderer in a lot result; is_winner marks awards.")
@dp.expect("winner_has_org", "NOT is_winner OR org_ref IS NOT NULL")
@dp.expect("value_has_currency", "tender_value IS NULL OR tender_currency IS NOT NULL")
def silver_awards():
    return (_ok().select("publication_number", F.explode("parsed.awards").alias("a"))
            .select("publication_number", *typed("a", AWARD)))
