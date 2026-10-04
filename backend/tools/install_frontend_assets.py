"""One-time online installation of pinned browser assets and existing fonts."""
from pathlib import Path
from urllib.request import Request, urlopen
import re
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "vendor"
ASSETS = {
    "react.production.min.js": "https://cdnjs.cloudflare.com/ajax/libs/react/18.3.1/umd/react.production.min.js",
    "react-dom.production.min.js": "https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.3.1/umd/react-dom.production.min.js",
    "htm.umd.js": "https://cdn.jsdelivr.net/npm/htm@3.1.1/dist/htm.umd.js",
    "react.LICENSE": "https://raw.githubusercontent.com/facebook/react/v18.3.1/LICENSE",
    "htm.LICENSE": "https://raw.githubusercontent.com/developit/htm/3.1.1/LICENSE",
    "Inter.OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/OFL.txt",
    "Lora.OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/lora/OFL.txt",
}

def download(url):
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as response:
        return response.read()

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in ASSETS.items():
        content = download(url)
        (ROOT / name).write_bytes(content)
        manifest[name] = {"url": url, "sha256": hashlib.sha256(content).hexdigest()}
    css = download("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:wght@500;600&display=swap").decode()
    urls = list(dict.fromkeys(re.findall(r"https://[^)\s]+", css)))
    for i, url in enumerate(urls):
        name = f"font-{i}" + Path(url.split("?")[0]).suffix
        content = download(url)
        (ROOT / name).write_bytes(content)
        manifest[name] = {"url": url, "sha256": hashlib.sha256(content).hexdigest()}
        css = css.replace(url, name)
    (ROOT / "fonts.css").write_text(css, encoding="utf-8")
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Installed {len(manifest)} local assets in {ROOT}")

if __name__ == "__main__":
    main()
