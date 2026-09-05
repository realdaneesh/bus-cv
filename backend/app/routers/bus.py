import datetime
import os
import sys

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Bus
from app.schemas import BusResponse, BusLocationUpdate, BusLocationResponse
from app.config import settings

# Make edge-ai importable so the planned Mumbai route can be shared with the map.
_edge_ai = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "edge-ai"))
if _edge_ai not in sys.path:
    sys.path.insert(0, _edge_ai)

router = APIRouter(prefix="/api/bus", tags=["Bus"])

@router.get("/status", response_model=BusResponse)
def get_bus_status(bus_code: str = settings.ACTIVE_BUS_CODE, db: Session = Depends(get_db)):
    """
    Return BUS_01's real stored status.
    """
    bus = db.query(Bus).filter(Bus.bus_code == bus_code).first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bus with code '{bus_code}' not found in database."
        )
    return bus

@router.get("/location", response_model=BusLocationResponse)
def get_bus_location(bus_code: str = settings.ACTIVE_BUS_CODE, db: Session = Depends(get_db)):
    """
    Return the latest stored location for BUS_01.
    """
    bus = db.query(Bus).filter(Bus.bus_code == bus_code).first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bus with code '{bus_code}' not found in database."
        )
    return bus

@router.post("/location", response_model=BusLocationResponse)
def update_bus_location(loc: BusLocationUpdate, db: Session = Depends(get_db)):
    """
    Update the real bus location and speed in the database.
    """
    bus = db.query(Bus).filter(Bus.bus_code == loc.bus_code).first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bus with code '{loc.bus_code}' not found in database."
        )

    bus.latitude = loc.latitude
    bus.longitude = loc.longitude
    bus.speed = loc.speed
    bus.last_updated = datetime.datetime.now(datetime.timezone.utc)
    bus.gps_status = "LOCKED"

    db.commit()
    db.refresh(bus)
    return bus


@router.get("/route")
def get_bus_route():
    """
    Return the PLANNED, road-following Mumbai route as a polyline for the Urban Map.
    This route is SIMULATED GPS telemetry (not physical GPS hardware) and is
    labelled as such for transparency.
    """
    try:
        from gps_simulator import GPSSimulator
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load route simulator: {exc}"
        ) from exc

    route_pts = GPSSimulator().get_planned_route()
    return {
        "route": route_pts,
        "label": "SIMULATED MUMBAI ROAD ROUTE",
        "gps_mode": "SIMULATED_MUMBAI_ROAD_ROUTE",
        "is_simulated_gps": True,
        "point_count": len(route_pts),
    }
