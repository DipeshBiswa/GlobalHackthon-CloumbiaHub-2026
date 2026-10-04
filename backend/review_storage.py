"""JSON-file storage for translated reviews."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from review import TranslatedReview

STORAGE_PATH = Path(__file__).resolve().parent / "translated_reviews.json"


def load_translated_reviews() -> list[dict[str, Any]]:
    """Load all stored reviews, returning an empty list for a new store."""
    if not STORAGE_PATH.exists():
        return []

    with STORAGE_PATH.open("r", encoding="utf-8") as file:
        reviews = json.load(file)

    if not isinstance(reviews, list):
        raise ValueError("translated review storage must contain a JSON array.")
    return reviews


def save_translated_reviews(reviews: list[TranslatedReview]) -> None:
    """Append translated reviews to the JSON store with an atomic file replace."""
    stored_reviews = load_translated_reviews()
    stored_reviews.extend(review_to_dict(review) for review in reviews)

    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=STORAGE_PATH.parent,
        prefix=f"{STORAGE_PATH.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        json.dump(stored_reviews, temporary_file, ensure_ascii=False, indent=2)
        temporary_file.write("\n")
        temporary_path = Path(temporary_file.name)

    os.replace(temporary_path, STORAGE_PATH)


def review_to_dict(review: TranslatedReview) -> dict[str, Any]:
    """Convert a translated review to the JSON storage representation."""
    return {
        "rating": review.rating,
        "language": review.language,
        "date": review.date.isoformat(),
        "favorite": review.favorite,
        "improvement": review.improvement,
        "original_favorite": review.original_favorite,
        "original_improvement": review.original_improvement,
        "force_not_sure": review.force_not_sure,
    }
