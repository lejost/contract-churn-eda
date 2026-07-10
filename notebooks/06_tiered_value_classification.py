"""
06 — Tiered value classification
=================================

Goal: a raw field mixed several kinds of value together — normal entries,
placeholder/sentinel markers, obvious data-entry errors, and rare-but-real
extremes. Averaging over that mixture is meaningless. The fix is to classify
each value into a tier first, then compute statistics only where they make
sense.

The instinct: an "outlier" is not automatically an error. Separate genuine
extremes (keep, they carry signal) from placeholders and typos (exclude from
derived statistics but keep the row).

(Illustrative schema. No real data.)
"""

from pyspark.sql import functions as F

df = spark.table("records")

# === Assign each row to a tier ============================================
# Tiers, from a raw date-like field:
#   sentinel  — placeholder far-future marker ("open-ended")
#   typo      — implausible values from data-entry error
#   long_term — rare but genuine multi-decade extremes (keep!)
#   normal    — everyday values
df = df.withColumn(
    "tier",
    F.when(F.year("end_date") >= SENTINEL_YEAR, "sentinel")
     .when(F.year("end_date") > TYPO_THRESHOLD, "typo")
     .when(F.year("end_date") > LONG_TERM_THRESHOLD, "long_term")
     .otherwise("normal"),
)

# === Tier breakdown =======================================================
total = df.count()
(
    df.groupBy("tier")
      .agg(F.count("*").alias("n_rows"))
      .withColumn("pct", F.round(F.col("n_rows") * 100.0 / total, 2))
      .orderBy(F.desc("n_rows"))
      .show()
)

# === Derive the stat only where it's meaningful ===========================
# Compute duration for the tiers where it has meaning (normal + long_term).
# Sentinels and typos get NULL so they don't poison percentiles.
df = df.withColumn(
    "duration",
    F.when(
        F.col("tier").isin("normal", "long_term"),
        F.round(F.months_between("end_date", "start_date"), 1),
    ).otherwise(None),
)

df.select(
    F.expr("percentile(duration, 0.5)").alias("median"),
    F.expr("percentile(duration, 0.95)").alias("p95"),
    F.max("duration").alias("max_real"),
).show()
