import os
import datetime
import threading
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import Bus
from app.config import settings
from app.services.runtime_state import runtime_state

logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self):
        self._lock = threading.Lock()
        self._is_active: bool = False
        self._started_at: Optional[datetime.datetime] = None
        self._video_source: Optional[str] = None

        # Thread management
        self._worker_thread: Optional[threading.Thread] = None
        self._processor_instance: Optional[Any] = None
        self._stop_event: Optional[threading.Event] = None
        self._latest_error: Optional[str] = None
        self._video_validation: Optional[Dict[str, Any]] = None

    def is_running(self) -> bool:
        with self._lock:
            return self._is_active and (self._worker_thread is not None and self._worker_thread.is_alive())

    def get_status(self, db: Session, bus_code: str = "BUS_01") -> Dict[str, Any]:
        with self._lock:
            bus = db.query(Bus).filter(Bus.bus_code == bus_code).first()
            telemetry = runtime_state.get_live_telemetry()
            rt_status = runtime_state.get_status()
            error = self._latest_error or runtime_state.get_error()

            # Derive genuine statuses
            if rt_status == "ERROR":
                edge_ai_status = "ERROR"
                camera_status = "ERROR"
            elif self._is_active:
                edge_ai_status = "ONLINE"
                camera_status = "STREAMING"
            else:
                edge_ai_status = "STANDBY"
                camera_status = "DISCONNECTED"

            gps_status = bus.gps_status if bus else "LOCKED"

            uptime_seconds = None
            if self._is_active and self._started_at:
                uptime_seconds = int((datetime.datetime.now(datetime.timezone.utc) - self._started_at).total_seconds())

            if error:
                msg = f"Edge AI Error: {error}"
            elif self._is_active:
                msg = f"Edge AI pipeline active for {bus_code} (Running for {uptime_seconds or 0}s @ {telemetry['fps']} FPS)"
            else:
                msg = f"Monitoring offline for {bus_code}. Edge AI in STANDBY mode."

            return {
                "is_active": self._is_active,
                "bus_code": bus_code,
                "camera_status": camera_status,
                "edge_ai_status": edge_ai_status,
                "gps_status": gps_status,
                "started_at": self._started_at,
                "uptime_seconds": uptime_seconds,
                "fps": telemetry["fps"] if self._is_active else 0.0,
                "video_source": self._video_source,
                "video_validation": self._video_validation,
                "message": msg,
                "live_counts": telemetry["counts"],
                "live_gps": telemetry["gps"],
                "latest_error": error,
                # Phase 3B Road Hazard Telemetry
                "hazard_model_status": telemetry.get("hazard_model_status", "STANDBY"),
                "hazard_model_name": telemetry.get("hazard_model_name", "Pothole YOLOv8s (peterhdd)"),
                "latest_hazard_detections": telemetry.get("latest_hazard_detections", []),
                "confirmed_hazard_count": telemetry.get("confirmed_hazard_count", 0),
                "last_hazard": telemetry.get("last_hazard"),
                "hazard_fps": telemetry.get("hazard_fps", 0.0) if self._is_active else 0.0,
                "latest_hazard_error": telemetry.get("latest_hazard_error"),
                "device_name": telemetry.get("device_name", "CPU"),
                "processing_resolution": telemetry.get("processing_resolution", "1280x720 @ AI 480"),
                "vehicle_fps": telemetry.get("vehicle_fps", 0.0) if self._is_active else 0.0
            }


    def start_monitoring(
        self,
        db: Session,
        bus_code: str = "BUS_01",
        video_source: Optional[str] = None
    ) -> Dict[str, Any]:
        with self._lock:
            if self._is_active and self._worker_thread and self._worker_thread.is_alive():
                return {
                    "success": True,
                    "message": f"Monitoring is already active for {bus_code}.",
                    "status": self._get_status_unlocked(db, bus_code)
                }

            # Use the SAME deterministic priority logic as the Edge AI processor:
            # VIDEO_SOURCE env > TEST_MODE > DEMO/demo_traffic default > fallback.
            # (Previously this hardcoded urban_road_sample.mp4, bypassing demo mode.)
            if video_source:
                source = video_source
            else:
                from app.edge_ai.processor import get_default_video_source
                source = get_default_video_source()

            self._latest_error = None
            runtime_state.reset()
            self._video_source = source
            self._video_validation = None

            # Task 4: Validate the selected video BEFORE starting the pipeline.
            # If it cannot be opened, fail clearly instead of silently using a bad source.
            from app.edge_ai.processor import inspect_video
            vinfo = inspect_video(source)
            self._video_validation = vinfo
            if not vinfo["valid"]:
                err_msg = f"Cannot start monitoring with video '{source}': {vinfo['error']}"
                logger.error(err_msg)
                self._latest_error = err_msg
                runtime_state.set_status("ERROR", err_msg)
                return {
                    "success": False,
                    "message": err_msg,
                    "status": self._get_status_unlocked(db, bus_code)
                }

            # Create stop event and processor instance
            self._stop_event = threading.Event()
            try:
                from app.edge_ai.processor import VideoProcessor
                self._processor_instance = VideoProcessor(
                    video_source=source,
                    stop_event=self._stop_event
                )
            except Exception as e:
                err_msg = f"Failed to instantiate VideoProcessor: {e}"
                logger.error(err_msg, exc_info=True)
                self._latest_error = err_msg
                runtime_state.set_status("ERROR", err_msg)
                return {
                    "success": False,
                    "message": err_msg,
                    "status": self._get_status_unlocked(db, bus_code)
                }

            # Start worker thread
            def _worker_target():
                try:
                    self._processor_instance.run()
                except Exception as worker_err:
                    logger.error(f"Error in VideoProcessor worker thread: {worker_err}", exc_info=True)
                    self._latest_error = str(worker_err)
                    runtime_state.set_status("ERROR", str(worker_err))
                finally:
                    with self._lock:
                        self._is_active = False

            self._worker_thread = threading.Thread(
                target=_worker_target,
                name=f"EdgeAI-Worker-{bus_code}",
                daemon=True
            )
            self._worker_thread.start()

            self._is_active = True
            self._started_at = datetime.datetime.now(datetime.timezone.utc)

            # Update database status
            bus = db.query(Bus).filter(Bus.bus_code == bus_code).first()
            if bus:
                bus.edge_ai_status = "ONLINE"
                bus.camera_status = "STREAMING"
                bus.last_updated = datetime.datetime.now(datetime.timezone.utc)
                db.commit()

            return {
                "success": True,
                "message": f"Monitoring started for {bus_code}. YOLO processing video: {os.path.basename(source)}",
                "status": self._get_status_unlocked(db, bus_code)
            }

    def stop_monitoring(self, db: Session, bus_code: str = "BUS_01") -> Dict[str, Any]:
        with self._lock:
            if not self._is_active and (not self._worker_thread or not self._worker_thread.is_alive()):
                return {
                    "success": True,
                    "message": f"Monitoring is already inactive for {bus_code}.",
                    "status": self._get_status_unlocked(db, bus_code)
                }

            # 1. Signal stop to processor
            if self._stop_event:
                self._stop_event.set()

            # 2. Wait for worker thread to exit cleanly (up to 4 seconds)
            thread = self._worker_thread
            processor = self._processor_instance

        if thread and thread.is_alive():
            thread.join(timeout=4.0)

        with self._lock:
            self._is_active = False
            self._started_at = None
            self._worker_thread = None
            self._processor_instance = None
            self._stop_event = None
            self._video_validation = None

            runtime_state.set_status("STANDBY")

            # Update database state
            bus = db.query(Bus).filter(Bus.bus_code == bus_code).first()
            if bus:
                bus.edge_ai_status = "STANDBY"
                bus.camera_status = "DISCONNECTED"
                bus.last_updated = datetime.datetime.now(datetime.timezone.utc)
                db.commit()

            return {
                "success": True,
                "message": f"Monitoring cleanly stopped for {bus_code}. Video resources released.",
                "status": self._get_status_unlocked(db, bus_code)
            }

    def _get_status_unlocked(self, db: Session, bus_code: str) -> Dict[str, Any]:
        """Internal helper for status without acquiring lock again."""
        bus = db.query(Bus).filter(Bus.bus_code == bus_code).first()
        telemetry = runtime_state.get_live_telemetry()
        rt_status = runtime_state.get_status()
        error = self._latest_error or runtime_state.get_error()

        if rt_status == "ERROR":
            edge_ai_status = "ERROR"
            camera_status = "ERROR"
        elif self._is_active:
            edge_ai_status = "ONLINE"
            camera_status = "STREAMING"
        else:
            edge_ai_status = "STANDBY"
            camera_status = "DISCONNECTED"

        gps_status = bus.gps_status if bus else "LOCKED"
        uptime_seconds = None
        if self._is_active and self._started_at:
            uptime_seconds = int((datetime.datetime.now(datetime.timezone.utc) - self._started_at).total_seconds())

        msg = (
            f"Edge AI Error: {error}" if error else
            f"Edge AI pipeline active for {bus_code}" if self._is_active else
            f"Monitoring offline for {bus_code}. Edge AI in STANDBY mode."
        )

        return {
            "is_active": self._is_active,
            "bus_code": bus_code,
            "camera_status": camera_status,
            "edge_ai_status": edge_ai_status,
            "gps_status": gps_status,
            "started_at": self._started_at,
            "uptime_seconds": uptime_seconds,
            "fps": telemetry["fps"] if self._is_active else 0.0,
            "video_source": self._video_source,
            "video_validation": self._video_validation,
            "message": msg,
            "live_counts": telemetry["counts"],
            "live_gps": telemetry["gps"],
            "latest_error": error,
            # Phase 3B Road Hazard Telemetry
            "hazard_model_status": telemetry.get("hazard_model_status", "STANDBY"),
            "hazard_model_name": telemetry.get("hazard_model_name", "Pothole YOLOv8s (peterhdd)"),
            "latest_hazard_detections": telemetry.get("latest_hazard_detections", []),
            "confirmed_hazard_count": telemetry.get("confirmed_hazard_count", 0),
            "last_hazard": telemetry.get("last_hazard"),
            "hazard_fps": telemetry.get("hazard_fps", 0.0) if self._is_active else 0.0,
            "latest_hazard_error": telemetry.get("latest_hazard_error"),
            "device_name": telemetry.get("device_name", "CPU"),
            "processing_resolution": telemetry.get("processing_resolution", "1280x720 @ AI 480"),
            "vehicle_fps": telemetry.get("vehicle_fps", 0.0) if self._is_active else 0.0
        }


monitoring_service = MonitoringService()
