from datetime import date
import pytest
from echo_analytics import patterns
from knowledge import SUGGESTIONS

def submit(client, **values):
    payload = {"rating":5,"favorite_en":"The guide was great.","improvement_en":"The path was too steep."}
    payload.update(values)
    response = client.post("/api/reviews",json=payload)
    assert response.status_code == 201, response.text
    return response.json()

def test_review_storage_validation_filters_restore(client, fast_pipeline):
    for payload in [{"rating":5}, {"rating":0,"favorite_en":"Good"}, {"rating":True,"favorite_en":"Good"}, {"rating":5,"favorite_en":"..."}, {"rating":5,"favorite_en":"Hello","language":"sw"}]:
        assert client.post("/api/reviews",json=payload).status_code == 422
    r = submit(client, favorite_en="  Original English  ",improvement_en="",share_consent=True)
    assert r["favorite_en"] == "  Original English  "
    assert r["favorite_sw"] == "Tafsiri:   Original English  "
    assert r["improvement_sw"] == ""
    assert r["share_consent"] and r["translation_status"] == "translated"
    assert client.get("/api/reviews/"+r["id"]).json() == r
    assert len(client.get("/api/reviews?filter=5").json()) == 1
    assert client.get("/api/reviews?filter=4").json() == []
    assert client.get("/api/reviews?filter=3").json() == []
    assert len(client.get("/api/reviews?filter=complaint").json()) == 1
    assert client.get("/api/reviews?filter=bogus").status_code == 422
    assert client.delete("/api/reviews/"+r["id"]).status_code == 200
    assert client.get("/api/reviews").json() == []
    assert client.patch("/api/reviews/"+r["id"]+"/restore").status_code == 200
    assert len(client.get("/api/reviews").json()) == 1
    submit(client, favorite_en="", improvement_en="A steep path")
    assert client.get("/api/reviews").json()[0]["favorite_sw"] == ""

def test_uncertainty_correction_preserves_prediction(client, fast_pipeline):
    r = submit(client, favorite_en="ambiguous",improvement_en="")
    assert r["classification_status"] == "not_sure"
    assert len(client.get("/api/reviews?filter=not_sure").json()) == 1
    result = client.patch(f'/api/reviews/{r["id"]}/classification',json={"topics":[{"topic":"guide_quality","sentiment":"positive"}],"checked":True}).json()
    assert result["model_prediction"] == r["model_prediction"]
    assert result["manual_override"]["checked"]
    assert result["topics"][0]["classifier_score"] is None
    assert result["classification_status"] == "classified"
    assert client.get("/api/reviews?filter=not_sure").json() == []
    assert client.patch(f'/api/reviews/{r["id"]}/classification',json={"topics":[{"topic":"invented","sentiment":"positive"}]}).status_code == 422

@pytest.mark.parametrize("count,confidence",[(1,None),(2,None),(3,"medium"),(4,"medium"),(5,"high"),(6,"high")])
def test_support_distinct_reviews(count, confidence):
    topic = {"topic":"tour_difficulty","sentiment":"negative","classifier_score":.99}
    rs = [{"id":str(i),"topics":[topic,topic]} for i in range(count)]
    result = patterns(rs)
    if confidence is None:
        assert result == []
    else:
        assert result[0]["supporting_review_count"] == count
        assert result[0]["pattern_confidence"] == confidence
        assert result[0]["suggestion"] == SUGGESTIONS["tour_difficulty:negative"]["suggestion"]

def test_plans_baseline_progress_dashboard_monthly(client, fast_pipeline):
    assert client.post("/api/plans",json={"key":"tour_difficulty:negative"}).status_code == 422
    for _ in range(3): submit(client)
    stats = client.get("/api/dashboard").json()
    assert stats == {"reviews_this_week":3,"average_rating":5,"new_reviews":3,"not_sure_count":0,"active_plan_count":0}
    suggestion = client.get("/api/suggestions").json()[0]
    assert suggestion["pattern_confidence"] == "medium"
    p = client.post("/api/plans",json={"key":suggestion["key"],"status":"saved"}).json()
    assert p["started_at"] is None
    p = client.patch('/api/plans/'+p["id"],json={"status":"trying"}).json()
    assert p["review_count_at_start"] == 3 and p["topic_count_at_start"] == 3 and p["average_rating_at_start"] == 5
    assert client.get("/api/dashboard").json()["active_plan_count"] == 1
    for _ in range(2): submit(client,favorite_en="ambiguous",improvement_en="")
    assert client.get("/api/plans").json()[0]["progress"] == {"waiting":True,"n":2}
    submit(client,favorite_en="ambiguous",improvement_en="")
    progress = client.get("/api/plans").json()[0]["progress"]
    assert not progress["waiting"] and progress["res"] == "better"
    for status in ["done","saved","trying","stopped"]:
        assert client.patch('/api/plans/'+p["id"],json={"status":status}).json()["status"] == status
    assert client.patch('/api/plans/'+p["id"],json={"status":"bad"}).status_code == 422
    month = client.get("/api/performance/monthly?month="+date.today().strftime("%Y-%m")).json()
    assert month["review_count"] == 6 and month["average_rating"] == 5
    assert month["top_negative_topics"][0]["supporting_review_count"] == 3
    assert len(month["plans_tried"]) == 1
    assert client.get("/api/performance/monthly?month=bad").status_code == 422
    client.post("/api/reviews/seen")
    assert client.get("/api/dashboard").json()["new_reviews"] == 0
    client.post("/api/suggestions/decision",json={"key":suggestion["key"]})
    assert client.get("/api/suggestions").json() == []
    client.post("/api/suggestions/decision",json={"key":suggestion["key"],"ignored":False})
    assert len(client.get("/api/suggestions").json()) == 1
    assert client.delete('/api/plans/'+p["id"]).status_code == 200

def test_login_pin_lockout_account_isolation(client, fast_pipeline):
    r = submit(client)
    client.post("/api/pin/lock")
    assert client.get("/api/dashboard").status_code == 403
    submit(client)  # Visitors can submit while the owner dashboard is locked.
    for _ in range(4): assert client.post("/api/pin/unlock",json={"pin":"1111"}).status_code == 401
    assert client.post("/api/pin/unlock",json={"pin":"1111"}).status_code == 429
    assert client.post("/api/pin/unlock",json={"pin":"0000"}).status_code == 429
    client.post("/api/auth/logout")
    assert client.get("/api/reviews").status_code == 401
    assert client.post("/api/auth/login",json={"username":"noor","password":"incorrect"}).status_code == 401
    assert client.post("/api/auth/signup",json={"username":"second","password":"goodpassword","display_name":"Second"}).status_code == 201
    assert client.post("/api/pin/unlock",json={"pin":"0000"}).status_code == 200
    assert client.get("/api/reviews").json() == []
    assert client.get('/api/reviews/'+r["id"]).status_code == 404
    assert client.delete('/api/reviews/'+r["id"]).status_code == 404
    assert client.patch("/api/pin",json={"pin":"1234"}).status_code == 200
    client.post("/api/pin/lock")
    assert client.post("/api/pin/unlock",json={"pin":"1234"}).status_code == 200

def test_month_boundary_and_progress_directions():
    from echo_analytics import monthly, baseline, progress
    r = {"id":"old","date":"2025-12-31","created_at":"2025-12-31T00:00:00","rating":3,"topics":[]}
    new = {**r,"id":"new","date":"2026-01-01","rating":5}
    assert monthly("2026-01",[r,new],[])["change_from_previous_month"] == 2
    topic = {"topic":"guide_quality","sentiment":"positive"}
    p = {"key":"guide_quality:positive","started_at":"2026-01-01"}
    p.update(baseline(p,[r]))
    rs = [{**new,"id":str(i),"created_at":"2026-01-02","topics":[topic]} for i in range(3)]
    assert progress(p,rs)["res"] == "better"
    p["topic_count_at_start"] = 1
    assert progress(p,rs)["res"] == "same"
    for review in rs: review["topics"] = []
    assert progress(p,rs)["res"] == "worse"
