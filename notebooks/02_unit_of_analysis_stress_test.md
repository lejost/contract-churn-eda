# 02 — Stress-testing the unit-of-analysis key

**Goal:** decide whether a candidate grouping key is safe to use as the unit of analysis, or whether it fragments / leaks. Measure where it breaks instead of picking on intuition.

Generic schema: each record has an `entity_id`, a candidate `group_key`, a finer `item_id`, and a `value`.

### Signal 1 — fan-out: how many items sit under one key?

```python
from pyspark.sql import functions as F

fanout = (
    df.filter(F.col("`group_key`").isNotNull())
      .groupBy("`group_key`")
      .agg(F.countDistinct("`item_id`").alias("n_items"))
)

fanout.selectExpr(
    "percentile(n_items, 0.5)  as p50",
    "percentile(n_items, 0.9)  as p90",
    "percentile(n_items, 0.99) as p99",
    "max(n_items) as max_items",
).show()
# Illustrative: median 1, long right tail.
```

### Signal 2 — regime split: does the key group, match, or fragment?

```python
per_entity = (
    df.groupBy("`entity_id`")
      .agg(
          F.countDistinct("`group_key`").alias("n_keys"),
          F.countDistinct("`item_id`").alias("n_items"),
      )
      .withColumn(
          "regime",
          F.when(F.col("n_keys") <  F.col("n_items"), "groups")
           .when(F.col("n_keys") == F.col("n_items"), "matches_1to1")
           .otherwise("fragments"),
      )
)

per_entity.groupBy("regime").count().orderBy(F.desc("count")).show()
# Illustrative: large majority in safe regimes; small fragment tail.
```

### Signal 3 — hard reject: does one key span entities it shouldn't?

```python
leaky = (
    df.groupBy("`group_key`")
      .agg(F.countDistinct("`entity_id`").alias("n_entities"))
      .filter(F.col("n_entities") > 1)
)
print("Keys spanning >1 entity:", leaky.count())   # illustrative: negligible

# Flag-and-keep rather than discard the key.
df = (
    df.join(leaky.select("`group_key`").withColumn("is_leaky_key", F.lit(True)),
            on="group_key", how="left")
      .fillna({"is_leaky_key": False})
)
```

**Decision:** the key is usable for the overwhelming majority; rare leaky cases carry a flag so each downstream feature decides whether to exclude them. Measured, not guessed.
