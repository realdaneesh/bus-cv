"""
Download full resolution real road photos for road damage model evaluation.
"""
import urllib.request
from pathlib import Path

IMAGES_DIR = Path(__file__).resolve().parent / "sample_images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

DIRECT_IMAGES = [
    {
        "filename": "pothole_villeray.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/86/Pothole_in_Villeray%2C_Montr%C3%A9al.jpg"
    },
    {
        "filename": "pothole_repair.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/83/Pothole_repair.jpg"
    }
]

def fetch_direct():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for item in DIRECT_IMAGES:
        dest = IMAGES_DIR / item["filename"]
        try:
            req = urllib.request.Request(item["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
                f.write(resp.read())
            print(f"[+] Downloaded real image: {item['filename']} ({dest.stat().st_size / 1024:.1f} KB)")
        except Exception as e:
            print(f"[-] Error fetching {item['filename']}: {e}")

if __name__ == "__main__":
    fetch_direct()
