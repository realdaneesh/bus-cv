"""
Edge AI - Road Hazard Event Manager & Orchestrator
Processes raw computer vision hazard detections through:
1. Confidence Filtering (>= 0.60)
2. Temporal Confirmation (requires multiple detections within a time window)
3. GPS Location Association (attaches real vehicle telemetry)
4. Spatial Deduplication (prevents multiple events within a 15-meter radius)
5. Explainable AI Priority Estimation (Operational priority based on bbox area and confidence)
6. Backend Event Emission (POST /api/events)
"""

import math
import time
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def compute_box_iou(boxA: List[float], boxB: List[float]) -> float:
    """Compute Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h

    boxA_area = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxB_area = max(1.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    union_area = boxA_area + boxB_area - inter_area
    return inter_area / union_area if union_area > 0 else 0.0

def compute_centroid_distance(boxA: List[float], boxB: List[float]) -> float:
    """Compute Euclidean distance between centers of two boxes."""
    cAx, cAy = (boxA[0] + boxA[2]) / 2.0, (boxA[1] + boxA[3]) / 2.0
    cBx, cBy = (boxB[0] + boxB[2]) / 2.0, (boxB[1] + boxB[3]) / 2.0
    return math.hypot(cAx - cBx, cAy - cBy)


class HazardTrack:
    """Tracks a single detected hazard across consecutive frames for temporal confirmation."""
    def __init__(self, detection: Dict[str, Any], track_id: int):
        self.track_id = track_id
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.hits = 1
        self.latest_bbox = detection.get("bbox", [0, 0, 0, 0])
        self.highest_conf = detection.get("confidence", 0.0)
        self.max_area_ratio = detection.get("area_ratio", 0.0)
        self.source = detection.get("source", "peterhdd_pothole_yolov8s")
        self.is_emitted = False

    def update(self, detection: Dict[str, Any]):
        self.last_seen = time.time()
        self.hits += 1
        self.latest_bbox = detection.get("bbox", self.latest_bbox)
        conf = detection.get("confidence", 0.0)
        if conf > self.highest_conf:
            self.highest_conf = conf
        area = detection.get("area_ratio", 0.0)
        if area > self.max_area_ratio:
            self.max_area_ratio = area


class HazardEventManager:
    def __init__(
        self,
        event_sender: Optional[Any] = None,
        min_confidence: float = 0.60,
        confirmation_count: int = 2,
        confirmation_window_seconds: float = 5.0,
        dedup_radius_meters: float = 15.0
    ):
        """
        :param event_sender: Instance of EventSender to transmit confirmed events to backend.
        :param min_confidence: Raw detection confidence filter (default 0.60).
        :param confirmation_count: Number of frame detections required to confirm a hazard (default 2).
        :param confirmation_window_seconds: Time window for temporal confirmation (default 5.0s).
        :param dedup_radius_meters: Spatial deduplication radius in meters (default 15.0m).
        """
        self.sender = event_sender
        self.min_confidence = min_confidence
        self.confirmation_count = confirmation_count
        self.confirmation_window_seconds = confirmation_window_seconds
        self.dedup_radius_meters = dedup_radius_meters

        self._active_tracks: List[HazardTrack] = []
        self._next_track_id = 1
        self._emitted_events: List[Dict[str, Any]] = []
        self.confirmed_count = 0
        self.dedup_suppressed_count = 0
        self.last_confirmed_event: Optional[Dict[str, Any]] = None

    def calculate_operational_priority(self, highest_conf: float, area_ratio: float, hits: int) -> str:
        """
        Explainable AI operational priority calculation.
        NOTE: This is an AI detection priority estimate, not a physical depth measurement.
        """
        if highest_conf >= 0.82 or area_ratio >= 0.035:
            return "HIGH"
        elif highest_conf >= 0.68 or hits >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    def process_detections(
        self,
        detections: List[Dict[str, Any]],
        gps_data: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of raw detections from the road hazard detector.
        Returns a list of newly created UrbanEvent payloads emitted during this step.
        """
        now = time.time()
        new_events_emitted = []

        # 1. Filter detections by minimum confidence threshold
        valid_detections = [
            d for d in detections
            if d.get("confidence", 0.0) >= self.min_confidence
        ]

        # 2. Match valid detections against active temporal tracks
        for det in valid_detections:
            bbox = det.get("bbox", [])
            matched_track = None

            for track in self._active_tracks:
                if track.is_emitted:
                    continue
                
                # Check bounding box IoU or centroid proximity
                iou = compute_box_iou(bbox, track.latest_bbox)
                c_dist = compute_centroid_distance(bbox, track.latest_bbox)
                
                # Match if IoU >= 0.15 or centroid distance <= 120 pixels
                if iou >= 0.15 or c_dist <= 120.0:
                    matched_track = track
                    break

            if matched_track:
                matched_track.update(det)
            else:
                # Create a new candidate track
                new_track = HazardTrack(det, self._next_track_id)
                self._next_track_id += 1
                self._active_tracks.append(new_track)

        # 3. Check for confirmed tracks that have not yet been emitted
        lat = gps_data.get("latitude", 28.6139)
        lng = gps_data.get("longitude", 77.2090)

        for track in self._active_tracks:
            if track.is_emitted:
                continue

            # Check temporal confirmation criteria
            time_span = track.last_seen - track.first_seen
            if track.hits >= self.confirmation_count and (now - track.first_seen) <= self.confirmation_window_seconds:
                # 4. Spatial Deduplication check against previously emitted events
                is_duplicate = False
                for prev in self._emitted_events:
                    dist = haversine_distance(lat, lng, prev["latitude"], prev["longitude"])
                    if dist <= self.dedup_radius_meters:
                        is_duplicate = True
                        prev["last_seen"] = now
                        prev["detection_count"] = prev.get("detection_count", 1) + track.hits
                        if track.highest_conf > prev.get("highest_conf", 0.0):
                            prev["highest_conf"] = track.highest_conf
                        logger.info(
                            f"[DEDUP] Pothole track #{track.track_id} suppressed: Matches existing event #{prev.get('id', 'local')} ({dist:.1f}m <= {self.dedup_radius_meters}m)"
                        )
                        break

                if is_duplicate:
                    self.dedup_suppressed_count += 1
                    track.is_emitted = True
                    continue

                # 5. Calculate AI Operational Priority
                priority = self.calculate_operational_priority(
                    highest_conf=track.highest_conf,
                    area_ratio=track.max_area_ratio,
                    hits=track.hits
                )

                # 6. Emit real event to backend
                event_payload = {
                    "event_type": "POTHOLE",
                    "confidence": round(track.highest_conf, 4),
                    "latitude": lat,
                    "longitude": lng,
                    "priority": priority,
                    "source": track.source,
                    "is_demo_data": False,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "hits": track.hits,
                    "track_id": track.track_id
                }

                logger.info(
                    f"[CONFIRMED HAZARD] Emitting POTHOLE at GPS ({lat:.5f}, {lng:.5f}) | Conf: {track.highest_conf:.2f} | Priority: {priority}"
                )

                if self.sender:
                    res = self.sender.send_urban_event(
                        event_type="POTHOLE",
                        confidence=track.highest_conf,
                        latitude=lat,
                        longitude=lng,
                        source=track.source
                    )
                    if res and "id" in res:
                        event_payload["id"] = res["id"]

                self._emitted_events.append({
                    "id": event_payload.get("id"),
                    "latitude": lat,
                    "longitude": lng,
                    "highest_conf": track.highest_conf,
                    "timestamp": now,
                    "last_seen": now,
                    "detection_count": track.hits
                })

                self.confirmed_count += 1
                self.last_confirmed_event = event_payload
                new_events_emitted.append(event_payload)
                track.is_emitted = True

        # 4. Clean up stale tracks older than 2x confirmation window
        cutoff = now - (self.confirmation_window_seconds * 2)
        self._active_tracks = [
            t for t in self._active_tracks
            if t.last_seen >= cutoff and not (t.is_emitted and (now - t.last_seen) > 3.0)
        ]

        return new_events_emitted

    def get_summary(self) -> Dict[str, Any]:
        """Return operational telemetry for runtime state & frontend HUD."""
        return {
            "confirmed_count": self.confirmed_count,
            "dedup_suppressed_count": self.dedup_suppressed_count,
            "last_confirmed_event": self.last_confirmed_event,
            "active_tracks_count": len(self._active_tracks)
        }
