from pathlib import Path
import os
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"

from transformers import AutoModel, AutoTokenizer

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_DIR = Path(__file__).resolve().parent / "models" / "insight-model"

print("Downloading offline insight model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModel.from_pretrained(MODEL_ID)
tokenizer.save_pretrained(MODEL_DIR)
model.save_pretrained(MODEL_DIR)
print(f"Saved to {MODEL_DIR}")
