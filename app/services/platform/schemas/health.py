from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class SystemInfo(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float


class HealthResponse(BaseModel):
    status: HealthStatus
    service: str
    creator: str
    version: str
    uptime_seconds: float
    timestamp: datetime
    checks: dict[str, Any]
    system: SystemInfo
