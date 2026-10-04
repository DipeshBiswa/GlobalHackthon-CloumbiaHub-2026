"""Development-only Yelp pattern audit. Never imports reviews into Echo."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from farm_taxonomy import TOPICS as FARM_TOPICS, LEGACY_ALIASES

# The coffee-farm taxonomy is a reviewed development source.
TOPICS = FARM_TOPICS

def build(source, output):
    reviews = json.loads(Path(source).read_text(encoding="utf-8-sig"))
    counts, categories = Counter(), Counter()
    for review in reviews:
        text = review["text"].lower()
        categories.update(x.strip() for x in review.get("categories", "").split(","))
        for topic, (_, _, phrases, _, _) in TOPICS.items():
            if any(re.search(r"\b" + re.escape(p) + r"\b", text) for p in phrases):
                counts[topic] += 1
    rules = {"version": 2, "phrase_threshold": 0.30, "semantic_threshold": 0.42, "semantic_margin": 0.06,
             "min_support": 3, "high_support": 5, "legacy_topic_aliases": LEGACY_ALIASES, "topics": {}}
    suggestions = {}
    for topic, (name, sw, phrases, positive, negative) in TOPICS.items():
        rules["topics"][topic] = {"name": name, "name_sw": sw, "phrases": phrases,
                                  "description": name + ": " + ", ".join(phrases)}
        for sentiment, advice in [("positive", positive), ("negative", negative),
                                  ("request", negative)]:
            key = topic + ":" + sentiment
            summary = {"positive": "Visitors praised", "negative": "Visitors raised concerns about", "request": "Visitors asked for improvements to"}[sentiment] + " " + name.lower() + "."
            suggestions[key] = {"topic": topic, "sentiment": sentiment, "title": name,
                                "summary": summary, "suggestion": advice}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Keep precomputed localizations only when their English source is unchanged.
    previous_path = output / "echo_suggestions.json"
    if previous_path.exists():
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        for key, rule in suggestions.items():
            old = previous.get(key, {})
            for field in ["title", "summary", "suggestion"]:
                if old.get(field) == rule[field] and old.get(field + "_sw"):
                    rule[field + "_sw"] = old[field + "_sw"]
    for name, value in [("echo_topic_rules.json", rules), ("echo_suggestions.json", suggestions),
                        ("yelp_knowledge_audit.json", {"sample_count": len(reviews), "topic_review_matches": dict(counts), "top_categories": categories.most_common(20),
                         "method": "Case-insensitive whole-phrase review counts; no raw text retained. Thresholds are application defaults, not calibrated probabilities.",
                         "taxonomy_decisions": "Coffee-farm specialization requested for Noor's demo: 17 active topics distinguish education, roasting, tasting, farm content, scenery and culture. Four legacy topic names retain read-time aliases. Yelp counts assess phrase coverage; coffee-specific categories and advice are business requirements, not inferred training labels."})]:
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return counts

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "data"))
    args = parser.parse_args()
    print(dict(build(args.source, args.output)))
