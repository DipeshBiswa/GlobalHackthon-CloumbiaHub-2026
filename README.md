# Echo — offline visitor feedback

Echo helps Noor understand feedback about her coffee farm. Visitors submit a rating,
their favorite part, and what could improve. Local OPUS translates English into
Kiswahili, and local MiniLM classifies the original English into coffee-farm topics.
Echo counts recurring feedback and selects suggestions from a fixed, reviewed
advice library. It includes bilingual reviews, manual corrections, monthly
performance, and plans with before/after tracking.

A local FastAPI server serves the frontend and API. SQLite saves each account's
reviews and plans. **Normal use works offline after the one-time online setup.**

## One-time online setup

Complete these steps on **each computer** that will run Echo. Stay connected to
the internet until setup finishes with **Echo ready**. Run commands in order; if
one fails, resolve its error before continuing.

### 1. Install the prerequisites

You need Git, Python 3.10 or newer, and a browser. Make Git and Python available in Terminal or
PowerShell. The setup script creates its own Python environment; there is no
Node/npm installation or cloud account to configure.

On macOS/Linux, check:

```sh
git --version
python3 --version
```

On Windows PowerShell, check:

```powershell
git --version
py -3 --version
```

Windows setup also accepts `python` if the `py` launcher is unavailable.

### 2. Clone the correct branch

The offline app and automatic demo import are on **Backend-frontend-test1**.
Run these Git commands in Terminal or PowerShell:

```sh
git clone --branch Backend-frontend-test1 https://github.com/DipeshBiswa/GlobalHackthon-CloumbiaHub-2026.git
cd GlobalHackthon-CloumbiaHub-2026
git branch --show-current
```

The last command should print `Backend-frontend-test1`.

You are now at the **repository root**: the folder containing `README.md`,
`backend`, and `frontend`. The following setup commands start from this folder.
For a clone you already have, use [the update instructions](#update-an-existing-clone).

### 3. Run setup while online

**macOS/Linux — Terminal, from the repository root:**

```sh
sh backend/setup.sh
```

**Windows — PowerShell, from the repository root:**

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\setup.ps1
```

Setup automatically:

1. Creates the Python environment in `backend/.venv`.
2. Installs the packages in `backend/requirements.txt`.
3. Downloads missing OPUS English-to-Kiswahili and MiniLM models.
4. Checks translation and classification using local model files.
5. Prints **Echo ready** when preparation succeeds.

The first model download can take several minutes. `Requirement already satisfied`
only describes installed Python packages; wait for the model checks and
**Echo ready** before proceeding.

Model weights are excluded from Git, so cloning alone does not install them.
Browser libraries and fonts are bundled in `frontend/vendor/`. Demo reviews are
also bundled and require no generation command.

### 4. Start Echo

Once setup succeeds, you can disconnect the internet.

**macOS/Linux — from the repository root:**

```sh
sh backend/run_offline.sh
```

**Windows — from the repository root:**

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\run_offline.ps1
```

Keep the Terminal or PowerShell window running. In a browser on the **same
computer**, open **http://127.0.0.1:8000/**. This server supplies both the frontend
and backend. Its health check is **http://127.0.0.1:8000/health**.

### 5. Log in and use the demo

| Setting | Value |
|---|---|
| Username | `noor` |
| Password | `coffee2025` |
| Dashboard PIN | `0000` |

Open **Noor's Dashboard** and enter the PIN. On first startup, an untouched Noor
account receives **225 synthetic reviews for all twelve months of 2026**, including
English, Kiswahili, predictions, and a directions improvement plan. Tasting
complaints show High confidence, group-size complaints show Medium confidence,
and the directions plan shows Better.

Use **Visitor Feedback** to submit a new English review. The backend translates,
classifies, and saves it locally. Visitors can submit while the dashboard is PIN
locked. Signing up creates a separate account with its own data and initial PIN
`0000`.

Press **Control+C** on Mac/Linux or **Ctrl+C** on Windows to stop the server.
Stopping preserves the database. The frontend's **Restart** button logs out and
returns to the welcome screen; it also preserves reviews and plans.

## Every later start: offline

Return to the cloned repository and run the start command. You do not need to
rerun setup or generate demo reviews for daily use. The start scripts set the
model libraries to offline mode.

Choose the command matching your **current folder**:

| System | Current folder | Start command |
|---|---|---|
| macOS/Linux | Repository root | `sh backend/run_offline.sh` |
| macOS/Linux | Inside `backend` | `sh run_offline.sh` |
| Windows PowerShell | Repository root | `powershell -ExecutionPolicy Bypass -File .\backend\run_offline.ps1` |
| Windows PowerShell | Inside `backend` | `powershell -ExecutionPolicy Bypass -File .\run_offline.ps1` |

Open **http://127.0.0.1:8000/** and keep the server window running. Reviews,
translations, classification, suggestions, plans, and monthly statistics work
locally. Installing dependencies, downloading models, and fetching Git updates
require internet.

## Update an existing clone

Stop the backend with Control+C/Ctrl+C and connect to the internet. These Git
commands work from either the repository root or its `backend` folder:

```sh
git fetch origin
git switch Backend-frontend-test1
git pull --ff-only
```

Rerun setup after an update to install changed dependencies and prepare missing
models. Existing model weights are reused. Use the commands for your current folder:

| System | Current folder | Online setup | Start afterward |
|---|---|---|---|
| macOS/Linux | Repository root | `sh backend/setup.sh` | `sh backend/run_offline.sh` |
| macOS/Linux | Inside `backend` | `sh setup.sh` | `sh run_offline.sh` |
| Windows PowerShell | Repository root | `powershell -ExecutionPolicy Bypass -File .\backend\setup.ps1` | `powershell -ExecutionPolicy Bypass -File .\backend\run_offline.ps1` |
| Windows PowerShell | Inside `backend` | `powershell -ExecutionPolicy Bypass -File .\setup.ps1` | `powershell -ExecutionPolicy Bypass -File .\run_offline.ps1` |

Wait for **Echo ready**, start the backend, and reload the browser. Existing reviews,
plans, credentials, and owner decisions are preserved.

## Troubleshooting setup and startup

| What you see | What to do |
|---|---|
| Setup ends with `Environment ready. Run ./download_model.sh...` | This is the older setup script from `main`. Follow the branch switch and update steps, then rerun setup. |
| `Offline translation model is missing` or a missing MiniLM model | Run online setup on `Backend-frontend-test1` and wait for Echo ready. Python packages alone are not the model files. |
| `No such file or directory` | Check your current folder. Inside `backend`, use `sh setup.sh` and `sh run_offline.sh`; from the root, include the `backend/` prefix. |
| `cd: .../bin/python: Not a directory` | `cd` accepts folders. A Python path is an executable; run it directly rather than trying to enter it. |
| Browser cannot connect | Keep the backend running and use `http://127.0.0.1:8000/` on that computer. Check Terminal for startup errors and try `/health`. |

On Mac/Linux, inspect your location and branch with:

```sh
pwd
ls
git branch --show-current
```

On Windows PowerShell:

```powershell
Get-Location
Get-ChildItem
git branch --show-current
```

When reporting a failure, include the command, current folder and branch, and the
final 30 lines of the traceback including the last error message.

## Bundled demo and local storage

`backend/data/synthetic/noor_reviews.json` and `noor_plans.json` contain the
pretranslated, preclassified demo. Import requires no model inference or extra
review download. The dashboard and review cards identify synthetic data. Future
months are intentional simulation data; live reviews still reject future dates.

Import runs once for an untouched `noor` account, including an existing empty
account. Existing reviews, plans, or ignored-suggestion decisions cause import to
be skipped. Deleted reviews also count as existing records. A persistent marker
prevents restarts from restoring data you removed.

Each clone creates its own `backend/echo.db`; data is not shared between computers.
Virtual environments, databases, model weights, backups, and translation caches
are excluded from Git. Standard setup stores OPUS in `backend/models/opus-en-sw/`
and MiniLM in `backend/models/insight-model/`. An existing root OPUS model in
`models/opus-en-sw/` is also supported.

To start a fresh database without importing the demo, set `ECHO_SEED_DEMO=0`.
This does not remove already imported data. From the repository root:

```sh
ECHO_SEED_DEMO=0 sh backend/run_offline.sh
```

Windows PowerShell equivalent:

```powershell
$env:ECHO_SEED_DEMO = '0'
powershell -ExecutionPolicy Bypass -File .\backend\run_offline.ps1
```

See [the demo documentation](docs/SYNTHETIC_DEMO.md) for the monthly story,
rating distribution, controlled patterns, and preservation rules.

## Repository layout

| Location | Purpose |
|---|---|
| `frontend/` | Phone-style interface, API client, bundled browser libraries and fonts |
| `backend/api.py` and `echo_api.py` | Local server, account/PIN access, reviews, suggestions, plans and performance |
| `backend/translate_opus.py` and `insight_model.py` | Local translation and English topic classification |
| `backend/review_pipeline.py` | Shared processing for live and developer-generated reviews |
| `backend/store.py` and `echo_analytics.py` | SQLite storage, recurring patterns and before/after statistics |
| `backend/data/` | Reviewed 17-topic knowledge, approved advice, synthetic data and audits |
| `backend/tools/` | One-time model preparation and optional development utilities |
| `backend/tests/` | Isolated API, model, demo-import and browser verification |
| `docs/` | Implementation and synthetic demo documentation |

## Optional developer commands

These commands run from the **repository root**, using the `backend/.venv` created
by setup. If you maintain a root `.venv`, use its Python instead.

### Run tests

Windows PowerShell:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q
```

macOS/Linux:

```sh
backend/.venv/bin/python -m pytest backend/tests -q
```

Tests use isolated databases. Real model tests block outgoing connections and
verify OPUS/MiniLM inference. Other tests cover validation, owner isolation,
corrections, demo import, confidence thresholds and plan tracking.

Browser checks require **Microsoft Edge** and the development dependencies.
Windows PowerShell:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\backend\.venv\Scripts\python.exe backend/tests/browser_offline.py
.\backend\.venv\Scripts\python.exe backend/tests/browser_offline.py --seeded-demo
```

macOS/Linux, with Microsoft Edge installed:

```sh
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
backend/.venv/bin/python backend/tests/browser_offline.py
backend/.venv/bin/python backend/tests/browser_offline.py --seeded-demo
```

The seeded check starts from an empty database and verifies automatic import,
all twelve monthly counts and ratings, confidence cases, and the Better plan.
Both browser checks reject external requests. Artifacts go to ignored
`backend/test-results/`.

For a manual offline check, finish setup, disconnect the internet, start Echo,
inspect the demo, and submit a new English review. Verify Kiswahili, suggestions
and monthly data, then stop and restart to confirm persistence. To test exact
three/five-review thresholds independently of the demo, use a new separate
account or a fresh database with `ECHO_SEED_DEMO=0`.

### Regenerate the demo only when changing it

Automatic import is sufficient for ordinary clones. Developer regeneration runs
the real models again and can take longer. Windows PowerShell:

```powershell
.\backend\.venv\Scripts\python.exe backend/tools/generate_synthetic_reviews.py --count 225 --year 2026 --seed 42 --reset
```

macOS/Linux:

```sh
backend/.venv/bin/python backend/tools/generate_synthetic_reviews.py --count 225 --year 2026 --seed 42 --reset
```

Inside the Mac `backend` folder, use `./.venv/bin/python` and
`tools/generate_synthetic_reviews.py`. Reset replaces only Noor's synthetic
reviews/plans and backs up the database first. Real data and other accounts are
preserved. See [the demo documentation](docs/SYNTHETIC_DEMO.md) for details.

### Rebuild development knowledge

Runtime knowledge is already bundled. An optional rebuild requires your own Yelp
reference sample; the app does not need that sample to run. Replace the sample
path below with the path on your computer:

```powershell
.\backend\.venv\Scripts\python.exe backend/tools/build_echo_knowledge.py 'path/to/echo_yelp_tourism_sample.json'
.\backend\.venv\Scripts\python.exe backend/tools/localize_knowledge.py
```

On Mac/Linux, use `backend/.venv/bin/python` for the same scripts. The build audits
reference feedback into the reviewed 17-topic library without importing visitor
records. Localization pretranslates fixed approved advice. Runtime selects from
these files and never scans Yelp or generates new advice.

### Run a separate frontend server

The normal port-8000 server already serves the frontend. For development, an
optional local proxy can serve it on port 5500 while the backend stays on 8000.
In a second terminal, from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe frontend/serve.py
```

On Mac/Linux, use `backend/.venv/bin/python frontend/serve.py`. Open
**http://127.0.0.1:5500/**. This server proxies `/api/` so account cookies work.
Opening `index.html` as a file does not provide the local API.

## API and implementation details

- `/api/auth/signup`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`
- `/api/pin/unlock`, `/api/pin/lock`, `PATCH /api/pin`
- `POST/GET /api/reviews`, `GET/DELETE /api/reviews/{id}`
- `PATCH /api/reviews/{id}/restore`, `PATCH /api/reviews/{id}/classification`
- `POST /api/reviews/seen`, `GET /api/dashboard`, `GET /api/knowledge`
- `GET /api/suggestions`, `POST /api/suggestions/decision`
- `GET/POST /api/plans`, `PATCH/DELETE /api/plans/{id}`
- `GET /api/performance/monthly?month=YYYY-MM`, `GET /health`

Login identifies the business receiving feedback. Owner data requires account
login and PIN unlock; data is isolated by account. `/docs` and `/redoc` are
disabled to avoid remote documentation assets; the schema is at `/openapi.json`.
Legacy translation-only endpoints remain protected utilities with their JSON
store. Echo's frontend uses the SQLite `/api/` routes.

See [the offline implementation report](docs/OFFLINE_IMPLEMENTATION.md) for rules,
thresholds, provenance and limitations, and [the demo documentation](docs/SYNTHETIC_DEMO.md)
for the fictional full-year data.
