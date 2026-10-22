"""Agent registration and heartbeat tracking service."""

from datetime import datetime
from sqlalchemy.orm import Session

from backend.models.db_models import Agent, Project, User
from backend.models.schemas import AgentHeartbeatRequest, AgentRegisterRequest, AgentResponse
from shared.timeutil import utc_now_naive


def register_agent(db: Session, payload: AgentRegisterRequest) -> AgentResponse:
    # Ensure user and project exist or auto-create demo references if needed
    user = db.get(User, payload.user_id)
    if not user:
        user = User(user_id=payload.user_id, name=f"User {payload.user_id}", role=payload.role.value)
        db.add(user)
        db.commit()

    project = db.get(Project, payload.project_id)
    if not project:
        project = Project(
            project_id=payload.project_id,
            name=f"Project {payload.project_id}",
            folder_path="",
            owner_user_id=payload.user_id,
        )
        db.add(project)
        db.commit()

    agent = db.query(Agent).filter(Agent.agent_id == payload.agent_id).first()
    if not agent:
        agent = Agent(
            agent_id=payload.agent_id,
            user_id=payload.user_id,
            project_id=payload.project_id,
            role=payload.role.value,
            machine_name=payload.machine_name,
            machine_id=payload.machine_id,
            status="ONLINE",
            last_seen=utc_now_naive(),
        )
        db.add(agent)
    else:
        agent.user_id = payload.user_id
        agent.project_id = payload.project_id
        agent.role = payload.role.value
        agent.machine_name = payload.machine_name
        agent.machine_id = payload.machine_id
        agent.status = "ONLINE"
        agent.last_seen = utc_now_naive()

    db.commit()
    db.refresh(agent)
    return agent


def heartbeat_agent(db: Session, payload: AgentHeartbeatRequest) -> dict:
    agent = db.query(Agent).filter(Agent.agent_id == payload.agent_id).first()
    if agent:
        agent.last_seen = utc_now_naive()
        agent.status = "ONLINE" if payload.monitoring_active else "PAUSED"
        db.commit()
        return {"status": "ok", "agent_id": agent.agent_id, "agent_status": agent.status}
    return {"status": "not_found", "agent_id": payload.agent_id}


def list_agents(db: Session, project_id: str | None = None) -> list[Agent]:
    query = db.query(Agent).order_by(Agent.last_seen.desc())
    if project_id:
        query = query.filter(Agent.project_id == project_id)
    return query.all()


def get_agent(db: Session, agent_id: str) -> Agent | None:
    return db.query(Agent).filter(Agent.agent_id == agent_id).first()
