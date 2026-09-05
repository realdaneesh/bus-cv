import math
import datetime
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.models import UrbanEvent, Bus
from app.schemas import UrbanEventCreate
from app.config import settings

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the earth in meters.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


class EventProcessResult:
    def __init__(self, success: bool, status: str, message: str, event: Optional[UrbanEvent] = None):
        self.success = success
        self.status = status  # "CREATED", "DROPPED_LOW_CONFIDENCE", "DUPLICATE_SUPPRESSED"
        self.message = message
        self.event = event


class EventProcessor:
    def __init__(self, confidence_threshold: Optional[float] = None, cooldown_seconds: Optional[int] = None, proximity_meters: Optional[float] = None):
        self.confidence_threshold = confidence_threshold or settings.DETECTION_CONFIDENCE_THRESHOLD
        self.cooldown_seconds = cooldown_seconds or settings.EVENT_COOLDOWN_SECONDS
        self.proximity_meters = proximity_meters or settings.DUPLICATE_PROXIMITY_METERS

    def calculate_priority(self, event_type: str, confidence: float) -> str:
        """
        Calculates priority based on confidence and event severity.
        - High hazard types at high confidence get CRITICAL/HIGH.
        - Standard rules:
            >= 0.90 -> HIGH (or CRITICAL for severe road hazards)
            >= 0.75 -> MEDIUM
            otherwise -> LOW
        """
        event_type_upper = event_type.upper()

        if confidence >= 0.90:
            if event_type_upper in ["POTHOLE", "ROAD_DAMAGE", "WATERLOGGING"]:
                return "HIGH"
            return "HIGH"
        elif confidence >= 0.75:
            return "MEDIUM"
        else:
            return "LOW"

    def check_duplicate_or_cooldown(self, db: Session, event_type: str, latitude: float, longitude: float, bus_id: int) -> Tuple[bool, Optional[UrbanEvent]]:
        """
        Check if an event of the same type was already detected within proximity_meters
        in the last cooldown_seconds.
        """
        cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=self.cooldown_seconds)

        # Query recent events of the same type for this bus or all buses
        recent_events = db.query(UrbanEvent).filter(
            UrbanEvent.event_type == event_type.upper(),
            UrbanEvent.status == "ACTIVE",
            UrbanEvent.timestamp >= cutoff_time
        ).all()

        for ev in recent_events:
            distance = haversine_distance(latitude, longitude, ev.latitude, ev.longitude)
            if distance <= self.proximity_meters:
                return True, ev

        return False, None

    def process_and_store_event(self, db: Session, event_in: UrbanEventCreate, bus: Bus) -> EventProcessResult:
        """
        Core intelligence pipeline:
        1. Confidence check
        2. Duplicate / Cooldown check (spatial + temporal)
        3. Priority computation
        4. DB persistence
        """
        event_type_normalized = event_in.event_type.strip().upper()

        # 1. Confidence validation
        if event_in.confidence < self.confidence_threshold:
            return EventProcessResult(
                success=False,
                status="DROPPED_LOW_CONFIDENCE",
                message=f"Confidence {event_in.confidence:.2f} is below required threshold {self.confidence_threshold:.2f}"
            )

        # 2. Duplicate / Cooldown validation
        is_duplicate, existing_event = self.check_duplicate_or_cooldown(
            db=db,
            event_type=event_type_normalized,
            latitude=event_in.latitude,
            longitude=event_in.longitude,
            bus_id=bus.id
        )

        if is_duplicate and existing_event:
            return EventProcessResult(
                success=False,
                status="DUPLICATE_SUPPRESSED",
                message=f"Duplicate detection suppressed. Matches active event #{existing_event.id} within cooldown window ({self.cooldown_seconds}s).",
                event=existing_event
            )

        # 3. Calculate priority
        calculated_priority = self.calculate_priority(event_type_normalized, event_in.confidence)

        # 4. Create and persist event
        new_event = UrbanEvent(
            event_type=event_type_normalized,
            confidence=round(event_in.confidence, 4),
            latitude=event_in.latitude,
            longitude=event_in.longitude,
            timestamp=event_in.timestamp or datetime.datetime.now(datetime.timezone.utc),
            status="ACTIVE",
            priority=calculated_priority,
            bus_id=bus.id,
            evidence_path=event_in.evidence_path,
            source=event_in.source or "AI_DETECTION",
            is_demo_data=event_in.is_demo_data if event_in.is_demo_data is not None else False
        )


        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        return EventProcessResult(
            success=True,
            status="CREATED",
            message=f"Urban event #{new_event.id} created successfully with priority {calculated_priority}.",
            event=new_event
        )

# Global default processor instance
event_processor = EventProcessor()
