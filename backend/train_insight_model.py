"""Fine-tune a small tourism topic head from a local Yelp archive.

The Yelp archive is read in place and is never copied into the repository.
Labels are weak supervision from tourism categories and explainable keywords;
the pretrained MiniLM encoder remains frozen.
"""

import argparse
import json
import random
import tarfile
from collections import Counter
from pathlib import Path

import torch
from torch.nn import CrossEntropyLoss, Linear
from torch.optim import AdamW

from insight_model import InsightModel, TOPICS

TOURISM_CATEGORIES = (
    "Tours",
    "Travel Services",
    "Hotels & Travel",
    "Museums",
    "Landmarks & Historical Buildings",
    "Parks",
    "Outdoor Recreation",
    "Arts & Entertainment",
)
LABEL_KEYWORDS = {
    "guide_quality": ("guide", "staff", "friendly", "welcoming", "knowledgeable"),
    "scenery": ("view", "scenery", "waterfall", "river", "beach", "sunset", "nature"),
    "culture_history": ("history", "historical", "culture", "museum", "tradition", "architecture"),
    "food": ("food", "meal", "restaurant", "tasting", "cooking", "market"),
    "coffee_roasting": ("coffee", "roast", "roasting", "espresso"),
    "tour_difficulty": ("steep", "tiring", "stairs", "hike", "difficult", "hard walk"),
    "tour_timing": ("wait", "rushed", "slow", "time", "long", "hour"),
    "group_size": ("group", "crowded", "busy", "people"),
    "transportation": ("parking", "pickup", "bus", "transport", "direction", "drive"),
    "accessibility": ("accessible", "wheelchair", "mobility", "seating", "shade", "restroom"),
    "souvenirs": ("souvenir", "gift", "craft", "shop", "buy", "take home"),
}


def tourism_business_ids(archive: Path) -> set[str]:
    ids: set[str] = set()
    with tarfile.open(archive, "r") as tar:
        member = tar.getmember("yelp_academic_dataset_business.json")
        stream = tar.extractfile(member)
        if stream is None:
            raise ValueError("The Yelp archive does not contain business data.")
        for raw in stream:
            row = json.loads(raw)
            categories = row.get("categories") or ""
            if any(category in categories for category in TOURISM_CATEGORIES):
                ids.add(row["business_id"])
    return ids


def weak_label(text: str) -> str | None:
    lowered = text.lower()
    matches = [
        (topic, sum(lowered.count(keyword) for keyword in keywords))
        for topic, keywords in LABEL_KEYWORDS.items()
    ]
    topic, score = max(matches, key=lambda item: item[1])
    return topic if score else None


def load_examples(archive: Path, business_ids: set[str], limit: int) -> list[tuple[str, str]]:
    examples: list[tuple[str, str]] = []
    with tarfile.open(archive, "r") as tar:
        member = tar.getmember("yelp_academic_dataset_review.json")
        stream = tar.extractfile(member)
        if stream is None:
            raise ValueError("The Yelp archive does not contain review data.")
        for raw in stream:
            row = json.loads(raw)
            if row.get("business_id") not in business_ids:
                continue
            text = str(row.get("text", "")).strip()
            label = weak_label(text)
            if text and label:
                examples.append((text, label))
                if len(examples) >= limit:
                    break
    random.Random(42).shuffle(examples)
    return examples


def train(archive: Path, epochs: int, limit: int, batch_size: int) -> None:
    business_ids = tourism_business_ids(archive)
    examples = load_examples(archive, business_ids, limit)
    if len(examples) < 50:
        raise ValueError(f"Only {len(examples)} labeled examples found; need at least 50.")

    encoder = InsightModel(use_finetuned=False)
    labels = list(TOPICS)
    label_to_index = {label: index for index, label in enumerate(labels)}
    texts = [text for text, _ in examples]
    targets = torch.tensor([label_to_index[label] for _, label in examples])
    embedding_batches: list[torch.Tensor] = []
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            embedding_batches.append(
                encoder._embed(texts[start : start + batch_size]).cpu()
            )
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
    embeddings = torch.cat(embedding_batches)

    head = Linear(embeddings.shape[1], len(labels))
    optimizer = AdamW(head.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = CrossEntropyLoss()
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = loss_fn(head(embeddings), targets)
        loss.backward()
        optimizer.step()

    output_dir = encoder.model_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(head.state_dict(), output_dir / "topic_head.pt")
    (output_dir / "topic_head.json").write_text(
        json.dumps(
            {
                "labels": labels,
                "examples": len(examples),
                "tourism_businesses": len(business_ids),
                "label_counts": Counter(label for _, label in examples),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Trained tourism topic head with {len(examples)} examples.")
    print(f"Saved reusable local artifact to {output_dir}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    train(args.archive, args.epochs, args.limit, args.batch_size)
