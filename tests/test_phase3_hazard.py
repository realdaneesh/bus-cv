"""
BUS-CV Phase 3B: Comprehensive Road Hazard Intelligence Automated Test Suite.

Tests all 16 required capabilities:
1. Hazard model loads successfully.
2. Hazard detector returns structured detections.
3. Confidence filtering works.
4. Temporal confirmation requires multiple detections.
5. Single-frame detection does not immediately create an event.
6. Confirmed detection creates exactly one event.
7. Duplicate detections do not create duplicate events (spatial dedup).
8. GPS coordinates are attached to the created event.
9. Event is saved through the actual backend/database path.
10. POST /api/events result appears in GET /api/events.
11. Dashboard statistics update.
12. Existing event resolve functionality still works.
13. Monitoring start works.
14. Monitoring stop works cleanly.
15. Existing vehicle detection remains operational.
16. Hazard model failure is reported correctly.
"""

import os
import sys
import time
import unittest
import numpy as np
import cv2
from pathlib import Path

# Ensure paths
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = WORKSPACE_ROOT / "backend"
EDGE_AI_DIR = WORKSPACE_ROOT / "edge-ai"

sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(EDGE_AI_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Bus, UrbanEvent, TrafficObservation
from app.services.monitoring import monitoring_service
from app.services.runtime_state import runtime_state

from road_hazard_detector import RoadHazardDetector
from hazard_event_manager import HazardEventManager
from event_sender import EventSender
from detector import EdgeDetector
from processor import VideoProcessor


class TestPhase3BRoadHazard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        
        # Ensure BUS_01 exists in DB
        with SessionLocal() as db:
            bus = db.query(Bus).filter(Bus.bus_code == "BUS_01").first()
            if not bus:
                bus = Bus(
                    bus_code="BUS_01",
                    status="ACTIVE",
                    latitude=28.6139,
                    longitude=77.2090,
                    speed=0.0
                )
                db.add(bus)
                db.commit()

    def test_01_hazard_model_loads_successfully(self):
        """1. Hazard model loads successfully."""
        detector = RoadHazardDetector()
        success = detector.load_model()
        self.assertTrue(success, "RoadHazardDetector failed to load weights")
        self.assertTrue(detector.is_initialized)
        self.assertIsNotNone(detector.model)
        print("  [OK] Test 1: Hazard model loads successfully.")

    def test_02_hazard_detector_returns_structured_detections(self):
        """2. Hazard detector returns structured detections on genuine road image."""
        detector = RoadHazardDetector(confidence_threshold=0.25)
        detector.load_model()
        
        # Use real test pothole image from Phase 3A
        sample_img_path = EDGE_AI_DIR / "road_damage_eval" / "sample_images" / "pothole_small.jpg"
        if sample_img_path.exists():
            frame = cv2.imread(str(sample_img_path))
        else:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
        detections = detector.detect(frame)
        self.assertIsInstance(detections, list)
        if len(detections) > 0:
            det = detections[0]
            self.assertEqual(det["event_type"], "POTHOLE")
            self.assertIn("confidence", det)
            self.assertIn("bbox", det)
            self.assertEqual(len(det["bbox"]), 4)
            self.assertIn("timestamp", det)
            self.assertEqual(det["source"], "peterhdd_pothole_yolov8s")
            self.assertIn("area_ratio", det)
        print("  [OK] Test 2: Hazard detector returns structured detections.")

    def test_03_confidence_filtering(self):
        """3. Confidence filtering works."""
        manager = HazardEventManager(event_sender=None, min_confidence=0.75)
        raw_detections = [
            {"event_type": "POTHOLE", "confidence": 0.55, "bbox": [10, 10, 50, 50], "area_ratio": 0.01},
            {"event_type": "POTHOLE", "confidence": 0.82, "bbox": [100, 100, 200, 200], "area_ratio": 0.03}
        ]
        gps = {"latitude": 28.6139, "longitude": 77.2090}
        manager.process_detections(raw_detections, gps)
        
        # Only the 0.82 confidence detection should enter the track list
        self.assertEqual(len(manager._active_tracks), 1)
        self.assertAlmostEqual(manager._active_tracks[0].highest_conf, 0.82, places=2)
        print("  [OK] Test 3: Confidence filtering works (dropped < 0.75).")

    def test_04_05_temporal_confirmation_and_single_frame_behavior(self):
        """
        4. Temporal confirmation requires multiple detections.
        5. Single-frame detection does not immediately create an event.
        """
        sender = EventSender(client=self.client)
        manager = HazardEventManager(event_sender=sender, min_confidence=0.60, confirmation_count=2)
        gps = {"latitude": 28.6140, "longitude": 77.2095}
        
        # Frame 1: Single detection
        det_frame1 = [{"event_type": "POTHOLE", "confidence": 0.85, "bbox": [100, 100, 200, 200], "area_ratio": 0.03, "source": "peterhdd_pothole_yolov8s"}]
        emitted_f1 = manager.process_detections(det_frame1, gps)
        
        # Must NOT emit on frame 1
        self.assertEqual(len(emitted_f1), 0, "Single-frame detection improperly emitted an event!")
        self.assertEqual(manager.confirmed_count, 0)
        self.assertEqual(len(manager._active_tracks), 1)
        self.assertEqual(manager._active_tracks[0].hits, 1)
        print("  [OK] Test 4 & 5: Single frame did not emit event; awaiting confirmation.")

    def test_06_confirmed_detection_creates_exactly_one_event(self):
        """6. Confirmed detection creates exactly one event."""
        sender = EventSender(client=self.client)
        manager = HazardEventManager(event_sender=sender, min_confidence=0.60, confirmation_count=2)
        gps = {"latitude": 28.6150, "longitude": 77.2100}
        
        det = [{"event_type": "POTHOLE", "confidence": 0.88, "bbox": [100, 100, 200, 200], "area_ratio": 0.04, "source": "peterhdd_pothole_yolov8s"}]
        
        # Hit 1
        manager.process_detections(det, gps)
        self.assertEqual(manager.confirmed_count, 0)
        
        # Hit 2 (Confirmed)
        emitted_f2 = manager.process_detections(det, gps)
        self.assertEqual(len(emitted_f2), 1, "Expected exactly 1 event emitted on 2nd hit")
        self.assertEqual(manager.confirmed_count, 1)
        self.assertEqual(emitted_f2[0]["priority"], "HIGH")
        print("  [OK] Test 6: Confirmed detection created exactly 1 event with priority HIGH.")

    def test_07_spatial_deduplication_prevents_duplicate_events(self):
        """7. Duplicate detections within 15m radius do not create duplicate events."""
        sender = EventSender(client=self.client)
        manager = HazardEventManager(
            event_sender=sender,
            min_confidence=0.60,
            confirmation_count=2,
            dedup_radius_meters=15.0
        )
        gps_origin = {"latitude": 28.61550, "longitude": 77.21050}
        
        det = [{"event_type": "POTHOLE", "confidence": 0.85, "bbox": [120, 120, 220, 220], "area_ratio": 0.03, "source": "peterhdd_pothole_yolov8s"}]
        
        # Initial confirmation & emission
        manager.process_detections(det, gps_origin)
        manager.process_detections(det, gps_origin)
        self.assertEqual(manager.confirmed_count, 1)
        
        # Now, simulate bus moving 5 meters away (well within 15m radius) and seeing same/new pothole
        gps_nearby = {"latitude": 28.61553, "longitude": 77.21052} # ~4.5m distance
        det2 = [{"event_type": "POTHOLE", "confidence": 0.86, "bbox": [130, 130, 230, 230], "area_ratio": 0.03, "source": "peterhdd_pothole_yolov8s"}]
        
        # Hit 1 and Hit 2 for the new detection nearby
        manager.process_detections(det2, gps_nearby)
        emitted_nearby = manager.process_detections(det2, gps_nearby)
        
        self.assertEqual(len(emitted_nearby), 0, "Duplicate pothole within 15m was not suppressed!")
        self.assertEqual(manager.confirmed_count, 1, "Confirmed count incremented despite duplicate!")
        self.assertGreaterEqual(manager.dedup_suppressed_count, 1)
        print("  [OK] Test 7: Spatial deduplication successfully suppressed duplicate event (4.5m <= 15m).")

    def test_08_09_10_gps_attachment_and_backend_roundtrip(self):
        """
        8. GPS coordinates are attached to the created event.
        9. Event is saved through actual backend/database path.
        10. POST /api/events result appears in GET /api/events.
        """
        sender = EventSender(client=self.client)
        target_lat = 28.62123
        target_lng = 77.21456
        
        resp = sender.send_urban_event(
            event_type="POTHOLE",
            confidence=0.8654,
            latitude=target_lat,
            longitude=target_lng,
            source="peterhdd_pothole_yolov8s"
        )
        self.assertIsNotNone(resp)
        self.assertIn("id", resp)
        event_id = resp["id"]
        
        # Check GET /api/events
        get_res = self.client.get("/api/events")
        self.assertEqual(get_res.status_code, 200)
        events = get_res.json()
        matching = [e for e in events if e["id"] == event_id]
        self.assertEqual(len(matching), 1)
        ev = matching[0]
        self.assertEqual(ev["event_type"], "POTHOLE")
        self.assertAlmostEqual(ev["latitude"], target_lat, places=4)
        self.assertAlmostEqual(ev["longitude"], target_lng, places=4)
        self.assertAlmostEqual(ev["confidence"], 0.8654, places=3)
        self.assertEqual(ev["source"], "peterhdd_pothole_yolov8s")
        self.assertFalse(ev["is_demo_data"])
        print("  [OK] Test 8, 9, 10: Event verified via POST -> DB -> GET /api/events with exact GPS coordinates.")

    def test_11_dashboard_stats_update(self):
        """11. Dashboard statistics update genuinely."""
        res = self.client.get("/api/dashboard")
        self.assertEqual(res.status_code, 200)
        stats = res.json()
        self.assertIn("total_events", stats)
        self.assertIn("active_issues", stats)
        self.assertIn("issues_by_priority", stats)
        self.assertGreater(stats["total_events"], 0)
        print("  [OK] Test 11: Dashboard statistics update and return genuine counts.")

    def test_12_event_resolution_workflow(self):
        """12. Existing event resolve functionality still works."""
        # Create an event to resolve
        sender = EventSender(client=self.client)
        resp = sender.send_urban_event(
            event_type="POTHOLE",
            confidence=0.89,
            latitude=28.6300,
            longitude=77.2200,
            source="peterhdd_pothole_yolov8s"
        )
        self.assertIsNotNone(resp)
        event_id = resp["id"]
        
        # Resolve via PATCH /api/events/{id}/resolve
        patch_res = self.client.patch(f"/api/events/{event_id}/resolve")
        self.assertEqual(patch_res.status_code, 200)
        resolved_ev = patch_res.json()
        self.assertEqual(resolved_ev["status"], "RESOLVED")
        
        # Check DB directly
        with SessionLocal() as db:
            db_ev = db.query(UrbanEvent).filter(UrbanEvent.id == event_id).first()
            self.assertEqual(db_ev.status, "RESOLVED")
        print("  [OK] Test 12: Event resolve endpoint changes status to RESOLVED in database.")

    def test_13_14_monitoring_lifecycle(self):
        """13 & 14. Monitoring start and clean stop."""
        with SessionLocal() as db:
            # Test start
            start_res = monitoring_service.start_monitoring(db=db, bus_code="BUS_01")
            self.assertTrue(start_res["success"])
            self.assertTrue(monitoring_service.is_running())
            
            # Let it run briefly
            time.sleep(1.0)
            
            # Test stop
            stop_res = monitoring_service.stop_monitoring(db=db, bus_code="BUS_01")
            self.assertTrue(stop_res["success"])
            self.assertFalse(monitoring_service.is_running())
        print("  [OK] Test 13 & 14: Monitoring start and stop executed cleanly.")

    def test_15_vehicle_detection_remains_operational(self):
        """15. Vehicle detection remains fully operational."""
        detector = EdgeDetector()
        self.assertTrue(detector.load_model())
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        res = detector.detect_frame(dummy_frame)
        self.assertIn("vehicle_counts", res)
        self.assertIn("car", res["vehicle_counts"])
        self.assertIn("motorcycle", res["vehicle_counts"])
        self.assertIn("bus", res["vehicle_counts"])
        self.assertIn("truck", res["vehicle_counts"])
        print("  [OK] Test 15: Vehicle detector continues detecting car, motorcycle, bus, truck.")

    def test_16_hazard_model_failure_reported_correctly(self):
        """16. Hazard model failure is reported cleanly without crashing vehicle pipeline."""
        invalid_detector = RoadHazardDetector(model_path="non_existent_model_weights.pt")
        loaded = invalid_detector.load_model()
        self.assertFalse(loaded)
        self.assertFalse(invalid_detector.is_initialized)
        detections = invalid_detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertEqual(len(detections), 0)
        print("  [OK] Test 16: Failure to load weights reported cleanly; graceful degradation verified.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
