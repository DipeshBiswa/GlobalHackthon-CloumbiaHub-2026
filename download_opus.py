from pathlib import Path
from transformers import MarianMTModel, MarianTokenizer

MODEL_ID = "Helsinki-NLP/opus-mt-en-sw"
MODEL_DIR = Path(__file__).resolve().parent / "models" / "opus-en-sw"

print("Downloading English → Kiswahili model...")

tokenizer = MarianTokenizer.from_pretrained(MODEL_ID)
model = MarianMTModel.from_pretrained(MODEL_ID)

tokenizer.save_pretrained(MODEL_DIR)
model.save_pretrained(MODEL_DIR)

print(f"Saved to {MODEL_DIR}")