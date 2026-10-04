"""Development-only OPUS localization of the fixed, approved advice library."""
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from translate_opus import translate_many
import torch

def main():
    path = BACKEND / "data" / "echo_suggestions.json"
    suggestions = json.loads(path.read_text(encoding="utf-8"))
    torch.set_num_threads(4)
    missing = list(dict.fromkeys(rule[field] for rule in suggestions.values()
                                for field in ["title", "summary", "suggestion"]
                                if not rule.get(field + "_sw")))
    cache = {}
    for offset in range(0,len(missing),8):
        batch = missing[offset:offset+8]
        cache.update(zip(batch,translate_many(batch)))
        print(f"Localized {min(offset+len(batch),len(missing))}/{len(missing)} distinct texts",flush=True)
    for key, rule in suggestions.items():
        for field in ["title", "summary", "suggestion"]:
            source = rule[field]
            if not rule.get(field + "_sw"):
                rule[field + "_sw"] = cache[source]
    path.write_text(json.dumps(suggestions,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__ == "__main__": main()
