"""
01 — Anonymisation-first workflow
=================================

Goal: replace direct identifiers with stable surrogate keys *before* any
analysis, so the relational structure survives but re-identification is
impossible.

Technique: dense_rank() over an identifier column gives a compact,
deterministic integer label — the same input always maps to the same
surrogate, which is what lets you still join and group correctly.

Doing this first is a governance decision, not a formatting one. Every later
step operates on surrogate keys, so no artefact can leak an identity.

(Illustrative schema. No real data.)
"""

from pyspark.sql import functions as F
from pyspark.sql.window import Window

id_cols = ["entity_name", "entity_id", "parent_id"]  # generic placeholders

df = spark.table("records")


def anonymise(df, col):
    """Map an identifier column to a deterministic surrogate integer."""
    w = Window.orderBy(F.col(f"`{col}`"))
    return df.withColumn(f"{col}__anon", F.dense_rank().over(w))


for c in id_cols:
    df = anonymise(df, c)

df = df.drop(*id_cols)  # keep only anonymised versions downstream
