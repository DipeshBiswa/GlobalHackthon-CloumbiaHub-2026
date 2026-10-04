"""One-time setup: download missing assets, then verify both models offline."""
import os
from pathlib import Path
import subprocess
import sys

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent

def run(path):
    subprocess.run([sys.executable, str(path)], check=True)

def main():
    local_opus = BACKEND / "models" / "opus-en-sw"
    existing_opus = ROOT / "models" / "opus-en-sw"
    if not any((p / "model.safetensors").is_file() for p in (local_opus, existing_opus)):
        run(BACKEND / "download_opus.py")
    if not (BACKEND / "models" / "insight-model" / "model.safetensors").is_file():
        run(BACKEND / "download_insight_model.py")
    if not (ROOT / "frontend" / "vendor" / "manifest.json").is_file():
        run(BACKEND / "tools" / "install_frontend_assets.py")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, str(BACKEND))
    from translate_opus import translate
    from insight_model import InsightModel
    print("Offline translation check:", translate("The guide was friendly."))
    print("Offline classifier check:", InsightModel().classify("The guide was friendly."))
    print("Echo is ready. Start the local server with run_offline.ps1 or run_offline.sh.")

if __name__ == "__main__": main()
