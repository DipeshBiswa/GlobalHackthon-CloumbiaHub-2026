"""Validate the checked-in, actually processed demo artifact against product cases."""
from collections import Counter
import json
from pathlib import Path

def test_processed_noor_demo_has_translations_and_measured_patterns():
    from echo_analytics import patterns, progress
    from knowledge import RULES
    directory = Path(__file__).resolve().parents[1] / "data" / "synthetic"
    reviews = json.loads((directory/"noor_reviews.json").read_text(encoding="utf-8"))
    report = json.loads((directory/"noor_demo_report.json").read_text(encoding="utf-8"))
    assert len(reviews) == 225
    assert {r["date"][:7] for r in reviews} == {f"2026-{month:02}" for month in range(1,13)}
    required = {"id","rating","date","created_at","favorite_en","favorite_sw","improvement_en","improvement_sw","share_consent","translation_status","classification_status","topics","is_synthetic","deleted"}
    assert all(required <= r.keys() for r in reviews)
    for review in reviews:
        assert review["is_synthetic"] and not review["deleted"]
        assert review["synthetic_business"] == "Noor's Coffee Farm"
        assert review["translation_status"] == "translated"
        assert bool(review["favorite_en"].strip()) == bool(review["favorite_sw"].strip())
        assert bool(review["improvement_en"].strip()) == bool(review["improvement_sw"].strip())
        assert review["manual_override"] is None
        assert review["topics"] == review["model_prediction"]["topics"]
        assert all(p["topic"] in RULES["topics"] and p["method"] in {"minilm","phrase+minilm"} for p in review["topics"])
    groups = {p["key"]:p for p in patterns(reviews)}
    assert groups["coffee_tasting:negative"]["supporting_review_count"] >= 5
    assert groups["coffee_tasting:negative"]["pattern_confidence"] == "high"
    assert groups["group_size:negative"]["supporting_review_count"] == 4
    assert groups["group_size:negative"]["pattern_confidence"] == "medium"
    assert "facilities:request" not in groups
    assert sum(any(p["topic"] == "facilities" and p["sentiment"] == "request" for p in r["topics"]) for r in reviews) == 2
    assert len(report["plans"]) == 1
    assert progress(report["plans"][0],reviews)["res"] == "better"
    assert Counter(r["rating"] for r in reviews) == {5:124,4:67,3:22,2:9,1:3}

def test_legacy_topic_aliases_preserve_original_predictions(client):
    import store
    with store.connect() as db:
        owner = db.execute("SELECT id FROM users WHERE username='noor'").fetchone()[0]
    prediction = {"topics":[{"topic":"food_tasting","sentiment":"positive","classifier_score":.6}]}
    record = {"id":"legacy","created_at":"2025-01-01","favorite_en":"The coffee tasting was lovely.","topics":prediction["topics"],"model_prediction":prediction}
    store.put("reviews",record,owner)
    result = store.records("reviews",owner)[0]
    assert result["topics"][0]["topic"] == "coffee_tasting"
    assert result["model_prediction"]["topics"][0]["topic"] == "food_tasting"
    assert result["favorite_en"] == record["favorite_en"]
