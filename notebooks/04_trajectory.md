# 04 — Trajectory over time (feature-readiness)

**Goal:** answer "is this entity's engagement growing or shrinking over time?" — the trajectory that per-entity features derive from.

### Interval-overlap aggregation (not naive sum)

Records have overlapping and expired time windows. To get the *active* total at a moment `T`, sum only the records whose window contains `T`:

```python
from pyspark.sql import functions as F

def active_total_at(df, T):
    return (
        df.filter((F.col("start_date") <= F.lit(T)) &
                  (F.col("end_date")   >= F.lit(T)))
          .groupBy("`entity_id`", "`item_id`")
          .agg(F.sum("value").alias("active_value"))
          .withColumn("as_of", F.lit(T))
    )
```

Naive `sum(value)` over all records double-counts expired ones — the interval filter is what makes the number mean "active right now."

### Event-based grid vs calendar grid (the check that mattered)

The evaluation dates are themselves a modelling choice:

- **Calendar grid** — fixed period-ends. External, uniform.
- **Event-based grid** — each entity's own start/end dates. Internal to its actual lifeline.

```python
events = (
    df.select("`entity_id`", "`item_id`", F.col("start_date").alias("evt")).distinct()
      .union(
          df.select("`entity_id`", "`item_id`", F.col("end_date").alias("evt")).distinct()
      )
)
```

**Finding (illustrative):** the two grids gave materially different distributions. An artefact bucket produced by the calendar grid collapsed under the event grid, and the reducing/expanding shares shifted by several points. **The event-based grid became canonical**; the calendar version was kept only for traceability.

### Trajectory classification

```python
traj = (
    active_series
    .withColumn("first_v", F.first("active_value").over(w))
    .withColumn("last_v",  F.last("active_value").over(w))
    .withColumn("ratio",   F.col("last_v") / F.col("first_v"))
    .withColumn(
        "trend",
        F.when(F.col("n_events") == 1, "single_point")
         .when(F.col("ratio") < 1, "reducing")
         .when(F.col("ratio") > 1, "expanding")
         .otherwise("flat"),
    )
)
```

Rolled up per entity (all-flat / net-reducing / net-expanding / mixed), this feeds the churn features directly: slope, count of reducing items, and the divergence between coarse and fine-grained churn.
