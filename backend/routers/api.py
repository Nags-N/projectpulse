"""API route handlers for ProjectPulse AI."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.db_models import Agent, Project, ProjectEventRecord, TaskRecord, User
from backend.models.schemas import (
    ActivitySummary,
    AgentHeartbeatRequest,
    AgentRegisterRequest,
    AgentResponse,
    AppConfigResponse,
    DefectCreate,
    DefectStatusUpdate,
    DeveloperSummaryResponse,
    EventIngestRequest,
    EventResponse,
    ManagerDashboardResponse,
    MonitoringStatusUpdate,
    ProjectCreate,
    ProjectResponse,
    TaskCreate,
    TaskResponse,
    UserCreate,
    UserResponse,
    VerdictCreate,
    AIChatRequest,
    AIChatResponse,
    EvidenceResponse,
    TaskEvidenceDetailResponse,
    SyncRunResponse,
    JiraConnectRequest,
    JiraProjectResponse,
    JiraSyncRequest,
    AIRiskItem,
    AISummaryRequest,
    AISummaryResponse,
    TimelineItemResponse,
    CodeExplanationResponse,
    new_id,
)
from backend.integrations.jira.schemas import (
    JiraCommentItem,
    JiraIssueDetailResponse,
    JiraIssueItem,
    JiraSyncStatsResponse,
    JiraTestConnectionResponse,
)
from backend.integrations.jira.service import JiraService
from backend.services.agent_service import get_agent, heartbeat_agent, list_agents, register_agent
from backend.services.ai_service import answer_project_query, get_ai_suggestions
from backend.services.evidence_service import get_task_evidence_detail
from backend.services.event_service import (
    create_event,
    get_developer_summary,
    get_manager_dashboard,
    get_tester_metrics,
    list_events,
)
from backend.services.monitoring_status import get_monitoring_status, set_monitoring_status
from backend.services.qa_service import (
    get_qa_metrics,
    list_defects,
    record_qa_verdict,
    report_defect,
    update_defect_status,
)
from backend.services.seed_service import DEMO_PROJECT_ID, DEMO_USER_ID, seed_demo_data
from backend.services.task_service import create_or_update_task, list_tasks
from shared.event_types import UserRole

router = APIRouter()


# ---------------------------------------------------------
# Health & Configuration
# ---------------------------------------------------------

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ProjectPulse AI Backend",
        "version": "1.0.0",
        "phase": 1,
    }


@router.get("/config", response_model=AppConfigResponse)
def get_app_config(db: Session = Depends(get_db)):
    """Return default project and user IDs for agents and frontend."""
    target_project_id = settings.jira_project_key or DEMO_PROJECT_ID
    project = db.get(Project, target_project_id)
    if not project:
        project = db.get(Project, DEMO_PROJECT_ID)
    user = db.get(User, DEMO_USER_ID)
    if not project or not user:
        seed_demo_data(db)
        project = db.get(Project, target_project_id) or db.get(Project, DEMO_PROJECT_ID)
        user = db.get(User, DEMO_USER_ID)

    monitoring = get_monitoring_status()
    return AppConfigResponse(
        project_id=project.project_id if project else target_project_id,
        user_id=user.user_id if user else DEMO_USER_ID,
        project_name=project.name if project else f"Project {target_project_id}",
        monitoring_active=monitoring.get("active", True),
    )


@router.post("/monitoring-status")
def update_monitoring_status(payload: MonitoringStatusUpdate):
    set_monitoring_status(payload.active, payload.project_id)
    return get_monitoring_status()


@router.get("/monitoring-status")
def read_monitoring_status():
    return get_monitoring_status()


# ---------------------------------------------------------
# Agent Management & Heartbeats
# ---------------------------------------------------------

@router.post("/agents/register", response_model=AgentResponse, status_code=201)
def api_register_agent(payload: AgentRegisterRequest, db: Session = Depends(get_db)):
    """Register or update an agent installation across developer/tester/QA machines."""
    return register_agent(db, payload)


@router.post("/agents/heartbeat")
def api_agent_heartbeat(payload: AgentHeartbeatRequest, db: Session = Depends(get_db)):
    """Keep-alive heartbeat sent periodically by running agents."""
    return heartbeat_agent(db, payload)


@router.get("/agents", response_model=list[AgentResponse])
def api_list_agents(project_id: str | None = None, db: Session = Depends(get_db)):
    """List all registered agents and their current status."""
    return list_agents(db, project_id=project_id)


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def api_get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return agent


# ---------------------------------------------------------
# Users & Projects
# ---------------------------------------------------------

@router.get("/users", response_model=list[UserResponse])
def api_list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.post("/users", response_model=UserResponse, status_code=201)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    user_id = payload.user_id or new_id("USR")
    if db.get(User, user_id):
        raise HTTPException(status_code=409, detail="User already exists")

    role_val = payload.role.value if hasattr(payload.role, "value") else str(payload.role)
    user = User(
        user_id=user_id,
        name=payload.name,
        role=role_val,
        external_id=payload.external_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/projects", response_model=list[ProjectResponse])
def get_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def register_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if not db.get(User, payload.owner_user_id):
        raise HTTPException(status_code=404, detail="Owner user not found")

    project_id = payload.project_id or new_id("PRJ")
    if db.get(Project, project_id):
        raise HTTPException(status_code=409, detail="Project already exists")

    project = Project(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        folder_path=payload.folder_path,
        owner_user_id=payload.owner_user_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------
# Event Ingestion & Retrieval
# ---------------------------------------------------------

@router.post("/events", response_model=EventResponse, status_code=201)
def ingest_event(payload: EventIngestRequest, db: Session = Depends(get_db)):
    try:
        return create_event(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/events", response_model=list[EventResponse])
def get_events(
    project_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    role: str | None = Query(default=None),
    source: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_events(
        db,
        project_id=project_id,
        agent_id=agent_id,
        user_id=user_id,
        role=role,
        source=source,
        event_type=event_type,
        limit=limit,
    )


@router.get("/events/{event_id}", response_model=EventResponse)
def get_event(event_id: str, db: Session = Depends(get_db)):
    record = db.get(ProjectEventRecord, event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Event not found")
    from backend.services.event_service import _event_to_response

    return _event_to_response(record)


@router.get("/projects/{project_id}/events", response_model=list[EventResponse])
def get_project_events(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return list_events(db, project_id=project_id, limit=limit)


# ---------------------------------------------------------
# Tasks (Normalized Project-Management Tasks)
# ---------------------------------------------------------

@router.get("/tasks", response_model=list[TaskResponse])
def api_list_tasks(project_id: str | None = None, db: Session = Depends(get_db)):
    return list_tasks(db, project_id=project_id)


@router.post("/tasks", response_model=TaskResponse, status_code=201)
def api_create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    return create_or_update_task(db, payload)


@router.get("/tasks/{task_id}/evidence", response_model=TaskEvidenceDetailResponse)
def api_get_task_evidence(task_id: str, db: Session = Depends(get_db)):
    detail = get_task_evidence_detail(db, task_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return detail


# ---------------------------------------------------------
# Summaries & Dashboards
# ---------------------------------------------------------

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
    role: str = Query(default="PROJECT_MANAGER"),
    db: Session = Depends(get_db),
):
    try:
        return get_manager_dashboard(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/analytics")
def project_sprint_analytics(
    project_id: str,
    sprint: str = Query(default="Sprint 1"),
    db: Session = Depends(get_db),
):
    from backend.services.risk_service import get_sprint_analytics
    return get_sprint_analytics(db, project_id=project_id, sprint_name=sprint)



@router.get("/projects/{project_id}/testing")
def project_testing_metrics(project_id: str, db: Session = Depends(get_db)):
    try:
        return get_tester_metrics(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------
# QA & Defect Tracking Endpoints
# ---------------------------------------------------------

@router.get("/projects/{project_id}/qa")
def api_get_qa_metrics(project_id: str, db: Session = Depends(get_db)):
    try:
        return get_qa_metrics(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/defects")
def api_list_defects(project_id: str, db: Session = Depends(get_db)):
    return list_defects(db, project_id=project_id)


@router.post("/projects/{project_id}/defects", status_code=201)
def api_report_defect(project_id: str, payload: DefectCreate, db: Session = Depends(get_db)):
    return report_defect(
        db=db,
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        priority=payload.priority,
        related_task_id=payload.related_task_id,
        reported_by=payload.reported_by,
    )


@router.post("/defects/{defect_id}/status")
def api_update_defect_status(defect_id: str, payload: DefectStatusUpdate, db: Session = Depends(get_db)):
    defect = update_defect_status(db, defect_id=defect_id, new_status=payload.status)
    if not defect:
        raise HTTPException(status_code=404, detail=f"Defect '{defect_id}' not found")
    return defect


@router.post("/projects/{project_id}/qa/verdict")
def api_record_qa_verdict(project_id: str, payload: VerdictCreate, db: Session = Depends(get_db)):
    return record_qa_verdict(
        db=db,
        project_id=project_id,
        approved=payload.approved,
        build_ref=payload.build_ref,
        notes=payload.notes,
    )


# ---------------------------------------------------------
# Real Jira Cloud Integration Endpoints (Feature 4)
# ---------------------------------------------------------

@router.get("/integrations/jira/test", response_model=JiraTestConnectionResponse)
def api_test_jira_connection(project_key: str | None = None, db: Session = Depends(get_db)):
    """Test live Jira Cloud connectivity and verify access to target project."""
    service = JiraService(db)
    target_key = project_key or settings.jira_project_key or "KAN"
    return service.test_connection(project_key=target_key)


@router.get("/integrations/jira/info")
def api_jira_info():
    """Return current Jira connection status, project, and masked credentials."""
    from backend.integrations.registry import integration_manager
    adapter = integration_manager.get_adapter("JIRA")
    if hasattr(adapter, "get_connection_info"):
        return adapter.get_connection_info()
    return {"platform": "JIRA", "connected": adapter.is_connected() if adapter else False}


@router.post("/integrations/jira/connect")
def api_connect_jira(payload: JiraConnectRequest, db: Session = Depends(get_db)):
    """Connect to live Jira Cloud with supplied credentials."""
    from backend.integrations.registry import integration_manager
    adapter = integration_manager.get_adapter("JIRA")
    if not adapter:
        raise HTTPException(status_code=500, detail="Jira adapter not registered")
    success = adapter.connect({
        "base_url": payload.base_url,
        "email": payload.email,
        "api_token": payload.api_token,
    })
    service = JiraService(db)
    service._record_connection_status(success, getattr(adapter, "_last_error", None), payload.email)
    return {
        "status": "ok" if success else "error",
        "connected": adapter.is_connected(),
        "user_display_name": getattr(adapter, "_user_display_name", ""),
        "message": "Connected to live Jira Cloud" if success else (getattr(adapter, "_last_error", "Failed to connect to Jira Cloud")),
    }


@router.get("/integrations/jira/projects")
def api_get_jira_projects():
    """List accessible projects from live Jira Cloud."""
    from backend.integrations.registry import integration_manager
    adapter = integration_manager.get_adapter("JIRA")
    if not adapter:
        raise HTTPException(status_code=500, detail="Jira adapter not registered")
    return adapter.get_projects()


@router.get("/integrations/jira/issues", response_model=list[JiraIssueItem])
def api_get_jira_issues(
    project_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    jql: str | None = None,
    db: Session = Depends(get_db),
):
    """Retrieve real Jira issues from live Jira Cloud (or synchronized database cache)."""
    service = JiraService(db)
    target_project = project_id or settings.jira_project_key or "KAN"
    return service.get_issues(project_key=target_project, limit=limit, offset=offset, jql=jql)


@router.get("/integrations/jira/issues/{issue_key}", response_model=JiraIssueDetailResponse)
def api_get_jira_issue_detail(issue_key: str, db: Session = Depends(get_db)):
    """Retrieve real Jira issue detail including live comments and Atlassian Document Format parsed text."""
    service = JiraService(db)
    try:
        return service.get_issue_detail(issue_key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/integrations/jira/sync", response_model=JiraSyncStatsResponse)
def api_sync_jira_project(payload: JiraSyncRequest, db: Session = Depends(get_db)):
    """Synchronize real Jira Cloud issues for a project into TaskRecord database."""
    service = JiraService(db)
    target_project = payload.jira_project_key or payload.project_id or settings.jira_project_key or "KAN"
    return service.sync_project(project_key=target_project)


@router.post("/integrations/jira/webhook")
def api_jira_webhook(payload: dict, db: Session = Depends(get_db)):
    """Handle incoming Jira Cloud webhooks for real-time issue updates/creations."""
    service = JiraService(db)
    return service.handle_webhook(payload, db)


# ---------------------------------------------------------
# PM Tool Integrations & Synchronization
# ---------------------------------------------------------

@router.get("/integrations")
def api_list_integrations():
    from backend.integrations.registry import integration_manager
    return integration_manager.list_integrations()


@router.post("/integrations/{platform}/connect")
def api_connect_integration(platform: str, payload: dict | None = None):
    from backend.integrations.registry import integration_manager
    success = integration_manager.connect_platform(platform, payload or {})
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to connect to {platform}")
    return {"status": "ok", "platform": platform, "connected": True}


@router.post("/integrations/{platform}/disconnect")
def api_disconnect_integration(platform: str):
    from backend.integrations.registry import integration_manager
    success = integration_manager.disconnect_platform(platform)
    return {"status": "ok", "platform": platform, "connected": False}


@router.post("/integrations/sync")
def api_sync_integrations(project_id: str = "DLX", db: Session = Depends(get_db)):
    from backend.services.sync_service import sync_all_integrations
    return sync_all_integrations(db, project_id=project_id)


@router.post("/integrations/{platform}/sync")
def api_sync_single_platform(platform: str, project_id: str = "DLX", db: Session = Depends(get_db)):
    from backend.services.sync_service import sync_single_platform
    return sync_single_platform(db, platform=platform, project_id=project_id)


@router.get("/integrations/history", response_model=list[SyncRunResponse])
def api_get_sync_history(project_id: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    from backend.services.sync_service import list_sync_history
    return list_sync_history(db, project_id=project_id, limit=limit)


# ---------------------------------------------------------
# AI Project Assistant (Phases 14 & 15)
# ---------------------------------------------------------

@router.get("/projects/{project_id}/ai/suggestions")
def api_get_ai_suggestions(project_id: str):
    return {"project_id": project_id, "suggestions": get_ai_suggestions(project_id)}


@router.post("/projects/{project_id}/ai/chat", response_model=AIChatResponse)
def api_chat_ai(project_id: str, payload: AIChatRequest, db: Session = Depends(get_db)):
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return answer_project_query(db=db, project_id=project_id, query=payload.query.strip())


# ---------------------------------------------------------
# AI-Powered Risk Detection Endpoints (Feature 1)
# ---------------------------------------------------------

@router.get("/projects/{project_id}/risks/ai", response_model=list[AIRiskItem])
def api_get_ai_risks(project_id: str, db: Session = Depends(get_db)):
    from backend.services.risk_service import evaluate_project_risks
    raw_risks = evaluate_project_risks(db, project_id=project_id)
    items = []
    for r in raw_risks:
        items.append(AIRiskItem(
            risk_id=r.get("risk_id", ""),
            rule_id=r.get("rule_id", ""),
            risk_type=r.get("risk_type", r.get("rule_id", "")),
            severity=r.get("severity", "MEDIUM"),
            category=r.get("category", "QUALITY"),
            title=r.get("title", ""),
            task_id=r.get("task_id", ""),
            task_title=r.get("task_title", ""),
            facts=r.get("facts", []),
            explanation=r.get("explanation", r.get("interpretation", "")),
            confidence=r.get("confidence", 1.0),
            suggested_action=r.get("suggested_action", ""),
            timestamp=r.get("timestamp", ""),
        ))
    return items


# ---------------------------------------------------------
# AI Project & Task Summaries Endpoints (Feature 2)
# ---------------------------------------------------------

@router.post("/projects/{project_id}/ai/summary", response_model=AISummaryResponse)
def api_generate_project_ai_summary(
    project_id: str,
    payload: AISummaryRequest,
    db: Session = Depends(get_db),
):
    from backend.services.ai_service import generate_project_ai_summary
    return generate_project_ai_summary(
        db=db,
        project_id=project_id,
        summary_type=payload.summary_type,
        user_id=payload.user_id,
        timeframe=payload.timeframe,
    )


@router.post("/tasks/{task_id}/ai/summary")
def api_generate_task_ai_summary(task_id: str, db: Session = Depends(get_db)):
    from backend.services.ai_service import generate_task_ai_summary
    return generate_task_ai_summary(db=db, task_id=task_id)


# ---------------------------------------------------------
# Unified Chronological Project Timeline (Feature 5)
# ---------------------------------------------------------

@router.get("/projects/{project_id}/timeline", response_model=list[TimelineItemResponse])
def api_get_unified_timeline(
    project_id: str,
    filter: str = Query(default="ALL", description="Filter category: ALL, JIRA, DEV, BUILD, TEST, QA, RISKS, AI"),
    limit: int = Query(default=150, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from backend.services.timeline_service import get_unified_project_timeline
    return get_unified_project_timeline(
        db=db,
        project_id=project_id,
        category_filter=filter.upper(),
        limit=limit,
    )


# ---------------------------------------------------------
# Explain WHY Code Changed (Feature 6)
# ---------------------------------------------------------

@router.get("/projects/{project_id}/code-explanations", response_model=list[CodeExplanationResponse])
def api_get_code_explanations(
    project_id: str,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from backend.services.code_explanation_service import explain_code_changes
    return explain_code_changes(db=db, project_id=project_id, limit=limit)




