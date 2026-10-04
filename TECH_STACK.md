# Echo Tech Stack in One Minute

Follow the arrows.

## 1. Frontend and backend

```mermaid
flowchart TD
    UI["Frontend: visitor form and owner dashboard<br/>HTML, CSS, JavaScript, React 18 + HTM"]
    API["Backend: Python, FastAPI + Pydantic<br/>Uvicorn runs the server; requests are validated"]
    AI["Local AI models<br/>PyTorch + Hugging Face Transformers"]
    DB[("SQLite<br/>Accounts, bilingual reviews, topics and plans")]
    UI <-->|"JSON requests and responses"| API
    API <-->|"English input and model results"| AI
    API <-->|"Save and load"| DB
```

## 2. Model logic

Both models receive the **original English review**.

```mermaid
flowchart TD
    EN["English review"]
    EN --> OPUS["OPUS-MT<br/>Tokenize text, generate translation, decode"]
    OPUS --> SW["Kiswahili review"]
    EN --> SPLIT["Split into short clauses"]
    SPLIT --> MINI["MiniLM<br/>Create meaning vectors"]
    MINI --> MATCH["Match against 17 topics<br/>Cosine similarity + phrase rules"]
    MATCH --> CHECK{"Enough evidence?"}
    CHECK -->|"Yes"| TAGS["Topic tags<br/>Rules set sentiment from wording, field and rating"]
    CHECK -->|"No"| UNSURE["Flag uncertain text<br/>Owner can review and correct"]
```

## 3. From reviews to action

```mermaid
flowchart TD
    SAVED["Saved topic and sentiment tags"]
    SAVED --> COUNT["Count distinct supporting reviews<br/>Under 3: wait; 3-4: medium; 5+: high confidence"]
    COUNT --> ADVICE["Select matching advice from reviewed JSON"]
    ADVICE --> DASH["Dashboard: suggestions and plans<br/>Compare feedback before and after an action"]
```

**Access:** PBKDF2-SHA256 password/PIN hashes and HttpOnly session cookies.
**Checks:** pytest, HTTPX and Playwright.

**Offline:** Shell/PowerShell setup downloads models once online. Then run locally
at `127.0.0.1:8000`, with bundled browser assets and 225 demo reviews.

Setup: [README.md](README.md). Product journeys: [DESIGN.md](DESIGN.md).
