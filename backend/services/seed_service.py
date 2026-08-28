"""Seed demo user and project on first startup."""

import logging

from sqlalchemy.orm import Session

from backend.models.db_models import Project, User
from shared.events import UserRole

logger = logging.getLogger(__name__)

DEMO_USER_ID = "U001"
DEMO_PROJECT_ID = "P001"


def seed_demo_data(db: Session) -> None:
    """Create demo developer and ProjectPulse AI project if not present."""
    user = db.get(User, DEMO_USER_ID)
    if not user:
        user = User(
            user_id=DEMO_USER_ID,
            name="Demo Developer",
            role=UserRole.DEVELOPER.value,
        )
        db.add(user)
        logger.info("Seeded demo user: %s", DEMO_USER_ID)

    project = db.get(Project, DEMO_PROJECT_ID)
    if not project:
        project = Project(
            project_id=DEMO_PROJECT_ID,
            name="ProjectPulse AI",
            folder_path="E:/projects/projectpulse",
            owner_user_id=DEMO_USER_ID,
        )
        db.add(project)
        logger.info("Seeded demo project: %s", DEMO_PROJECT_ID)

    db.commit()
