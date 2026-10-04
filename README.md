# GlobalHackthon-CloumbiaHub-2026

## Project layout

```text
backend/   Offline translation API, models, analytics, and JSON storage
frontend/  Frontend application goes here
```

## Run the backend

### macOS/Linux

From the repository root:

```bash
cd backend
./setup.sh
./download_model.sh
./download_insight_model.sh
./run_offline.sh
```

Run `download_model.sh` and `download_insight_model.sh` once while online.
After both models are downloaded, `run_offline.sh` works without Wi-Fi.

### Windows PowerShell

From the repository root:

```powershell
cd backend
.\setup.ps1
.\download_model.ps1
.\download_insight_model.ps1
.\run_offline.ps1
```

The two download commands require Wi-Fi only the first time. The server runs
locally at `http://127.0.0.1:8000`.

Open `frontend/index.html` in a browser while the backend is running. The
visitor review form sends submissions to the local translation API, and the
backend saves the translated result in `backend/translated_reviews.json`.
The frontend includes a local API helper in `frontend/api.js`.
That helper supports every backend endpoint: health checks, single review
translation, batch translation, translated-review retrieval, and insights.
When the app starts, it checks the backend and loads the saved translated
reviews and insights. After a new review is submitted, it refreshes that live
data so the Noor screens use the backend store.

## API endpoints

- `GET /health`
- `POST /reviews/translate`
- `POST /reviews/translate/batch`
- `GET /reviews/translated`
- `GET /reviews/insights`

Open `http://127.0.0.1:8000/docs` for local API documentation.

Translated reviews are saved in `backend/translated_reviews.json`.
Each new saved review keeps both the Kiswahili translation and the original
English text. Insights classify the original English text, avoiding the
language mismatch between translated review content and English topic labels.
The Noor frontend also loads those original fields for its local topic
labels, while displaying the Kiswahili fields as translations.
Monthly performance uses the current calendar year, so reviews submitted in
the current year appear in the month picker and review table.

To reset the local test store, replace `backend/translated_reviews.json` with
an empty JSON array (`[]`) and submit new reviews through the frontend or the
batch endpoint.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/reviews/translate \
  -H "Content-Type: application/json" \
  -d '{"rating":5,"language":"en","date":"2026-10-03","favorite":"The guide was friendly.","improvement":"Add more time."}'
```
