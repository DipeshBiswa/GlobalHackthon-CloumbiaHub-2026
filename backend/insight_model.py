"""Offline tourism-topic classifier backed by a local pretrained model."""

from dataclasses import dataclass
from pathlib import Path
import os
import re

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
from knowledge import RULES

import torch
from transformers import AutoModel, AutoTokenizer

MODEL_DIR = Path(__file__).resolve().parent / "models" / "insight-model"
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

TOPICS = {
    "guide_quality": "friendly, knowledgeable, welcoming tour guide",
    "scenery": "beautiful views, nature, sunset, river, waterfall, or beach",
    "culture_history": "local culture, history, traditions, community, or architecture",
    "food": "local food, meals, snacks, markets, tasting, or cooking",
    "coffee_roasting": "coffee beans, coffee roasting, or making coffee",
    "tour_difficulty": "steep, hard, tiring, inaccessible, or physically difficult route",
    "tour_timing": "rushed tour, not enough time, longer stops, or tour pacing",
    "group_size": "tour group too large or preference for a smaller group",
    "transportation": "transport, pickup, parking, bicycles, boats, or directions",
    "accessibility": "accessibility, mobility, seating, shade, or restroom needs",
    "souvenirs": "buying products or souvenirs to take home",
}
TOPICS = {key: rule["description"] for key, rule in RULES["topics"].items()}


@dataclass(frozen=True)
class TopicPrediction:
    topic: str
    score: float


class InsightModel:
    """Classify review text against fixed, explainable tourism topics."""

    def __init__(self) -> None:
        required_files = (MODEL_DIR / "config.json", MODEL_DIR / "model.safetensors")
        if not all(path.is_file() for path in required_files):
            raise FileNotFoundError(
                f"Offline insight model is missing from {MODEL_DIR}. "
                "Run download_insight_model.py while online."
            )

        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_DIR,
            local_files_only=True,
        )
        self.model = AutoModel.from_pretrained(
            MODEL_DIR,
            local_files_only=True,
        ).to(DEVICE)
        self.model.eval()
        self.topic_vectors = self._embed(list(TOPICS.values()))

    def _embed(self, texts: list[str]) -> torch.Tensor:
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        ).to(DEVICE)
        with torch.inference_mode():
            hidden = self.model(**inputs).last_hidden_state
        mask = inputs["attention_mask"].unsqueeze(-1)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        return torch.nn.functional.normalize(pooled, p=2, dim=1)

    def classify(self, text: str) -> TopicPrediction:
        scores = self._embed([text]) @ self.topic_vectors.T
        index = int(scores.argmax().item())
        return TopicPrediction(
            topic=list(TOPICS)[index],
            score=float(scores[0, index].item()),
        )

    def classify_review(self, favorite, improvement, rating):
        """Clause-level multi-topic evidence on original English, never translated text.

        Cosine similarity is a score, not a calibrated probability. Exact phrase
        evidence supplements MiniLM; ambiguous semantic-only matches abstain.
        """
        predictions = []
        uncertain = []
        for field, text in [("favorite", favorite), ("better", improvement)]:
            clauses = [c.strip() for c in re.split(r"[.!?;]|\bbut\b|\bhowever\b|,|\band\b", text, flags=re.I) if c.strip()]
            if not clauses:
                continue
            vectors = self._embed(clauses) @ self.topic_vectors.T
            for clause, scores in zip(clauses, vectors):
                ranked = sorted(zip(TOPICS, scores.tolist()), key=lambda x: -x[1])
                matches = []
                for topic, rule in RULES["topics"].items():
                    phrase = next((p for p in rule["phrases"] if re.search(r"\b" + re.escape(p) + r"\b", clause, re.I)), None)
                    score = float(scores[list(TOPICS).index(topic)])
                    if phrase and score >= RULES["phrase_threshold"]:
                        matches.append((topic, score, phrase, "phrase+minilm"))
                if not matches and ranked[0][1] >= RULES["semantic_threshold"] and ranked[0][1] - ranked[1][1] >= RULES["semantic_margin"]:
                    matches = [(ranked[0][0], ranked[0][1], "", "minilm")]
                if not matches:
                    uncertain.append({"text": clause, "field": field, "topic": ranked[0][0], "classifier_score": round(ranked[0][1], 4)})
                for topic, score, phrase, method in matches:
                    sentiment = sentiment_of(clause, rating, field)
                    predictions.append({"topic": topic, "sentiment": sentiment, "classifier_score": round(score, 4), "phrase": phrase, "field": field, "evidence": clause, "method": method})
        unique = {}
        for p in predictions:
            key = (p["topic"], p["sentiment"])
            if key not in unique or p["classifier_score"] > unique[key]["classifier_score"]:
                unique[key] = p
        return {"topics": list(unique.values()), "uncertain": uncertain,
                "classification_status": "classified" if unique else "not_sure"}


def sentiment_of(text, rating, field):
    lower = text.lower()
    if re.search(r"\b(no|without) (crowds|trash|wait|waiting)\b", lower):
        return "positive"
    if re.search(r"\b(not|never) (good|great|friendly|clean|helpful|worth)\b|too steep|too long|not enough|couldn't|\b(rushed|tiring|dirty|rude|overpriced|expensive|pricey|slippery|broken|bad|poor|hard|difficult)\b", lower):
        return "negative"
    if re.search(r"\b(please|wish|wanted|need|add|offer)\b|would love|more time", lower):
        return "request"
    if re.search(r"\b(great|excellent|wonderful|friendly|knowledgeable|kind|beautiful|delicious|helpful|clean|loved|liked|enjoyed|amazing|good|comfortable|personal|welcoming|welcomed|relaxed|perfectly|thoughtful|worth|easy|appreciated|peaceful|lovely)\b|like being invited", lower):
        return "positive"
    if field == "better":
        return "negative"
    return "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral"
