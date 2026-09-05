import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class Bus(Base):
    __tablename__ = "buses"

    id = Column(Integer, primary_key=True, index=True)
    bus_code = Column(String(50), unique=True, index=True, nullable=False)
    status = Column(String(50), default="ACTIVE")  # ACTIVE, INACTIVE, IDLE, MAINTENANCE
    latitude = Column(Float, nullable=False, default=19.1197)  # Mumbai - Powai
    longitude = Column(Float, nullable=False, default=72.9050) # Mumbai - Powai
    speed = Column(Float, default=0.0)  # km/h
    edge_ai_status = Column(String(50), default="STANDBY")  # ONLINE, OFFLINE, STANDBY
    camera_status = Column(String(50), default="DISCONNECTED")  # CONNECTED, DISCONNECTED, STREAMING
    gps_status = Column(String(50), default="SIMULATED_MUMBAI_ROUTE")
    last_updated = Column(DateTime, default=utc_now, onupdate=utc_now)

    events = relationship("UrbanEvent", back_populates="bus", cascade="all, delete-orphan")
    traffic_observations = relationship("TrafficObservation", back_populates="bus", cascade="all, delete-orphan")


class UrbanEvent(Base):
    __tablename__ = "urban_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), index=True, nullable=False)  # POTHOLE, GARBAGE, WATERLOGGING, ROAD_DAMAGE, etc.
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    status = Column(String(50), default="ACTIVE", index=True)  # ACTIVE, RESOLVED, INVESTIGATING
    priority = Column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    evidence_path = Column(String(255), nullable=True)
    source = Column(String(50), default="AI_DETECTION")  # SEED, AI_DETECTION, MANUAL_TEST
    is_demo_data = Column(Boolean, default=False, nullable=False)

    bus = relationship("Bus", back_populates="events")


class TrafficObservation(Base):
    __tablename__ = "traffic_observations"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_count = Column(Integer, default=0)
    car_count = Column(Integer, default=0)
    motorcycle_count = Column(Integer, default=0)
    bus_count = Column(Integer, default=0)
    truck_count = Column(Integer, default=0)
    traffic_level = Column(String(50), default="LOW")  # LOW, MODERATE, HEAVY, CONGESTED
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    source = Column(String(50), default="AI_DETECTION")  # SEED, AI_DETECTION, MANUAL_TEST
    is_demo_data = Column(Boolean, default=False, nullable=False)

    bus = relationship("Bus", back_populates="traffic_observations")

