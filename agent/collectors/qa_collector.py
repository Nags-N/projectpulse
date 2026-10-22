"""Dedicated QA Activity and Defect Tracking Collector.

Implements Section 10 of the ProjectPulse AI Master Architecture:
- Defect reporting (BUG_REPORTED)
- Defect verification & lifecycle (BUG_VERIFIED, BUG_REOPENED, BUG_CLOSED)
- Regression testing tracking (REGRESSION_STARTED, REGRESSION_COMPLETED)
- Build acceptance / verification verdicts (QA_APPROVED, QA_REJECTED)
"""

import logging
from typing import Any
from uuid import uuid4

from agent.collectors.base import BaseCollector
from shared.event_types import EventSource, EventType

logger = logging.getLogger(__name__)


class QACollector(BaseCollector):
    source_name = "QA"

    def report_defect(
        self,
        title: str,
        description: str = "",
        severity: str = "HIGH",  # LOW, MEDIUM, HIGH, CRITICAL
        priority: str = "HIGH",  # LOW, MEDIUM, HIGH, URGENT
        related_task: str = "",
        reported_by: str = "",
    ) -> dict[str, Any]:
        """Record and emit a new bug defect."""
        if not self.privacy_filter.is_active:
            return {}

        defect_id = f"DEF-{uuid4().hex[:6].upper()}"
        reporter = reported_by or self.config.user_name

        metadata = {
            "defect_id": defect_id,
            "severity": severity.upper(),
            "priority": priority.upper(),
            "related_task": related_task,
            "reported_by": reporter,
            "project": self.config.project_name,
        }

        event = self.normalizer.normalize(
            source=EventSource.QA,
            event_type=EventType.BUG_REPORTED,
            title=f"[{severity.upper()}] Defect: {title}",
            description=description or f"Defect logged by {reporter}",
            status="ERROR" if severity.upper() in ("HIGH", "CRITICAL") else "WARNING",
            metadata=metadata,
        )
        self.emit(event)
        logger.info("QA reported defect: %s [%s]", defect_id, title)
        return {"defect_id": defect_id, **metadata}

    def verify_defect(self, defect_id: str, title: str) -> None:
        """Mark a reported defect as verified/reproducible."""
        event = self.normalizer.normalize(
            source=EventSource.QA,
            event_type=EventType.BUG_VERIFIED,
            title=f"Verified Defect: {defect_id} - {title}",
            description=f"Defect {defect_id} verified by QA",
            status="WARNING",
            metadata={"defect_id": defect_id, "project": self.config.project_name},
        )
        self.emit(event)

    def close_defect(self, defect_id: str, title: str) -> None:
        """Mark a defect as resolved and closed."""
        event = self.normalizer.normalize(
            source=EventSource.QA,
            event_type=EventType.BUG_CLOSED,
            title=f"Closed Defect: {defect_id} - {title}",
            description=f"Defect {defect_id} verified resolved and closed by QA",
            status="SUCCESS",
            metadata={"defect_id": defect_id, "project": self.config.project_name},
        )
        self.emit(event)

    def start_regression(self, suite_name: str) -> None:
        """Record start of a QA regression testing cycle."""
        event = self.normalizer.normalize(
            source=EventSource.QA,
            event_type=EventType.REGRESSION_STARTED,
            title=f"QA Regression Started: {suite_name}",
            description=f"Full regression test cycle initiated for {suite_name}",
            status="INFO",
            metadata={"suite": suite_name, "project": self.config.project_name},
        )
        self.emit(event)

    def complete_regression(self, suite_name: str, passed_count: int, total_count: int) -> None:
        """Record completion of a QA regression cycle."""
        event = self.normalizer.normalize(
            source=EventSource.QA,
            event_type=EventType.REGRESSION_COMPLETED,
            title=f"QA Regression Completed: {suite_name} ({passed_count}/{total_count} passed)",
            description=f"Regression testing concluded for {suite_name}",
            status="SUCCESS" if passed_count == total_count else "WARNING",
            metadata={
                "suite": suite_name,
                "passed": passed_count,
                "total": total_count,
                "project": self.config.project_name,
            },
        )
        self.emit(event)

    def set_build_verdict(self, build_ref: str, approved: bool, reason: str = "") -> None:
        """Approve or reject a release/build candidate."""
        event_type = EventType.QA_APPROVED if approved else EventType.QA_REJECTED
        status = "SUCCESS" if approved else "ERROR"
        verdict_str = "Approved" if approved else "Rejected"

        event = self.normalizer.normalize(
            source=EventSource.QA,
            event_type=event_type,
            title=f"Build {verdict_str}: {build_ref}",
            description=reason or f"Build {build_ref} {verdict_str.lower()} by QA",
            status=status,
            metadata={"build_ref": build_ref, "approved": approved, "reason": reason},
        )
        self.emit(event)

    def start(self) -> None:
        self._running = True
        logger.info("QA collector initialized")

    def stop(self) -> None:
        self._running = False
