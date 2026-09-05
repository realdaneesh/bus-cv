"""
Edge AI - Dedicated Road Hazard Detector
Loads pretrained YOLOv8s pothole detection model (peterhdd/pothole-detection-yolov8).
Runs real Ultralytics inference to identify road surface hazards (Potholes).
Provides structured detection extraction, confidence thresholding, and HUD hazard annotation.
"""

import os
import cv2
import time
import datetime
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Hazard visual styling (BGR)
HAZARD_COLOR_PRIMARY = (0, 69, 255)     # Deep Orange / Red for high hazard
HAZARD_COLOR_SECONDARY = (0, 140, 255)   # Amber / Orange
HAZARD_COLOR_BADGE_BG = (15, 20, 35)    # Dark Slate for label backdrop

class RoadHazardDetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.60,
        enable_road_roi: bool = False,
        imgsz: int = 480
    ):
        """
        Initialize the dedicated road hazard detector.
        :param model_path: Explicit path to weights file.
        :param confidence_threshold: Minimum confidence filter (default 0.60).
        :param enable_road_roi: If True, crops the upper sky/horizon to focus on road pavement.
        :param imgsz: Inference resolution for CPU optimization (default 480).
        """
        self.confidence_threshold = confidence_threshold
        self.enable_road_roi = enable_road_roi
        self.imgsz = imgsz
        self.model = None
        self.is_initialized = False
        self.model_name = "Pothole YOLOv8s (peterhdd)"
        self.model_source = "peterhdd_pothole_yolov8s"
        
        # Device detection
        import torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        
        # Resolve model path: use explicit path if given, else scan candidate locations
        if model_path:
            self.model_path = model_path
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            candidates = [
                os.path.join(base_dir, "models", "road_damage", "peterhdd_pothole_yolov8s.pt"),
                os.path.join(base_dir, "road_damage_eval", "models", "peterhdd_pothole_yolov8s.pt"),
                os.path.join(base_dir, "peterhdd_pothole_yolov8s.pt"),
                os.path.join(os.path.dirname(base_dir), "peterhdd_pothole_yolov8s.pt")
            ]
            self.model_path = next((p for p in candidates if os.path.exists(p)), candidates[0])

    def load_model(self) -> bool:
        """
        Load Ultralytics YOLO model once per processor lifecycle.
        Returns True on success, False on failure.
        """
        if not os.path.exists(self.model_path):
            logger.error(f"Road hazard model weights not found at: {self.model_path}")
            self.is_initialized = False
            return False

        try:
            from ultralytics import YOLO
            logger.info(f"Loading Road Hazard YOLO model from: {self.model_path} (device={self.device})")
            self.model = YOLO(self.model_path)
            self.is_initialized = True
            logger.info(f"Road Hazard detector initialized successfully (conf_threshold={self.confidence_threshold}, imgsz={self.imgsz})")
            return True
        except Exception as e:
            logger.error(f"Failed to load Road Hazard model: {e}", exc_info=True)
            self.is_initialized = False
            return False

    def detect(self, frame, conf_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Run genuine YOLOv8 inference on a road camera frame.
        Extracts bounding box, real confidence, area ratio, and timestamp.
        """
        if not self.is_initialized:
            if not self.load_model():
                return []

        effective_conf = conf_threshold if conf_threshold is not None else self.confidence_threshold
        detections: List[Dict[str, Any]] = []
        h, w = frame.shape[:2]

        try:
            # Handle optional road ROI
            roi_y_offset = 0
            inference_frame = frame
            if self.enable_road_roi and h > 200:
                # Lower 65% of frame represents the road surface
                roi_y_offset = int(h * 0.35)
                inference_frame = frame[roi_y_offset:h, 0:w]

            import torch
            with torch.inference_mode():
                results = self.model(
                    inference_frame,
                    conf=effective_conf,
                    imgsz=self.imgsz,
                    device=self.device,
                    verbose=False
                )

            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()


            for r in results:
                if r.boxes is None or len(r.boxes) == 0:
                    continue

                for box in r.boxes:
                    conf = float(box.conf[0].item())
                    xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    
                    # Translate back to full frame coordinates if ROI was used
                    x1 = max(0.0, xyxy[0])
                    y1 = max(0.0, xyxy[1] + roi_y_offset)
                    x2 = min(float(w), xyxy[2])
                    y2 = min(float(h), xyxy[3] + roi_y_offset)

                    box_w = max(1.0, x2 - x1)
                    box_h = max(1.0, y2 - y1)
                    area_ratio = round((box_w * box_h) / (w * h), 5)

                    detections.append({
                        "event_type": "POTHOLE",
                        "confidence": round(conf, 4),
                        "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                        "area_ratio": area_ratio,
                        "timestamp": now_iso,
                        "source": self.model_source,
                        "model_name": self.model_name
                    })

        except Exception as e:
            logger.error(f"Road hazard inference error: {e}", exc_info=True)

        return detections

    def annotate(self, frame, detections: List[Dict[str, Any]], confirmed_count: int = 0):
        """
        Draw visually distinct road hazard annotations on the frame.
        - Hazard red/orange bounding boxes
        - Warning label badge with confidence & operational priority estimate
        """
        if not detections:
            return frame

        annotated = frame.copy()

        for det in detections:
            bbox = det.get("bbox", [])
            if len(bbox) != 4:
                continue

            x1, y1, x2, y2 = [int(v) for v in bbox]
            conf = det.get("confidence", 0.0)
            conf_pct = int(conf * 100)

            # Determine operational priority visual tag
            area = det.get("area_ratio", 0.0)
            if conf >= 0.85 or area >= 0.04:
                priority_tag = "HIGH"
                box_color = HAZARD_COLOR_PRIMARY
            elif conf >= 0.70:
                priority_tag = "MED"
                box_color = HAZARD_COLOR_SECONDARY
            else:
                priority_tag = "LOW"
                box_color = (0, 200, 255)

            # 1. Bounding box with corner accents
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
            corner_len = min(16, min((x2 - x1) // 3, (y2 - y1) // 3))
            if corner_len > 3:
                # Top-left
                cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), (255, 255, 255), 3)
                cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), (255, 255, 255), 3)
                # Bottom-right
                cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), (255, 255, 255), 3)
                cv2.line(annotated, (x2, y2), (x2, y2 - corner_len), (255, 255, 255), 3)

            # 2. Hazard badge label
            label = f"! POTHOLE {conf_pct}% [{priority_tag}]"
            (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            
            badge_y1 = max(0, y1 - th - 8)
            badge_y2 = max(th + 8, y1)
            cv2.rectangle(annotated, (x1, badge_y1), (x1 + tw + 10, badge_y2), box_color, -1)
            cv2.putText(
                annotated,
                label,
                (x1 + 4, max(th + 2, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        return annotated
