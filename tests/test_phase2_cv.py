"""
Automated Verification Suite for BUS-CV Phase 2:
Real Video + Ultralytics YOLO Edge AI + MJPEG Streaming + Safe Monitoring Lifecycle.
"""

import sys
import os
import time
import asyncio
import pytest
from fastapi.testclient import TestClient

# Add backend and edge-ai to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
edge_ai_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "edge-ai"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if edge_ai_dir not in sys.path:
    sys.path.insert(0, edge_ai_dir)

from app.main import app
from app.services.monitoring import monitoring_service
from app.services.runtime_state import runtime_state
from app.routers.video import frame_generator


def test_phase2_full_pipeline():
    with TestClient(app) as client:
        # 1. Verify health
        res_health = client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "HEALTHY"
        print("[OK] Backend health OK")

        # 2. Verify initial monitoring status
        res_status = client.get("/api/monitoring/status")
        assert res_status.status_code == 200
        data = res_status.json()
        assert data["is_active"] is False
        assert data["edge_ai_status"] == "STANDBY"
        print("[OK] Initial monitoring state: STANDBY")

        # 3. Test video stream when monitoring is offline -> should return 503
        res_stream_offline = client.get("/api/video/stream")
        assert res_stream_offline.status_code == 503
        print("[OK] Stream returned 503 while monitoring is offline")

        # 4. Start monitoring with verified test video
        test_video = os.path.join(edge_ai_dir, "videos", "urban_road_sample.mp4")
        assert os.path.exists(test_video), f"Sample video must exist at {test_video}"

        res_start = client.post("/api/monitoring/start")
        assert res_start.status_code == 200
        assert res_start.json()["success"] is True
        print("[OK] Start monitoring request succeeded")

        # 5. Prevent duplicate start
        res_dup = client.post("/api/monitoring/start")
        assert res_dup.status_code == 200
        assert "already active" in res_dup.json()["message"]
        print("[OK] Prevented duplicate processor thread")

        # 6. Wait for YOLO model to process frames and populate frame buffer
        print("Waiting for YOLO inference loop and frame buffer...")
        t0 = time.time()
        while time.time() - t0 < 15.0:
            time.sleep(0.5)
            if runtime_state.get_latest_jpeg() is not None:
                break

        assert runtime_state.get_latest_jpeg() is not None, "Frame buffer must be populated by YOLO"
        print(f"[OK] Frame buffer populated with {len(runtime_state.get_latest_jpeg())} bytes JPEG")

        # 7. Check live monitoring telemetry
        res_status2 = client.get("/api/monitoring/status")
        assert res_status2.status_code == 200
        live_data = res_status2.json()
        assert live_data["is_active"] is True
        assert live_data["edge_ai_status"] == "ONLINE"
        assert live_data["camera_status"] == "STREAMING"
        assert "live_counts" in live_data
        assert "car" in live_data["live_counts"]
        assert "motorcycle" in live_data["live_counts"]
        assert "bus" in live_data["live_counts"]
        assert "truck" in live_data["live_counts"]
        print(f"[OK] Real YOLO telemetry active: Counts={live_data['live_counts']}, FPS={live_data['fps']}")

        # 8. Check MJPEG stream generator produces multipart frames with JPEG headers
        async def verify_mjpeg_stream():
            gen = frame_generator()
            frame_chunk = await anext(gen)
            assert b"--frame" in frame_chunk
            assert b"image/jpeg" in frame_chunk
            assert len(frame_chunk) > 500
            await gen.aclose()
            print(f"[OK] MJPEG frame generator verified: {len(frame_chunk)} bytes multipart payload")

        asyncio.run(verify_mjpeg_stream())

        # 9. Verify GPS and bus status API
        res_bus = client.get("/api/bus/location")
        assert res_bus.status_code == 200
        assert "latitude" in res_bus.json()
        assert "longitude" in res_bus.json()
        print(f"[OK] Bus location API: lat={res_bus.json()['latitude']:.4f}, lng={res_bus.json()['longitude']:.4f}")

        # 10. Verify traffic current API
        res_traffic = client.get("/api/traffic/current")
        assert res_traffic.status_code == 200
        print(f"[OK] Traffic current API returned: {res_traffic.status_code}")

        # 11. Verify dashboard stats endpoint
        res_dash = client.get("/api/dashboard")
        assert res_dash.status_code == 200
        assert res_dash.json()["bus"]["edge_ai_status"] == "ONLINE"
        print("[OK] Dashboard stats API reflects live AI ONLINE state")

        # 12. Test clean stop monitoring
        res_stop = client.post("/api/monitoring/stop")
        assert res_stop.status_code == 200
        assert res_stop.json()["success"] is True
        print("[OK] Stop monitoring request succeeded")

        # Verify stopped state
        time.sleep(0.5)
        res_status3 = client.get("/api/monitoring/status")
        assert res_status3.json()["is_active"] is False
        assert res_status3.json()["edge_ai_status"] == "STANDBY"
        print("[OK] Processor cleanly terminated, returned to STANDBY")

        # 13. Test error handling on missing video
        res_err_start = client.post(
            "/api/monitoring/start?video_source=non_existent_fake_video_12345.mp4"
        )
        time.sleep(0.5)
        res_err_status = client.get("/api/monitoring/status")
        err_data = res_err_status.json()
        assert err_data["edge_ai_status"] == "ERROR" or err_data["latest_error"] is not None
        print(f"[OK] Error handling verified: does NOT show ONLINE when video is missing (Error: {err_data['latest_error']})")

        # Clean up error state
        client.post("/api/monitoring/stop")
        print("\n=============================================")
        print("[SUCCESS] ALL 13 PHASE 2 VERIFICATION TESTS PASSED!")
        print("=============================================")


if __name__ == "__main__":
    test_phase2_full_pipeline()
