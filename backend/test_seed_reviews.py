"""Regression checks for monthly demo coverage and safe, repeatable seeding."""

from collections import Counter
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from seed_reviews import ROOT, build_demo_reviews, review_key, seed_reviews, top_up_store


class MonthlyReviewSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = json.loads((ROOT / "backend" / "reviews.json").read_text(encoding="utf-8"))
        cls.original_samples = [review for review in fixture if not review.get("is_demo")]

    def test_every_month_has_fifteen_valid_bilingual_demos(self):
        source, translated = build_demo_reviews(self.original_samples)
        self.assertEqual(source[:len(self.original_samples)], self.original_samples)
        self.assertEqual(len(source), 180)
        self.assertEqual(len(translated), 180)
        self.assertEqual(
            Counter(review["date"][:7] for review in translated),
            {f"2026-{month:02d}": 15 for month in range(1, 13)},
        )
        self.assertEqual(len({review_key(review) for review in translated}), 180)
        for english, swahili in zip(source, translated):
            self.assertEqual(date.fromisoformat(english["date"]).year, 2026)
            self.assertTrue(1 <= english["rating"] <= 5)
            self.assertEqual(english["language"], "en")
            self.assertEqual(swahili["language"], "sw")
            self.assertTrue(swahili["is_demo"])
            self.assertEqual(review_key(english), review_key(swahili))
            self.assertNotEqual(english["favorite"], swahili["favorite"])
            self.assertNotEqual(english["improvement"], swahili["improvement"])
        self.assertEqual(build_demo_reviews(source), (source, translated))

    def test_top_up_preserves_existing_duplicates_and_busy_months(self):
        _, demos = build_demo_reviews(self.original_samples)
        original = {
            "rating": 4, "language": "sw", "date": "2026-10-04",
            "favorite": "Tulifurahia ziara.", "improvement": "Muda zaidi ungependeza.",
            "original_favorite": "We enjoyed the visit.",
            "original_improvement": "More time would be nice.",
            "custom_metadata": "must survive seeding",
        }
        stored = [dict(original) for _ in range(40)]
        stored += [dict(original, date="2026-09-15") for _ in range(6)]
        result = top_up_store(stored, demos)
        self.assertEqual(result[:len(stored)], stored)
        self.assertEqual(len(stored), 46)
        self.assertEqual(len(result), 205)
        counts = Counter(review["date"][:7] for review in result)
        self.assertEqual(counts["2026-10"], 40)
        self.assertTrue(all(count == 15 for month, count in counts.items() if month != "2026-10"))
        self.assertEqual(top_up_store(result, demos), result)

    def test_matching_seed_is_not_added_twice(self):
        _, demos = build_demo_reviews(self.original_samples)
        existing = dict(demos[0])
        existing.pop("is_demo")
        existing["favorite"] = "An older translated version of the same review."
        result = top_up_store([existing], demos)
        self.assertEqual(result[0], existing)
        self.assertEqual(sum(review_key(review) == review_key(existing) for review in result), 1)
        self.assertEqual(len(result), 180)

    def test_files_are_repeatable_and_browser_fixture_contains_no_live_reviews(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, storage, frontend = [root / name for name in ("reviews.json", "stored.json", "demo.js")]
            source.write_text(json.dumps(self.original_samples), encoding="utf-8")
            live = {
                "rating": 5, "language": "sw", "date": "2026-10-04",
                "favorite": "Unique live review text", "improvement": "Unique live improvement",
            }
            storage.write_text(json.dumps([live]), encoding="utf-8")
            first = seed_reviews(source, storage, frontend)
            self.assertEqual(first["stored_reviews"], 180)
            first_bytes = {path: path.read_bytes() for path in (source, storage, frontend)}
            first_mtimes = {path: path.stat().st_mtime_ns for path in first_bytes}
            second = seed_reviews(source, storage, frontend)
            self.assertEqual(second["added_to_store"], 0)
            self.assertEqual(first_bytes, {path: path.read_bytes() for path in first_bytes})
            self.assertEqual(first_mtimes, {path: path.stat().st_mtime_ns for path in first_bytes})
            seed_reviews(source, storage, frontend, check=True)
            self.assertNotIn(live["favorite"], frontend.read_text(encoding="utf-8"))
            browser_text = frontend.read_text(encoding="utf-8").split("const DEMO_REVIEWS = ", 1)[1]
            browser_demos = json.loads(browser_text.rstrip().removesuffix(";"))
            self.assertEqual(len(browser_demos), 180)
            self.assertTrue(all(review["is_demo"] for review in browser_demos))
            frontend.write_text("stale", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Run backend/seed_reviews.py"):
                seed_reviews(source, storage, frontend, check=True)
            self.assertEqual(frontend.read_text(encoding="utf-8"), "stale")


if __name__ == "__main__":
    unittest.main()
