"""
Thread-safe runtime state and frame buffer for BUS-CV Edge AI.
Stores live frame bytes (JPEG) for MJPEG streaming, live vehicle counts,
road hazard detections, confirmed hazard counts, FPS, GPS coordinates,
and processor error/lifecycle status.
"""

import threading
import datetime
from typing import Optional, Dict, Any, List

class EdgeAIRuntimeState:
    def __init__(self):
        self._lock = threading.Lock()
        self._latest_jpeg: Optional[bytes] = None
        self._live_counts: Dict[str, int] = {
            "car": 0,
            "motorcycle": 0,
            "bus": 0,
            "truck": 0,
            "total": 0
        }
        self._fps: float = 0.0
        self._gps: Dict[str, float] = {
            "latitude": 19.1197,
            "longitude": 72.9050,
            "speed": 0.0
        }
        self._status: str = "STANDBY"
        self._latest_error: Optional[str] = None
        self._frame_count: int = 0
        self._last_frame_time: Optional[datetime.datetime] = None

        # Road Hazard Intelligence State (Phase 3B)
        self._hazard_model_status: str = "STANDBY"
        self._hazard_model_name: str = "Pothole YOLOv8s (peterhdd)"
        self._latest_hazard_detections: List[Dict[str, Any]] = []
        self._confirmed_hazard_count: int = 0
        self._last_hazard: Optional[Dict[str, Any]] = None
        self._hazard_fps: float = 0.0
        self._latest_hazard_error: Optional[str] = None
        # Performance & Hardware Telemetry (Phase 3C)
        self._device_name: str = "CPU"
        self._processing_resolution: str = "1280x720 @ AI 480"
        self._vehicle_fps: float = 0.0

    def update_frame(
        self,
        jpeg_bytes: bytes,
        counts: Dict[str, int],
        fps: float,
        gps: Dict[str, float],
        hazard_detections: Optional[List[Dict[str, Any]]] = None,
        confirmed_hazard_count: Optional[int] = None,
        last_hazard: Optional[Dict[str, Any]] = None,
        hazard_fps: Optional[float] = None,
        hazard_status: Optional[str] = None,
        device_name: Optional[str] = None,
        processing_resolution: Optional[str] = None,
        vehicle_fps: Optional[float] = None
    ) -> None:
        with self._lock:
            self._latest_jpeg = jpeg_bytes
            self._live_counts = counts.copy()
            self._fps = fps
            self._gps = gps.copy()
            self._frame_count += 1
            self._last_frame_time = datetime.datetime.now(datetime.timezone.utc)

            if device_name is not None:
                self._device_name = device_name
            if processing_resolution is not None:
                self._processing_resolution = processing_resolution
            if vehicle_fps is not None:
                self._vehicle_fps = vehicle_fps

            if hazard_detections is not None:
                self._latest_hazard_detections = [d.copy() for d in hazard_detections]
            if confirmed_hazard_count is not None:
                self._confirmed_hazard_count = confirmed_hazard_count
            if last_hazard is not None:
                self._last_hazard = last_hazard.copy()
            if hazard_fps is not None:
                self._hazard_fps = hazard_fps
            if hazard_status is not None:
                self._hazard_model_status = hazard_status

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_jpeg

    def get_live_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counts": self._live_counts.copy(),
                "fps": round(self._fps, 1),
                "gps": self._gps.copy(),
                "frame_count": self._frame_count,
                "status": self._status,
                "latest_error": self._latest_error,
                "last_frame_time": self._last_frame_time.isoformat() if self._last_frame_time else None,
                # Road Hazard Telemetry
                "hazard_model_status": self._hazard_model_status,
                "hazard_model_name": self._hazard_model_name,
                "latest_hazard_detections": [d.copy() for d in self._latest_hazard_detections],
                "confirmed_hazard_count": self._confirmed_hazard_count,
                "last_hazard": self._last_hazard.copy() if self._last_hazard else None,
                "hazard_fps": round(self._hazard_fps, 1),
                "latest_hazard_error": self._latest_hazard_error,
                # Hardware & Resolution Telemetry
                "device_name": self._device_name,
                "processing_resolution": self._processing_resolution,
                "vehicle_fps": round(self._vehicle_fps if self._vehicle_fps > 0 else self._fps, 1)
            }

    def set_status(self, status: str, error: Optional[str] = None) -> None:
        with self._lock:
            self._status = status
            if error is not None:
                self._latest_error = error
            elif status in ("RUNNING", "STANDBY"):
                self._latest_error = None

    def set_hazard_status(self, status: str, error: Optional[str] = None) -> None:
        with self._lock:
            self._hazard_model_status = status
            if error is not None:
                self._latest_hazard_error = error
            elif status in ("ONLINE", "STANDBY"):
                self._latest_hazard_error = None

    def get_status(self) -> str:
        with self._lock:
            return self._status

    def get_error(self) -> Optional[str]:
        with self._lock:
            return self._latest_error

    def reset(self) -> None:
        with self._lock:
            self._latest_jpeg = None
            self._live_counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "total": 0}
            self._fps = 0.0
            self._status = "STANDBY"
            self._latest_error = None
            self._frame_count = 0
            self._last_frame_time = None
            self._hazard_model_status = "STANDBY"
            self._latest_hazard_detections = []
            self._confirmed_hazard_count = 0
            self._last_hazard = None
            self._hazard_fps = 0.0
            self._vehicle_fps = 0.0
            self._latest_hazard_error = None

runtime_state = EdgeAIRuntimeState()

