"""
Edge AI - Dual-Model Video Frame Processor & Pipeline Orchestrator
Coordinates:
1. OpenCV VideoCapture
2. Primary Vehicle Intelligence (YOLO11n): car, motorcycle, bus, truck
3. Dedicated Road Hazard Intelligence (YOLOv8s): Potholes with temporal confirmation & spatial deduplication
4. Multi-layer HUD Frame Annotation (Vehicles in green, Potholes in orange/red)
5. Live Frame Buffer for MJPEG streaming
6. Periodic Traffic Aggregation & Bus GPS Telemetry
"""

import os
import time
import cv2
import logging
import threading
from typing import Optional, List, Dict, Any

# Directory containing this package file (used to resolve bundled video assets).
_current_dir = os.path.dirname(os.path.abspath(__file__))

try:
    from app.services.runtime_state import runtime_state
except Exception:
    runtime_state = None

from app.edge_ai.gps_simulator import GPSSimulator
from app.edge_ai.detector import EdgeDetector
from app.edge_ai.event_sender import EventSender
from app.edge_ai.road_hazard_detector import RoadHazardDetector
from app.edge_ai.hazard_event_manager import HazardEventManager

logging.basicConfig(level=logging.INFO, format="[Processor] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BUS_CODE = os.environ.get("BUS_CODE", "BUS_01")
VIDEO_LOOP = os.environ.get("VIDEO_LOOP", "true").lower() in ("true", "1", "yes")
TRAFFIC_REPORT_INTERVAL_SEC = float(os.environ.get("TRAFFIC_REPORT_INTERVAL", "5.0"))
GPS_UPDATE_INTERVAL_SEC = float(os.environ.get("GPS_UPDATE_INTERVAL", "3.0"))

# Dual-Model Cadence Configuration (CPU Optimized)
VEHICLE_INFERENCE_INTERVAL = int(os.environ.get("VEHICLE_INFERENCE_INTERVAL", "1"))
HAZARD_INFERENCE_INTERVAL = int(os.environ.get("HAZARD_INFERENCE_INTERVAL", "3"))
HAZARD_MIN_CONFIDENCE = float(os.environ.get("HAZARD_MIN_CONFIDENCE", "0.60"))


# A real road-traffic clip dropped into edge-ai/videos/ with this exact name is
# auto-discovered as "REAL FOOTAGE" with zero code changes.
REAL_TRAFFIC_VIDEO = os.path.join(_current_dir, "videos", "real_traffic.mp4")


def classify_source_type(source: str) -> str:
    """
    Classify a video source so the UI never falsely labels synthetic footage as real.
    Returns one of: REAL FOOTAGE / DEVELOPMENT TEST FOOTAGE / TEST FOOTAGE / USER_PROVIDED
    """
    name = os.path.basename(source or "").lower()
    if name == "real_traffic.mp4":
        return "REAL FOOTAGE"
    if name == "demo_traffic.mp4":
        return "DEVELOPMENT TEST FOOTAGE"
    if name == "urban_road_sample.mp4":
        return "TEST FOOTAGE"
    return "USER_PROVIDED"


def get_default_video_source() -> str:
    """
    Deterministic priority rules for video source selection:
    1. Explicit VIDEO_SOURCE env var (highest priority)
    2. TEST_MODE=true -> edge-ai/videos/urban_road_sample.mp4 (automated tests only)
    3. Validated REAL demo footage -> edge-ai/videos/real_traffic.mp4
    4. Existing development demo -> edge-ai/videos/demo_traffic.mp4
    5. Fallback -> edge-ai/videos/urban_road_sample.mp4
    """
    video_source_env = os.environ.get("VIDEO_SOURCE", "").strip() or None
    test_mode = os.environ.get("TEST_MODE", "").lower() in ("true", "1", "yes")
    demo_mode = os.environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes")
    demo_video = os.path.join(_current_dir, "videos", "demo_traffic.mp4")

    selected = None
    reason = ""

    if video_source_env:
        selected = video_source_env
        reason = "VIDEO_SOURCE env var explicitly set"
    elif test_mode:
        selected = os.path.join(_current_dir, "videos", "urban_road_sample.mp4")
        reason = "TEST_MODE=true -> urban_road_sample.mp4 (automated tests)"
    elif os.path.exists(REAL_TRAFFIC_VIDEO):
        selected = REAL_TRAFFIC_VIDEO
        reason = "Validated real footage present -> real_traffic.mp4"
    elif demo_mode or os.path.exists(demo_video):
        selected = demo_video
        reason = "demo_traffic.mp4 present (development demo execution)"
    else:
        selected = os.path.join(_current_dir, "videos", "urban_road_sample.mp4")
        reason = "no real or demo footage -> fallback to urban_road_sample.mp4"

    # Clear runtime source-selection decision log (see Task 1 audit requirements)
    logger.info("[VIDEO SOURCE] ===================================================")
    logger.info(f"[VIDEO SOURCE] Requested override: {video_source_env or '(not set)'}")
    logger.info(f"[VIDEO SOURCE] TEST_MODE: {test_mode}")
    logger.info(f"[VIDEO SOURCE] DEMO_MODE: {demo_mode}")
    logger.info(
        f"[VIDEO SOURCE] demo_traffic exists: "
        f"{os.path.exists(demo_video)} ({demo_video})"
    )
    logger.info(f"[VIDEO SOURCE] Selected source: {selected}")
    logger.info(f"[VIDEO SOURCE] Classification: {classify_source_type(selected)}")
    logger.info(f"[VIDEO SOURCE] Selection reason: {reason}")
    logger.info("[VIDEO SOURCE] ===================================================")
    return selected


def inspect_video(source: str) -> Dict[str, Any]:
    """
    Task 4: Validate a video source BEFORE monitoring begins.
    Reports file existence + real metadata (resolution, FPS, total frames, duration).
    Returns {'valid': True, ...} on success, {'valid': False, 'error': ...} otherwise.
    """
    info: Dict[str, Any] = {
        "path": source,
        "exists": os.path.exists(source),
        "valid": False,
        "error": None,
    }

    logger.info("[VIDEO VALIDATION] ===============================================")
    logger.info(f"[VIDEO VALIDATION] file path: {source}")
    if not info["exists"]:
        info["error"] = f"Video file does not exist: {source}"
        logger.error(f"[VIDEO VALIDATION] exists: False | error: {info['error']}")
        logger.info("[VIDEO VALIDATION] ===============================================")
        return info
    logger.info("[VIDEO VALIDATION] exists: True")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        info["error"] = (
            f"OpenCV could not open video (codec/corruption): {source}"
        )
        logger.error(f"[VIDEO VALIDATION] error: {info['error']}")
        try:
            cap.release()
        except Exception:
            pass
        logger.info("[VIDEO VALIDATION] ===============================================")
        return info

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
    fps = round(float(cap.get(cv2.CAP_PROP_FPS) or 0.0), 2)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    duration = (frames / fps) if fps > 0 else 0.0

    info.update({
        "valid": True,
        "resolution": f"{width}x{height}",
        "width": width,
        "height": height,
        "fps": fps,
        "frames": frames,
        "duration_sec": round(duration, 2),
        "source_type": classify_source_type(source),
        "source_label": f"{os.path.basename(source)} ({classify_source_type(source)})",
    })
    logger.info(
        f"[VIDEO VALIDATION] resolution: {width}x{height} | fps: {fps} | "
        f"total frames: {frames} | duration: {duration:.2f}s"
    )
    cap.release()
    logger.info("[VIDEO VALIDATION] ===============================================")
    return info


class LatestFrameBuffer:
    """
    Single-slot, thread-safe, latest-frame-semantics buffer.
    The video reader publishes the newest frame; the road-hazard worker consumes
    only the most recent frame (dropping intermediately produced ones).
    No unbounded queues; no unnecessary frame copies.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._frame = None
        self._frame_id = 0
        self._location = None

    def publish(self, frame, frame_id: int, location) -> None:
        with self._lock:
            self._frame = frame
            self._frame_id = frame_id
            self._location = location

    def latest(self):
        with self._lock:
            return self._frame, self._frame_id, self._location


class VideoProcessor:
    def __init__(
        self,
        video_source: Optional[str] = None,
        stop_event: Optional[threading.Event] = None,
        video_loop: Optional[bool] = None,
        confidence_threshold: float = 0.50,
        hazard_confidence_threshold: float = HAZARD_MIN_CONFIDENCE,
        hazard_interval: int = HAZARD_INFERENCE_INTERVAL
    ):
        self.video_source = self.resolve_video_source(video_source)
        self.stop_event = stop_event
        self.video_loop = video_loop if video_loop is not None else VIDEO_LOOP
        self.hazard_interval = hazard_interval

        # Core Components
        self.gps = GPSSimulator()
        self.sender = EventSender(backend_url=BACKEND_URL, bus_code=BUS_CODE)
        
        # Dual Detectors
        self.vehicle_detector = EdgeDetector(confidence_threshold=confidence_threshold)
        self.hazard_detector = RoadHazardDetector(confidence_threshold=hazard_confidence_threshold)
        self.hazard_manager = HazardEventManager(
            event_sender=self.sender,
            min_confidence=hazard_confidence_threshold,
            confirmation_count=2,
            confirmation_window_seconds=5.0,
            dedup_radius_meters=15.0
        )

        self.is_running = False
        self._frame_count = 0
        self._fps = 0.0
        self._vehicle_fps = 0.0
        self._hazard_fps = 0.0
        self._device_name = "CPU"
        self._resolution_str = "1280x720 @ AI 480"
        self._window_frames: List[Dict[str, int]] = []
        self._last_traffic_report_time = time.time()
        self._last_gps_update_time = time.time()

        # Telemetry Cache (thread-safe: written by hazard worker, read by main loop)
        self._latest_hazard_detections: List[Dict[str, Any]] = []
        self._hazard_cache_lock = threading.Lock()
        self._hazard_avg_ms: float = 0.0

        # Road Hazard non-blocking worker (runs on a separate thread so the slow
        # pothole model NEVER blocks the vehicle detection / MJPEG stream).
        self._frame_buffer = LatestFrameBuffer()
        self._hazard_stop = threading.Event()
        self._hazard_thread: Optional[threading.Thread] = None
        self._last_hazard_frame_id = -1

    def resolve_video_source(self, explicit_source: Optional[str] = None) -> str:
        source = explicit_source or get_default_video_source()
        if not os.path.isabs(source) and not os.path.exists(source):
            alt = os.path.join(_current_dir, source)
            if os.path.exists(alt):
                return alt
            alt2 = os.path.join(os.path.dirname(_current_dir), source)
            if os.path.exists(alt2):
                return alt2
        return source

    def _start_hazard_worker(self) -> None:
        self._hazard_stop.clear()
        self._last_hazard_frame_id = -1
        self._hazard_avg_ms = 0.0
        self._hazard_thread = threading.Thread(
            target=self._hazard_worker_loop,
            name="bus-cv-hazard-worker",
            daemon=True,
        )
        self._hazard_thread.start()
        logger.info("[HAZARD WORKER] Road hazard inference worker started (non-blocking).")

    def _stop_hazard_worker(self) -> None:
        self._hazard_stop.set()
        if self._hazard_thread and self._hazard_thread.is_alive():
            self._hazard_thread.join(timeout=3.0)
        self._hazard_thread = None
        logger.info("[HAZARD WORKER] Road hazard inference worker stopped.")

    def _hazard_worker_loop(self) -> None:
        """
        Background loop: consumes ONLY the latest published frame and runs the slow
        pothole YOLO inference + event orchestration there, so the vehicle detection
        / MJPEG stream in the main thread is never blocked by it.
        """
        while not self._hazard_stop.is_set():
            frame, frame_id, location = self._frame_buffer.latest()
            if frame is None or frame_id == self._last_hazard_frame_id:
                time.sleep(0.02)
                continue
            if not self.hazard_loaded_flag:
                break

            t_haz = time.time()
            try:
                raw_hazards = self.hazard_detector.detect(frame)
            except Exception as e:
                logger.error(f"Road hazard inference error in worker: {e}", exc_info=True)
                raw_hazards = []
            latency = time.time() - t_haz

            with self._hazard_cache_lock:
                self._hazard_avg_ms = latency * 1000.0
                self._latest_hazard_detections = raw_hazards
            self._last_hazard_frame_id = frame_id
            self._hazard_fps = (1.0 / latency) if latency > 0 else 0.0

            # Temporal confirmation + spatial deduplication + event emission.
            try:
                if location and self.hazard_manager:
                    self.hazard_manager.process_detections(raw_hazards, location)
            except Exception as e:
                logger.error(f"Road hazard event processing error: {e}", exc_info=True)

            # Keep this cadence bounded so extreme slow pothole inference does not
            # starve the CPU below usable vehicle streaming.
            time.sleep(max(0.0, 0.1 - latency))

    def run(self):
        """
        Main processing loop:
        1. Validates and opens video source via OpenCV VideoCapture
        2. Loads YOLO vehicle model (YOLO11n) and road hazard model (YOLOv8s)
        3. Reads frames sequentially with configurable loop / termination
        4. Detects vehicles every frame (smooth telemetry)
        5. Detects potholes at configured cadence (approx 3-5 FPS on CPU)
        6. Processes hazards through confidence filter, temporal confirmation, and spatial deduplication
        7. Draws multi-layer HUD annotations (Vehicles + Potholes)
        8. Updates thread-safe runtime state & MJPEG buffer
        9. Periodically aggregates and posts traffic observations & GPS updates
        10. Cleanly releases all OpenCV resources on exit
        """
        logger.info(f"Starting Dual-Model VideoProcessor for {BUS_CODE}")
        logger.info(f"Target Video Source: {self.video_source}")
        logger.info(f"Inference Cadence: Vehicle=every {VEHICLE_INFERENCE_INTERVAL}f, Hazard=every {self.hazard_interval}f")

        if runtime_state:
            runtime_state.set_status("INITIALIZING")

        # 1. Validate video source file existence
        if not os.path.exists(self.video_source):
            err_msg = (
                f"Video source not found at: '{self.video_source}'. "
                "Please place an urban road traffic video in 'edge-ai/videos/' or set VIDEO_SOURCE."
            )
            logger.error(err_msg)
            if runtime_state:
                runtime_state.set_status("ERROR", err_msg)
            return

        # 2. Open OpenCV VideoCapture
        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            err_msg = f"OpenCV failed to open video source: '{self.video_source}'. Check video codec or file integrity."
            logger.error(err_msg)
            if runtime_state:
                runtime_state.set_status("ERROR", err_msg)
            return

        # 3. Load Primary Vehicle Model
        if not self.vehicle_detector.load_model():
            err_msg = "Vehicle YOLO model failed to load weights."
            logger.error(err_msg)
            if runtime_state:
                runtime_state.set_status("ERROR", err_msg)
            cap.release()
            return

        # Detect runtime device
        self._device_name = str(self.vehicle_detector.device).upper()
        if "CUDA" in self._device_name and not self._device_name.startswith("CUDA"):
            self._device_name = f"CUDA:{self._device_name}"
        elif "CPU" in self._device_name:
            self._device_name = "CPU"

        # Frame resolution detection
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        self._resolution_str = f"{width}x{height} @ AI 480"

        # 4. Load Road Hazard Model independently (degraded mode if fails)
        hazard_loaded = self.hazard_detector.load_model()
        if hazard_loaded:
            logger.info(f"Road Hazard AI model loaded successfully on {self.hazard_detector.device}.")
            if runtime_state:
                runtime_state.set_hazard_status("ONLINE")
        else:
            logger.warning("Road Hazard model failed to load. Operating in Vehicle-Only degraded mode.")
            if runtime_state:
                runtime_state.set_hazard_status("ERROR", "Failed to load pothole detection weights")

        self.is_running = True
        self.hazard_loaded_flag = hazard_loaded
        if runtime_state:
            runtime_state.set_status("RUNNING")

        # 4b. Start the non-blocking road-hazard worker (separate thread). If the
        # hazard model failed to load, the worker will not start and vehicle
        # detection continues unaffected (graceful degradation).
        if hazard_loaded:
            self._start_hazard_worker()
        else:
            logger.warning("Road Hazard worker NOT started (model unavailable). Vehicle-only mode.")
            if runtime_state:
                runtime_state.set_hazard_status("ERROR", "Failed to load pothole detection weights")

        video_native_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        target_frame_time = 1.0 / max(5.0, min(30.0, video_native_fps))
        fps_calc_time = time.time()
        fps_frames = 0
        vehicle_infer_count = 0
        hazard_infer_count = 0

        # Stage-wise performance profiling (genuine measured values, Task 3)
        prof_read_time = 0.0
        prof_vehicle_time = 0.0
        prof_hazard_time = 0.0
        prof_encode_time = 0.0

        logger.info(f"Video opened successfully: {int(cap.get(cv2.CAP_PROP_FRAME_COUNT))} frames @ {video_native_fps:.1f} FPS [{self._resolution_str}]")
        logger.info(f"Active Runtime Device: {self._device_name}")

        try:
            while self.is_running:
                # Check graceful stop event from monitoring service
                if self.stop_event and self.stop_event.is_set():
                    logger.info("Stop event detected. Initiating clean shutdown.")
                    break

                t_start = time.time()

                _t_read = time.time()
                ret, frame = cap.read()
                if not ret:
                    if self.video_loop:
                        logger.info("End of video reached. Looping back to frame 0.")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        logger.info("End of video reached. VIDEO_LOOP=false. Stopping processor.")
                        break

                prof_read_time += time.time() - _t_read
                self._frame_count += 1
                fps_frames += 1

                # Current GPS position
                location = self.gps.get_current_location()

                # Publish latest frame (latest-frame semantics) for the background
                # hazard worker. The slow pothole model never runs on this thread.
                self._frame_buffer.publish(frame, self._frame_count, location)

                # 5. Vehicle YOLO inference (Every frame)
                _t_veh = time.time()
                det_result = self.vehicle_detector.detect_frame(frame)
                prof_vehicle_time += time.time() - _t_veh
                vehicle_infer_count += 1
                live_counts = det_result["vehicle_counts"]
                vehicle_detections = det_result["detections"]
                self._window_frames.append(live_counts)

                # 6. Read the cached hazard results (updated by the hazard worker
                #    thread on its own schedule; never blocks the vehicle stream).
                with self._hazard_cache_lock:
                    cached_hazards = list(self._latest_hazard_detections)

                # Calculate measured overall FPS every 1 second
                now = time.time()
                elapsed_fps = now - fps_calc_time
                if elapsed_fps >= 1.0:
                    win_reads = fps_frames
                    win_veh = vehicle_infer_count
                    self._fps = fps_frames / elapsed_fps
                    self._vehicle_fps = vehicle_infer_count / elapsed_fps
                    # Genuine stage-wise profiling log (real measured latencies/FPS).
                    with self._hazard_cache_lock:
                        hazard_avg = self._hazard_avg_ms
                    logger.info(
                        f"[PERF] pipeline={self._fps:.2f} FPS | vehicle_infer={self._vehicle_fps:.2f} FPS "
                        f"| hazard_infer={self._hazard_fps:.2f} FPS | "
                        f"avg_read={prof_read_time / max(1, win_reads) * 1000:.1f}ms "
                        f"| avg_vehicle={prof_vehicle_time / max(1, win_veh) * 1000:.1f}ms "
                        f"| avg_hazard_worker={hazard_avg:.1f}ms "
                        f"| avg_encode={prof_encode_time / max(1, win_reads) * 1000:.1f}ms "
                        f"(hazard runs on background worker; never blocks vehicle stream)"
                    )
                    fps_frames = 0
                    vehicle_infer_count = 0
                    prof_read_time = 0.0
                    prof_vehicle_time = 0.0
                    prof_hazard_time = 0.0
                    prof_encode_time = 0.0
                    fps_calc_time = now

                # 7. Multi-layer HUD Annotation
                _t_enc = time.time()
                # Layer A: Vehicle annotations
                telemetry = {
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "speed": location["speed"],
                    "fps": self._fps,
                    "hazard_count": len(cached_hazards),
                    "confirmed_hazards": self.hazard_manager.confirmed_count,
                    "device": self._device_name,
                    "resolution": self._resolution_str
                }
                annotated = self.vehicle_detector.annotate_frame(
                    frame,
                    vehicle_detections,
                    live_counts,
                    telemetry
                )

                # Layer B: Road Hazard annotations (vibrant orange/red overlays, cached on intermediate frames)
                if cached_hazards:
                    annotated = self.hazard_detector.annotate(
                        annotated,
                        cached_hazards,
                        confirmed_count=self.hazard_manager.confirmed_count
                    )

                # 8. Encode JPEG for MJPEG stream
                _, jpeg_buf = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                jpeg_bytes = jpeg_buf.tobytes()
                prof_encode_time += time.time() - _t_enc

                # Update thread-safe runtime state
                if runtime_state:
                    runtime_state.update_frame(
                        jpeg_bytes=jpeg_bytes,
                        counts=live_counts,
                        fps=self._fps,
                        gps=location,
                        hazard_detections=cached_hazards,
                        confirmed_hazard_count=self.hazard_manager.confirmed_count,
                        last_hazard=self.hazard_manager.last_confirmed_event,
                        hazard_fps=self._hazard_fps,
                        hazard_status="ONLINE" if hazard_loaded else "ERROR",
                        device_name=self._device_name,
                        processing_resolution=self._resolution_str,
                        vehicle_fps=self._vehicle_fps
                    )

                # 9. Periodic GPS update to backend
                if now - self._last_gps_update_time >= GPS_UPDATE_INTERVAL_SEC:
                    self.gps.step()
                    new_loc = self.gps.get_current_location()
                    self.sender.update_bus_location(
                        latitude=new_loc["latitude"],
                        longitude=new_loc["longitude"],
                        speed=new_loc["speed"]
                    )
                    self._last_gps_update_time = now

                # 10. Periodic Traffic Aggregation to backend
                if now - self._last_traffic_report_time >= TRAFFIC_REPORT_INTERVAL_SEC:
                    self._report_aggregated_traffic(location)
                    self._last_traffic_report_time = now

                # Frame pacing
                t_elapsed = time.time() - t_start
                sleep_time = max(0.005, target_frame_time - t_elapsed)
                time.sleep(sleep_time)

        except Exception as e:
            err_msg = f"Exception inside video processing loop: {e}"
            logger.error(err_msg, exc_info=True)
            if runtime_state:
                runtime_state.set_status("ERROR", err_msg)
        finally:
            self.is_running = False
            self._stop_hazard_worker()
            cap.release()
            logger.info("OpenCV VideoCapture released.")
            if runtime_state:
                if runtime_state.get_status() != "ERROR":
                    runtime_state.set_status("STANDBY")
            logger.info("VideoProcessor terminated cleanly.")

    def _report_aggregated_traffic(self, location: Dict[str, Any]):
        """
        Aggregate actual YOLO detections from all frames in the window.
        Compute average vehicle count and vehicle breakdown, then post to /api/traffic.
        """
        if not self._window_frames:
            return

        n = len(self._window_frames)
        avg_car = int(round(sum(f["car"] for f in self._window_frames) / n))
        avg_motorcycle = int(round(sum(f["motorcycle"] for f in self._window_frames) / n))
        avg_bus = int(round(sum(f["bus"] for f in self._window_frames) / n))
        avg_truck = int(round(sum(f["truck"] for f in self._window_frames) / n))
        avg_total = int(round(sum(f["total"] for f in self._window_frames) / n))

        logger.info(
            f"[TRAFFIC] window aggregation: {n} frame(s) -> avg_total={avg_total} "
            f"(cars:{avg_car}, motorcycles:{avg_motorcycle}, buses:{avg_bus}, trucks:{avg_truck})"
        )

        obs = self.sender.send_traffic_observation(
            vehicle_count=avg_total,
            car_count=avg_car,
            motorcycle_count=avg_motorcycle,
            bus_count=avg_bus,
            truck_count=avg_truck,
            latitude=location["latitude"],
            longitude=location["longitude"],
            source="AI_DETECTION"
        )
        obs_id = obs.get("id") if isinstance(obs, dict) else None
        logger.info(f"[TRAFFIC] observation sent: POST /api/traffic -> observation ID: {obs_id}")
        self._window_frames.clear()


if __name__ == "__main__":
    processor = VideoProcessor()
    processor.run()

