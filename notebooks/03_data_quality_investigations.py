"""
03 — Data-quality investigations: "don't drop it, understand it"
================================================================

Four things looked like droppable noise. Each was profiled *before* removal.
The discipline: look at the records you're about to delete, because
`null != zero` and `anomalous != droppable`.

(Illustrative schema. No real data.)
"""

from pyspark.sql import functions as F

df = spark.table("records")

# === A. Negative values — a real decline, or an artefact? ==================
neg = df.filter(F.col("value") < 0)

# Profile the categorical fields across the WHOLE negative population, not one
# slice — a single slice is how you reach a wrong conclusion.
for c in ["type_field", "status_field"]:
    neg.groupBy(f"`{c}`").count().orderBy(F.desc("count")).show(truncate=False)
# Finding: negatives concentrate on an accounting pattern that nets out — not
# a genuine decline. A naive sum(value) would manufacture a fake signal.
# Prefer netting the matched pair, or "max value ever held".

# === B. Placeholder / sentinel values =====================================
# A far-future sentinel date marks "open-ended". Detect it as an outlier
# relative to the real data, then null the DERIVED field for those rows —
# otherwise an absurd outlier destroys every percentile.
SENTINEL = far_future_marker  # the placeholder year used by the source
df = df.withColumn(
    "duration",
    F.when(F.year("end_date") >= SENTINEL, None)
     .otherwise(F.round(F.months_between("end_date", "start_date"), 1)),
)

# === C. Missing values — genuinely missing, or hiding in a related column? =
null_val = df.filter(F.col("value").isNull())

# Hypothesis: the value lives in a related column when the main one is null.
# Test it before trusting it.
null_val.select(
    F.avg(F.col("related_col").isNotNull().cast("int")).alias("related_populated_rate")
).show()
# Finding: not populated when value is null -> no rescue. Keep + flag.
df = df.withColumn("is_null_value", F.col("value").isNull())

# === D. "Duplicates" — a phantom from the wrong key =======================
# Apparent duplicates appear only when comparing a subset of columns.
# On the TRUE record-level key, check for exact duplicates.
record_key = ["group_key", "item_id"]
print("Exact duplicates:", df.count() - df.dropDuplicates(record_key).count())
# Illustrative: 0. The right key dissolved the phantom.
