"""
BUS-CV - SIH Demo Database Reset Utility
Removes obsolete demo and test records, resets BUS_01 state to the Mumbai starting coordinates,
and initializes a clean demonstration environment.

Usage:
    python backend/scripts/reset_demo_data.py
"""

import os
import sys
import datetime

# Add backend directory to sys.path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_script_dir, ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.database import SessionLocal, engine, Base
from app.models import Bus, UrbanEvent, TrafficObservation
from app.config import settings


def reset_demo_database():
    print("=" * 60)
    print("BUS-CV: Resetting Database for Mumbai SIH Demonstration")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. Remove all old Urban Events
        num_events = db.query(UrbanEvent).delete()
        print(f"[-] Cleared {num_events} old urban event records.")

        # 2. Remove all old Traffic Observations
        num_traffic = db.query(TrafficObservation).delete()
        print(f"[-] Cleared {num_traffic} old traffic observation records.")

        # 3. Reset or Initialize BUS_01
        bus = db.query(Bus).filter(Bus.bus_code == settings.ACTIVE_BUS_CODE).first()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        if bus:
            bus.latitude = 19.1197  # Powai Lake / Hiranandani
            bus.longitude = 72.9050
            bus.speed = 0.0
            bus.status = "ACTIVE"
            bus.edge_ai_status = "STANDBY"
            bus.camera_status = "DISCONNECTED"
            bus.gps_status = "SIMULATED_MUMBAI_ROUTE"
            bus.last_updated = now_utc
            print(f"[OK] Reset BUS_01 state to Mumbai: (19.1197, 72.9050)")
        else:
            bus = Bus(
                bus_code=settings.ACTIVE_BUS_CODE,
                status="ACTIVE",
                latitude=19.1197,
                longitude=72.9050,
                speed=0.0,
                edge_ai_status="STANDBY",
                camera_status="DISCONNECTED",
                gps_status="SIMULATED_MUMBAI_ROUTE",
                last_updated=now_utc
            )
            db.add(bus)
            db.commit()
            db.refresh(bus)
            print(f"[OK] Created BUS_01 in Mumbai: (19.1197, 72.9050)")

        # 4. Seed Clean Mumbai Baseline Demo Events
        base_time = now_utc - datetime.timedelta(hours=1)
        demo_events = [
            UrbanEvent(
                event_type="POTHOLE",
                confidence=0.92,
                latitude=19.1224,
                longitude=72.9112,
                timestamp=base_time + datetime.timedelta(minutes=10),
                status="ACTIVE",
                priority="HIGH",
                bus_id=bus.id,
                evidence_path=None,
                source="SEED",
                is_demo_data=True
            ),
            UrbanEvent(
                event_type="ROAD_DAMAGE",
                confidence=0.84,
                latitude=19.1254,
                longitude=72.9158,
                timestamp=base_time + datetime.timedelta(minutes=20),
                status="ACTIVE",
                priority="MEDIUM",
                bus_id=bus.id,
                evidence_path=None,
                source="SEED",
                is_demo_data=True
            ),
            UrbanEvent(
                event_type="WATERLOGGING",
                confidence=0.95,
                latitude=19.1150,
                longitude=72.8920,
                timestamp=base_time + datetime.timedelta(minutes=35),
                status="ACTIVE",
                priority="HIGH",
                bus_id=bus.id,
                evidence_path=None,
                source="SEED",
                is_demo_data=True
            ),
            UrbanEvent(
                event_type="GARBAGE",
                confidence=0.78,
                latitude=19.1085,
                longitude=72.8830,
                timestamp=base_time + datetime.timedelta(minutes=45),
                status="RESOLVED",
                priority="MEDIUM",
                bus_id=bus.id,
                evidence_path=None,
                source="SEED",
                is_demo_data=True
            ),
            UrbanEvent(
                event_type="POTHOLE",
                confidence=0.88,
                latitude=19.1025,
                longitude=72.8740,
                timestamp=base_time + datetime.timedelta(minutes=55),
                status="ACTIVE",
                priority="MEDIUM",
                bus_id=bus.id,
                evidence_path=None,
                source="SEED",
                is_demo_data=True
            )
        ]
        db.add_all(demo_events)

        # 5. Seed Clean Mumbai Baseline Traffic Observation
        demo_traffic = TrafficObservation(
            vehicle_count=18,
            car_count=10,
            motorcycle_count=5,
            bus_count=2,
            truck_count=1,
            traffic_level="MODERATE",
            latitude=19.1197,
            longitude=72.9050,
            timestamp=now_utc - datetime.timedelta(minutes=5),
            bus_id=bus.id,
            source="SEED",
            is_demo_data=True
        )
        db.add(demo_traffic)
        db.commit()

        print(f"[OK] Seeded {len(demo_events)} Mumbai baseline events (is_demo_data=True).")
        print(f"[OK] Seeded 1 Mumbai baseline traffic observation (is_demo_data=True).")
        print("=" * 60)
        print("DATABASE RESET COMPLETE: Clean Mumbai Demo State Ready.")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"[!] Error resetting database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_demo_database()
