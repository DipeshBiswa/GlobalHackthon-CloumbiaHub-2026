# GlobalHackthon-CloumbiaHub-2026

## Project layout

```text
backend/   Offline translation API, models, analytics, and JSON storage
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

## API endpoints

- `GET /health`
- `POST /reviews/translate`
- `POST /reviews/translate/batch`
- `GET /reviews/translated`
- `GET /reviews/insights`

Open `http://127.0.0.1:8000/docs` for local API documentation.

Translated reviews are saved in `backend/translated_reviews.json`.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/reviews/translate \
  -H "Content-Type: application/json" \
  -d '{"rating":5,"language":"en","date":"2026-10-03","favorite":"The guide was friendly.","improvement":"Add more time."}'
```
