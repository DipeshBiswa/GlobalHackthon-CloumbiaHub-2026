import os
from pathlib import Path
from time import perf_counter

# Prevent Transformers from attempting any Hub or network access.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch
from transformers import MarianMTModel, MarianTokenizer

from review import Review, TranslatedReview

MODEL_DIR = Path(__file__).resolve().parent / "models" / "opus-en-sw"
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

if not (MODEL_DIR / "config.json").is_file() or not (
    MODEL_DIR / "model.safetensors"
).is_file():
    raise FileNotFoundError(
        f"Offline translation model is missing from {MODEL_DIR}. "
        "Run download_opus.py while online before using the API offline."
    )

print(f"Loading English → Kiswahili model on: {DEVICE}")

tokenizer = MarianTokenizer.from_pretrained(
    MODEL_DIR,
    local_files_only=True,
)
model = MarianMTModel.from_pretrained(
    MODEL_DIR,
    local_files_only=True,
).to(DEVICE)

model.eval()


def synchronize():
    if DEVICE == "mps":
        torch.mps.synchronize()


def translate(text: str) -> str:
    inputs = tokenizer(
        text,
        return_tensors="pt",
    )

    if inputs["input_ids"].shape[1] > model.config.max_position_embeddings:
        raise ValueError("Review too long. Try a shorter sentence.")

    inputs = inputs.to(DEVICE)

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=256,
            num_beams=8,
            do_sample=False,
        )

    return tokenizer.decode(
        output[0].cpu().tolist(),
        skip_special_tokens=True,
    )


def translate_review(review: Review) -> TranslatedReview:
    """Translate both written parts of a review into Kiswahili."""
    return TranslatedReview(
        rating=review.rating,
        language="sw",
        date=review.date,
        favorite=translate(review.favorite),
        improvement=translate(review.improvement),
        original_favorite=review.favorite,
        original_improvement=review.improvement,
    )


if __name__ == "__main__":
    while True:
        text = input("\nEnglish review (or 'quit'): ").strip()

        if text.lower() == "quit":
            break
        if not text:
            continue

        synchronize()
        start = perf_counter()

        try:
            result = translate(text)
            synchronize()
            elapsed = perf_counter() - start

            print(f"Kiswahili: {result}")
            print(f"Translation time: {elapsed:.2f}s")
        except ValueError as error:
            print(error)
