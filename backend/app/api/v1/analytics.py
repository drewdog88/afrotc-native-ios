"""Analytics and dashboard endpoints for recruitment metrics.

This is the mandatory "recruitment change over time" reporting system. It reads
from PotentialRecruit (current stage snapshot) and RecruitStageEvent (immutable
append-only log) to deliver funnel, trend, and dashboard stats.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Cadet, FollowUp, PotentialRecruit, RecruitStageEvent, User
from app.models.enums import FUNNEL_ORDER, RecruitStage
from app.models.followup import FollowUpStatus
from app.schemas.analytics import (
    DashboardStats,
    FunnelResponse,
    FunnelStageCount,
    TrendPoint,
    TrendSeries,
    TrendsResponse,
)

router = APIRouter(tags=["analytics"])


def _bucket_by_week(dt: datetime) -> str:
    """Return ISO week format: YYYY-Wnn."""
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def _bucket_by_month(dt: datetime) -> str:
    """Return year-month format: YYYY-MM."""
    return dt.strftime("%Y-%m")


@router.get("/analytics/funnel", response_model=FunnelResponse)
def get_funnel(
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FunnelResponse:
    """Current count of recruits per stage (respects FUNNEL_ORDER).

    The from/to date window filters recruits by created_at. Returns counts for
    EVERY stage in FUNNEL_ORDER, with 0 if none are at that stage.
    """
    stmt = select(
        PotentialRecruit.stage,
        func.count(PotentialRecruit.id).label("count"),
    ).group_by(PotentialRecruit.stage)

    if from_date:
        stmt = stmt.where(PotentialRecruit.created_at >= from_date)
    if to_date:
        stmt = stmt.where(PotentialRecruit.created_at <= to_date)

    rows = db.execute(stmt).all()
    counts_map = {row.stage: row.count for row in rows}

    # Ensure all FUNNEL_ORDER stages are present (0 if missing).
    stages = [
        FunnelStageCount(stage=stage.value, count=counts_map.get(stage.value, 0))
        for stage in FUNNEL_ORDER
    ]
    # Add DECLINED as well if it has any count.
    declined_count = counts_map.get(RecruitStage.DECLINED.value, 0)
    if declined_count > 0:
        stages.append(FunnelStageCount(stage=RecruitStage.DECLINED.value, count=declined_count))

    total = sum(s.count for s in stages)

    return FunnelResponse(
        stages=stages,
        total=total,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/analytics/trends", response_model=TrendsResponse)
def get_trends(
    metric: str | None = Query(None, description="Stage to track or 'all'"),
    interval: str = Query("week", pattern="^(week|month)$"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrendsResponse:
    """Time-series built from RecruitStageEvent log.

    For each period bucket, the number of transitions INTO each stage. Buckets
    changed_at by week or month. If metric is specified, filters to that stage;
    otherwise returns all stages.
    """
    stmt = select(RecruitStageEvent).order_by(RecruitStageEvent.changed_at)

    if from_date:
        stmt = stmt.where(RecruitStageEvent.changed_at >= from_date)
    if to_date:
        stmt = stmt.where(RecruitStageEvent.changed_at <= to_date)

    events = db.scalars(stmt).all()

    # Bucket events by period and stage.
    bucket_fn = _bucket_by_week if interval == "week" else _bucket_by_month
    # stage -> {period -> count}
    stage_buckets: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for event in events:
        period = bucket_fn(event.changed_at)
        stage = event.to_stage
        stage_buckets[stage][period] += 1

    # If metric is specified and is not "all", filter to that stage.
    if metric and metric != "all":
        stage_buckets = {metric: stage_buckets.get(metric, {})}

    # Convert to series.
    series = []
    for stage, buckets in sorted(stage_buckets.items()):
        points = [TrendPoint(period=p, count=c) for p, c in sorted(buckets.items())]
        series.append(TrendSeries(stage=stage, points=points))

    return TrendsResponse(
        series=series,
        interval=interval,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStats:
    """Summary stat cards for dashboard: total recruits, stage counts, cadets,
    open follow-ups, and a short recruits-created trend (last ~8 weeks).
    """
    # Total recruits and counts per stage.
    recruit_rows = db.execute(
        select(
            PotentialRecruit.stage,
            func.count(PotentialRecruit.id).label("count"),
        ).group_by(PotentialRecruit.stage)
    ).all()

    recruits_by_stage = [
        FunnelStageCount(stage=stage.value, count=0) for stage in FUNNEL_ORDER
    ]
    stage_map = {s.stage: s for s in recruits_by_stage}

    for row in recruit_rows:
        if row.stage in stage_map:
            stage_map[row.stage].count = row.count
        else:
            # Include DECLINED or any other stage not in FUNNEL_ORDER.
            recruits_by_stage.append(FunnelStageCount(stage=row.stage, count=row.count))

    total_recruits = sum(s.count for s in recruits_by_stage)

    # Total cadets and counts by status.
    cadet_rows = db.execute(
        select(
            Cadet.status,
            func.count(Cadet.id).label("count"),
        ).group_by(Cadet.status)
    ).all()

    cadets_by_status = [{"status": row.status, "count": row.count} for row in cadet_rows]
    total_cadets = sum(int(c["count"]) for c in cadets_by_status)

    # Open follow-ups count.
    open_followups = (
        db.scalar(
            select(func.count(FollowUp.id)).where(FollowUp.status == FollowUpStatus.OPEN.value)
        )
        or 0
    )

    # Recent trend: last ~8 weeks of recruit creation (bucketed by week).
    # Pull all recruits, bucket by week in Python for SQLite compatibility.
    all_recruits = db.scalars(
        select(PotentialRecruit.created_at).order_by(PotentialRecruit.created_at)
    ).all()

    week_buckets: dict[str, int] = defaultdict(int)
    for created_at in all_recruits:
        if created_at:
            week = _bucket_by_week(created_at)
            week_buckets[week] += 1

    # Take the last 8 weeks.
    sorted_weeks = sorted(week_buckets.items())
    recent_trend = [TrendPoint(period=w, count=c) for w, c in sorted_weeks[-8:]]

    return DashboardStats(
        total_recruits=total_recruits,
        recruits_by_stage=recruits_by_stage,
        total_cadets=total_cadets,
        cadets_by_status=cadets_by_status,
        open_followups=open_followups,
        recent_trend=recent_trend,
    )
