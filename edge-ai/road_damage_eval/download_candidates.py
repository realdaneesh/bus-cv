"""
Download and verify candidate pretrained road damage detection models from HuggingFace and public repositories.
"""
import os
import sys
import urllib.request
import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
MODELS_DIR = EVAL_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Candidate model definitions with direct download URLs
CANDIDATES = [
    {
        "id": "peterhdd_pothole_yolov8n",
        "name": "PeterHDD YOLOv8n Pothole",
        "author": "peterhdd",
        "description": "YOLOv8 nano fine-tuned for road potholes",
        "url": "https://huggingface.co/peterhdd/pothole-detection-yolov8/resolve/main/best.pt",
        "target_filename": "peterhdd_pothole_yolov8n.pt",
        "expected_classes": ["pothole"]
    },
    {
        "id": "arnabdhar_rdd_yolov8m",
        "name": "ArnabDhar YOLOv8 RDD2022 Multi-Class",
        "author": "arnabdhar",
        "description": "YOLOv8 model trained on RDD2022 dataset for multi-class road damage (D00, D10, D20, D40)",
        "url": "https://huggingface.co/arnabdhar/YOLOv8-RDD-Road-Damage-Detection/resolve/main/best.pt",
        "target_filename": "arnabdhar_rdd_yolov8m.pt",
        "expected_classes": ["D00", "D10", "D20", "D40"]
    },
    {
        "id": "keremberke_pothole_yolov8n",
        "name": "Keremberke YOLOv8n Pothole",
        "author": "keremberke",
        "description": "YOLOv8 nano pothole detection model",
        "url": "https://huggingface.co/keremberke/yolov8n-pothole/resolve/main/best.pt",
        "target_filename": "keremberke_pothole_yolov8n.pt",
        "expected_classes": ["pothole"]
    }
]

def download_file(url: str, dest_path: Path):
    if dest_path.exists() and dest_path.stat().st_size > 100_000:
        print(f"[*] Already downloaded: {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.2f} MB)")
        return True
    
    print(f"[*] Downloading {dest_path.name} from {url}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response, open(dest_path, "wb") as out_file:
            data = response.read()
            out_file.write(data)
        print(f"[+] Downloaded successfully: {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.2f} MB)")
        return True
    except Exception as e:
        print(f"[-] Failed to download {url}: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False

def inspect_model(model_path: Path):
    from ultralytics import YOLO
    try:
        model = YOLO(str(model_path))
        names = model.names
        print(f"    Loaded successfully! Classes ({len(names)}): {names}")
        return {
            "loaded": True,
            "classes": names,
            "num_classes": len(names),
            "size_mb": round(model_path.stat().st_size / (1024 * 1024), 2)
        }
    except Exception as e:
        print(f"    Failed to load into Ultralytics: {e}")
        return {
            "loaded": False,
            "error": str(e)
        }

def main():
    print("==================================================")
    print("BUS-CV Phase 3A: Road Damage Candidate Downloader")
    print("==================================================")
    
    results = {}
    for candidate in CANDIDATES:
        dest = MODELS_DIR / candidate["target_filename"]
        success = download_file(candidate["url"], dest)
        if success:
            print(f"[*] Inspecting model architecture and class labels: {candidate['name']}")
            info = inspect_model(dest)
            results[candidate["id"]] = {**candidate, **info}
        else:
            results[candidate["id"]] = {**candidate, "loaded": False, "error": "Download failed"}
            
    summary_path = EVAL_DIR / "candidates_meta.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Candidates metadata saved to: {summary_path}")

if __name__ == "__main__":
    main()
