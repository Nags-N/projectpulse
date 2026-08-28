"""In-memory monitoring status — updated by the background agent."""

from shared.timeutil import to_iso_utc, utc_now

_status: dict = {
    "active": True,
    "project_id": None,
    "updated_at": to_iso_utc(utc_now()),
}


def set_monitoring_status(active: bool, project_id: str | None = None) -> None:
    _status["active"] = active
    if project_id:
        _status["project_id"] = project_id
    _status["updated_at"] = to_iso_utc(utc_now())


def get_monitoring_status() -> dict:
    return dict(_status)
