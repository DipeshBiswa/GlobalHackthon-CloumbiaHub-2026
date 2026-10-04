# Echo offline implementation report

The coffee-farm synthetic-data extension is documented in
[SYNTHETIC_DEMO.md](SYNTHETIC_DEMO.md). It specializes the original 14-topic taxonomy
below into 17 farm topics and adds explicitly marked, model-processed demo records.
The 14-topic Yelp table records the original offline milestone's development audit;
the current audit is `backend/data/yelp_knowledge_audit.json`.

## Delivered behavior

The existing phone layout, colors, typography and screen structure are preserved.
Browser assets are local. A single localhost server serves the frontend and API.
SQLite `backend/echo.db` stores users, sessions, review records, model predictions,
manual overrides, plans, suggestion decisions and hashed PIN settings. The original
JSON utilities remain for protected translation-only experiments; the app never
uses them as its production database. No Yelp reviews or prototype seed reviews
are imported.

## Changed existing files

Frontend: `frontend/index.html`, `frontend/scripts.js`. `frontend/styles.css`
was inspected and left unchanged.

Backend: `backend/api.py`, `backend/review.py`, `backend/translate_opus.py`,
`backend/insight_model.py`, `backend/requirements.txt`, `backend/setup.ps1`,
`backend/setup.sh`, `backend/download_opus.py`, `backend/download_insight_model.py`.

Repository: `.gitignore`, `README.md`.

## New files

- `frontend/api-client.js`, `frontend/serve.py`
- `frontend/vendor/react.production.min.js`, `react-dom.production.min.js`,
  `htm.umd.js`, `fonts.css`, `manifest.json`, `font-0.ttf` through `font-5.ttf`,
  `react.LICENSE`, `htm.LICENSE`, `Inter.OFL.txt`, `Lora.OFL.txt`
- `backend/echo_api.py`, `echo_analytics.py`, `store.py`, `security.py`, `knowledge.py`
- `backend/requirements-dev.txt`
- `backend/data/echo_topic_rules.json`, `echo_suggestions.json`, `yelp_knowledge_audit.json`
- `backend/tools/build_echo_knowledge.py`, `install_frontend_assets.py`,
  `prepare_offline.py`, `localize_knowledge.py`
- `backend/tests/conftest.py`, `test_echo.py`, `test_offline_models.py`, `browser_offline.py`
- `docs/OFFLINE_IMPLEMENTATION.md`

Installed/generated artifacts excluded from Git: local MiniLM weights and tokenizer
files in `backend/models/insight-model/`, test databases, and
`backend/test-results/offline-example.json`, `browser-result.json`, `offline-browser.png`.
The existing OPUS weights remain in root `models/opus-en-sw/` and are reused.
Application startup creates `backend/echo.db`; tests use isolated databases.

## Taxonomy and Yelp evidence

The development sample has **1,500 reviews**. Whole-phrase matching counted each
review once per topic. These counts assess taxonomy coverage, not classifier accuracy.

| Topic | Matching reference reviews |
|---|---:|
| guide_quality | 162 |
| tour_content | 215 |
| tour_difficulty | 23 |
| timing_pacing | 27 |
| crowding_waits | 153 |
| price_value | 176 |
| facilities | 79 |
| transportation | 132 |
| food_tasting | 505 |
| cleanliness_upkeep | 93 |
| staff_service | 463 |
| souvenirs | 36 |
| accessibility | 25 |
| information_signage | 62 |

All 14 starting categories were retained. The broader hospitality/parks/food sample
supports expanding the old tour-only classifier: facilities, cleanliness, signage,
staff service and price need separate business actions. Scenery, culture/history,
exhibits and roasting are grouped into `tour_content`; food and coffee tasting are
grouped into `food_tasting`. Guide quality stays separate from staff service.

The sample influences phrase coverage and taxonomy decisions. It does **not** train
MiniLM, statistically calibrate confidence, prove sentiment accuracy, or establish
the support thresholds. Rules and approved advice are explicit development choices.
Only aggregate counts and category frequencies are retained in the audit. Runtime
reads the compact rules/advice files, never the source dataset.

Rebuild from repository root:

```powershell
.\.venv\Scripts\python.exe backend/tools/build_echo_knowledge.py "C:\Users\brand\OneDrive\Desktop\Yelp JSON\yelp_dataset\echo_yelp_tourism_sample.json"
.\.venv\Scripts\python.exe backend/tools/localize_knowledge.py
```

The optional `--output` argument redirects generated files. Localization uses OPUS
at development time to translate fixed approved advice; it writes no new advice.
Rebuild preserves existing translations when their English source is unchanged.

## Exact submission and classification flow

1. A logged-in account owns the local visitor station. Visitors can submit while
   the dashboard is PIN locked.
2. `POST /api/reviews` validates an integer rating 1–5, English input, a nonfuture
   date and at least one field containing a letter/number. Text is bounded at 2,000
   characters per field by the API and 300 by the existing UI.
3. Original English is preserved exactly, including whitespace. Blank fields are
   skipped by translation. OPUS `Helsinki-NLP/opus-mt-en-sw` translates only English
   to Kiswahili, from local files with both offline flags forced to 1.
4. MiniLM `all-MiniLM-L6-v2` embeds original English clauses and local topic
   descriptions. Existing attention-mask mean pooling and normalized embeddings
   are retained. Text is divided at punctuation, `but`, `however`, and `and`.
5. Each clause can match multiple explicit topic phrases if its topic cosine score
   is at least **0.30**. Otherwise a semantic-only topic is accepted when the best
   cosine score is at least **0.42**, with at least **0.06** margin over the runner-up.
   Unaccepted clauses retain their best prediction and score as uncertain evidence.
6. Deterministic sentiment checks obvious negative wording and negation, requests,
   praise, field context, then rating. Topic wording overrides the rating. Ratings
   4–5 lean positive, 1–2 negative, 3 neutral. Requests have their own category.
7. Repeated topic/sentiment pairs in one review are deduplicated. No accepted topic
   means `classification_status = "not_sure"`. Accepted topics include field,
   phrase, evidence, method and `classifier_score`; uncertain clauses remain in
   `model_prediction`. Cosine scores are **not calibrated probabilities**.
8. A complete record is atomically persisted with English, Kiswahili, consent,
   timestamps, translation/classification statuses and original model output. A
   processing failure returns 503 without saving a partial record; the UI retains
   the input. Success returns the stored record and the UI shows thank-you.
9. On unlock, dashboard data refreshes from SQLite. Reviews, details and monthly
   rows show Kiswahili first and English underneath. Counts exclude deleted records.

The Not Sure screen uses real classifier abstentions. Manual topic/sentiment
correction is saved as `manual_override`; `model_prediction` is unchanged. Corrections
replace effective topics for that review and do not retrain MiniLM. The API supports
multiple manual topics; the current UI assigns one correction at a time.

## Exact suggestions and confidence

Aggregation uses all active reviews belonging to the account, rather than Yelp or
only the current week. Group by `(topic, sentiment)` and count **distinct review IDs**.
Repeated phrases within a single review never increase support.

| Distinct matching Echo reviews | Result |
|---|---|
| 0–2 | No actionable suggestion |
| 3–4 | Medium pattern confidence |
| 5+ | High pattern confidence |

Classifier score never upgrades pattern confidence. Positive, negative and request
groups map to exact keys in `echo_suggestions.json`. Neutral groups have no advice.
Each result includes topic, a fixed summary, support count, pattern confidence,
approved advice and supporting IDs. Ignore persists a suppression decision. Not
now saves the plan; Try it starts it. The server requires three matching reviews
before it allows creation of an approved suggestion plan.

## Plans, baseline and statistics

Plan records include owner ID, topic, key, title, description, status, creation,
update and start timestamps. Statuses: `saved`, `trying`, `done`, `stopped`.
On entering `trying`, the server captures review count, average rating, count of
matching-topic reviews and review IDs at start. Restarting a saved/stopped plan
captures a new baseline.

Only reviews created after the start and absent from the baseline count as new.
Until three new reviews arrive, progress says waiting. Then compare matching-topic
share before and after: an absolute shift of at most **10 percentage points** is
No change. For praise, an increase is Better; for complaints/requests, a decrease
is Better. The reverse is Worse. This is observational tracking, not causal proof.

Dashboard returns trailing seven-calendar-day review count, lifetime average rating,
reviews created since last viewed, unresolved Not Sure count and trying-plan count.
Viewing All Reviews persists the last-seen timestamp.

Monthly performance uses review visit dates, proper previous-month/year boundaries,
review count and mean rating. It returns the mean difference from the previous month
when both months have data, deduplicated top positive/negative topics, plans started
that month, and matching reviews. All arithmetic is normal Python. The selector
includes the current year and years represented in the account's reviews.

## Setup, start and test commands

From the repository root, initial online setup:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe backend/tools/prepare_offline.py
```

Backend start:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend: open **http://127.0.0.1:8000/**. Optional separate frontend:

```powershell
.\.venv\Scripts\python.exe frontend/serve.py
```

Then open **http://127.0.0.1:5500/**. This proxies API calls locally.

Tests:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe backend/tests/browser_offline.py
```

The automated offline model test reloads OPUS and constructs MiniLM with every
socket connection blocked, then translates, classifies, submits reviews and checks
approved suggestions. The browser test permits only loopback requests in both
Python and the browser. It also checks deletion/undo, plan status transitions,
reload persistence and manual correction. See README for the physical-disconnection
procedure. Automated network denial was exercised; Wi-Fi was not physically toggled.

Demo credentials: **noor / coffee2025**. PIN: **0000**. Passwords and PINs use
salted PBKDF2-SHA256 with 310,000 iterations. Sessions are opaque HttpOnly,
SameSite=Strict cookies expiring after 24 hours. Five failed PIN attempts cause
a persisted 30-second lockout. Login, PIN unlock and data ownership are enforced
on the server, not just hidden in the UI.

## Real model examples

Recorded offline OPUS output:

> English: The guide was friendly.
>
> Kiswahili: Kiongozi alikuwa mwenye urafiki.

For “The guide was great, but the path was too steep and the tour felt rushed.”
with rating 5, real MiniLM outputs include:

```json
[
  {"topic":"guide_quality","sentiment":"positive","classifier_score":0.5966},
  {"topic":"tour_difficulty","sentiment":"negative","classifier_score":0.5699},
  {"topic":"timing_pacing","sentiment":"negative","classifier_score":0.7905}
]
```

Three actual test submissions of the friendly-guide review yielded:

```json
{
  "key":"guide_quality:positive",
  "summary":"Visitors praised guide quality.",
  "supporting_review_count":3,
  "pattern_confidence":"medium",
  "suggestion":"Keep emphasizing knowledgeable, welcoming guides."
}
```

These are isolated test records, not seeded app content. Full measured examples
are in the generated offline test artifact.

## Remaining limitations

- MiniLM similarity/phrase thresholds are initial heuristics, not validated on a
  labeled tourism evaluation set. Broad phrases can overlap; clause splitting,
  sarcasm, contextual negation and ambiguous references can cause errors.
- OPUS translations, including pretranslated advice, need native Kiswahili review.
  Long input exceeding OPUS's token window is rejected rather than silently truncated.
- Visitor input is English-only. Dashboard labels support English/Kiswahili.
- Manual corrections change stored effective topics without training the model;
  the UI currently corrects one topic per action, while the API accepts multiple.
- Restore is available through the API and immediate UI Undo; there is no trash
  screen. PIN changes are available through the API; there is no PIN-settings screen.
- No password recovery, installer executable, encrypted-at-rest database, local
  backup/export UI, or public multi-device visitor link is included. Local login
  works; the demo account and default PIN are intentionally available for testing.
- Plan results describe changes in review patterns, not proven effects of actions.
  Model processing is serialized for a single local visitor station.
- Python dependencies/model weights require initial installation. The optional
  browser test requires Playwright and an installed Edge browser.

The requested offline application path is implemented; remaining items above are
quality, packaging and auxiliary-management limitations.
