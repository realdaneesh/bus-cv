"""
Initial database seed for BUS-CV prototype.
Initializes BUS_01 in Mumbai (Powai corridor) and seeds baseline demo records.
All seed records explicitly have source="SEED" and is_demo_data=True.
"""

import datetime
from sqlalchemy.orm import Session
from app.models import Bus, UrbanEvent, TrafficObservation
from app.config import settings


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def seed_database(db: Session):
    """
    Seed initial BUS_01 and baseline test events/traffic data in Mumbai.
    All test events explicitly have source="SEED" and is_demo_data=True.
    """
    # 1. Seed or verify BUS_01
    bus = db.query(Bus).filter(Bus.bus_code == settings.ACTIVE_BUS_CODE).first()
    if not bus:
        bus = Bus(
            bus_code=settings.ACTIVE_BUS_CODE,
            status="ACTIVE",
            latitude=19.1197,  # Mumbai - Powai Lake / Hiranandani
            longitude=72.9050,
            speed=22.5,
            edge_ai_status="STANDBY",
            camera_status="DISCONNECTED",
            gps_status="SIMULATED_MUMBAI_ROUTE",
            last_updated=utc_now()
        )
        db.add(bus)
        db.commit()
        db.refresh(bus)
    else:
        # If existing bus was in Delhi, update to Mumbai
        if bus.latitude > 25.0:
            bus.latitude = 19.1197
            bus.longitude = 72.9050
            bus.gps_status = "SIMULATED_MUMBAI_ROUTE"
            bus.last_updated = utc_now()
            db.commit()

    # 2. Seed baseline events if no events exist yet
    event_count = db.query(UrbanEvent).count()
    if event_count == 0:
        base_time = utc_now() - datetime.timedelta(hours=2)
        demo_events = [
            UrbanEvent(
                event_type="POTHOLE",
                confidence=0.92,
                latitude=19.1224,
                longitude=72.9112,
                timestamp=base_time + datetime.timedelta(minutes=15),
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
                timestamp=base_time + datetime.timedelta(minutes=30),
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
                timestamp=base_time + datetime.timedelta(minutes=45),
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
                timestamp=base_time + datetime.timedelta(minutes=60),
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
                timestamp=base_time + datetime.timedelta(minutes=75),
                status="ACTIVE",
                priority="MEDIUM",
                bus_id=bus.id,
                evidence_path=None,
                source="SEED",
                is_demo_data=True
            )
        ]
        db.add_all(demo_events)
        db.commit()

    # 3. Seed baseline traffic observation if none exist
    traffic_count = db.query(TrafficObservation).count()
    if traffic_count == 0:
        demo_traffic = TrafficObservation(
            vehicle_count=18,
            car_count=10,
            motorcycle_count=5,
            bus_count=2,
            truck_count=1,
            traffic_level="MODERATE",
            latitude=19.1197,
            longitude=72.9050,
            timestamp=utc_now() - datetime.timedelta(minutes=10),
            bus_id=bus.id,
            source="SEED",
            is_demo_data=True
        )
        db.add(demo_traffic)
        db.commit()
