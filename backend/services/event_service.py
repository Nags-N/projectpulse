"""Business logic for events and summaries."""

from datetime import date
from types import SimpleNamespace

from sqlalchemy.orm import Session

from backend.database import metadata_from_json, metadata_to_json
from backend.models.db_models import Project, ProjectEventRecord, User
from backend.models.schemas import (
    ActivitySummary,
    DeveloperSummaryResponse,
    EventIngestRequest,
    EventResponse,
    ManagerDashboardResponse,
    new_id,
)
from backend.services.monitoring_status import get_monitoring_status
from shared.events import EventType
from shared.summarizer import describe_event, narrative_summary, recent_activity_title, what_you_did
from shared.timeutil import DISPLAY_TZ_NAME, as_utc, display_day_bounds_utc_naive, today_in_display_tz, to_utc_naive


def _record_meta(record: ProjectEventRecord) -> dict:
    return metadata_from_json(record.metadata_json)


def _summary_event(record: ProjectEventRecord) -> SimpleNamespace:
    return SimpleNamespace(
        event_type=record.event_type,
        title=record.title,
        description=record.description,
        metadata=_record_meta(record),
    )


def _event_to_response(record: ProjectEventRecord) -> EventResponse:
    meta = _record_meta(record)
    return EventResponse(
        event_id=record.event_id,
        project_id=record.project_id,
        user_id=record.user_id,
        role=record.role,
        source=record.source,
        event_type=record.event_type,
        title=record.title,
        description=record.description,
        status=record.status,
        timestamp=as_utc(record.timestamp),
        metadata=meta,
        created_at=as_utc(record.created_at),
        human_description=describe_event(
            record.event_type, record.title, record.description, meta
        ),
        display_title=recent_activity_title(
            record.event_type, record.title, meta, record.description
        ),
    )


def create_event(db: Session, payload: EventIngestRequest) -> EventResponse:
    project = db.get(Project, payload.project_id)
    if not project:
        raise ValueError(f"Project '{payload.project_id}' not found")

    user = db.get(User, payload.user_id)
    if not user:
        raise ValueError(f"User '{payload.user_id}' not found")

    event_id = payload.event_id or new_id()
    record = ProjectEventRecord(
        event_id=event_id,
        project_id=payload.project_id,
        user_id=payload.user_id,
        role=payload.role.value,
        source=payload.source.value,
        event_type=payload.event_type.value,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        timestamp=to_utc_naive(payload.timestamp),
        metadata_json=metadata_to_json(payload.metadata),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _event_to_response(record)


def list_events(
    db: Session,
    project_id: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
) -> list[EventResponse]:
    query = db.query(ProjectEventRecord).order_by(ProjectEventRecord.timestamp.desc())
    if project_id:
        query = query.filter(ProjectEventRecord.project_id == project_id)
    if user_id:
        query = query.filter(ProjectEventRecord.user_id == user_id)
    records = query.limit(limit).all()
    return [_event_to_response(r) for r in records]


def _summarize_events(events: list[ProjectEventRecord]) -> ActivitySummary:
    summary = ActivitySummary()
    summary.total_activities = len(events)
    for event in events:
        et = event.event_type
        if et == EventType.GIT_COMMIT.value:
            summary.commits += 1
        elif et == EventType.BUILD_FAILED.value:
            summary.build_failures += 1
        elif et == EventType.BUILD_SUCCEEDED.value:
            summary.build_successes += 1
        elif et == EventType.FILE_MODIFIED.value:
            summary.file_modifications += 1
        elif et == EventType.FILE_CREATED.value:
            summary.files_created += 1
        elif et in (EventType.GIT_BRANCH_CHANGED.value, EventType.GIT_BRANCH_CREATED.value):
            summary.branch_changes += 1
    return summary


def _current_status(events: list[ProjectEventRecord]) -> str:
    if not events:
        return "No activity recorded today"
    latest = max(events, key=lambda e: e.timestamp)
    if latest.event_type == EventType.BUILD_FAILED.value:
        return "Build issues detected — development in progress"
    if latest.event_type == EventType.BUILD_SUCCEEDED.value:
        return "Build healthy — development in progress"
    if latest.event_type == EventType.GIT_COMMIT.value:
        return "Active development — recent commits"
    return "Development in progress"


def get_developer_summary(
    db: Session,
    project_id: str,
    user_id: str,
    summary_date: date | None = None,
) -> DeveloperSummaryResponse:
    project = db.get(Project, project_id)
    if not project:
        raise ValueError(f"Project '{project_id}' not found")

    day = summary_date or today_in_display_tz()
    start, end = display_day_bounds_utc_naive(day)
    events = (
        db.query(ProjectEventRecord)
        .filter(
            ProjectEventRecord.project_id == project_id,
            ProjectEventRecord.user_id == user_id,
            ProjectEventRecord.timestamp >= start,
            ProjectEventRecord.timestamp <= end,
        )
        .order_by(ProjectEventRecord.timestamp.desc())
        .all()
    )

    activity = _summarize_events(events)
    monitoring = get_monitoring_status()
    summary_events = [_summary_event(e) for e in events]
    did = what_you_did(summary_events, activity)

    return DeveloperSummaryResponse(
        project_id=project.project_id,
        project_name=project.name,
        date=day.isoformat(),
        activity=activity,
        highlights=did,
        recent_events=[_event_to_response(e) for e in events[:10]],
        current_status=_current_status(events),
        narrative_summary=narrative_summary(summary_events, activity),
        what_you_did=did,
        monitoring_active=monitoring.get("active", True),
        display_timezone=DISPLAY_TZ_NAME,
    )


def _manager_signals(events: list[ProjectEventRecord]) -> list[str]:
    signals: list[str] = []

    if events:
        signals.append("✓ Development activity active")
    else:
        signals.append("⚠ No project activity recorded yet")
        return signals

    recent_failures = [
        e for e in events if e.event_type == EventType.BUILD_FAILED.value
    ][:3]
    for failure in recent_failures:
        module = metadata_from_json(failure.metadata_json).get("module", failure.title)
        signals.append(f"⚠ Build failure detected — {module}")

    recent_commits = [e for e in events if e.event_type == EventType.GIT_COMMIT.value]
    if recent_commits:
        signals.append(f"✓ {len(recent_commits)} Git commit(s) recorded")

    return signals


def _manager_narrative(events: list[ProjectEventRecord], activity: ActivitySummary) -> str:
    if not events:
        return "No project activity has been recorded yet. Waiting for developer activity."

    summary_events = [_summary_event(e) for e in events]
    developer_text = narrative_summary(summary_events, activity)
    parts = ["Development activity is currently active.", developer_text]
    if activity.build_failures:
        parts.append(
            f"{activity.build_failures} build failure{'s' if activity.build_failures != 1 else ''} require{'s' if activity.build_failures == 1 else ''} attention."
        )
    elif activity.build_successes:
        parts.append("Recent builds are passing.")
    return " ".join(parts)


def get_manager_dashboard(db: Session, project_id: str) -> ManagerDashboardResponse:
    project = db.get(Project, project_id)
    if not project:
        raise ValueError(f"Project '{project_id}' not found")

    events = (
        db.query(ProjectEventRecord)
        .filter(ProjectEventRecord.project_id == project_id)
        .order_by(ProjectEventRecord.timestamp.desc())
        .limit(200)
        .all()
    )

    activity = _summarize_events(events)

    return ManagerDashboardResponse(
        project_id=project.project_id,
        project_name=project.name,
        activity=activity,
        recent_events=[_event_to_response(e) for e in events[:10]],
        signals=_manager_signals(events),
        narrative_summary=_manager_narrative(events, activity),
    )
