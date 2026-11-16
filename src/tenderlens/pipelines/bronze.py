"""Lakeflow pipeline, bronze layer: one row per notice XML, read incrementally from the raw volume."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from tenderlens import ted

SCHEMA = StructType([StructField(n, StringType()) for n in
                     ("package_id", "file_name", "publication_number", "notice_type", "xml")])


def explode(batches):
    import pandas as pd

    for b in batches:
        rows = [{"package_id": path.rsplit("/", 1)[-1].removesuffix(".tar.gz"), **n}
                for path, content in zip(b["path"], b["content"], strict=True)
                for n in ted.notices(content)]
        yield pd.DataFrame(rows, columns=SCHEMA.fieldNames())


@dp.table(name="bronze_notices", comment="Raw eForms notice XML from TED daily packages, one row per notice.")
@dp.expect_or_fail("has_publication_number", "publication_number IS NOT NULL")
@dp.expect("known_notice_type", f"notice_type IN ({', '.join(repr(t) for t in sorted(ted.NOTICE_TYPES))})")
def bronze_notices():
    raw = (spark.readStream.format("cloudFiles")  # noqa: F821 (spark is injected by the pipeline runtime)
           .option("cloudFiles.format", "binaryFile")
           .option("pathGlobFilter", "*.tar.gz")
           .load(spark.conf.get("tenderlens.raw_path")))  # noqa: F821
    return (raw.select("path", "content").mapInPandas(explode, SCHEMA)
            .withColumn("ingested_at", F.current_timestamp()))
