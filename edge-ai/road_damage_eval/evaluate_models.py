"""
BUS-CV Phase 3A: Comprehensive Road Damage AI Model Evaluation Harness.

Benchmarks candidate models on real-world road defect imagery, measuring:
- Inference latency & FPS on CPU
- Class coverage & mapping
- Pothole detection accuracy & confidence
- Crack & surface distress capability
- False positive resistance on negative controls (clean road, manholes, markings)
- Memory footprint & model size
- Outputs visual annotations and structured JSON results.
"""

import os
import sys
import time
import json
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO

EVAL_DIR = Path(__file__).resolve().parent
MODELS_DIR = EVAL_DIR / "models"
IMAGES_DIR = EVAL_DIR / "sample_images"
RESULTS_DIR = EVAL_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATES = [
    {
        "id": "peterhdd_yolov8s",
        "name": "PeterHDD YOLOv8s (Pothole Detection)",
        "model_file": MODELS_DIR / "peterhdd_pothole_yolov8s.pt",
        "type": "Single-Class Pothole Detector (YOLOv8s)",
        "source": "https://huggingface.co/peterhdd/pothole-detection-yolov8"
    },
    {
        "id": "samdutse_yolov8s",
        "name": "Samdutse YOLOv8s (Pothole Detection)",
        "model_file": MODELS_DIR / "samdutse_pothole_yolov8.pt",
        "type": "Single-Class Pothole Detector (YOLOv8s)",
        "source": "https://huggingface.co/samdutse/pothole-yolov8"
    },
    {
        "id": "ianmutai_iris_yolov8n",
        "name": "IanMutai IRIS Road Detection v2 (YOLOv8n)",
        "model_file": MODELS_DIR / "ianmutai_iris_rdd_yolov8.pt",
        "type": "Multi-Class Urban Road Distress & Infrastructure (YOLOv8n)",
        "source": "https://huggingface.co/ianmutai/iris-road-detection-v2"
    }
]

def load_and_warmup(model_path: Path):
    model = YOLO(str(model_path))
    # Warmup run
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    for _ in range(3):
        model.predict(dummy, verbose=False, conf=0.25)
    return model

def benchmark_latency(model, image_path: Path, num_iterations=10):
    img = cv2.imread(str(image_path))
    if img is None:
        return 0, 0
        
    latencies = []
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        _ = model.predict(img, verbose=False, conf=0.25)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0) # ms
        
    avg_latency = float(np.mean(latencies))
    fps = 1000.0 / avg_latency if avg_latency > 0 else 0
    return round(avg_latency, 2), round(fps, 1)

def evaluate_candidate(candidate_info: dict, test_images: list):
    model_path = candidate_info["model_file"]
    if not model_path.exists():
        return {"status": "error", "error": "Model file not found"}
        
    file_size_mb = round(model_path.stat().st_size / (1024 * 1024), 2)
    print(f"\n=======================================================")
    print(f"Evaluating: {candidate_info['name']} ({file_size_mb} MB)")
    print(f"=======================================================")
    
    try:
        model = load_and_warmup(model_path)
    except Exception as e:
        print(f"[-] Failed to load model: {e}")
        return {"status": "error", "error": str(e)}
        
    classes_dict = model.names
    print(f"[*] Supported Classes ({len(classes_dict)}): {classes_dict}")
    
    candidate_result_dir = RESULTS_DIR / candidate_info["id"]
    candidate_result_dir.mkdir(parents=True, exist_ok=True)
    
    image_evaluations = []
    total_detections = 0
    pothole_detections = 0
    crack_detections = 0
    false_positives_negative_control = 0
    all_latencies = []
    
    for img_info in test_images:
        img_path = img_info["path"]
        img = cv2.imread(str(img_path))
        if img is None:
            continue
            
        lat_ms, fps = benchmark_latency(model, img_path, num_iterations=5)
        all_latencies.append(lat_ms)
        
        # Run inference at standard confidence
        results = model.predict(img, verbose=False, conf=0.25)
        res = results[0]
        
        detections = []
        annotated_img = img.copy()
        
        if res.boxes is not None and len(res.boxes) > 0:
            for box in res.boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                cls_id = int(box.cls[0].cpu().numpy())
                conf = float(box.conf[0].cpu().numpy())
                cls_name = classes_dict.get(cls_id, str(cls_id)).upper()
                
                detections.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(conf, 3),
                    "box": [int(v) for v in xyxy]
                })
                
                # Draw on annotated image
                # Color code: Pothole = Red/Orange, Crack = Purple, Other = Cyan
                if "POTHOLE" in cls_name or cls_name == "0":
                    color = (0, 69, 255) # Red-Orange
                    label = f"POTHOLE {conf:.2f}"
                    pothole_detections += 1
                elif "CRACK" in cls_name:
                    color = (255, 0, 255) # Magenta
                    label = f"CRACK {conf:.2f}"
                    crack_detections += 1
                else:
                    color = (255, 200, 0) # Cyan/Yellow
                    label = f"{cls_name} {conf:.2f}"
                    
                x1, y1, x2, y2 = xyxy
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 3)
                
                # Label badge
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(annotated_img, (x1, max(0, y1 - 22)), (x1 + tw + 8, max(22, y1)), color, -1)
                cv2.putText(annotated_img, label, (x1 + 4, max(16, y1 - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                total_detections += 1
                
                if img_info.get("category") == "negative_control":
                    false_positives_negative_control += 1
                    
        # Add header banner to saved image
        banner = f"{candidate_info['name']} | Detections: {len(detections)} | Latency: {lat_ms}ms ({fps} FPS)"
        cv2.putText(annotated_img, banner, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        annotated_path = candidate_result_dir / f"{img_info['id']}_annotated.jpg"
        cv2.imwrite(str(annotated_path), annotated_img)
        
        image_evaluations.append({
            "image_id": img_info["id"],
            "filename": img_path.name,
            "category": img_info["category"],
            "detections_count": len(detections),
            "detections": detections,
            "latency_ms": lat_ms,
            "fps": fps,
            "annotated_artifact": str(annotated_path)
        })
        
        print(f"  -> [{img_info['category'].upper()}] {img_path.name}: {len(detections)} detections ({lat_ms} ms)")
        for d in detections:
            print(f"      * {d['class_name']} (conf: {d['confidence']}) @ {d['box']}")
            
    avg_total_latency = round(float(np.mean(all_latencies)), 2) if all_latencies else 0
    avg_fps = round(1000.0 / avg_total_latency, 1) if avg_total_latency > 0 else 0
    
    return {
        "candidate_id": candidate_info["id"],
        "name": candidate_info["name"],
        "type": candidate_info["type"],
        "source": candidate_info["source"],
        "size_mb": file_size_mb,
        "classes": classes_dict,
        "num_classes": len(classes_dict),
        "avg_latency_ms": avg_total_latency,
        "avg_fps": avg_fps,
        "total_detections": total_detections,
        "pothole_detections": pothole_detections,
        "crack_detections": crack_detections,
        "false_positives_on_negative_controls": false_positives_negative_control,
        "image_results": image_evaluations
    }

def main():
    print("=====================================================================")
    print("BUS-CV Phase 3A: Road Damage AI Model Benchmarking & Evaluation Suite")
    print("=====================================================================")
    
    # Collect all test images
    test_images = []
    for f in sorted(IMAGES_DIR.glob("*.jpg")):
        name = f.stem
        cat = "pothole" if "pothole" in name else "crack" if "crack" in name else "negative_control"
        test_images.append({
            "id": name,
            "path": f,
            "category": cat
        })
        
    print(f"Found {len(test_images)} test images for benchmark.")
    
    benchmark_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware": "CPU (Edge Compatible Benchmark)",
        "num_test_images": len(test_images),
        "candidates": {}
    }
    
    for cand in CANDIDATES:
        cand_results = evaluate_candidate(cand, test_images)
        benchmark_report["candidates"][cand["id"]] = cand_results
        
    report_file = EVAL_DIR / "benchmark_report.json"
    with open(report_file, "w") as f:
        json.dump(benchmark_report, f, indent=2)
        
    print("\n=====================================================================")
    print(f"[+] Benchmarking complete! Full JSON report written to: {report_file}")
    print("=====================================================================")
    
    # Print summary table
    print("\nSUMMARY COMPARISON TABLE:")
    print(f"{'Model Name':<35} | {'Size':<8} | {'Classes':<7} | {'Avg Latency':<12} | {'FPS':<6} | {'Potholes':<8} | {'False Pos':<9}")
    print("-" * 95)
    for cid, data in benchmark_report["candidates"].items():
        if "error" in data:
            print(f"{data.get('name', cid):<35} | ERROR: {data['error']}")
        else:
            print(f"{data['name']:<35} | {data['size_mb']}MB | {data['num_classes']:<7} | {data['avg_latency_ms']} ms{'':<5} | {data['avg_fps']:<6} | {data['pothole_detections']:<8} | {data['false_positives_on_negative_controls']:<9}")

if __name__ == "__main__":
    main()
