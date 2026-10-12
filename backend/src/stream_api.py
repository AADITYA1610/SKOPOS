from fastapi import APIRouter, HTTPException

from src.stream_models import SensorReading, StreamSessionCreate
from src.stream_quality import summarize_window
from src.stream_store import stream_store


router = APIRouter(prefix="/streams", tags=["Streams"])


def session_with_quality(session_id: str):
    try:
        session = stream_store.get_session(session_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Stream session not found",
        ) from None

    session["quality_summary"] = summarize_window(session["readings"])
    return session


@router.post("/sessions", status_code=201)
def create_stream_session(settings: StreamSessionCreate):
    session = stream_store.create_session(settings)
    session["quality_summary"] = summarize_window(session["readings"])
    return session


@router.post("/sessions/{session_id}/readings", status_code=201)
def submit_reading(session_id: str, reading: SensorReading):
    try:
        return stream_store.add_reading(session_id, reading)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Stream session not found",
        ) from None


@router.get("/sessions/{session_id}")
def get_stream_session(session_id: str):
    return session_with_quality(session_id)