# Noor's Coffee Farm synthetic demo

The local `noor` account is seeded with **225 fictional reviews** for all twelve
months of **2026**, using **seed 42**. No Yelp text or unrelated businesses were
used. Every record has `is_synthetic: true`, the real Echo schema, both English and
Kiswahili, original model evidence and no manual classification override.

The dashboard labels the simulation and review cards display a Synthetic badge.
Future months are intentionally included. The live review API still rejects future
dates and writes `is_synthetic: false`. Viewing reviews marks the actual records
seen so future demo timestamps cannot keep generating false new-review badges.

## Use the bundled demo

The branch contains the fully processed reviews and directions plan. On startup,
`backend/demo_data.py` imports them into a fresh database or an existing empty
`noor` account. No generation, translation, classification or extra download is
required for that import. Existing reviews and plans are left untouched. A
persistent import marker prevents restarts from readding deleted demo records.

For a fresh Mac clone, run these from the repository root:

```sh
sh backend/setup.sh
sh backend/run_offline.sh
```

Setup still downloads the models once for live visitor submissions. The bundled
demo itself needs no model inference. If Terminal is already inside `backend`,
use `sh setup.sh` and then `sh run_offline.sh`.

For an existing Mac clone, stop the running backend and run:

```sh
git pull --ff-only
sh backend/run_offline.sh
```

Inside `backend`, use `git pull --ff-only` and then `sh run_offline.sh`. Open
**http://127.0.0.1:8000/**. Login: **noor / coffee2025**. PIN: **0000**.
Set `ECHO_SEED_DEMO=0` before starting to opt out of automatic import for an empty
database; this does not delete data that has already been imported.

## Optional developer generation or reset

Regeneration is only needed to change the demo. From the repository root with
installed offline models and the root Windows environment:

```powershell
.\.venv\Scripts\python.exe backend/tools/generate_synthetic_reviews.py --count 225 --year 2026 --seed 42 --reset
```

With the setup script's Mac environment, from the repository root:

```sh
backend/.venv/bin/python backend/tools/generate_synthetic_reviews.py --count 225 --year 2026 --seed 42 --reset
```

Inside `backend`, that command starts with `./.venv/bin/python` and uses
`tools/generate_synthetic_reviews.py`.

Defaults are 225 reviews, 2026, seed 42. Optional `--batch-size`, `--threads` and
`--output-dir` control local preprocessing. The first run performs real OPUS
inference; later runs reuse cached translations of identical English and rerun
MiniLM. Delete the ignored translation cache to force full retranslation.

`--reset` deletes only records explicitly marked synthetic for `noor`, including
the seeded synthetic plan. Real reviews, owner-created plans, other accounts,
credentials and suppression decisions are preserved. Writes are one transaction,
after processing and validating the default confidence cases. A local SQLite backup
is written to `backend/data/backups/` before seeding. Stable IDs make repeated runs
with the same parameters idempotent.

Restart the backend to load updated taxonomy/approved advice, then open
**http://127.0.0.1:8000/**. Login: **noor / coffee2025**. PIN: **0000**.

## Files and processing

- Generator: `backend/tools/generate_synthetic_reviews.py`
- Curated fictional feedback: `backend/tools/noor_feedback.py`
- Shared HTTP/demo processing: `backend/review_pipeline.py`
- Reviewed coffee-farm taxonomy: `backend/data/farm_taxonomy.py`
- Compact runtime knowledge: `backend/data/echo_topic_rules.json`, `echo_suggestions.json`
- Full processed export: `backend/data/synthetic/noor_reviews.json`
- Bundled synthetic plan: `backend/data/synthetic/noor_plans.json`
- Automatic startup importer: `backend/demo_data.py`
- Measured audit: `backend/data/synthetic/noor_demo_report.json`
- Ignored reusable OPUS cache: `backend/data/synthetic/opus_translation_cache.json`

Sources combine varied short visitor observations, personal notes and occasional
longer feedback. They cover the form's favorite and improvement fields, including
single-field submissions. There are 225 unique feedback pairs. The generated audit
reports the exact number of Noor mentions, blank fields and classification statuses.
It also includes monthly statistics, approved suggestions and measured plan progress.

Translation uses the existing local Helsinki OPUS English-to-Kiswahili model with
eight deterministic beams, batched to reduce preprocessing time. Blank fields are
skipped. Classification runs the same local MiniLM/phrase classifier used by POST
`/api/reviews`, on original English only. No labels are forced to meet a demo case;
the default run refuses to replace the database if measured cases fail.

## Monthly story and rating mix

| Month | Reviews | Story |
|---|---:|---|
| January | 10 | Quieter visits; some difficulty finding the farm |
| February | 11 | Low volume; directions still need improvement |
| March | 17 | Growing visitor numbers and coffee education |
| April | 20 | More visits; last early directions complaints |
| May | 26 | Busy season; clearer directions introduced |
| June | 27 | Busy visits; roasting/tasting and walking feedback |
| July | 28 | Highest volume; pacing and hearing complaints |
| August | 26 | Busy season continues; shade and route requests |
| September | 20 | Comfortable groups and stronger ratings |
| October | 17 | Especially positive coffee-tasting feedback |
| November | 12 | Lower volume and strong ratings |
| December | 11 | Quieter visits, positive finish to the year |

| Rating | Reviews | Percentage |
|---|---:|---:|
| 5 | 124 | 55.1% |
| 4 | 67 | 29.8% |
| 3 | 22 | 9.8% |
| 2 | 9 | 4.0% |
| 1 | 3 | 1.3% |

Each late-year month also contains four-star visits rather than being uniformly
perfect. Praise for Noor can coexist with a lower overall rating or a complaint
about the path, duration, group or transport. Obvious topic praise takes priority
over star-rating fallback.

## Controlled cases measured from real model output

| Topic / sentiment | Support | Expected outcome |
|---|---:|---|
| coffee_tasting / negative | 12 | High confidence; add a few extra minutes to tasting |
| group_size / negative | 4 | Medium confidence; consider smaller groups or quieter explanations |
| facilities / request | 2 | No actionable seating suggestion |

Positive facilities feedback can independently support a maintenance suggestion;
the two seating requests do not cross the request threshold. Likewise, praise and
complaints about small/large groups are counted separately.

The seeded plan **Clearer directions to Noor's farm** starts on May 1. Its baseline
contains 58 reviews with 7 direction complaints. The 167 later reviews contain no
direction complaints. The complaint-share drop exceeds the existing ten-percentage-
point threshold, so My Plans reports **Better**. This is a fictional scenario, not
evidence that a real intervention occurred. Reviews and the plan are marked synthetic.

## Coffee-farm taxonomy

The 17 active topics are:

`guide_quality`, `coffee_education`, `coffee_roasting`, `coffee_tasting`,
`farm_tour_content`, `tour_difficulty`, `timing_pacing`, `group_size`, `facilities`,
`transportation`, `accessibility`, `price_value`, `staff_service`, `souvenirs`,
`information_signage`, `scenery`, `local_culture`.

The prior broad topic names have read-time compatibility aliases: `tour_content`
to `farm_tour_content`, `food_tasting` to `coffee_tasting`, `crowding_waits` to
`group_size`, and `cleanliness_upkeep` to `facilities`. Original model predictions
are preserved; older effective topics and plan keys remain usable.

The Yelp development audit was rebuilt for phrase coverage against the 1,500-review
reference sample. Coffee-specific topics are explicit farm business requirements,
not trained labels inferred from Yelp. Runtime never scans that sample.
Kiswahili advice is pretranslated from fixed approved English advice.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe backend/tests/browser_offline.py
.\.venv\Scripts\python.exe backend/tests/browser_offline.py --seeded-demo
```

Tests cover reproducibility, monthly/rating distributions, realistic field lengths,
shared processing, future-date rejection, reset isolation, stable repeated writes,
legacy aliases, measured demo thresholds and before/after tracking. The real model
test blocks socket connections and checks batched OPUS as well as single translation.
The seeded browser check starts with an empty temporary database and exercises
automatic import, then checks the synthetic badges, all 225 reviews, High/Medium topic suggestions,
the Better plan result, and all twelve monthly counts and averages. It blocks
external connections in both Python and the browser.

The dataset is handcrafted synthetic feedback, not research data or evidence about
Noor's real business. Similarities and sentiment remain heuristic, and Kiswahili
translations need native-speaker review. Full-year future data affects chronological
ordering in the demo; it does not change live submission validation.
