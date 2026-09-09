"""
Edge AI - Backend Event Sender
HTTP client that posts detections and telemetry to the BUS-CV FastAPI backend.
Supports direct HTTP requests, test client delegation, and in-process fallback.
"""

import time
import json
import logging
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

logging.basicConfig(level=logging.INFO, format="[EventSender] %(message)s")
logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:8000"
BUS_CODE = "BUS_01"


class EventSender:
    def __init__(
        self,
        backend_url: str = BACKEND_URL,
        bus_code: str = BUS_CODE,
        client: Optional[Any] = None
    ):
        self.backend_url = backend_url.rstrip("/")
        self.bus_code = bus_code
        self.client = client  # Optional TestClient or Session

    def _post(self, path: str, payload: Dict[str, Any], retries: int = 2) -> Optional[Dict]:
        # 1. TestClient / custom client path
        if self.client:
            try:
                resp = self.client.post(path, json=payload)
                if resp.status_code in (200, 201):
                    return resp.json()
                else:
                    logger.warning(f"Client POST {path} -> HTTP {resp.status_code}")
                    return None
            except Exception as e:
                logger.warning(f"Client POST {path} failed: {e}")
                return None

        # 2. Standard requests path
        if not requests:
            logger.error("'requests' package not installed.")
            return None

        url = f"{self.backend_url}{path}"
        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=2.0)
                if resp.status_code in (200, 201):
                    return resp.json()
                else:
                    logger.warning(f"POST {path} attempt {attempt} -> HTTP {resp.status_code}: {resp.text[:120]}")
            except requests.exceptions.ConnectionError:
                # Backend server not currently running on host:port, don't sleep in loop
                logger.debug(f"Backend not reachable at {self.backend_url}{path}")
                break
            except Exception as e:
                logger.warning(f"POST {path} attempt {attempt} failed: {e}")
            time.sleep(0.3)

        # 3. Direct in-process fallback if backend is running in the same process
        return self._direct_db_fallback(path, payload)

    def _direct_db_fallback(self, path: str, payload: Dict[str, Any]) -> Optional[Dict]:
        """Fall back to direct DB session if backend is in same process and HTTP server is not bound."""
        try:
            import datetime
            from app.database import SessionLocal
            from app.models import Bus, TrafficObservation
            from app.routers.analytics import determine_traffic_level

            utc_now = datetime.datetime.now(datetime.timezone.utc)
            with SessionLocal() as db:
                bus = db.query(Bus).filter(Bus.bus_code == self.bus_code).first()
                if not bus:
                    return None

                if path == "/api/bus/location":
                    bus.latitude = payload["latitude"]
                    bus.longitude = payload["longitude"]
                    bus.speed = payload.get("speed", bus.speed)
                    bus.last_updated = utc_now
                    db.commit()
                    return {"success": True, "bus_code": self.bus_code}

                elif path == "/api/traffic":
                    total = payload.get("vehicle_count", 0)
                    t_level = payload.get("traffic_level") or determine_traffic_level(total)
                    obs = TrafficObservation(
                        vehicle_count=total,
                        car_count=payload.get("car_count", 0),
                        motorcycle_count=payload.get("motorcycle_count", 0),
                        bus_count=payload.get("bus_count", 0),
                        truck_count=payload.get("truck_count", 0),
                        traffic_level=t_level,
                        latitude=payload["latitude"],
                        longitude=payload["longitude"],
                        bus_id=bus.id,
                        source=payload.get("source", "AI_DETECTION"),
                        is_demo_data=payload.get("is_demo_data", False),
                        timestamp=utc_now
                    )
                    db.add(obs)
                    db.commit()
                    return {"id": obs.id, "traffic_level": t_level}
        except Exception:
            pass
        return None

    def send_urban_event(
        self,
        event_type: str,
        confidence: float,
        latitude: float,
        longitude: float,
        evidence_path: Optional[str] = None,
        source: str = "AI_DETECTION"
    ) -> Optional[Dict]:
        payload = {
            "event_type": event_type,
            "confidence": round(confidence, 4),
            "latitude": latitude,
            "longitude": longitude,
            "bus_code": self.bus_code,
            "source": source,
            "is_demo_data": False,
            "evidence_path": evidence_path
        }
        return self._post("/api/events", payload)

    def send_traffic_observation(
        self,
        vehicle_count: int,
        car_count: int,
        motorcycle_count: int,
        bus_count: int,
        truck_count: int,
        latitude: float,
        longitude: float,
        traffic_level: Optional[str] = None,
        source: str = "AI_DETECTION"
    ) -> Optional[Dict]:
        payload = {
            "vehicle_count": vehicle_count,
            "car_count": car_count,
            "motorcycle_count": motorcycle_count,
            "bus_count": bus_count,
            "truck_count": truck_count,
            "latitude": latitude,
            "longitude": longitude,
            "bus_code": self.bus_code,
            "source": source,
            "is_demo_data": False,
            "traffic_level": traffic_level
        }
        return self._post("/api/traffic", payload)

    def update_bus_location(self, latitude: float, longitude: float, speed: float) -> Optional[Dict]:
        payload = {
            "bus_code": self.bus_code,
            "latitude": latitude,
            "longitude": longitude,
            "speed": round(speed, 2)
        }
        return self._post("/api/bus/location", payload)
