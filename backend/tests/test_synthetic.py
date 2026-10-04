"""Demo generation tests; no writes to the actual owner database."""
from pathlib import Path
import sys
from collections import Counter
import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0,str(TOOLS))
from generate_synthetic_reviews import generate_sources, persist_demo, demo_plan
from review_pipeline import process_review


def test_default_sources_are_reproducible_full_year_coffee_farm():
    reviews = generate_sources()
    assert reviews == generate_sources()
    assert reviews != generate_sources(seed=43)
    assert len(reviews) == 225
    assert len({r["id"] for r in reviews}) == 225
    assert len({(r["favorite_en"],r["improvement_en"]) for r in reviews}) == 225
    assert Counter(r["date"][5:7] for r in reviews) == dict(zip([f"{m:02}" for m in range(1,13)],[10,11,17,20,26,27,28,26,20,17,12,11]))
    assert Counter(r["rating"] for r in reviews) == {5:124,4:67,3:22,2:9,1:3}
    assert sum("noor" in (r["favorite_en"]+r["improvement_en"]).lower() for r in reviews) > 150
    assert all(r["synthetic_business"] == "Noor's Coffee Farm" for r in reviews)
    assert all(r["favorite_en"] or r["improvement_en"] for r in reviews)
    assert any(not r["favorite_en"] for r in reviews) and any(not r["improvement_en"] for r in reviews)
    assert all(len(r["favorite_en"]) <= 300 and len(r["improvement_en"]) <= 300 for r in reviews)
    assert Counter(r["synthetic_scenario"] for r in reviews)["group_size"] == 4
    assert Counter(r["synthetic_scenario"] for r in reviews)["facilities"] == 2
    assert not any(r["synthetic_scenario"] == "information_signage" for r in reviews if r["date"] >= "2026-05-01")


@pytest.mark.parametrize("count",[200,250])
def test_requested_count_variants(count):
    reviews = generate_sources(count=count,year=2025,seed=7)
    assert len(reviews) == count
    assert len({r["date"][:7] for r in reviews}) == 12
    assert all(r["date"].startswith("2025") for r in reviews)


def test_shared_pipeline_marks_real_and_demo_reviews_without_overriding_classifier():
    class Model:
        def classify_review(self,*args):
            return {"topics":[{"topic":"coffee_roasting","sentiment":"positive","classifier_score":.7}],"classification_status":"classified","uncertain":[]}
    source = {"rating":5,"date":"2026-12-15","favorite_en":"Noor roasted coffee for us.","improvement_en":"","share_consent":False}
    calls = []
    def translate(text):
        calls.append(text)
        return "Kahawa ya Noor."
    demo = process_review(source,translate,Model(),is_synthetic=True,created_at="2026-12-15T12:00:00+00:00")
    assert calls == [source["favorite_en"]]
    assert demo["favorite_en"] == source["favorite_en"] and demo["favorite_sw"] == "Kahawa ya Noor."
    assert demo["improvement_sw"] == "" and demo["is_synthetic"] is True
    assert demo["topics"] == demo["model_prediction"]["topics"]
    assert demo["topics"] is not demo["model_prediction"]["topics"]
    live = process_review(source,translate,Model())
    assert live["is_synthetic"] is False


def test_reset_preserves_real_reviews_other_accounts_and_real_plans(client, fast_pipeline):
    import store
    with store.connect() as db:
        owner = db.execute("SELECT id FROM users WHERE username='noor'").fetchone()[0]
        db.execute("INSERT INTO users(id,username,password_hash,display_name,pin_hash) VALUES('other','other','hash','Other','hash')")
    real = client.post("/api/reviews",json={"rating":5,"favorite_en":"Actual visitor feedback"}).json()
    old = {**real,"id":"old-synthetic","is_synthetic":True}
    other = {**old,"id":"other-owner-review"}
    store.put("reviews",old,owner)
    store.put("reviews",other,"other")
    store.put("plans",{"id":"real-plan","key":"tour_difficulty:negative","is_synthetic":False},owner)
    store.put("plans",{"id":"old-demo-plan","key":"tour_difficulty:negative","is_synthetic":True},owner)
    new = {**old,"id":"new-synthetic"}
    persist_demo([new],[],owner,reset=True)
    assert {r["id"] for r in store.records("reviews",owner)} == {real["id"],new["id"]}
    assert {p["id"] for p in store.records("plans",owner)} == {"real-plan"}
    assert [r["id"] for r in store.records("reviews","other")] == [other["id"]]
    persist_demo([new],[],owner,reset=False)
    assert len(store.records("reviews",owner)) == 2


def test_future_dates_remain_rejected_by_live_api_and_demo_seen_count_works(client,fast_pipeline):
    response = client.post("/api/reviews",json={"rating":5,"date":"2099-12-31","favorite_en":"Real visitor"})
    assert response.status_code == 422
    import store
    with store.connect() as db:
        owner = db.execute("SELECT id FROM users WHERE username='noor'").fetchone()[0]
    demo = {"id":"future-demo","rating":5,"date":"2099-12-31","created_at":"2099-12-31T12:00:00+00:00","favorite_en":"Noor's farm","favorite_sw":"Shamba la Noor","improvement_en":"","improvement_sw":"","classification_status":"classified","topics":[],"is_synthetic":True,"owner_seen":False}
    store.put("reviews",demo,owner)
    assert client.get("/api/dashboard").json()["new_reviews"] == 1
    client.post("/api/reviews/seen")
    assert client.get("/api/dashboard").json()["new_reviews"] == 0
    client.post("/api/reviews",json={"rating":5,"favorite_en":"A new real visitor"})
    assert client.get("/api/dashboard").json()["new_reviews"] == 1


def test_local_classifier_respects_positive_topic_wording_in_low_star_review():
    from insight_model import sentiment_of
    assert sentiment_of("Our group size was comfortable",2,"favorite") == "positive"
    assert sentiment_of("I liked the small group",1,"favorite") == "positive"
    assert sentiment_of("The large group made it difficult to hear Noor",5,"better") == "negative"
