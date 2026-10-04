"""Real models, with every outgoing socket connection rejected."""
import json
import socket
from pathlib import Path

def test_real_offline_vertical_slice(client, monkeypatch, tmp_path):
    def blocked(*args, **kwargs):
        raise AssertionError("Runtime attempted network access")
    monkeypatch.setattr(socket.socket,"connect",blocked)
    import echo_api
    echo_api.classifier.cache_clear()
    model = echo_api.classifier()
    result = model.classify_review("The guide was great, but the path was too steep and the tour felt rushed.", "", 5)
    pairs = {(p["topic"],p["sentiment"]) for p in result["topics"]}
    assert {("guide_quality","positive"),("tour_difficulty","negative"),("timing_pacing","negative")} <= pairs
    uncertain = model.classify_review("xyzzy quux 7392", "", 3)
    assert uncertain["classification_status"] == "not_sure"
    import translate_opus
    import importlib
    import os
    # Reload OPUS after installing the socket guard: startup loading is tested too.
    importlib.reload(translate_opus)
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
    text = "The guide was friendly."
    sw = translate_opus.translate(text)
    assert sw and sw != text
    assert translate_opus.translate("  ") == ""
    assert translate_opus.translate_many([text,""],batch_size=2) == [sw,""]
    examples = []
    for _ in range(3):
        response = client.post("/api/reviews",json={"rating":5,"favorite_en":text,"improvement_en":""})
        assert response.status_code == 201, response.text
        review = response.json()
        assert review["favorite_en"] == text and review["favorite_sw"] == sw
        assert review["improvement_sw"] == ""
        examples.append(review)
    suggestions = client.get("/api/suggestions").json()
    assert any(p["key"] == "guide_quality:positive" and p["pattern_confidence"] == "medium" for p in suggestions)
    evidence = {"english":text,"kiswahili":sw,"classification":result,"suggestions":suggestions,"network":"all socket.connect calls blocked"}
    output = Path(__file__).resolve().parents[1] / "test-results"
    output.mkdir(exist_ok=True)
    (output / "offline-example.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")

def test_frontend_assets_have_no_external_runtime_sources(client):
    html = client.get("/").text
    assert 'src="https://' not in html and 'href="https://' not in html
    for path in ["vendor/react.production.min.js","vendor/react-dom.production.min.js","vendor/htm.umd.js","vendor/fonts.css","api-client.js","scripts.js"]:
        response = client.get('/'+path)
        assert response.status_code == 200
        if path.endswith("fonts.css"): assert "https://" not in response.text
