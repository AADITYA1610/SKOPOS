from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StreamSessionCreate(BaseModel):
    """Settings supplied when creating a stream session."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    source_type: Literal["simulated", "sensor", "api"] = "simulated"
    window_size: int = Field(default=100, ge=10, le=1000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Session name cannot be blank")
        return value


class SensorReading(BaseModel):
    """One environmental reading submitted to a session."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=100)
    timestamp: datetime
    sensor_id: str = Field(min_length=1, max_length=100)

    temperature: float | None = Field(default=None, allow_inf_nan=False)
    humidity: float | None = Field(default=None, allow_inf_nan=False)

    @field_validator("event_id", "sensor_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Identifier cannot be blank")
        return value

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone")
        return value