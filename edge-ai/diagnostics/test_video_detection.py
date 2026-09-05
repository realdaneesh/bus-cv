"""
BUS-CV — Task 5: Video → YOLO → Detections diagnostic.

Verifies that a selected demo video actually produces non-zero, real YOLO11n
vehicle detections BEFORE the frontend/backend monitors it.

Usage:
    python edge-ai/diagnostics/test_video_detection.py [video_path] [--samples N]

    - video_path : optional path to the .mp4; defaults to the processor's
                   selected demo source (edge-ai/videos/demo_traffic.mp4).
    - --samples  : number of frames to sample evenly across the video (default 10).

It prints, per sampled frame, the real detection counts via the same
EdgeDetector (YOLO11n, COCO classes car=2, motorcycle=3, bus=5, truck=7) that
the live pipeline uses, plus the aggregate totals across all sampled frames.
"""

import os
import sys
import time
import argparse
from typing import Dict, List

# Ensure edge-ai is importable regardless of CWD
_edge_ai_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if _edge_ai_dir not in sys.path:
    sys.path.insert(0, _edge_ai_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Video -> YOLO -> Detection diagnostic")
    parser.add_argument("video_path", nargs="?", default=None,
                        help="Path to the video to diagnose (defaults to demo_traffic.mp4)")
    parser.add_argument("--samples", type=int, default=10,
                        help="Number of frames to sample across the video (default 10)")
    args = parser.parse_args()

    from detector import EdgeDetector
    import cv2

    # Resolve the selected video using the same priority logic as the pipeline.
    if args.video_path:
        video_path = args.video_path
    else:
        from processor import get_default_video_source
        video_path = get_default_video_source()
        print(f"[VIDEO SOURCE] Default-selected source: {video_path}")

    if not os.path.exists(video_path):
        print(f"[ERROR] Video file does not exist: {video_path}")
        return 1

    print(f"[DIAG] Opening video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] OpenCV failed to open video: {video_path}")
        return 1

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    duration = (total_frames / fps) if fps > 0 else 0.0
    print(f"[DIAG] Metadata: {width}x{height} | {fps:.2f} FPS | {total_frames} frames | {duration:.2f}s")

    print("[DIAG] Loading YOLO11n vehicle model (EdgeDetector)...")
    t0 = time.time()
    detector = EdgeDetector(confidence_threshold=0.50)
    if not detector.load_model():
        print("[ERROR] Failed to load YOLO11n model.")
        return 1
    print(f"[DIAG] Model loaded on {detector.device} in {time.time() - t0:.1f}s")

    # Sample frame indices evenly across the whole video
    n = max(1, min(args.samples, total_frames if total_frames > 0 else args.samples))
    if total_frames > 0:
        sample_indices = sorted({int(i * (total_frames - 1) / max(1, n - 1))
                                 for i in range(n)})
    else:
        sample_indices = list(range(n))

    totals: Dict[str, int] = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "vehicles_detected": 0}
    all_detection_counts: List[int] = []
    total_infer_time = 0.0

    print("\n[DIAG] Rendering frame-by-frame detection report:\n")
    for idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"Frame {idx}: [no frame read]")
            continue

        t_infer = time.time()
        result = detector.detect_frame(frame)
        total_infer_time += time.time() - t_infer

        counts = result["vehicle_counts"]
        dets = result["detections"]
        all_detection_counts.append(counts["total"])

        for cls in ("car", "motorcycle", "bus", "truck"):
            totals[cls] += counts[cls]
        totals["vehicles_detected"] += counts["total"]

        det_desc = ", ".join(
            f"{d['class']}={sum(1 for x in dets if x['class'] == d['class'])}"
            for d in dets[:20]
        ) if dets else "none"
        print(
            f"Frame {idx}:\n"
            f"  cars: {counts['car']}\n"
            f"  motorcycles: {counts['motorcycle']}\n"
            f"  buses: {counts['bus']}\n"
            f"  trucks: {counts['truck']}\n"
            f"  (detections: {det_desc})"
        )

    cap.release()

    avg_infer_ms = (total_infer_time / len(all_detection_counts)) * 1000 if all_detection_counts else 0.0

    print("\n[DIAG] ===== TOTAL DETECTIONS ACROSS SAMPLED FRAMES =====")
    print(f"  cars:        {totals['car']}")
    print(f"  motorcycles: {totals['motorcycle']}")
    print(f"  buses:       {totals['bus']}")
    print(f"  trucks:      {totals['truck']}")
    print(f"  detected vehicles: {totals['vehicles_detected']} across {len(all_detection_counts)} sampled frames")
    print(f"  avg YOLO inference per sampled frame: {avg_infer_ms:.0f} ms")
    print("==========================================================")

    # Honest verdict: never claim real detections that don't exist.
    if totals["vehicles_detected"] == 0:
        print("[VERDICT] FAIL: ZERO vehicle detections — this source does NOT contain "
              "meaningful, detectable traffic for the SIH demo.")
        return 1
    print("[VERDICT] PASS: Non-zero YOLO vehicle detections measured on this source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())