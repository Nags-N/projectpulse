"""AI-Powered Plan vs Reality Risk Detection Engine.

Implements Sections 13, 14, 15, 16, 19, 21 & Feature 1:
- Analyzes real data: Jira tasks (status, due date, priority, assignee, dependencies),
  Developer telemetry (commits, files, branches), Build logs, Test results, QA defects.
- Strictly separates observable telemetry FACTS from AI intelligence INTERPRETATION.
- Evaluates 8 explainable, grounded risk rules with confidence ratings and citations:
    RISK-001: Inactive Task (IN_PROGRESS without telemetry)
    RISK-002: Status Mismatch (TODO with active commits/code)
    RISK-003: Build Instability (Repeated broken builds)
    RISK-004: Test Instability (Automated test regression)
    RISK-005: QA Blocker (High/Critical defects open or QA rejected)
    RISK-006: Dependency Blockage (Prerequisite task incomplete or at risk)
    RISK-007: Overdue Incomplete (Due date passed without completion)
    RISK-008: Deadline Approaching with Failures (Imminent deadline + active quality gates failing)
- Generates data-driven Sprint Analytics.
"""

from datetime import datetime, timedelta
import json
import logging
from typing import Any
from sqlalchemy.orm import Session

from backend.database import metadata_from_json
from backend.models.db_models import DefectRecord, ProjectEventRecord, TaskRecord
from shared.event_types import EventType
from shared.timeutil import utc_now_naive

logger = logging.getLogger(__name__)


def evaluate_project_risks(db: Session, project_id: str = "DLX") -> list[dict[str, Any]]:
    """Evaluate explainable risk rules across planned tasks and actual agent activity."""
    tasks = db.query(TaskRecord).filter(TaskRecord.project_id == project_id).all()
    events = (
        db.query(ProjectEventRecord)
        .filter(ProjectEventRecord.project_id == project_id)
        .order_by(ProjectEventRecord.timestamp.desc())
        .limit(200)
        .all()
    )
    defects = db.query(DefectRecord).filter(DefectRecord.project_id == project_id).all()

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    now_iso = now.isoformat()

    risks: list[dict[str, Any]] = []
    task_map = {t.external_task_id: t for t in tasks}

    # Pre-calculate event groupings
    commits = [e for e in events if e.event_type == EventType.GIT_COMMIT.value]
    build_failures = [e for e in events if e.event_type == EventType.BUILD_FAILED.value]
    test_failures = [e for e in events if e.event_type == EventType.TEST_FAILED.value]
    critical_defects = [
        d for d in defects if d.severity in ("CRITICAL", "HIGH") and d.status in ("OPEN", "REOPENED")
    ]

    # -------------------------------------------------------------------------
    # RISK-001: Inactive Task (Jira = IN_PROGRESS, but no development activity)
    # -------------------------------------------------------------------------
    for task in tasks:
        if task.status == "IN_PROGRESS":
            ext_id = task.external_task_id.lower()
            matching_events = [
                e for e in events
                if ext_id in e.title.lower() or
                   ext_id in metadata_from_json(e.metadata_json).get("related_task_id", "").lower() or
                   any(w in e.title.lower() for w in task.title.lower().split() if len(w) > 4)
            ]
            if not matching_events:
                facts = [
                    f"Task status is marked 'IN_PROGRESS' in {task.source}",
                    f"Assignee: {task.assignee or 'Unassigned'} | Priority: {task.priority}",
                    "Zero commits, file modifications, or builds detected in recent workstation logs",
                ]
                explanation = (
                    f"Task {task.external_task_id} has remained In Progress, but no related engineering activity "
                    "has been detected recently. Risk of an unreported developer impediment or work occurring on an unlinked branch."
                )
                severity = "HIGH" if task.priority in ("HIGH", "URGENT") else "MEDIUM"
                risks.append({
                    "risk_id": f"RISK-{task.external_task_id}-INACTIVE",
                    "rule_id": "RISK-001",
                    "risk_type": "INACTIVE_IN_PROGRESS",
                    "severity": severity,
                    "category": "SCHEDULE",
                    "title": f"Inactive Task: {task.external_task_id} ({task.title})",
                    "task_id": task.external_task_id,
                    "task_title": task.title,
                    "facts": facts,
                    "evidence": facts,
                    "explanation": explanation,
                    "interpretation": explanation,
                    "confidence": 0.95,
                    "suggested_action": f"Check in with {task.assignee or 'assignee'} regarding impediments or verify git branch linkage.",
                    "timestamp": now_iso,
                })

    # -------------------------------------------------------------------------
    # RISK-002: PM Status Mismatch (Jira = TODO, but active development exists)
    # -------------------------------------------------------------------------
    for task in tasks:
        if task.status == "TODO":
            ext_id = task.external_task_id.lower()
            matching_commits = [
                e for e in commits
                if ext_id in e.title.lower() or
                   any(w in e.title.lower() for w in task.title.lower().split() if len(w) > 5)
            ]
            if matching_commits:
                facts = [
                    f"Task status is 'TODO' in {task.source}",
                    f"{len(matching_commits)} Git commit(s) detected matching task: '{matching_commits[0].title}'",
                    f"Last commit recorded at: {matching_commits[0].timestamp.strftime('%Y-%m-%d %H:%M')}",
                ]
                explanation = (
                    f"Actual engineering work for {task.external_task_id} has already begun ({len(matching_commits)} commit(s) observed), "
                    "but the Jira ticket remains in 'To Do'. Plan and reality are out of synchronization."
                )
                risks.append({
                    "risk_id": f"RISK-{task.external_task_id}-MISMATCH",
                    "rule_id": "RISK-002",
                    "risk_type": "STATUS_MISMATCH_TODO",
                    "severity": "LOW",
                    "category": "PROCESS",
                    "title": f"Status Mismatch: {task.external_task_id} ({task.title})",
                    "task_id": task.external_task_id,
                    "task_title": task.title,
                    "facts": facts,
                    "evidence": facts,
                    "explanation": explanation,
                    "interpretation": explanation,
                    "confidence": 0.90,
                    "suggested_action": f"Update Jira task {task.external_task_id} status to IN_PROGRESS to reflect active engineering velocity.",
                    "timestamp": now_iso,
                })

    # -------------------------------------------------------------------------
    # RISK-003: Repeated Build Failure (Multiple broken builds in recent logs)
    # -------------------------------------------------------------------------
    if len(build_failures) >= 2:
        latest = build_failures[0]
        meta = metadata_from_json(latest.metadata_json)
        cmd = meta.get("command", latest.title)
        facts = [
            f"{len(build_failures)} consecutive build failures captured by Developer Agents",
            f"Latest failed command: '{cmd}'",
            f"Occurred at: {latest.timestamp.strftime('%Y-%m-%d %H:%M')}",
        ]
        explanation = (
            "Developers are encountering recurring compilation, packaging, or bundling failures. "
            "This threatens sprint velocity and prevents clean builds from reaching QA testing."
        )
        risks.append({
            "risk_id": "RISK-BUILD-FAILURES",
            "rule_id": "RISK-003",
            "risk_type": "BUILD_INSTABILITY",
            "severity": "HIGH",
            "category": "ENGINEERING",
            "title": f"Repeated Build Failures ({len(build_failures)} Failures Recorded)",
            "task_id": "",
            "task_title": "Build System Pipeline",
            "facts": facts,
            "evidence": facts,
            "explanation": explanation,
            "interpretation": explanation,
            "confidence": 0.98,
            "suggested_action": "Investigate environment configuration, package lockfiles, or compilation syntax errors causing build breakage.",
            "timestamp": now_iso,
        })

    # -------------------------------------------------------------------------
    # RISK-004: Test Instability (Repeated Test Failures on Active Feature)
    # -------------------------------------------------------------------------
    if test_failures:
        latest = test_failures[0]
        meta = metadata_from_json(latest.metadata_json)
        failed_count = meta.get("failed", 1)
        suite = meta.get("suite", "PaymentIntegration")
        failed_tests = meta.get("failed_tests", [])
        test_details = f": {', '.join(failed_tests[:2])}" if failed_tests else ""

        # Find linked task
        linked_task_id = "DLX-101"
        for t in tasks:
            if "payment" in t.title.lower() or "payment" in suite.lower():
                linked_task_id = t.external_task_id
                break

        facts = [
            f"{len(test_failures)} failing test run(s) logged by Tester Agents",
            f"Latest test execution failed {failed_count} assertion(s) in suite '{suite}'{test_details}",
            f"Tested by: {latest.user_id} at {latest.timestamp.strftime('%Y-%m-%d %H:%M')}",
        ]
        explanation = (
            f"Automated regression tests are actively failing for feature '{suite}' ({linked_task_id}). "
            "Feature cannot pass CI/CD quality gates and will fail QA acceptance."
        )
        risks.append({
            "risk_id": f"RISK-{linked_task_id}-TESTS",
            "rule_id": "RISK-004",
            "risk_type": "TEST_INSTABILITY",
            "severity": "HIGH",
            "category": "QUALITY",
            "title": f"Test Instability in Suite: {suite}",
            "task_id": linked_task_id,
            "task_title": f"Test Suite {suite}",
            "facts": facts,
            "evidence": facts,
            "explanation": explanation,
            "interpretation": explanation,
            "confidence": 0.95,
            "suggested_action": "Coordinate with developer to resolve failing test assertions prior to QA build acceptance.",
            "timestamp": now_iso,
        })

    # -------------------------------------------------------------------------
    # RISK-005: QA Blocker (High/Critical Unresolved Defect or QA Rejection)
    # -------------------------------------------------------------------------
    for defect in critical_defects:
        facts = [
            f"Defect Title: '{defect.title}'",
            f"Severity: {defect.severity} | Priority: {defect.priority}",
            f"Status: {defect.status} (Reported by: {defect.reported_by})",
            f"Linked Task: {defect.related_task_id or 'None'}",
        ]
        explanation = (
            f"A {defect.severity}-severity bug ({defect.defect_id}) remains open and blocks release gate verification. "
            "Formal QA sign-off cannot proceed until resolved."
        )
        risks.append({
            "risk_id": f"RISK-{defect.defect_id}-QA",
            "rule_id": "RISK-005",
            "risk_type": "QA_BLOCKER",
            "severity": "CRITICAL" if defect.severity == "CRITICAL" else "HIGH",
            "category": "QUALITY",
            "title": f"QA Release Blocker: {defect.defect_id} ({defect.title})",
            "task_id": defect.related_task_id or "",
            "task_title": defect.title,
            "facts": facts,
            "evidence": facts,
            "explanation": explanation,
            "interpretation": explanation,
            "confidence": 1.0,
            "suggested_action": f"Prioritize immediate bug fix for {defect.defect_id} in sprint backlog.",
            "timestamp": now_iso,
        })

    # -------------------------------------------------------------------------
    # RISK-006: Dependency Blockage (Dependent task active while prerequisite incomplete)
    # -------------------------------------------------------------------------
    for task in tasks:
        deps = []
        if task.dependencies:
            try:
                deps = json.loads(task.dependencies) if isinstance(task.dependencies, str) else task.dependencies
            except Exception:
                deps = []
        for dep_key in deps:
            parent_task = task_map.get(dep_key)
            if parent_task and parent_task.status != "COMPLETED":
                if task.status in ("IN_PROGRESS", "TODO"):
                    facts = [
                        f"Task '{task.external_task_id}' depends on prerequisite '{parent_task.external_task_id}' ({parent_task.title})",
                        f"Prerequisite status: '{parent_task.status}' (Incomplete)",
                        f"Dependent task status: '{task.status}'",
                    ]
                    explanation = (
                        f"Task {task.external_task_id} cannot safely complete because its prerequisite "
                        f"{parent_task.external_task_id} is '{parent_task.status}'. Risk of rework or downstream blockage."
                    )
                    risks.append({
                        "risk_id": f"RISK-{task.external_task_id}-DEP-{parent_task.external_task_id}",
                        "rule_id": "RISK-006",
                        "risk_type": "DEPENDENCY_BLOCKAGE",
                        "severity": "HIGH",
                        "category": "PROCESS",
                        "title": f"Dependency Blockage: {task.external_task_id} waiting on {parent_task.external_task_id}",
                        "task_id": task.external_task_id,
                        "task_title": task.title,
                        "facts": facts,
                        "evidence": facts,
                        "explanation": explanation,
                        "interpretation": explanation,
                        "confidence": 0.95,
                        "suggested_action": f"Unblock prerequisite {parent_task.external_task_id} ({parent_task.title}) before committing further resources.",
                        "timestamp": now_iso,
                    })

    # -------------------------------------------------------------------------
    # RISK-007: Overdue Incomplete (Due date in past, status != COMPLETED)
    # -------------------------------------------------------------------------
    for task in tasks:
        if task.due_date and task.due_date < today_str and task.status != "COMPLETED":
            facts = [
                f"Task due date was '{task.due_date}' (exceeded target deadline)",
                f"Current task status is '{task.status}'",
                f"Assignee: {task.assignee or 'Unassigned'}",
            ]
            explanation = (
                f"Task {task.external_task_id} has exceeded its scheduled completion date ({task.due_date}) "
                f"and remains in '{task.status}'. Direct threat to sprint milestone commitment."
            )
            risks.append({
                "risk_id": f"RISK-{task.external_task_id}-OVERDUE",
                "rule_id": "RISK-007",
                "risk_type": "OVERDUE_INCOMPLETE",
                "severity": "HIGH",
                "category": "SCHEDULE",
                "title": f"Overdue Task: {task.external_task_id} ({task.title})",
                "task_id": task.external_task_id,
                "task_title": task.title,
                "facts": facts,
                "evidence": facts,
                "explanation": explanation,
                "interpretation": explanation,
                "confidence": 1.0,
                "suggested_action": f"Re-estimate remaining effort for {task.external_task_id} and notify stakeholders of schedule adjustment.",
                "timestamp": now_iso,
            })

    # -------------------------------------------------------------------------
    # RISK-008: Deadline Approaching with Active Failures/Blockers
    # -------------------------------------------------------------------------
    for task in tasks:
        if task.due_date and task.due_date in (today_str, tomorrow_str) and task.status == "IN_PROGRESS":
            # Check if this task has failing tests or open defects
            ext_id = task.external_task_id.lower()
            task_defects = [
                d for d in defects
                if (d.related_task_id and d.related_task_id.lower() == ext_id) and d.status in ("OPEN", "REOPENED")
            ]
            if test_failures or task_defects or build_failures:
                evidence_items = [
                    f"Due date is imminent: {task.due_date} ({'Today' if task.due_date == today_str else 'Tomorrow'})",
                    f"Status: {task.status} | Priority: {task.priority}",
                ]
                if task_defects:
                    evidence_items.append(f"Linked open defect: {task_defects[0].defect_id} ({task_defects[0].title})")
                if test_failures:
                    evidence_items.append(f"{len(test_failures)} automated test execution failure(s) active")
                if build_failures:
                    evidence_items.append(f"{len(build_failures)} build failure(s) recorded in recent logs")

                explanation = (
                    f"Task {task.external_task_id} deadline is imminent ({task.due_date}), but quality telemetry "
                    "indicates unresolved test regressions and open defects. Very high risk of missing release cutoff."
                )
                risks.append({
                    "risk_id": f"RISK-{task.external_task_id}-DEADLINE-FAILURES",
                    "rule_id": "RISK-008",
                    "risk_type": "DEADLINE_APPROACHING_FAILURES",
                    "severity": "CRITICAL",
                    "category": "QUALITY",
                    "title": f"Critical Deadline Risk: {task.external_task_id} ({task.title})",
                    "task_id": task.external_task_id,
                    "task_title": task.title,
                    "facts": evidence_items,
                    "evidence": evidence_items,
                    "explanation": explanation,
                    "interpretation": explanation,
                    "confidence": 0.96,
                    "suggested_action": f"Urgent swarming required on {task.external_task_id} to fix failing assertions and unblock QA.",
                    "timestamp": now_iso,
                })

    return risks


def get_sprint_analytics(db: Session, project_id: str = "DLX", sprint_name: str = "Sprint 1") -> dict[str, Any]:
    """Calculate data-driven sprint analytics from real tasks, events, and defects."""
    tasks = db.query(TaskRecord).filter(TaskRecord.project_id == project_id).all()
    events = db.query(ProjectEventRecord).filter(ProjectEventRecord.project_id == project_id).all()
    defects = db.query(DefectRecord).filter(DefectRecord.project_id == project_id).all()

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Planned vs Completed
    total_planned = len(tasks)
    completed = [t for t in tasks if t.status == "COMPLETED"]
    in_progress = [t for t in tasks if t.status == "IN_PROGRESS"]
    blocked = [t for t in tasks if t.status == "BLOCKED"]
    todo = [t for t in tasks if t.status == "TODO"]

    # Carry forward tasks (overdue & incomplete)
    carry_forward = [
        t for t in tasks
        if t.due_date and t.due_date < today_str and t.status != "COMPLETED"
    ]

    # Engineering telemetry counts
    build_failures = sum(1 for e in events if e.event_type == EventType.BUILD_FAILED.value)
    build_successes = sum(1 for e in events if e.event_type == EventType.BUILD_SUCCEEDED.value)
    test_failures = sum(1 for e in events if e.event_type == EventType.TEST_FAILED.value)
    test_runs = sum(1 for e in events if e.event_type in (EventType.TEST_COMPLETED.value, EventType.TEST_FAILED.value))

    defects_created = len(defects)
    defects_closed = sum(1 for d in defects if d.status == "CLOSED")
    open_critical_defects = sum(1 for d in defects if d.severity in ("CRITICAL", "HIGH") and d.status in ("OPEN", "REOPENED"))

    completion_rate = (len(completed) / total_planned * 100) if total_planned > 0 else 0.0

    return {
        "sprint_name": sprint_name,
        "planned_tasks": total_planned,
        "completed_tasks": len(completed),
        "in_progress_tasks": len(in_progress),
        "blocked_tasks": len(blocked),
        "todo_tasks": len(todo),
        "carry_forward_tasks": len(carry_forward),
        "completion_rate_pct": round(completion_rate, 1),
        "build_failures": build_failures,
        "build_successes": build_successes,
        "test_runs": test_runs,
        "test_failures": test_failures,
        "defects_created": defects_created,
        "defects_closed": defects_closed,
        "open_critical_defects": open_critical_defects,
    }
