"""Install optional Git hooks within the project repo for push detection."""

import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

HOOK_MARKER = "# ProjectPulse AI hook"
PRE_PUSH_HOOK = """#!/bin/sh
# ProjectPulse AI hook — records push metadata locally (no network, no content)
{marker}
LOG_DIR="$(git rev-parse --git-dir)/projectpulse"
LOG_FILE="$LOG_DIR/push.log"
mkdir -p "$LOG_DIR"
BRANCH="$(git branch --show-current 2>/dev/null || echo unknown)"
HASH="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
TS="$(date +%s 2>/dev/null || echo 0)"
echo "$HASH $BRANCH $TS" >> "$LOG_FILE"
exit 0
"""


def install_pre_push_hook(git_dir: Path) -> bool:
    """
    Install a pre-push hook in the project's .git/hooks folder.

    The hook only writes commit hash + branch to .git/projectpulse/push.log
    inside the project repository. No external calls, no file contents.
    """
    hooks_dir = git_dir / "hooks"
    hook_path = hooks_dir / "pre-push"

    if not hooks_dir.exists():
        return False

    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8", errors="ignore")
        if HOOK_MARKER in existing:
            logger.debug("ProjectPulse pre-push hook already installed")
            return True
        logger.info("pre-push hook exists without ProjectPulse marker — not overwriting")
        return False

    content = PRE_PUSH_HOOK.format(marker=HOOK_MARKER)
    hook_path.write_text(content, encoding="utf-8")

    try:
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass

    (git_dir / "projectpulse").mkdir(parents=True, exist_ok=True)
    logger.info("Installed ProjectPulse pre-push hook at %s", hook_path)
    return True
