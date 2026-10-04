"""Import the checked-in, already processed Noor demo without model inference."""
import json
from pathlib import Path

import store

BUNDLE_DIR = Path(__file__).parent / "data" / "synthetic"
SEED_KEY = "noor_demo_seed_v1"


def _read_bundle(filename, required):
    records = json.loads((BUNDLE_DIR / filename).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"Bundled demo {filename} must contain a list.")
    for record in records:
        if (not isinstance(record, dict) or not required <= record.keys()
                or record.get("is_synthetic") is not True
                or record.get("synthetic_business") != "Noor's Coffee Farm"):
            raise ValueError(f"Bundled demo {filename} contains an invalid synthetic record.")
    if len({record["id"] for record in records}) != len(records):
        raise ValueError(f"Bundled demo {filename} contains duplicate IDs.")
    return records


def seed_bundled_demo(user_id):
    """Seed an untouched Noor account once; preserve owner edits on every restart."""
    with store.connect() as db:
        # Serialize startup checks and inserts if multiple workers start together.
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM app_metadata WHERE key=?", (SEED_KEY,)).fetchone():
            return False
        owner = db.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
        if owner is None or owner["username"] != "noor":
            raise ValueError("The bundled demo belongs to the noor account.")
        if any(db.execute(f"SELECT 1 FROM {table} WHERE user_id=? LIMIT 1", (user_id,)).fetchone()
               for table in ("reviews", "plans", "decisions")):
            db.execute("INSERT INTO app_metadata VALUES (?,?)", (SEED_KEY, "skipped-existing-data"))
            return False

        reviews = _read_bundle("noor_reviews.json", {
            "id", "rating", "date", "created_at", "favorite_en", "favorite_sw",
            "improvement_en", "improvement_sw", "share_consent", "translation_status",
            "classification_status", "topics", "model_prediction", "deleted",
        })
        plans = _read_bundle("noor_plans.json", {"id", "key", "created_at", "status"})
        if not reviews:
            raise ValueError("The bundled demo has no reviews.")
        for review in reviews:
            db.execute("INSERT INTO reviews VALUES (?,?,?,?,?)", (
                review["id"], user_id, review["created_at"], int(review["deleted"]),
                json.dumps(review, ensure_ascii=False),
            ))
        for plan in plans:
            plan["user_id"] = user_id
            plan.pop("progress", None)
            db.execute("INSERT INTO plans VALUES (?,?,?)", (
                plan["id"], user_id, json.dumps(plan, ensure_ascii=False),
            ))
        db.execute("INSERT INTO app_metadata VALUES (?,?)", (SEED_KEY, "imported"))
    return True
