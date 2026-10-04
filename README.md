# GlobalHackthon-CloumbiaHub-2026

## Run the review translation API

The API translates English reviews into Kiswahili using the local OPUS model.
After the model is downloaded, translation and the API run without Wi-Fi.

### 1. Clone the repository

```bash
git clone <repository-url>
cd GlobalHackthon-CloumbiaHub-2026
```

### 2. Create the virtual environment

macOS/Linux:

```bash
./setup.sh
```

This creates `.venv/` locally. The environment is not committed to Git because
virtual environments are machine-specific.

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
```

### 3. Download the model once while online

`models/` is excluded from Git because the model is large. Run this step
while the computer has Wi-Fi:

macOS/Linux:

```bash
./download_model.sh
```

Windows PowerShell:

```powershell
.venv\Scripts\python download_opus.py
```

This creates `models/opus-en-sw/`. Keep that directory on the computer; it is
required for offline translation. Do not run `download_opus.py` offline.

### 4. Start offline

macOS/Linux:

```bash
./run_offline.sh
```

Windows PowerShell:

```powershell
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
.venv\Scripts\uvicorn.exe --app-dir . api:app --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`. Open
`http://127.0.0.1:8000/docs` for the local Swagger page.

### Endpoints

- `GET /health` checks that the local API is running.
- `POST /reviews/translate` translates and saves one review.
- `POST /reviews/translate/batch` translates and saves up to 50 reviews.
- `GET /reviews/translated` reads saved translations from
  `translated_reviews.json`.

Example request:

```bash
curl -X POST http://127.0.0.1:8000/reviews/translate \
  -H "Content-Type: application/json" \
  -d '{"rating":5,"language":"en","date":"2026-10-03","favorite":"The guide was friendly.","improvement":"Add more time."}'
```

The translated reviews are stored locally in `translated_reviews.json`.