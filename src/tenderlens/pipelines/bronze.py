"""Lakeflow pipeline, bronze layer: one row per notice XML, read incrementally from the raw volume."""

from pyspark import cloudpickle
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from tenderlens import ted

# Workers can't import tenderlens; ship this pure module with the UDF instead. (Functions defined in this
# pipeline file can't be shipped: the runtime loads it through internal modules workers don't have.)
cloudpickle.register_pickle_by_value(ted)

SCHEMA = StructType([StructField(n, StringType()) for n in ted.NOTICE_COLUMNS])


@dp.table(name="bronze_notices", comment="Raw eForms notice XML from TED daily packages, one row per notice.")
@dp.expect_or_fail("has_publication_number", "publication_number IS NOT NULL")
@dp.expect("known_notice_type", f"notice_type IN ({', '.join(repr(t) for t in sorted(ted.NOTICE_TYPES))})")
def bronze_notices():
    raw = (spark.readStream.format("cloudFiles")  # noqa: F821 (spark is injected by the pipeline runtime)
           .option("cloudFiles.format", "binaryFile")
           .option("pathGlobFilter", "*.tar.gz")
           .option("cloudFiles.maxFilesPerTrigger", 8)  # small micro-batches: bounded memory, committed progress
           .load(spark.conf.get("tenderlens.raw_path")))  # noqa: F821
    return (raw.select("path", "content").mapInPandas(ted.explode_packages, SCHEMA)
            .withColumn("ingested_at", F.current_timestamp()))
