"""
05 — Schema profiling of an unknown table
==========================================

Goal: before any modelling question, characterise a table you've been handed —
size, cardinality, null structure, and how granular the "natural key" is.
This is the first pass that tells you what you're even working with.

The instinct: never trust a column's meaning from its name. Measure its
cardinality and null rate, and confirm what combination of columns is actually
unique at the row level.

(Illustrative schema. No real data.)
"""

from pyspark.sql import functions as F

df = spark.table("records")

# === Size and grain =======================================================
n_rows = df.count()
print(f"Rows: {n_rows:,}")

# === Per-column null rate + cardinality ===================================
# One pass over the frame: for every column, how populated is it and how many
# distinct values does it carry? High-cardinality + low-null = candidate key;
# low-cardinality = candidate categorical feature.
profile = df.select(
    *[
        F.round(F.avg(F.col(f"`{c}`").isNull().cast("int")) * 100, 2).alias(f"{c}__null_pct")
        for c in df.columns
    ],
    *[
        F.countDistinct(F.col(f"`{c}`")).alias(f"{c}__ndistinct")
        for c in df.columns
    ],
)
profile.show(vertical=True, truncate=False)

# === Confirm the natural row-level key ====================================
# A "key" is only a key if it's actually unique. Test the candidate before
# building anything on top of it.
candidate_key = ["group_key", "item_id"]
n_key_combos = df.select(*candidate_key).distinct().count()
print(f"Distinct {candidate_key} combos: {n_key_combos:,}")
print(f"Unique at row level: {n_key_combos == n_rows}")

# === Cardinality of the entities we care about ============================
entity_cols = ["entity_id", "group_key", "item_id"]
df.agg(
    *[F.countDistinct(F.col(f"`{c}`")).alias(c) for c in entity_cols]
).show()
