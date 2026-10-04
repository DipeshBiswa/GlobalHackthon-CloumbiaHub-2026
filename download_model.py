from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_ID = "facebook/nllb-200-distilled-600M"
MODEL_DIR = Path(__file__).resolve().parent / "models" / "nllb"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    src_lang="swh_Latn",
)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID)

tokenizer.save_pretrained(MODEL_DIR)
model.save_pretrained(MODEL_DIR)

print(f"Downloaded to {MODEL_DIR}")