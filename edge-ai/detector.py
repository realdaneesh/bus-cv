"""
Edge AI - Object & Vehicle Detector
Runs real inference using Ultralytics YOLO (yolo11n.pt).
Detects and classifies real vehicles: car, motorcycle, bus, truck.
Draws genuine detection annotations and telemetry overlay onto frames.
"""

import os
import cv2
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# COCO vehicle class mappings
VEHICLE_CLASS_NAMES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

# Color palette for bounding boxes (BGR)
CLASS_COLORS = {
    "car": (246, 130, 59),        # Blue/Cyan
    "motorcycle": (232, 212, 0),   # Cyan
    "bus": (11, 158, 245),         # Amber
    "truck": (94, 63, 244),        # Rose/Red
    "default": (129, 185, 16)      # Emerald
}


class EdgeDetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.50,
        imgsz: int = 480
    ):
        # Locate model weights: use explicit path if provided, else scan candidate locations
        if model_path:
            self.model_path = model_path
        else:
            candidates = [
                os.path.join(os.path.dirname(__file__), "models", "vehicle", "yolo11n.pt"),
                os.path.join(os.path.dirname(__file__), "yolo11n.pt"),
                os.path.join(os.path.dirname(__file__), "..", "yolo11n.pt"),
                "yolo11n.pt",
                "yolov8n.pt"
            ]
            self.model_path = next((p for p in candidates if os.path.exists(p)), "yolo11n.pt")

        self.confidence_threshold = confidence_threshold
        self.imgsz = imgsz
        self.model = None
        self.is_initialized = False

        # Device & Threading Optimization
        import torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        if self.device == "cpu":
            torch.set_num_threads(min(4, os.cpu_count() or 4))

    def load_model(self) -> bool:
        """
        Load Ultralytics YOLO weights onto detected device.
        Returns True on success, False on failure.
        """
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO model from: {self.model_path} (device={self.device})")
            self.model = YOLO(self.model_path)
            self.is_initialized = True
            logger.info(f"YOLO detector successfully initialized with threshold={self.confidence_threshold}, imgsz={self.imgsz}")
            return True
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}", exc_info=True)
            self.is_initialized = False
            return False

    def detect_frame(self, frame) -> Dict[str, Any]:
        """
        Run real YOLO inference on a single OpenCV BGR frame.
        Filters for COCO vehicle classes: car, motorcycle, bus, truck.
        Returns normalized detections and vehicle counts.
        """
        if not self.is_initialized:
            success = self.load_model()
            if not success:
                return {
                    "detections": [],
                    "vehicle_counts": {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "total": 0},
                    "hazards": []
                }

        counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "total": 0}
        detections: List[Dict[str, Any]] = []

        try:
            import torch
            with torch.inference_mode():
                # Run inference with optimized imgsz resolution on detected device
                results = self.model(
                    frame,
                    conf=self.confidence_threshold,
                    imgsz=self.imgsz,
                    device=self.device,
                    verbose=False
                )

            for r in results:
                boxes = r.boxes
                if boxes is None or len(boxes) == 0:
                    continue

                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    if cls_id in VEHICLE_CLASS_NAMES:
                        vehicle_class = VEHICLE_CLASS_NAMES[cls_id]
                        conf = float(box.conf[0].item())
                        xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                        bbox = [round(v, 1) for v in xyxy]

                        counts[vehicle_class] += 1
                        counts["total"] += 1

                        detections.append({
                            "class": vehicle_class,
                            "confidence": round(conf, 3),
                            "bbox": bbox
                        })

        except Exception as e:
            logger.error(f"Inference error on frame: {e}")

        return {
            "detections": detections,
            "vehicle_counts": counts,
            "hazards": []  # Empty as standard COCO YOLO does not detect potholes/hazards
        }


    def annotate_frame(
        self,
        frame,
        detections: List[Dict[str, Any]],
        counts: Dict[str, int],
        telemetry: Optional[Dict[str, Any]] = None
    ):
        """
        Draw genuine bounding boxes, labels, and real-time HUD telemetry on the frame.
        """
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # 1. Draw vehicle bounding boxes
        for det in detections:
            bbox = det["bbox"]
            cls_name = det["class"]
            conf = det["confidence"]

            x1, y1, x2, y2 = [int(v) for v in bbox]
            color = CLASS_COLORS.get(cls_name, CLASS_COLORS["default"])

            # Bounding box rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Label badge
            label_text = f"{cls_name.upper()} {int(conf * 100)}%"
            (tw, th), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(
                annotated,
                (x1, max(0, y1 - th - 6)),
                (x1 + tw + 6, max(th + 6, y1)),
                color,
                -1
            )
            cv2.putText(
                annotated,
                label_text,
                (x1 + 3, max(th + 1, y1 - 3)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (10, 15, 25),
                1,
                cv2.LINE_AA
            )

        # 2. Draw HUD Header Banner
        banner_h = 44
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (9, 13, 22), -1)
        cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)
        cv2.line(annotated, (0, banner_h), (w, banner_h), (0, 212, 232), 1)

        # Brand Title
        cv2.putText(
            annotated,
            "BUS-CV  AI MONITORING",
            (12, 27),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 212, 232),
            2,
            cv2.LINE_AA
        )

        # Telemetry string
        gps_str = ""
        speed_str = ""
        fps_str = ""
        if telemetry:
            lat = telemetry.get("latitude")
            lng = telemetry.get("longitude")
            speed = telemetry.get("speed", 0.0)
            fps = telemetry.get("fps", 0.0)
            if lat is not None and lng is not None:
                gps_str = f"GPS: {lat:.4f}, {lng:.4f}"
            speed_str = f"{speed:.1f} km/h"
            fps_str = f"{fps:.1f} FPS"

        hud_info = f"VEHICLES: {counts.get('total', 0)} (C:{counts.get('car', 0)} M:{counts.get('motorcycle', 0)} B:{counts.get('bus', 0)} T:{counts.get('truck', 0)}) | {gps_str} | {fps_str}"
        cv2.putText(
            annotated,
            hud_info,
            (w - 560 if w > 650 else 12, 27 if w > 650 else banner_h + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (220, 230, 242),
            1,
            cv2.LINE_AA
        )

        return annotated
