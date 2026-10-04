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
The frontend topic vocabulary covers the same major tourism themes as the
backend insights classifier, reducing unnecessary "Not sure" results.

## Fine-tune the local insight model

The optional Yelp fine-tuning workflow trains only a small linear topic head
over the frozen local MiniLM encoder. It reads the Yelp archive as a stream,
uses tourism-business reviews with explainable keyword labels, and does not
extract or copy the archive.

Run it from the repository root after the insight model has been downloaded:

```bash
cd backend
../.venv/bin/python train_insight_model.py \
  "../Yelp JSON/yelp_dataset.tar" \
  --limit 2000 \
  --epochs 20 \
  --batch-size 8
```

The reusable artifact is written to
`backend/models/insight-model/topic_head.pt`, with training metadata in
`topic_head.json`. The API automatically loads the head when both files are
present; without them it continues using the original embedding classifier.
Another local repository can reuse the artifact by pointing its insight-model
directory at this same model directory or copying the two topic-head files
alongside the matching MiniLM model.

The Yelp archive is intentionally ignored by Git because of its size and
dataset terms. The generated model files are also ignored through the
`models/` rule.

To reset the local test store, replace `backend/translated_reviews.json` with
an empty JSON array (`[]`) and submit new reviews through the frontend or the
batch endpoint.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/reviews/translate \
  -H "Content-Type: application/json" \
  -d '{"rating":5,"language":"en","date":"2026-10-03","favorite":"The guide was friendly.","improvement":"Add more time."}'
```
