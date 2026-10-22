"""Dedicated Testing Collector with pluggable framework adapters.

Implements Section 9 & 23 of the ProjectPulse AI Master Architecture:
- Adapter-based architecture (BaseTestAdapter, PytestAdapter, JestAdapter)
- Emits TEST_STARTED, TEST_COMPLETED, TEST_PASSED, TEST_FAILED
- Extracts test suite name, framework, total, passed, failed, skipped, and duration.
"""

import logging
import re
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from agent.collectors.base import BaseCollector
from shared.event_types import EventSource, EventType

logger = logging.getLogger(__name__)


class BaseTestAdapter(ABC):
    """Base adapter interface for test frameworks."""

    @property
    @abstractmethod
    def framework_name(self) -> str:
        pass

    @abstractmethod
    def parse_output(self, stdout: str, stderr: str, returncode: int, duration_seconds: float) -> dict[str, Any]:
        """Parse raw test runner output into normalized test result metrics."""
        pass


class PytestAdapter(BaseTestAdapter):
    """Adapter for parsing pytest output and summaries."""

    framework_name = "pytest"

    def parse_output(self, stdout: str, stderr: str, returncode: int, duration_seconds: float) -> dict[str, Any]:
        combined = f"{stdout}\n{stderr}"
        
        passed = 0
        failed = 0
        skipped = 0
        total = 0

        # Regex for summary line: e.g. "=== 2 failed, 15 passed, 1 skipped in 4.12s ==="
        m_passed = re.search(r"(\d+)\s+passed", combined)
        m_failed = re.search(r"(\d+)\s+failed", combined)
        m_skipped = re.search(r"(\d+)\s+skipped", combined)

        if m_passed:
            passed = int(m_passed.group(1))
        if m_failed:
            failed = int(m_failed.group(1))
        if m_skipped:
            skipped = int(m_skipped.group(1))

        total = passed + failed + skipped
        if total == 0:
            # Fallback if specific counts not found
            total = 1 if returncode == 0 else 1
            if returncode == 0:
                passed = 1
            else:
                failed = 1

        # Extract failed test names if available
        failed_tests = re.findall(r"FAILED\s+([^\s:]+::[^\s]+)", combined)
        if not failed_tests:
            failed_tests = re.findall(r"FAILED\s+([^\s]+)", combined)

        # Detect suite name from output or file args
        m_suite = re.search(r"collected \d+ items? from ([\w\-/_\.]+)", combined)
        suite_name = m_suite.group(1) if m_suite else "pytest-suite"

        return {
            "framework": self.framework_name,
            "suite": suite_name,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_seconds": round(duration_seconds, 2),
            "exit_code": returncode,
            "failed_tests": failed_tests[:5],
        }


class JestAdapter(BaseTestAdapter):
    """Adapter for Jest / JavaScript test runners."""

    framework_name = "jest"

    def parse_output(self, stdout: str, stderr: str, returncode: int, duration_seconds: float) -> dict[str, Any]:
        combined = f"{stdout}\n{stderr}"
        m_tests = re.search(r"Tests:\s+(?:(\d+)\s+failed,\s+)?(?:(\d+)\s+passed,\s+)?(\d+)\s+total", combined)
        passed, failed, total = 0, 0, 0
        if m_tests:
            failed = int(m_tests.group(1)) if m_tests.group(1) else 0
            passed = int(m_tests.group(2)) if m_tests.group(2) else 0
            total = int(m_tests.group(3)) if m_tests.group(3) else (passed + failed)
        else:
            total = 1
            if returncode == 0:
                passed = 1
            else:
                failed = 1

        return {
            "framework": self.framework_name,
            "suite": "jest-suite",
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": max(0, total - (passed + failed)),
            "duration_seconds": round(duration_seconds, 2),
            "exit_code": returncode,
            "failed_tests": [],
        }


class TestCollector(BaseCollector):
    """Dedicated collector for test execution and telemetry."""

    source_name = "TEST"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.adapters: dict[str, BaseTestAdapter] = {
            "pytest": PytestAdapter(),
            "jest": JestAdapter(),
        }

    def record_test_run(
        self,
        framework: str,
        suite_name: str,
        total: int,
        passed: int,
        failed: int,
        skipped: int = 0,
        duration_seconds: float = 0.0,
        failed_tests: list[str] | None = None,
    ):
        """Record normalized test results and emit TEST_PASSED or TEST_FAILED events."""
        if not self.privacy_filter.is_active:
            return

        is_passed = failed == 0
        event_type = EventType.TEST_PASSED if is_passed else EventType.TEST_FAILED
        status = "SUCCESS" if is_passed else "WARNING"

        title = f"{framework} {suite_name}: {passed}/{total} passed"
        if failed > 0:
            title += f" ({failed} failed)"

        desc_parts = [f"{passed} passed, {failed} failed"]
        if skipped > 0:
            desc_parts.append(f"{skipped} skipped")
        desc_parts.append(f"in {duration_seconds:.2f}s")
        description = ", ".join(desc_parts)

        metadata = {
            "framework": framework,
            "suite": suite_name,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_seconds": round(duration_seconds, 2),
            "pass_rate": round((passed / total * 100), 1) if total > 0 else 0.0,
            "failed_tests": failed_tests or [],
            "project": self.config.project_name,
        }

        # Emit TEST_COMPLETED
        completed_event = self.normalizer.normalize(
            source=EventSource.TEST,
            event_type=EventType.TEST_COMPLETED,
            title=title,
            description=description,
            status=status,
            metadata=metadata,
        )
        self.emit(completed_event)

        # Emit specific TEST_FAILED or TEST_PASSED event
        outcome_event = self.normalizer.normalize(
            source=EventSource.TEST,
            event_type=event_type,
            title=title,
            description=description,
            status=status,
            metadata=metadata,
        )
        self.emit(outcome_event)
        logger.info("Recorded test event: %s [%s]", title, status)

    def execute_and_record_tests(self, command: str, framework: str = "pytest", suite_name: str = "") -> dict[str, Any]:
        """Runs a test command safely, parses results using the adapter, and emits events."""
        project_path = self.config.project_path
        if not project_path or not project_path.exists():
            logger.warning("Project path invalid — cannot run tests")
            return {"status": "error", "message": "Invalid project path"}

        adapter = self.adapters.get(framework, self.adapters["pytest"])

        # Emit TEST_STARTED
        start_event = self.normalizer.normalize(
            source=EventSource.TEST,
            event_type=EventType.TEST_STARTED,
            title=f"Test run started: {command}",
            description=f"Executing {framework} test suite in {project_path.name}",
            status="INFO",
            metadata={"framework": framework, "command": command, "project": self.config.project_name},
        )
        self.emit(start_event)

        start_time = time.monotonic()
        try:
            proc = subprocess.run(
                command,
                cwd=str(project_path),
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            duration = time.monotonic() - start_time
            parsed = adapter.parse_output(proc.stdout, proc.stderr, proc.returncode, duration)
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start_time
            parsed = {
                "framework": framework,
                "suite": suite_name or "timeout-suite",
                "total": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "duration_seconds": round(duration, 2),
                "exit_code": 124,
                "failed_tests": ["Test run timed out after 300s"],
            }
        except Exception as exc:
            duration = time.monotonic() - start_time
            parsed = {
                "framework": framework,
                "suite": suite_name or "error-suite",
                "total": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "duration_seconds": round(duration, 2),
                "exit_code": 1,
                "failed_tests": [str(exc)],
            }

        effective_suite = suite_name or parsed.get("suite", "test-suite")
        self.record_test_run(
            framework=parsed.get("framework", framework),
            suite_name=effective_suite,
            total=parsed.get("total", 1),
            passed=parsed.get("passed", 0),
            failed=parsed.get("failed", 0),
            skipped=parsed.get("skipped", 0),
            duration_seconds=parsed.get("duration_seconds", duration),
            failed_tests=parsed.get("failed_tests", []),
        )
        return parsed

    def start(self) -> None:
        self._running = True
        logger.info("Test collector initialized")

    def stop(self) -> None:
        self._running = False
