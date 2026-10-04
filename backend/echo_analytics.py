"""Deterministic statistics, support thresholds and approved advice."""
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean
from knowledge import RULES, SUGGESTIONS

def average(reviews):
    return round(mean(r["rating"] for r in reviews), 2) if reviews else 0

def patterns(reviews):
    groups = defaultdict(list)
    for review in reviews:
        for key in {p["topic"] + ":" + p["sentiment"] for p in review["topics"]}:
            groups[key].append(review["id"])
    result = []
    for key, ids in sorted(groups.items(), key=lambda item: -len(item[1])):
        if len(ids) < RULES["min_support"] or key not in SUGGESTIONS:
            continue
        result.append({"key": key, **SUGGESTIONS[key], "supporting_review_count": len(ids),
                       "pattern_confidence": "high" if len(ids) >= RULES["high_support"] else "medium",
                       "review_ids": ids})
    return result

def dashboard(reviews, plans, last_seen=""):
    today = date.today()
    week = [r for r in reviews if (today - timedelta(days=6)).isoformat() <= r["date"] <= today.isoformat()]
    return {"reviews_this_week": len(week), "average_rating": average(reviews),
            "new_reviews": sum(not r.get("owner_seen", r["created_at"] <= last_seen) for r in reviews),
            "not_sure_count": sum(r["classification_status"] == "not_sure" for r in reviews),
            "active_plan_count": sum(p["status"] == "trying" for p in plans)}

def baseline(plan, reviews):
    key = plan["key"]
    return {"review_count_at_start": len(reviews), "average_rating_at_start": average(reviews),
            "topic_count_at_start": sum(any(p["topic"] + ":" + p["sentiment"] == key for p in r["topics"]) for r in reviews),
            "review_ids_at_start": [r["id"] for r in reviews]}

def progress(plan, reviews):
    if not plan.get("started_at"):
        return {"waiting": True, "n": 0}
    after = [r for r in reviews if r["id"] not in plan["review_ids_at_start"] and r["created_at"] > plan["started_at"]]
    count = sum(any(p["topic"] + ":" + p["sentiment"] == plan["key"] for p in r["topics"]) for r in after)
    if len(after) < 3:
        return {"waiting": True, "n": len(after)}
    before = plan["topic_count_at_start"] / max(1, plan["review_count_at_start"])
    delta = count / len(after) - before
    positive = plan["key"].endswith(":positive")
    result = "same" if abs(delta) <= .1 else "better" if (delta > 0) == positive else "worse"
    return {"waiting": False, "n": len(after), "c": count, "total": len(after), "res": result,
            "average_rating_after": average(after)}

def monthly(month, reviews, plans):
    year, number = map(int, month.split("-"))
    previous = f"{year-1}-12" if number == 1 else f"{year}-{number-1:02}"
    current = [r for r in reviews if r["date"].startswith(month)]
    prior = [r for r in reviews if r["date"].startswith(previous)]
    groups = defaultdict(set)
    for r in current:
        for p in r["topics"]:
            groups[(p["topic"], p["sentiment"])].add(r["id"])
    def top(sentiment):
        return [{"topic": topic, "supporting_review_count": len(ids)} for (topic, feeling), ids in sorted(groups.items(), key=lambda x: -len(x[1])) if feeling == sentiment][:3]
    return {"month": month, "review_count": len(current), "average_rating": average(current),
            "change_from_previous_month": round(average(current)-average(prior), 2) if current and prior else None,
            "top_positive_topics": top("positive"), "top_negative_topics": top("negative"),
            "plans_tried": [p for p in plans if (p.get("started_at") or "").startswith(month)], "reviews": current}
