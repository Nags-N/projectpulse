"""Build activity collector for ProjectPulse AI.

Monitors only approved project build/test commands in accordance with Section 8:
- npm run build
- npm test
- pytest
- mvn test
- gradle test

Emits:
- BUILD_STARTED
- BUILD_SUCCEEDED
- BUILD_FAILED
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Any

from agent.collectors.base import BaseCollector
from shared.event_types import EventSource, EventType

logger = logging.getLogger(__name__)

# Approved build commands only (never monitor arbitrary shell commands)
APPROVED_BUILD_COMMANDS = {
    "npm run build": {"category": "BUILD", "framework": "npm"},
    "npm test": {"category": "TEST", "framework": "jest/npm"},
    "pytest": {"category": "TEST", "framework": "pytest"},
    "mvn test": {"category": "TEST", "framework": "maven"},
    "gradle test": {"category": "TEST", "framework": "gradle"},
}


class BuildCollector(BaseCollector):
    source_name = "BUILD"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_command_approved(self, command: str) -> bool:
        cmd_clean = command.strip().lower()
        return any(cmd_clean == approved or cmd_clean.startswith(f"{approved} ") for approved in APPROVED_BUILD_COMMANDS)

    def record_build_execution(self, command: str, returncode: int, duration_seconds: float, output_snippet: str = ""):
        """Record the outcome of an approved build command."""
        if not self.privacy_filter.is_active:
            return

        cmd_clean = command.strip()
        is_success = returncode == 0
        event_type = EventType.BUILD_SUCCEEDED if is_success else EventType.BUILD_FAILED
        status = "SUCCESS" if is_success else "ERROR"

        title = f"Build {'succeeded' if is_success else 'failed'}: {cmd_clean}"
        description = f"Command '{cmd_clean}' exited with code {returncode} in {duration_seconds:.2f}s"

        metadata = {
            "command": cmd_clean,
            "exit_code": returncode,
            "duration_seconds": round(duration_seconds, 2),
            "project": self.config.project_name,
        }
        if output_snippet and not is_success:
            # Capture only non-sensitive last line for failure diagnosis
            clean_snippet = output_snippet.strip().splitlines()[-1] if output_snippet.strip() else ""
            metadata["failure_snippet"] = clean_snippet[:150]

        event = self.normalizer.normalize(
            source=EventSource.BUILD,
            event_type=event_type,
            title=title,
            description=description,
            status=status,
            metadata=metadata,
        )
        self.emit(event)
        logger.info("Emitted build event: %s (%s)", title, status)

    def execute_and_record(self, command: str) -> int:
        """Safely executes an approved build command in the project directory and records telemetry."""
        if not self.is_command_approved(command):
            logger.warning("Rejected command '%s' — not in approved build command allowlist", command)
            return -1

        project_path = self.config.project_path
        if not project_path or not project_path.exists():
            logger.warning("Project path invalid — cannot run build command")
            return -1

        # Emit BUILD_STARTED
        start_event = self.normalizer.normalize(
            source=EventSource.BUILD,
            event_type=EventType.BUILD_STARTED,
            title=f"Build started: {command}",
            description=f"Running '{command}' in {project_path.name}",
            status="INFO",
            metadata={"command": command, "project": self.config.project_name},
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
                timeout=180,
            )
            duration = time.monotonic() - start_time
            self.record_build_execution(command, proc.returncode, duration, proc.stderr or proc.stdout)
            return proc.returncode
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start_time
            self.record_build_execution(command, 124, duration, "Build command timed out after 180s")
            return 124
        except Exception as exc:
            duration = time.monotonic() - start_time
            self.record_build_execution(command, 1, duration, str(exc))
            return 1

    def start(self) -> None:
        self._running = True
        logger.info("Build collector initialized for approved commands")

    def stop(self) -> None:
        self._running = False
