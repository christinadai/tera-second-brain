# tera Second Brain

A consumer intelligence pipeline for tera. It reads what people actually say
about skincare on Reddit, tidies and labels it, and turns it into evidence the
team can act on, with every claim traceable back to the post it came from.

Built during an 8 week internship starting 31 August 2026. Designed to be run
and extended by people who do not write code.

## What it answers

**Track A, first:** what should tera make? The top product types by volume of
discussion, the pain points attached to each, and explicit analysis of an
overnight face serum and lip products whether or not they rank highly.

**Track B, after:** what would consumers believe? If tera leads with potency
claims, what triggers skepticism and what proof gets accepted instead.

The system supplies evidence and ranks it. It does not make recommendations.
A person decides.

## How information moves

```
pull -> raw -> clean -> match -> classify -> aggregate -> brief
```

Each stage writes its own table and nothing overwrites `raw`, so every line in
a briefing traces back to its source post, and the data can be reprocessed
without collecting it again.

## The three tables

| Table | In plain terms | Rule |
|---|---|---|
| `raw` | What Reddit said, copied down exactly | Written once, never edited |
| `cleaned_labeled` | That text tidied up and labelled | Rebuildable from `raw` |
| `job_logs` | The clock-in record for every run | Carries a typed outcome, not just a count |

Ranking is not stored. It is computed by SQL over `cleaned_labeled` each time a
briefing is built, so re-ranking is free.

## Quick start

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then fill in your Reddit credentials
./.venv/bin/python scripts/init_db.py
./.venv/bin/python scripts/verify_reddit.py
./.venv/bin/python scripts/pull_once.py --limit 10
```

Full setup, operation, debugging and known limits: [docs/OPERATIONS.md](docs/OPERATIONS.md).

## What is deliberately not here

Campaign launching, TikTok, scientific papers, any interface beyond the
briefing, sentiment scores, historical backfill, and automated recommendations.
Each was considered and cut. The reasoning is in OPERATIONS.md, because being
able to say why something is absent is part of the work.
