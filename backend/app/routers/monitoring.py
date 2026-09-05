from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import MonitoringStatusResponse, MonitoringActionResponse
from app.services.monitoring import monitoring_service
from app.config import settings

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring & Edge AI"])

@router.get("/status", response_model=MonitoringStatusResponse)
def get_monitoring_status(
    bus_code: str = Query(settings.ACTIVE_BUS_CODE),
    db: Session = Depends(get_db)
):
    """
    Query genuine backend monitoring state and Edge AI pipeline status.
    """
    status_data = monitoring_service.get_status(db=db, bus_code=bus_code)
    return status_data

@router.post("/start", response_model=MonitoringActionResponse)
def start_monitoring(
    bus_code: str = Query(settings.ACTIVE_BUS_CODE),
    video_source: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Signal backend to initiate Edge AI monitoring pipeline for BUS_01.
    Accepts optional configurable video_source path.
    Updates DB edge_ai_status and camera_status.
    """
    res = monitoring_service.start_monitoring(db=db, bus_code=bus_code, video_source=video_source)
    return res

@router.post("/stop", response_model=MonitoringActionResponse)
def stop_monitoring(
    bus_code: str = Query(settings.ACTIVE_BUS_CODE),
    db: Session = Depends(get_db)
):
    """
    Signal backend to stop monitoring pipeline and return edge AI to standby.
    """
    res = monitoring_service.stop_monitoring(db=db, bus_code=bus_code)
    return res
