"""Seed Noor's fictional full-year demo through real offline Echo processing.

Reset replaces only synthetic records for the local noor account. Live visitor
validation remains unchanged; simulated future dates are tooling-only metadata.
"""
import argparse
from calendar import monthrange
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sqlite3
import sys
from uuid import NAMESPACE_URL, uuid5

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from noor_feedback import FAVORITES, IMPROVEMENTS, PERSONAL_NOTES

MONTH_COUNTS = [10, 11, 17, 20, 26, 27, 28, 26, 20, 17, 12, 11]
RATING_WEIGHTS = {5: 124, 4: 67, 3: 22, 2: 9, 1: 3}


def apportion(count, weights):
    total = sum(weights)
    portions = [count * value / total for value in weights]
    result = [int(value) for value in portions]
    for i in sorted(range(len(weights)), key=lambda i: (-(portions[i]-result[i]), i))[:count-sum(result)]:
        result[i] += 1
    return result


def generate_sources(count=225, year=2026, seed=42):
    if count < 24:
        raise ValueError("At least 24 reviews are needed for a twelve-month story.")
    if not 1900 <= year <= 2100:
        raise ValueError("Year must be between 1900 and 2100.")
    rng = random.Random(seed)
    counts = apportion(count, MONTH_COUNTS)
    slots = [(month, position, size) for month, size in enumerate(counts, 1) for position in range(size)]
    # Busy visits tend to have lower ratings; October and year-end have stronger ratings.
    seasonal = {1:.2, 2:.25, 3:.35, 4:.4, 5:0, 6:-.1, 7:-.2, 8:-.1, 9:.55, 10:.9, 11:1, 12:1}
    ranking = sorted(range(count), key=lambda i: seasonal[slots[i][0]] + rng.random() * 1.6)
    star_counts = apportion(count, list(RATING_WEIGHTS.values()))
    stars = [star for star, amount in zip(RATING_WEIGHTS, star_counts) for _ in range(amount)]
    assigned = dict(zip(reversed(ranking), stars))
    # Strong late-year ratings still include some four-star visits; avoid three
    # unrealistically perfect months while preserving the overall distribution.
    donors = [i for i, (month, _, _) in enumerate(slots) if month < 10 and assigned[i] == 4]
    for month in [10, 11, 12]:
        targets = [i for i, (m, _, _) in enumerate(slots) if m == month and assigned[i] == 5]
        for target in targets[:max(1,round(counts[month-1]*.2))]:
            if donors:
                donor = donors.pop(0)
                assigned[donor], assigned[target] = 5, 4
    result, used = [], set()
    topic_names = list(FAVORITES)
    for index, (month, position, size) in enumerate(slots):
        rating = assigned[index]
        day = min(monthrange(year, month)[1], 1 + int((position + .35) * monthrange(year, month)[1] / size))
        visit_date = f"{year}-{month:02}-{day:02}"
        # Controlled complaints are disjoint by position. Everything else supports
        # the annual story without silently increasing group/seating complaint counts.
        scenario = None
        if month in {1, 2} and position in {0, 1, 2} or month in {3, 4} and position == 0:
            scenario = "information_signage"
        elif month in {5, 6, 7, 8} and position == 1:
            scenario = "group_size"
        elif month in {3, 7} and position == 2:
            scenario = "facilities"
        elif month in {5, 6, 7, 8} and position in {3, 5}:
            scenario = "coffee_tasting"
        elif month <= 8 and position in {4, 9}:
            scenario = "tour_difficulty"
        elif month in {5, 6, 7, 8} and position in {6, 11}:
            scenario = "coffee_roasting"
        elif position == size - 1:
            scenario = "souvenirs"
        elif month in {5, 6, 7, 8} and position in {12, 17}:
            scenario = "accessibility"
        elif rating <= 3:
            scenario = rng.choice(["tour_difficulty", "coffee_roasting", "timing_pacing", "price_value", "transportation"])
        elif rng.random() < (.15 if month >= 9 else .35):
            scenario = rng.choice(["souvenirs", "coffee_roasting", "timing_pacing", "accessibility", "price_value", "transportation"])
        if scenario:
            choices = IMPROVEMENTS[scenario]
            n = sum(r["synthetic_scenario"] == scenario for r in result)
            improvement = choices[n % len(choices)]
        else:
            improvement = ""
        preferred = "coffee_tasting" if month == 10 and position % 3 != 0 else topic_names[(index * 7 + month) % len(topic_names)]
        if preferred == "information_signage" and month < 5:
            preferred = "guide_quality"
        # Use short feedback, ordinary two-sentence feedback and occasional detail.
        for attempt in range(200):
            favorite = rng.choice(FAVORITES[preferred])
            if rng.random() < .66:
                favorite += " " + rng.choice(PERSONAL_NOTES)
            if position % 13 == 8:
                other = rng.choice(["coffee_education", "coffee_roasting", "local_culture", "scenery"])
                detail = rng.choice(FAVORITES[other])
                if len(favorite + " " + detail) <= 300:
                    favorite += " " + detail
            if (favorite, improvement) not in used:
                break
        else:
            raise ValueError("Could not produce enough varied feedback; reduce count.")
        # A few realistic improvement-only submissions, never the controlled cases.
        if scenario not in {"information_signage", "group_size", "facilities", "coffee_tasting"} and improvement and index % 19 == 10:
            favorite = ""
        used.add((favorite, improvement))
        result.append({"rating":rating, "date":visit_date, "language":"en",
                       "favorite_en":favorite, "improvement_en":improvement,
                       "share_consent":rng.random() < .64,
                       "synthetic_scenario":scenario, "synthetic_business":"Noor's Coffee Farm",
                       "synthetic_batch":f"noor-{year}-{seed}-{count}",
                       "synthetic_index":index,
                       "id":str(uuid5(NAMESPACE_URL, f"echo:noor:{year}:{seed}:{count}:{index}")),
                       "created_at":f"{visit_date}T{10 + position % 8:02}:{(index * 7) % 60:02}:00+00:00"})
    return sorted(result, key=lambda r:r["created_at"])


def report_for(reviews, plans):
    from echo_analytics import monthly, patterns, progress
    support = Counter((p["topic"], p["sentiment"]) for r in reviews
                      for p in { (p["topic"],p["sentiment"]):p for p in r["topics"] }.values())
    scenario_checks = []
    for topic, sentiment, expected in [("coffee_tasting","negative","high"),
                                       ("group_size","negative","medium"),
                                       ("facilities","request",None)]:
        count = support[(topic,sentiment)]
        observed = "high" if count >= 5 else "medium" if count >= 3 else None
        scenario_checks.append({"topic":topic,"sentiment":sentiment,"support":count,
                                "expected_confidence":expected,"observed_confidence":observed,
                                "passed":observed == expected})
    return {"business":"Noor's Coffee Farm", "review_count":len(reviews),
            "is_synthetic":True, "year":int(reviews[0]["date"][:4]),
            "rating_counts":dict(Counter(r["rating"] for r in reviews)),
            "mentions_noor":sum("noor" in (r["favorite_en"]+r["improvement_en"]).lower() for r in reviews),
            "unique_feedback_pairs":len({(r["favorite_en"],r["improvement_en"]) for r in reviews}),
            "blank_favorites":sum(not r["favorite_en"] for r in reviews),
            "blank_improvements":sum(not r["improvement_en"] for r in reviews),
            "topic_counts":dict(Counter(p["topic"] for r in reviews for p in r["topics"])),
            "classification_statuses":dict(Counter(r["classification_status"] for r in reviews)),
            "controlled_patterns":scenario_checks, "patterns":patterns(reviews),
            "months":[{k:v for k,v in monthly(f'{reviews[0]["date"][:4]}-{month:02}', reviews, plans).items() if k not in {"reviews","plans_tried"}} for month in range(1,13)],
            "plans":[{**p,"progress":progress(p,reviews)} for p in plans],
            "processing":"Local OPUS translation and MiniLM classification via shared review_pipeline; no topic overrides.",
            "future_dates":"Full simulated year; future dates are deliberate demo records, not real visitor submissions."}


def demo_plan(reviews, user_id, year, seed):
    from echo_analytics import baseline
    from knowledge import SUGGESTIONS
    started_at = f"{year}-05-01T00:00:00+00:00"
    before = [r for r in reviews if r["created_at"] < started_at]
    key = "information_signage:negative"
    approved = SUGGESTIONS[key]
    plan = {"id":str(uuid5(NAMESPACE_URL,f"echo:noor:directions-plan:{year}:{seed}")),
            "user_id":user_id,"key":key,"topic":approved["topic"],
            "title":"Clearer directions to Noor's farm", "description":approved["suggestion"],
            "status":"trying","created_at":started_at,"started_at":started_at,
            "updated_at":started_at,"is_synthetic":True,
            "synthetic_business":"Noor's Coffee Farm"}
    plan.update(baseline(plan,before))
    if plan["topic_count_at_start"] < 3:
        return []
    return [plan]


def persist_demo(reviews, plans, user_id, reset=False):
    import store
    # One transaction: failed processing never removes the previous demo.
    with store.connect() as db:
        if reset:
            for table in ["reviews", "plans"]:
                db.execute(f"DELETE FROM {table} WHERE user_id=? AND json_extract(data,'$.is_synthetic')=1",(user_id,))
        for r in reviews:
            db.execute("INSERT INTO reviews VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,created_at=excluded.created_at,deleted=excluded.deleted",
                       (r["id"],user_id,r["created_at"],int(r["deleted"]),json.dumps(r,ensure_ascii=False)))
        for p in plans:
            db.execute("INSERT INTO plans VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",(p["id"],user_id,json.dumps(p,ensure_ascii=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count",type=int,default=225)
    parser.add_argument("--year",type=int,default=2026)
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument("--reset",action="store_true",help="Replace only Noor's synthetic reviews/plans; preserve real data.")
    parser.add_argument("--batch-size",type=int,default=8)
    parser.add_argument("--threads",type=int,default=4,help="CPU inference threads for the development batch.")
    parser.add_argument("--output-dir",type=Path,default=BACKEND/"data"/"synthetic")
    args = parser.parse_args()
    sources = generate_sources(args.count,args.year,args.seed)
    import torch
    torch.set_num_threads(max(1,args.threads))
    import store
    from echo_api import initialize, classifier
    from review_pipeline import process_review
    from translate_opus import translate, translate_many
    initialize()
    with store.connect() as db:
        user_id = db.execute("SELECT id FROM users WHERE username='noor'").fetchone()[0]
    args.output_dir.mkdir(parents=True,exist_ok=True)
    cache_path = args.output_dir/"opus_translation_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    cache_version = "opus-mt-en-sw:beams8:max256:v1"
    if cache.get("model") != cache_version:
        cache = {"model":cache_version,"translations":{}}
    translations = cache["translations"]
    texts = list(dict.fromkeys(r[field] for r in sources for field in ["favorite_en","improvement_en"] if r[field].strip()))
    missing = [text for text in texts if text not in translations]
    print(f"Generating {len(sources)} reviews; {len(missing)} distinct texts need local OPUS translation.",flush=True)
    # Checkpoint every batch so an interrupted development run can resume.
    for start in range(0,len(missing),args.batch_size):
        batch = missing[start:start+args.batch_size]
        translations.update(zip(batch,translate_many(batch,args.batch_size)))
        cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding="utf-8")
        print(f"Translated {min(start+len(batch),len(missing))}/{len(missing)} texts",flush=True)
    model = classifier()
    reviews = []
    for i, source in enumerate(sources,1):
        record_id, created_at = source["id"], source["created_at"]
        record = process_review(source,translate,model,record_id=record_id,created_at=created_at,
                                is_synthetic=True,translations=translations)
        reviews.append(record)
        if i % 25 == 0 or i == len(sources):
            print(f"Classified {i}/{len(sources)} reviews",flush=True)
    plans = demo_plan(reviews,user_id,args.year,args.seed)
    report = report_for(reviews,plans)
    # The default controlled demonstration must reflect actual classifier output.
    if args.count == 225 and args.year == 2026 and args.seed == 42 and (
        not all(c["passed"] for c in report["controlled_patterns"])
        or not report["plans"] or report["plans"][0]["progress"].get("res") != "better"
    ):
        (args.output_dir/"failed_pattern_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        raise RuntimeError("Controlled patterns did not match real classifier output. Database was left unchanged; inspect failed_pattern_report.json.")
    backup_dir = BACKEND/"data"/"backups"
    backup_dir.mkdir(parents=True,exist_ok=True)
    backup = backup_dir/("echo-before-synthetic-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")+".db")
    with store.connect() as source_db, sqlite3.connect(backup) as target_db:
        source_db.backup(target_db)
    persist_demo(reviews,plans,user_id,args.reset)
    (args.output_dir/"noor_reviews.json").write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.output_dir/"noor_demo_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"database":str(store.DB_PATH),"review_count":len(reviews),"rating_counts":report["rating_counts"],"controlled_patterns":report["controlled_patterns"],"backup":str(backup)},indent=2),flush=True)


if __name__ == "__main__":
    main()
