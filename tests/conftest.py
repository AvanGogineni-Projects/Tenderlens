"""Let the pipeline modules import without Spark: their pure functions are tested here, the Spark
wiring runs on Databricks."""
import sys
import types


class _Field:
    def __init__(self, name, *_):
        self.name = name


class _Struct:
    def __init__(self, fields):
        self.fields = fields

    def fieldNames(self):
        return [f.name for f in self.fields]


def _passthrough(*_a, **_k):
    return lambda f: f


if "pyspark" not in sys.modules:
    mods = {m: types.ModuleType(m) for m in
            ("pyspark", "pyspark.cloudpickle", "pyspark.pipelines", "pyspark.sql", "pyspark.sql.functions", "pyspark.sql.types")}
    dp = mods["pyspark.pipelines"]
    dp.table = dp.expect = dp.expect_or_fail = _passthrough
    mods["pyspark"].pipelines = dp
    mods["pyspark"].cloudpickle = mods["pyspark.cloudpickle"]
    mods["pyspark.cloudpickle"].register_pickle_by_value = lambda _m: None
    mods["pyspark.sql"].functions = mods["pyspark.sql.functions"]
    t = mods["pyspark.sql.types"]
    t.StringType, t.StructField, t.StructType = (lambda: None), _Field, _Struct
    sys.modules.update(mods)
