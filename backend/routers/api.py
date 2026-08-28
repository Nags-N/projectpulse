"""API route handlers."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.db_models import Project, User
from backend.models.schemas import (
    ActivitySummary,
    AppConfigResponse,
    DeveloperSummaryResponse,
    EventIngestRequest,
    EventResponse,
    ManagerDashboardResponse,
    MonitoringStatusUpdate,
    ProjectCreate,
    ProjectResponse,
    UserCreate,
    UserResponse,
    new_id,
)
from backend.services.event_service import (
    create_event,
    get_developer_summary,
    get_manager_dashboard,
    list_events,
)
from backend.services.monitoring_status import get_monitoring_status, set_monitoring_status
from backend.services.seed_service import DEMO_PROJECT_ID, DEMO_USER_ID, seed_demo_data
from shared.events import UserRole

router = APIRouter()


@router.get("/config", response_model=AppConfigResponse)
def get_app_config(db: Session = Depends(get_db)):
    """Return default project/user IDs for the frontend."""
    project = db.get(Project, DEMO_PROJECT_ID)
    user = db.get(User, DEMO_USER_ID)
    if not project or not user:
        seed_demo_data(db)
        project = db.get(Project, DEMO_PROJECT_ID)
        user = db.get(User, DEMO_USER_ID)

    monitoring = get_monitoring_status()
    return AppConfigResponse(
        project_id=project.project_id,
        user_id=user.user_id,
        project_name=project.name,
        monitoring_active=monitoring.get("active", True),
    )


@router.post("/monitoring-status")
def update_monitoring_status(payload: MonitoringStatusUpdate):
    set_monitoring_status(payload.active, payload.project_id)
    return get_monitoring_status()


@router.get("/monitoring-status")
def read_monitoring_status():
    return get_monitoring_status()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "ProjectPulse AI Backend"}


@router.post("/users", response_model=UserResponse, status_code=201)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    user_id = payload.user_id or new_id()
    if db.get(User, user_id):
        raise HTTPException(status_code=409, detail="User already exists")

    user = User(user_id=user_id, name=payload.name, role=payload.role.value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def register_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if not db.get(User, payload.owner_user_id):
        raise HTTPException(status_code=404, detail="Owner user not found")

    project_id = payload.project_id or new_id()
    if db.get(Project, project_id):
        raise HTTPException(status_code=409, detail="Project already exists")

    project = Project(
        project_id=project_id,
        name=payload.name,
        folder_path=payload.folder_path,
        owner_user_id=payload.owner_user_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectResponse])
def get_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post("/events", response_model=EventResponse, status_code=201)
def ingest_event(payload: EventIngestRequest, db: Session = Depends(get_db)):
    try:
        return create_event(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/events", response_model=list[EventResponse])
def get_events(
    project_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_events(db, project_id=project_id, user_id=user_id, limit=limit)


@router.get("/projects/{project_id}/events", response_model=list[EventResponse])
def get_project_events(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return list_events(db, project_id=project_id, limit=limit)


@router.get("/projects/{project_id}/summary", response_model=DeveloperSummaryResponse)
def project_developer_summary(
    project_id: str,
    user_id: str = Query(..., description="Developer user ID"),
    summary_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        return get_developer_summary(db, project_id, user_id, summary_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/dashboard", response_model=ManagerDashboardResponse)
def project_manager_dashboard(
    project_id: str,
    role: UserRole = Query(default=UserRole.PROJECT_MANAGER),
    db: Session = Depends(get_db),
):
    if role != UserRole.PROJECT_MANAGER:
        raise HTTPException(status_code=403, detail="Manager role required")
    try:
        return get_manager_dashboard(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
