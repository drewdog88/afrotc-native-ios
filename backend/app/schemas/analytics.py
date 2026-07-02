"""Analytics and dashboard schemas for recruitment metrics."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FunnelStageCount(BaseModel):
    """Count of recruits at a specific stage."""

    stage: str
    count: int


class FunnelResponse(BaseModel):
    """Current funnel snapshot showing recruits per stage."""

    stages: list[FunnelStageCount]
    total: int
    from_date: datetime | None = None
    to_date: datetime | None = None


class TrendPoint(BaseModel):
    """A single point in a time series."""

    period: str  # e.g., "2025-W01" for week or "2025-01" for month
    count: int


class TrendSeries(BaseModel):
    """Time series for a single stage or metric."""

    stage: str
    points: list[TrendPoint]


class TrendsResponse(BaseModel):
    """Time-series data for stage transitions over time."""

    series: list[TrendSeries]
    interval: str  # "week" or "month"
    from_date: datetime | None = None
    to_date: datetime | None = None


class DashboardStats(BaseModel):
    """Summary statistics for the dashboard overview."""

    total_recruits: int
    recruits_by_stage: list[FunnelStageCount]
    total_cadets: int
    cadets_by_status: list[dict[str, int | str]]  # [{"status": "active", "count": 10}, ...]
    open_followups: int
    recent_trend: list[TrendPoint]  # Last ~8 weeks of recruit creation
