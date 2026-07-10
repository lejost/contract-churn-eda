# Churn-Signal Foundations — EDA & Data Interrogation

The exploratory work behind a churn-prediction effort. I didn't train the production models — I did the groundwork that decides whether they can be trusted: choosing the unit of analysis, defining the label, and testing assumptions before anyone built on them. **Python · PySpark · Databricks**, on a large multi-year transactional dataset.

> *Methodology only. Every schema, number, and example is generic and illustrative — no employer, dataset, or business detail is described or inferable. These 6 notebooks distil the techniques from a ~10-notebook analysis into representative, self-contained examples.*

## The core idea

Most churn models fail upstream — on a **mis-defined label or unit of analysis** — not in the modelling. This repo is that upstream part: three questions that quietly break any downstream model if you get them wrong.

**1. What is the unit of analysis?**
Stress-tested a candidate grouping key across the whole dataset (fan-out, regime split, cross-entity leak test). Verdict: safe for the overwhelming majority, with the rare bad cases flagged rather than dropped — measured, not guessed.

**2. What does the label mean?**
"Churn" turned out to have two definitions (coarse vs fine-grained) that *disagree*. A model trained only on the coarse label is structurally blind to the fine-grained signal — a modelling risk that's cheap to catch in EDA and catastrophic to discover after shipping.

**3. Which data is real, and which is a landmine?**
Negatives, placeholder values, missing entries, and apparent duplicates all *looked* like noise. I profiled each before dropping it — and several were signal, not noise. `null ≠ zero`, `anomalous ≠ droppable`.

## Skills shown

- **PySpark / Databricks** at scale — window functions, `countDistinct`, interval-overlap aggregation.
- **Statistical EDA** — percentile-driven summaries, regime bucketing, distribution-shape classification.
- **Applied-ML judgement** — treating unit-of-analysis, label, and data-trust as first-class modelling decisions.
- **Data governance** — anonymisation-first workflow, confidentiality-aware reporting.
- **Intellectual honesty** — an explicit ledger of unverified assumptions, so plausible claims never silently became "facts."

## Repo layout

```
notebooks/
├── 01_anonymisation.py                  privacy-first surrogate keys
├── 02_unit_of_analysis_stress_test.py   validating the grouping key
├── 03_data_quality_investigations.py    "don't drop it, understand it"
├── 04_trajectory.py                     time-aware trend, feature-readiness
├── 05_schema_profiling.py               characterising an unknown table
└── 06_tiered_value_classification.py    separating outliers from errors
```

The notebooks are Python / PySpark, shown on an abstract schema — illustrative of technique, not runnable against any real dataset.
