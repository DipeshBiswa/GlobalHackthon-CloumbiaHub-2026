"""Compact, versioned local knowledge; no development dataset at runtime."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
RULES = json.loads((DATA / "echo_topic_rules.json").read_text(encoding="utf-8"))
SUGGESTIONS = json.loads((DATA / "echo_suggestions.json").read_text(encoding="utf-8"))
