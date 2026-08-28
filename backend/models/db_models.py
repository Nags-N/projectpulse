"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from shared.timeutil import utc_now_naive


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="DEVELOPER")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    events: Mapped[list["ProjectEventRecord"]] = relationship(back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    folder_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    owner: Mapped["User"] = relationship(back_populates="projects")
    events: Mapped[list["ProjectEventRecord"]] = relationship(back_populates="project")


class ProjectEventRecord(Base):
    __tablename__ = "project_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.project_id"))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"))
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="INFO")
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    project: Mapped["Project"] = relationship(back_populates="events")
    user: Mapped["User"] = relationship(back_populates="events")
