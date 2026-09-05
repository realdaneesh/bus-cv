from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import UrbanEvent, Bus
from app.schemas import UrbanEventCreate, UrbanEventResponse
from app.services.event_processor import event_processor
from app.config import settings

router = APIRouter(prefix="/api/events", tags=["Urban Events"])

@router.post("", response_model=UrbanEventResponse, status_code=status.HTTP_201_CREATED)
def create_urban_event(
    event_in: UrbanEventCreate,
    db: Session = Depends(get_db)
):
    """
    Store a real urban detection event through the EventProcessor layer:
    - Confidence thresholding
    - Duplicate detection & cooldown check (spatial & temporal)
    - Priority calculation
    """
    bus_code = event_in.bus_code or settings.ACTIVE_BUS_CODE
    bus = db.query(Bus).filter(Bus.bus_code == bus_code).first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bus '{bus_code}' not found."
        )

    result = event_processor.process_and_store_event(db=db, event_in=event_in, bus=bus)

    if not result.success:
        if result.status == "DROPPED_LOW_CONFIDENCE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result.message
            )
        elif result.status == "DUPLICATE_SUPPRESSED":
            # Return existing event with 200 OK or 409 Conflict info
            if result.event:
                return result.event
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result.message
            )

    return result.event

@router.get("", response_model=List[UrbanEventResponse])
def list_urban_events(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: ACTIVE, RESOLVED, INVESTIGATING"),
    source_filter: Optional[str] = Query(None, alias="source", description="Filter by source: SEED, AI_DETECTION, MANUAL_TEST"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Return stored urban events ordered by most recent first.
    Allows filtering by status and data provenance.
    """
    query = db.query(UrbanEvent)

    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(UrbanEvent.status == status_filter.upper())

    if source_filter and source_filter.upper() != "ALL":
        query = query.filter(UrbanEvent.source == source_filter.upper())

    events = query.order_by(UrbanEvent.timestamp.desc()).limit(limit).all()
    return events

@router.get("/{event_id}", response_model=UrbanEventResponse)
def get_urban_event(event_id: int, db: Session = Depends(get_db)):
    """
    Return a specific urban event by ID.
    """
    event = db.query(UrbanEvent).filter(UrbanEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event #{event_id} not found."
        )
    return event

@router.patch("/{event_id}/resolve", response_model=UrbanEventResponse)
def resolve_urban_event(event_id: int, db: Session = Depends(get_db)):
    """
    Actually update the event status to RESOLVED in the database.
    """
    event = db.query(UrbanEvent).filter(UrbanEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event #{event_id} not found."
        )

    event.status = "RESOLVED"
    db.commit()
    db.refresh(event)
    return event
