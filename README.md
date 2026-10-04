# Echo — offline visitor feedback

Echo preserves the frontend's phone layout and runs through a local FastAPI server.
SQLite stores English and generated Kiswahili together. Local OPUS translates;
local MiniLM and topic phrases classify English. Python counts distinct Echo
reviews and selects advice from a fixed, approved local library.

## Install once while online

Windows PowerShell, from the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe backend/tools/prepare_offline.py
```

Alternatively, `./backend/setup.ps1` creates `backend/.venv` and prepares models.
On macOS/Linux, from the repository root:

```sh
sh backend/setup.sh
sh backend/run_offline.sh
```

If Terminal is already inside `backend`, use `sh setup.sh` and then
`sh run_offline.sh`. The browser libraries, fonts and licenses are included in
`frontend/vendor/`. Setup downloads missing models for live translation and
classification, then verifies both using local-only loading.

OPUS: `backend/models/opus-en-sw/`; the existing root `models/opus-en-sw/` is also
supported. MiniLM: `backend/models/insight-model/`. Model weights and SQLite
databases are excluded from Git. Prepare each demonstration machine while online.

## Start offline

```powershell
.\backend\run_offline.ps1
```

Open **http://127.0.0.1:8000/**. This serves both the API and the existing
`frontend/` directory; no separate frontend process is required.

Equivalent backend command with the root environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir backend --host 127.0.0.1 --port 8000
```

Optional separate frontend, in another terminal:

```powershell
.\.venv\Scripts\python.exe frontend/serve.py
```

Open **http://127.0.0.1:5500/**. This local server proxies `/api/` to port 8000
so HttpOnly account cookies work without browser storage of passwords or tokens.
Avoid opening `index.html` directly or using a plain static server in the
separate-port configuration. Both servers bind to loopback.

Demo login: **noor / coffee2025**. Dashboard PIN: **0000**. Sign up creates a
separate local owner with PIN 0000. `PATCH /api/pin` changes that PIN after unlock.
Restart logs out without deleting reviews or plans.

## Noor's full-year synthetic demo

The branch includes 225 synthetic coffee-farm reviews for all twelve months of
2026 and a directions improvement plan. The checked-in JSON already contains real
model translations and classifications. Starting the backend automatically imports
it into a fresh database, or an existing empty `noor` account. No generation,
extra download or model inference is needed to load the demo.

Existing reviews and plans are left untouched. A persistent import marker keeps
restarts from restoring reviews you deleted. Set `ECHO_SEED_DEMO=0` before starting
to opt out of automatic import. The dashboard and review cards label the synthetic data;
future months are deliberate simulation data, and normal visitor submissions still
reject future dates.

For an existing Mac clone, from the repository root:

```sh
git pull --ff-only
sh backend/run_offline.sh
```

If Terminal is already inside `backend`, run `git pull --ff-only` and then
`sh run_offline.sh`. Restart any running backend after pulling, then log in with
**noor / coffee2025**, PIN **0000**.

Optional developer regeneration, from the repository root with the root Windows
environment:

```powershell
.\.venv\Scripts\python.exe backend/tools/generate_synthetic_reviews.py --count 225 --year 2026 --seed 42 --reset
```

With the setup script's Mac environment, the equivalent root command is:

```sh
backend/.venv/bin/python backend/tools/generate_synthetic_reviews.py --count 225 --year 2026 --seed 42 --reset
```

Regeneration is only needed when changing the demo. Restart the backend after
taxonomy changes. Reset replaces only Noor's synthetic reviews/plans and backs
up the database first.
Real reviews, real plans and other accounts are preserved. A first run translates
250 distinct texts; later runs reuse the real OPUS translation cache and classify
the English again. Full exported records and the measured audit are in
`backend/data/synthetic/`. See [the synthetic demo report](docs/SYNTHETIC_DEMO.md)
for the monthly story, 17 coffee-farm topics and controlled confidence cases.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Tests include real OPUS/MiniLM loading and inference while every outgoing
`socket.connect` is rejected. Other tests inject a translator/classifier to
isolate validation, persistence and business rules. Test databases are isolated
from `backend/echo.db`.

Optional actual-browser test (Edge must be installed):

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe backend/tests/browser_offline.py
.\.venv\Scripts\python.exe backend/tests/browser_offline.py --seeded-demo
```

The browser test rejects non-loopback requests in both browser and Python. It
exercises login, submissions, PIN, bilingual reviews, advice, plans, monthly
statistics, delete/undo, reload persistence and manual correction. Artifacts go
to ignored `backend/test-results/`. See [the implementation report](docs/OFFLINE_IMPLEMENTATION.md)
for exact rules, thresholds, data provenance, changes and limitations.

Manual disconnected test:

For the exact support thresholds below, use a fresh database with
`ECHO_SEED_DEMO=0`. Opting out does not remove an already imported demo.

1. Complete installation and model preparation while online.
2. Disconnect Wi-Fi/Ethernet. Set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
3. Start the backend; open its localhost URL and log in.
4. Switch to Visitor Feedback. Submit English with a rating and either text field.
5. Unlock with 0000. Verify Kiswahili first and unchanged English underneath.
6. Submit three matching reviews: expect medium-confidence approved advice.
   Five matching reviews: expect high confidence. One or two: no actionable advice.
7. Accept, save, start and complete plans. Check monthly statistics. Correct an
   uncertain review; delete and undo a review. Reload to verify persistence.
8. In developer tools, confirm all requests use localhost. Runtime also forces
   the model offline flags. `/docs` and `/redoc` are disabled to avoid remote
   documentation assets; the schema remains available at `/openapi.json`.

## Development knowledge rebuild

```powershell
.\.venv\Scripts\python.exe backend/tools/build_echo_knowledge.py "C:\Users\brand\OneDrive\Desktop\Yelp JSON\yelp_dataset\echo_yelp_tourism_sample.json"
.\.venv\Scripts\python.exe backend/tools/localize_knowledge.py
```

The first command audits 1,500 reference reviews into topic counts and a reviewed
17-topic coffee-farm phrase/advice library. It retains no Yelp text and never imports visitor
records. The second pretranslates approved English advice with local OPUS;
runtime advice is selected from the file. Unchanged translations survive a rebuild.
Neither script runs at app startup or for review submissions.

## API

- `/api/auth/signup`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`
- `/api/pin/unlock`, `/api/pin/lock`, `PATCH /api/pin`
- `POST/GET /api/reviews`, `GET/DELETE /api/reviews/{id}`
- `PATCH /api/reviews/{id}/restore`, `PATCH /api/reviews/{id}/classification`
- `POST /api/reviews/seen`, `GET /api/dashboard`, `GET /api/knowledge`
- `GET /api/suggestions`, `POST /api/suggestions/decision`
- `GET/POST /api/plans`, `PATCH/DELETE /api/plans/{id}`
- `GET /api/performance/monthly?month=YYYY-MM`, `GET /health`

Login identifies the business receiving feedback. Visitors can submit while its
dashboard is PIN locked; owner data requires login and unlock. Data is isolated
by account. Existing translation-only endpoints remain protected testing utilities
with their legacy JSON store; Echo's UI exclusively uses SQLite `/api/` routes.
Old prototype/JSON reviews are not imported because translated-only records
cannot reconstruct their English source.
