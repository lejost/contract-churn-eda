# Churn-Signal Foundations — EDA & Data Interrogation

> **What this is:** an analytical case study of the exploratory work behind a customer-churn / retention initiative. I didn't train the production models — I did the groundwork that decides whether those models can be trusted: choosing the unit of analysis, validating the fields that define the label, and testing the assumptions before anyone built on them.
>
> **On the data:** methodology only. Every schema, number, and example here is generic and illustrative. No employer, dataset, or business detail is described or inferable.

---

## TL;DR for a busy reviewer

I led the exploratory-data-analysis phase of a churn-prediction effort on a large transactional dataset (hundreds of thousands of records, multi-year) in **Databricks / PySpark**.

The core problem was not "build a model." It was: **before you can predict churn, you have to answer three questions that quietly break every downstream model if you get them wrong.**

1. **What is the unit of analysis?** — What counts as one "thing" you're tracking over time? I tested a candidate grouping key across the whole dataset and quantified exactly where it held and where it broke down.
2. **What does the label actually mean?** — "Churn" can be defined at more than one level, and those definitions *disagree*. I showed this changes what the model is even predicting.
3. **Which data is real, and which is a landmine?** — Placeholder values, negatives, missing entries, and apparent duplicates all *look* like noise. I investigated each before anyone dropped it; several were signal, not noise.

The output was a set of validated findings and a manager-facing narrative that turned "here's a messy table" into "here's what we can and can't safely model, and why."

---

## Why this work matters (the ML angle)

Most churn-model failures aren't modelling failures — they're **label and unit-of-analysis failures** that happen upstream, in the part everyone rushes through. A model trained on a mis-defined target can score well in validation and still be useless in production, because it learned the wrong thing.

This repo is the part of the ML lifecycle that decides whether the eventual model is worth building:

| ML lifecycle stage | What I did |
|---|---|
| Problem framing | Reframed "predict churn" into three answerable sub-questions: unit, label, data trust |
| Data validation | Investigated every "drop it" candidate before dropping |
| Label definition | Showed the target is *ambiguous* and quantified the competing definitions |
| Feature-readiness | Built the time-series trajectory that per-entity features derive from |
| Assumption tracking | Kept an explicit "unverified assumptions" ledger so plausible claims never silently became facts |

---

## The analytical narrative

### 1. Privacy first

Before any analysis, all direct identifiers were replaced with deterministic surrogate keys. This preserves the *relational structure* the analysis needs (which records belong together) while removing the ability to re-identify anything. Analysis never touches raw identifiers.

*Skill: privacy-by-design — data governance before touching the data.*

### 2. Choosing the unit of analysis

The central design question was **what to treat as one unit tracked over time** — a broad grouping key, or a finer one. The broad key groups related records into one lifeline; the finer key tracks each component independently. The choice determines what every later feature means.

I didn't just pick one. I **stress-tested the candidate key** across the entire dataset with three signals:
- **Fan-out** — how many components sit under one key (typically one, with a long tail).
- **Regime split** — I bucketed every entity by whether the key *grouped*, *matched 1:1*, or *fragmented* its components. The large majority fell into "safe" regimes.
- **Hard-reject test** — does any single key illegitimately span entities it shouldn't? Only a negligible fraction did — small enough to **flag and keep** rather than discard the key.

**Decision:** the key is usable for the overwhelming majority of the data; the rare bad cases carry a boolean flag so each downstream feature can exclude them. The difference between "it looked fine on a sample" and "I know exactly where it breaks and I've fenced it off."

*Skill: turning an architectural decision into a measurable one instead of a judgement call.*

### 3. The label is ambiguous — and that's a finding

"Churn" felt like one thing until the data showed it was two:

- **Coarse churn** — the entity disappears entirely and doesn't return.
- **Fine-grained churn** — the relationship continues, but the customer quietly reduces part of it.

These disagree. Because a meaningful share of relationships involve more than one component, a customer can look retained at the coarse level while genuinely pulling back at the fine level. **A model trained only on the coarse label is structurally blind to the fine-grained signal.** Surfacing this in EDA is cheap; discovering it after a model ships is not.

*Skill: recognising an ambiguous target as a modelling risk, and quantifying it.*

### 4. Building the trajectory (feature-readiness)

To ask "is this relationship growing or shrinking over time?" I built a **time-aware aggregation**: at each event date, sum only what is *active* at that moment (window overlap: `start ≤ T ≤ end`) rather than summing every record (which double-counts things that already expired).

I classified each trajectory as **flat / reducing / expanding / single-point**, then rolled it up per entity.

A methodology check mattered here: I first evaluated on a **fixed calendar grid**, then re-ran on an **event-based grid** (each entity's own event dates). The two gave *materially different* answers — the calendar grid produced an artefact bucket that collapsed under the event grid, shifting the reducing/expanding shares by several points. I made the event-based grid canonical and kept the calendar version only for traceability.

*Skill: recognising that the choice of evaluation grid is itself a modelling decision — and validating it rather than trusting the first result.*

### 5. Data-quality investigations ("don't drop it, understand it")

Four things looked like droppable noise. I profiled each before deletion:

- **Negative values** — looked like a decline signal. Profiling the whole population showed they were an accounting artefact that nets out, not a real decline. **Summing them naively would have manufactured a fake signal.**
- **Placeholder values** — a far-future sentinel used as an "open-ended" marker. Left in a duration calculation it produces absurd outliers that destroy every percentile. **Kept the records, nulled the derived field.**
- **Missing values** — a small fraction where the quantity is structurally undefined. I checked whether the value hid in a related column (it didn't) before concluding it was genuinely missing. **Kept and flagged, never silently dropped.**
- **"Duplicates"** — an alarming apparent duplicate rate turned out to be an artefact of comparing only a subset of columns. On the true record-level key, exact duplicates were **zero**. The right key dissolved the phantom problem.

*Skill: the most valuable EDA instinct — `null ≠ zero`, `anomalous ≠ droppable`. Each of these, dropped naively, would have biased the eventual model.*

### 6. A ledger of unverified assumptions

I kept a running list of **claims that sounded plausible but hadn't been tested against the data**. Each entry records what *is* verified, what *isn't*, and the exact query that would settle it.

This is a discipline, not a document: it stops attractive narratives from hardening into "facts" that get baked into features. An unverified assumption about the label is exactly how you ship a confident, wrong model.

*Skill: intellectual honesty — arguably the rarest and most valuable trait in an applied practitioner.*

---

## What I'd do next (the modelling bridge)

- **Define the churn label formally** — set the "gone" threshold empirically from the observed gap distribution, rather than guessing.
- **Engineer per-entity features** from the validated trajectories: slope, count of reducing components, coarse-vs-fine churn divergence, tenure.
- **Baseline model** — start interpretable (logistic / gradient-boosted trees) precisely *because* the label is subtle; interpretability catches a label leak before it ships.
- **Validate against both churn definitions** separately, since a single headline metric would hide the coarse-vs-fine blind spot.

---

## Tech & skills

- **PySpark / Databricks** — analysis at scale, window functions, `countDistinct`, interval-overlap aggregation.
- **Statistical EDA** — percentile-driven summaries (never mean-only on skewed data), regime bucketing, distribution-shape classification.
- **Data governance** — anonymisation-first workflow, confidentiality-aware reporting.
- **Communication** — turned the findings into a manager-facing narrative (problem → evidence → decision) for a non-technical audience.
- **Applied-ML judgement** — treating unit-of-analysis, label definition, and data-trust as first-class modelling decisions, not preprocessing chores.

## Repo layout

```
portfolio/
├── README.md            ← the case study
└── notebooks/           ← methods-only PySpark on a generic schema
    ├── 01_anonymisation.md
    ├── 02_unit_of_analysis_stress_test.md
    ├── 03_data_quality_investigations.md
    └── 04_trajectory.md
```

The notebooks show the *shape* of the technique on an abstract schema. Illustrative, not runnable against any real dataset.
