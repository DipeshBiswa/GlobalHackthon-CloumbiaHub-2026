"""Replace the local review store with reviews from the visitor CSV."""

from __future__ import annotations

import csv
import json
import re
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

from review import Review
from review_storage import STORAGE_PATH
from translate_opus import translate_review

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "visitor_answers_syntheticdatasheet.csv"
YEAR = 2026
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def is_unclear(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return (
        normalized in {"?", "n/a", "na", "none", "not sure", "the thing at the end."}
        or len(re.sub(r"[^a-z]", "", normalized)) < 8
    )


def read_reviews() -> list[tuple[Review, bool]]:
    rows: list[tuple[Review, bool]] = []
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as file:
        for index, row in enumerate(csv.DictReader(file), start=2):
            month = row["Month (Jan-Dec)"].strip().lower()
            if month not in MONTHS:
                raise ValueError(f"Invalid month on CSV line {index}: {month!r}")
            favorite = row["Favorite Part"].strip()
            improvement = row["What could be better"].strip()
            review = Review(
                rating=float(row["Rating (stars)"]),
                language="en",
                date=date(YEAR, MONTHS[month], ((index - 2) % 28) + 1),
                favorite=favorite,
                improvement=improvement,
            )
            rows.append((review, is_unclear(favorite) or is_unclear(improvement)))
    return rows


def replace_store() -> dict[str, int]:
    translated = []
    for review, force_not_sure in read_reviews():
        result = translate_review(review)
        translated.append({
            "rating": result.rating,
            "language": result.language,
            "date": result.date.isoformat(),
            "favorite": result.favorite,
            "improvement": result.improvement,
            "original_favorite": result.original_favorite,
            "original_improvement": result.original_improvement,
            "force_not_sure": force_not_sure,
        })

    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=STORAGE_PATH.parent,
        prefix=f"{STORAGE_PATH.name}.", suffix=".tmp", delete=False,
    ) as file:
        json.dump(translated, file, ensure_ascii=False, indent=2)
        file.write("\n")
        temporary_path = Path(file.name)
    temporary_path.replace(STORAGE_PATH)
    return {
        "total": len(translated),
        "not_sure": sum(item["force_not_sure"] for item in translated),
    }


if __name__ == "__main__":
    print(json.dumps(replace_store(), indent=2))
