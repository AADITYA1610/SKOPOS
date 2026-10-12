from collections import deque
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from src.stream_models import SensorReading, StreamSessionCreate


class StreamStore:
    def __init__(self):
        self._sessions = {}
        self._lock = Lock()

    def create_session(self, settings: StreamSessionCreate):
        session_id = str(uuid4())

        session = {
            "session_id": session_id,
            "name": settings.name,
            "source_type": settings.source_type,
            "window_size": settings.window_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_received": 0,
            "readings": deque(maxlen=settings.window_size),
        }

        with self._lock:
            self._sessions[session_id] = session
            return self._snapshot(session)

    def add_reading(self, session_id: str, reading: SensorReading):
        with self._lock:
            session = self._get_session(session_id)

            record = reading.model_dump(mode="json")
            record["received_at"] = datetime.now(timezone.utc).isoformat()

            session["readings"].append(record)
            session["total_received"] += 1

            return {
                "session_id": session_id,
                "total_received": session["total_received"],
                "window_count": len(session["readings"]),
                "reading": record.copy(),
            }

    def get_session(self, session_id: str):
        with self._lock:
            session = self._get_session(session_id)
            return self._snapshot(session)

    def _get_session(self, session_id: str):
        if session_id not in self._sessions:
            raise KeyError("Stream session not found")

        return self._sessions[session_id]

    def _snapshot(self, session):
        return {
            "session_id": session["session_id"],
            "name": session["name"],
            "source_type": session["source_type"],
            "window_size": session["window_size"],
            "created_at": session["created_at"],
            "total_received": session["total_received"],
            "window_count": len(session["readings"]),
            "readings": [
                record.copy() for record in session["readings"]
            ],
        }


stream_store = StreamStore()