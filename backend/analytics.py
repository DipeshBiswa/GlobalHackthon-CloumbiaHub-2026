"""Structured tourism insights built from classified reviews."""

from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Any

from insight_model import InsightModel

RECOMMENDATIONS = {
    "guide_quality": "Keep investing in friendly, knowledgeable guides.",
    "scenery": "Preserve the best viewpoints and allow time for photos.",
    "culture_history": "Give the cultural and historical stops more time.",
    "food": "Keep the most popular food experiences and tasting options.",
    "coffee_roasting": "Make coffee roasting a highlight and give it more time.",
    "tour_difficulty": "Offer a shorter route and add rest stops.",
    "tour_timing": "Increase time at the stops visitors mention most.",
    "group_size": "Offer smaller groups or a smaller-group option.",
    "transportation": "Improve pickup, parking, route, and transport instructions.",
    "accessibility": "Publish accessibility details and add seating or shade.",
    "souvenirs": "Offer small local products or souvenirs to take home.",
}


@dataclass(frozen=True)
class ClassifiedReview:
    rating: float
    date: str
    text: str
    topic: str
    score: float
    sentiment: str


def build_insights(
    reviews: list[dict[str, Any]],
    model: InsightModel,
) -> dict[str, Any]:
    classified: list[ClassifiedReview] = []
    for review in reviews:
        favorite = str(review.get("favorite", "")).strip()
        improvement = str(review.get("improvement", "")).strip()
        text = f"{favorite} {improvement}".strip()
        prediction = model.classify(text)
        rating = float(review["rating"])
        sentiment = "positive" if rating >= 4 else "negative" if rating <= 2 else "mixed"
        classified.append(
            ClassifiedReview(
                rating=rating,
                date=str(review["date"]),
                text=text,
                topic=prediction.topic,
                score=prediction.score,
                sentiment=sentiment,
            )
        )

    total = len(classified)
    counts = Counter(item.topic for item in classified)
    themes = []
    for topic, count in counts.most_common():
        percentage = round(count / total * 100, 1) if total else 0
        confidence = "high" if count >= 5 and percentage >= 20 else (
            "medium" if count >= 3 and percentage >= 10 else "low"
        )
        themes.append(
            {
                "topic": topic,
                "visitor_count": count,
                "percentage": percentage,
                "confidence": confidence,
                "recommendation": RECOMMENDATIONS[topic],
                "evidence": [
                    item.text for item in classified if item.topic == topic
                ][:3],
            }
        )

    ratings = [item.rating for item in classified]
    return {
        "total_reviews": total,
        "average_rating": round(mean(ratings), 2) if ratings else 0,
        "positive_review_percentage": round(
            sum(item.sentiment == "positive" for item in classified) / total * 100, 1
        ) if total else 0,
        "themes": themes,
    }
