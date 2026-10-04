import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["ECHO_DB"] = str(Path(__file__).parent / "test-bootstrap.db")

@pytest.fixture
def client(tmp_path, monkeypatch):
    import store
    import echo_api
    from fastapi.testclient import TestClient
    from api import app
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "echo.db")
    echo_api.initialize()
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username":"noor", "password":"coffee2025"}).status_code == 200
        assert client.post("/api/pin/unlock", json={"pin":"0000"}).status_code == 200
        yield client

@pytest.fixture
def fast_pipeline(monkeypatch):
    import echo_api
    import translate_opus
    class Classifier:
        def classify_review(self, favorite, improvement, rating):
            topics = [] if "ambiguous" in favorite else [{"topic":"tour_difficulty", "sentiment":"negative", "classifier_score":.88, "field":"better", "phrase":"steep"}]
            return {"topics": topics, "uncertain":[], "classification_status":"classified" if topics else "not_sure"}
    monkeypatch.setattr(echo_api, "classifier", lambda: Classifier())
    monkeypatch.setattr(translate_opus, "translate", lambda text: "Tafsiri: " + text)
