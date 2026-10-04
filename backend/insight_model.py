"""Offline tourism-topic classifier backed by a local pretrained model."""

import json
from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class TopicPrediction:
    topic: str
    score: float


class InsightModel:
    """Classify review text against fixed, explainable tourism topics."""

    def __init__(self, use_finetuned: bool = True) -> None:
        self.model_dir = MODEL_DIR
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
        self.topic_head = None
        head_path = MODEL_DIR / "topic_head.pt"
        metadata_path = MODEL_DIR / "topic_head.json"
        if use_finetuned and head_path.is_file() and metadata_path.is_file():
            metadata = metadata_path.read_text(encoding="utf-8")
            if json.loads(metadata).get("labels") == list(TOPICS):
                self.topic_head = torch.nn.Linear(
                    self.model.config.hidden_size,
                    len(TOPICS),
                ).to(DEVICE)
                self.topic_head.load_state_dict(torch.load(head_path, map_location=DEVICE))
                self.topic_head.eval()

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
        if self.topic_head is not None:
            embedding = self._embed([text])
            scores = self.topic_head(embedding)
            index = int(scores.argmax().item())
            return TopicPrediction(
                topic=list(TOPICS)[index],
                score=float(scores.softmax(dim=1)[0, index].item()),
            )
        scores = self._embed([text]) @ self.topic_vectors.T
        index = int(scores.argmax().item())
        return TopicPrediction(
            topic=list(TOPICS)[index],
            score=float(scores[0, index].item()),
        )
