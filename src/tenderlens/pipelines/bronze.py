"""Lakeflow pipeline, bronze layer: one row per notice XML, read incrementally from the raw volume."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from tenderlens import ted

SCHEMA = StructType([StructField(n, StringType()) for n in
                     ("package_id", "file_name", "publication_number", "notice_type", "xml")])


def explode(batches, chunk: int = 500):
    """Unpack packages into notice rows, yielding small frames so memory stays flat (a package is ~60 MB
    of XML once unpacked)."""
    import pandas as pd

    for b in batches:
        for path, content in zip(b["path"], b["content"], strict=True):
            pid = path.rsplit("/", 1)[-1].removesuffix(".tar.gz")
            rows = []
            for n in ted.notices(content):
                rows.append({"package_id": pid, **n})
                if len(rows) == chunk:
                    yield pd.DataFrame(rows, columns=SCHEMA.fieldNames())
                    rows = []
            if rows:
                yield pd.DataFrame(rows, columns=SCHEMA.fieldNames())


@dp.table(name="bronze_notices", comment="Raw eForms notice XML from TED daily packages, one row per notice.")
@dp.expect_or_fail("has_publication_number", "publication_number IS NOT NULL")
@dp.expect("known_notice_type", f"notice_type IN ({', '.join(repr(t) for t in sorted(ted.NOTICE_TYPES))})")
def bronze_notices():
    raw = (spark.readStream.format("cloudFiles")  # noqa: F821 (spark is injected by the pipeline runtime)
           .option("cloudFiles.format", "binaryFile")
           .option("pathGlobFilter", "*.tar.gz")
           .option("cloudFiles.maxFilesPerTrigger", 8)  # small micro-batches: bounded memory, committed progress
           .load(spark.conf.get("tenderlens.raw_path")))  # noqa: F821
    return (raw.select("path", "content").mapInPandas(explode, SCHEMA)
            .withColumn("ingested_at", F.current_timestamp()))
