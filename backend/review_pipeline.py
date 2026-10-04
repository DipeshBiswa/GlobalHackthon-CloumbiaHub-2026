"""One local processing pipeline shared by HTTP submissions and demo tooling."""
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4


def process_review(source, translate, classifier, *, record_id=None, created_at=None,
                   is_synthetic=False, translations=None):
    # HTTP validation belongs to ReviewPayload; tooling supplies validated demo sources.
    if source.get("language", "en") != "en":
        raise ValueError("Only English source feedback is supported.")
    favorite, improvement = source["favorite_en"], source["improvement_en"]
    if not any(c.isalnum() for c in favorite + improvement):
        raise ValueError("At least one meaningful text field is required.")
    if isinstance(source["rating"], bool) or source["rating"] not in range(1, 6):
        raise ValueError("Rating must be between one and five.")
    translated = translations or {}
    def sw(text):
        if not text.strip():
            return ""
        return translated[text] if text in translated else translate(text)
    favorite_sw, improvement_sw = sw(favorite), sw(improvement)
    prediction = classifier.classify_review(favorite, improvement, source["rating"])
    return {**source, "id": record_id or str(uuid4()),
            "created_at": created_at or datetime.now(timezone.utc).isoformat(),
            "favorite_sw": favorite_sw, "improvement_sw": improvement_sw,
            "translation_status": "translated", **prediction,
            "model_prediction": deepcopy(prediction), "manual_override": None,
            "checked": False, "is_synthetic": is_synthetic, "owner_seen": False, "deleted": False}
