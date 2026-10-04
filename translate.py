from pathlib import Path
from time import perf_counter

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_DIR = Path(__file__).resolve().parent / "models" / "nllb"

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Loading model on: {DEVICE}")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    local_files_only=True,
)

model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_DIR,
    local_files_only=True,
).to(DEVICE)

model.eval()

SOURCE_LANGUAGES = {
    "en": "eng_Latn",
    "de": "deu_Latn",
    "fr": "fra_Latn",
}

TARGET_ID = tokenizer.convert_tokens_to_ids("swh_Latn")


def translate(text, source):
    tokenizer.src_lang = SOURCE_LANGUAGES[source]

    inputs = tokenizer(
        text,
        return_tensors="pt",
    ).to(DEVICE)

    if inputs["input_ids"].shape[1] > 512:
        raise ValueError("Text too long. Translate shorter sentences.")

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            forced_bos_token_id=TARGET_ID,
            max_new_tokens=256,
            num_beams=4,
            do_sample=False,
        )

    return tokenizer.decode(
        output[0].cpu().tolist(),
        skip_special_tokens=True,
    )


if __name__ == "__main__":
    while True:
        source = input(
            "\nSource language (en/de/fr), or quit: "
        ).strip().lower()

        if source == "quit":
            break

        if source not in SOURCE_LANGUAGES:
            print("Choose en, de, or fr.")
            continue

        text = input("Review: ").strip()
        if not text:
            continue

        start = perf_counter()

        try:
            result = translate(text, source)
            print(f"Kiswahili: {result}")
            print(f"Translation time: {perf_counter() - start:.2f}s")
        except ValueError as error:
            print(error)