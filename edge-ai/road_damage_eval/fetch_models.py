"""
Download multiple candidate models for evaluation.
"""
import urllib.request
from pathlib import Path
from ultralytics import YOLO
import json

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATES = [
    {
        "id": "peterhdd_pothole_yolov8s",
        "name": "PeterHDD YOLOv8s Pothole",
        "repo": "peterhdd/pothole-detection-yolov8",
        "url": "https://huggingface.co/peterhdd/pothole-detection-yolov8/resolve/main/best.pt",
        "filename": "peterhdd_pothole_yolov8s.pt"
    },
    {
        "id": "samdutse_pothole_yolov8",
        "name": "Samdutse YOLOv8 Pothole",
        "repo": "samdutse/pothole-yolov8",
        "url": "https://huggingface.co/samdutse/pothole-yolov8/resolve/main/best.pt",
        "filename": "samdutse_pothole_yolov8.pt"
    },
    {
        "id": "ianmutai_iris_rdd_yolov8",
        "name": "IanMutai IRIS Road Damage YOLOv8",
        "repo": "ianmutai/iris-road-detection-v2",
        "url": "https://huggingface.co/ianmutai/iris-road-detection-v2/resolve/main/best.pt",
        "filename": "ianmutai_iris_rdd_yolov8.pt"
    }
]

def download_and_inspect():
    results = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for cand in CANDIDATES:
        dest = MODELS_DIR / cand["filename"]
        print(f"\n==========================================")
        print(f"Processing candidate: {cand['name']}")
        
        if not dest.exists() or dest.stat().st_size < 100_000:
            print(f"Downloading from {cand['url']}...")
            try:
                req = urllib.request.Request(cand["url"], headers=headers)
                with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
                    out.write(resp.read())
                print(f"[+] Download complete: {dest.stat().st_size / (1024*1024):.2f} MB")
            except Exception as e:
                print(f"[-] Download failed: {e}")
                results[cand["id"]] = {"name": cand["name"], "status": "download_failed", "error": str(e)}
                continue
        else:
            print(f"[*] Already cached: {dest.stat().st_size / (1024*1024):.2f} MB")
            
        try:
            model = YOLO(str(dest))
            names = model.names
            print(f"[+] Successfully loaded into YOLO!")
            print(f"    Classes: {names}")
            print(f"    Task: {model.task}")
            results[cand["id"]] = {
                "name": cand["name"],
                "status": "loaded",
                "file": cand["filename"],
                "size_mb": round(dest.stat().st_size / (1024*1024), 2),
                "classes": names,
                "task": model.task
            }
        except Exception as e:
            print(f"[-] Failed to load model: {e}")
            results[cand["id"]] = {"name": cand["name"], "status": "load_error", "error": str(e)}

    out_file = Path(__file__).resolve().parent / "models_summary.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_file}")

if __name__ == "__main__":
    download_and_inspect()
