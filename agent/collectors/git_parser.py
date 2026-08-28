"""Parse Git reflog and activity signals into normalized event hints."""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class GitSignalType(str, Enum):
    COMMIT = "GIT_COMMIT"
    BRANCH_CHANGED = "GIT_BRANCH_CHANGED"
    BRANCH_CREATED = "GIT_BRANCH_CREATED"
    PULL = "GIT_PULL"
    PUSH = "GIT_PUSH"


@dataclass
class GitSignal:
    signal_type: GitSignalType
    branch: str = ""
    commit_hash: str = ""
    message: str = ""
    raw_line: str = ""


REFLOG_LINE = re.compile(
    r"^[0-9a-f]{7,40}\s+[0-9a-f]{7,40}\s+.+\s+\d+\s+[+-]\d+\t(.+)$"
)


def read_current_branch(git_dir: Path) -> str:
    head_file = git_dir / "HEAD"
    if not head_file.exists():
        return "unknown"
    content = head_file.read_text(encoding="utf-8", errors="ignore").strip()
    if content.startswith("ref: refs/heads/"):
        return content.removeprefix("ref: refs/heads/")
    return content[:7] if len(content) >= 7 else "detached"


def branch_from_ref_path(path: Path) -> str:
    """Extract branch name from .git/logs/refs/heads/<branch> path."""
    parts = path.parts
    try:
        idx = parts.index("heads")
        return "/".join(parts[idx + 1 :])
    except ValueError:
        return path.stem


def parse_reflog_line(line: str, default_branch: str = "") -> GitSignal | None:
    line = line.strip()
    if not line:
        return None

    match = REFLOG_LINE.match(line)
    action = match.group(1) if match else line.split("\t", 1)[-1]

    commit_hash = line.split()[1] if line.split()[0].isalnum() and len(line.split()) > 1 else ""

    action_lower = action.lower()

    if action_lower.startswith("commit"):
        msg = action.split(":", 1)[-1].strip() if ":" in action else action
        return GitSignal(
            signal_type=GitSignalType.COMMIT,
            branch=default_branch,
            commit_hash=commit_hash,
            message=msg,
            raw_line=line,
        )

    if "checkout:" in action_lower and "moving from" in action_lower:
        # checkout: moving from main to feature/payment
        parts = action.split("moving from ", 1)[-1]
        if " to " in parts:
            _, to_branch = parts.rsplit(" to ", 1)
            return GitSignal(
                signal_type=GitSignalType.BRANCH_CHANGED,
                branch=to_branch.strip(),
                commit_hash=commit_hash,
                message=action,
                raw_line=line,
            )

    if action_lower.startswith("branch:"):
        if "created" in action_lower:
            branch = default_branch
            if "Branch: created" in action:
                branch = action.split("Branch: created", 1)[-1].strip().strip('"')
            return GitSignal(
                signal_type=GitSignalType.BRANCH_CREATED,
                branch=branch or default_branch,
                commit_hash=commit_hash,
                message=action,
                raw_line=line,
            )

    if "pull" in action_lower or "fetch" in action_lower and "merge" in action_lower:
        return GitSignal(
            signal_type=GitSignalType.PULL,
            branch=default_branch,
            commit_hash=commit_hash,
            message=action,
            raw_line=line,
        )

    if "push" in action_lower:
        return GitSignal(
            signal_type=GitSignalType.PUSH,
            branch=default_branch,
            commit_hash=commit_hash,
            message=action,
            raw_line=line,
        )

    return None


def parse_push_log_line(line: str) -> GitSignal | None:
    """Parse lines written by the optional pre-push hook."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # format: PUSH|<branch>|<commit_hash>|<remote>
    if line.startswith("PUSH|"):
        parts = line.split("|")
        if len(parts) >= 3:
            return GitSignal(
                signal_type=GitSignalType.PUSH,
                branch=parts[1],
                commit_hash=parts[2],
                message=f"Pushed to {parts[3] if len(parts) > 3 else 'remote'}",
                raw_line=line,
            )

    return None
