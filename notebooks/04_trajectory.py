"""
04 — Trajectory over time (feature-readiness)
=============================================

Goal: answer "is this entity's engagement growing or shrinking over time?" —
the trajectory that per-entity features derive from.

Naive sum(value) over all records double-counts expired ones; the interval
filter is what makes the number mean "active right now".

The evaluation grid is itself a modelling decision — validated below rather
than trusted at first result.

(Illustrative schema. No real data.)
"""

from pyspark.sql import functions as F

df = spark.table("records")


# === Interval-overlap aggregation (not naive sum) =========================
def active_total_at(df, T):
    """Sum only the records whose time window contains T."""
    return (
        df.filter((F.col("start_date") <= F.lit(T)) &
                  (F.col("end_date") >= F.lit(T)))
          .groupBy("`entity_id`", "`item_id`")
          .agg(F.sum("value").alias("active_value"))
          .withColumn("as_of", F.lit(T))
    )


# === Event-based grid vs calendar grid (the check that mattered) ==========
# Calendar grid = fixed period-ends (external, uniform).
# Event grid = each entity's own start/end dates (internal to its lifeline).
events = (
    df.select("`entity_id`", "`item_id`", F.col("start_date").alias("evt")).distinct()
      .union(
          df.select("`entity_id`", "`item_id`", F.col("end_date").alias("evt")).distinct()
      )
)
# Finding: the two grids gave materially different distributions. An artefact
# bucket produced by the calendar grid collapsed under the event grid,
# shifting reducing/expanding shares by several points. Event grid is
# canonical; calendar kept only for traceability.

# === Trajectory classification ============================================
traj = (
    active_series
    .withColumn("first_v", F.first("active_value").over(w))
    .withColumn("last_v", F.last("active_value").over(w))
    .withColumn("ratio", F.col("last_v") / F.col("first_v"))
    .withColumn(
        "trend",
        F.when(F.col("n_events") == 1, "single_point")
         .when(F.col("ratio") < 1, "reducing")
         .when(F.col("ratio") > 1, "expanding")
         .otherwise("flat"),
    )
)
# Rolled up per entity (all-flat / net-reducing / net-expanding / mixed), this
# feeds churn features: slope, count of reducing items, and the divergence
# between coarse and fine-grained churn.
