"""Deterministic, metadata-only activity descriptions. Never reads source files."""

from __future__ import annotations

from pathlib import PurePosixPath

from shared.events import EventType

FRIENDLY_FILES = {
    "tray_app.py": "the tray application",
    "main.py": "the application entry point",
    "config.py": "the configuration",
    "database.py": "the database layer",
    "api.py": "the API",
    "schemas.py": "the API schemas",
    "event_service.py": "event processing",
    "backend_client.py": "the backend client",
    "file_watcher.py": "the file watcher",
    "git_watcher.py": "the Git collector",
    "git_parser.py": "Git parsing",
    "privacy_filter.py": "the privacy filter",
    "normalizer.py": "event normalization",
    "DeveloperView.jsx": "the developer dashboard",
    "ManagerView.jsx": "the manager dashboard",
    "ActivityTimeline.jsx": "the activity timeline",
    "client.js": "the frontend API client",
    "App.jsx": "the frontend app shell",
}

FRIENDLY_MODULES = {
    "agent": "the agent",
    "backend": "the backend",
    "frontend": "the frontend",
    "shared": "shared project components",
    "scripts": "project scripts",
    "data": "project data files",
}


def _posix(path: str) -> str:
    return (path or "").replace("\\", "/").strip("/")


def _file_name(path: str) -> str:
    return PurePosixPath(_posix(path)).name


def _module_name(path: str) -> str:
    parts = [p for p in _posix(path).split("/") if p]
    if len(parts) >= 2:
        return parts[0]
    return ""


def _words_from_stem(name: str) -> str:
    stem = name.rsplit(".", 1)[0] if "." in name else name
    spaced = []
    current = ""
    for ch in stem.replace("-", "_"):
        if ch == "_":
            if current:
                spaced.append(current)
                current = ""
            continue
        if ch.isupper() and current and not current[-1].isupper():
            spaced.append(current)
            current = ch
        else:
            current += ch
    if current:
        spaced.append(current)
    return " ".join(w.lower() for w in spaced if w)


def friendly_file(path: str) -> str:
    name = _file_name(path)
    if name in FRIENDLY_FILES:
        return FRIENDLY_FILES[name]
    words = _words_from_stem(name)
    if words:
        return f"the {words}"
    return name or "a project file"


def friendly_module(path: str) -> str:
    module = _module_name(path).lower()
    if module in FRIENDLY_MODULES:
        return FRIENDLY_MODULES[module]
    if module:
        return f"the {module} module"
    return "the project"


def _commit_message(metadata: dict, description: str = "", title: str = "") -> str:
    msg = (
        metadata.get("commit_message")
        or metadata.get("message")
        or ""
    )
    if not msg and description and not description.lower().startswith("file "):
        msg = description
    msg = str(msg).strip().strip('"').strip("'")
    if msg.lower().startswith("commit:"):
        msg = msg.split(":", 1)[-1].strip()
    if not msg and title.lower().startswith("commit"):
        msg = title
    return msg


def _commit_clause(message: str) -> str:
    if not message:
        return "committed project changes"
    lower = message.lower()
    rest = message
    for prefix in ("fix:", "fixed:", "fix ", "fixed "):
        if lower.startswith(prefix):
            rest = message[len(prefix) :].strip()
            if rest.lower().endswith(" fix"):
                return f"committed a {rest.lower()}"
            return f"committed a {rest.lower()} fix"
    for prefix in ("add:", "added:", "add ", "added "):
        if lower.startswith(prefix):
            rest = message[len(prefix) :].strip()
            if "feature" in rest.lower():
                return f"committed {rest.lower()}"
            return f"committed the {rest.lower()} feature"
    for prefix in ("update:", "updated:", "update ", "updated "):
        if lower.startswith(prefix):
            rest = message[len(prefix) :].strip()
            return f"committed {rest.lower()} updates"
    return f'committed "{message}"'


def describe_event(
    event_type: str,
    title: str = "",
    description: str = "",
    metadata: dict | None = None,
) -> str:
    """One-sentence human description from event metadata only."""
    meta = metadata or {}
    file_path = str(meta.get("file") or "")
    branch = str(meta.get("branch") or "")
    et = event_type or ""

    if et == EventType.FILE_MODIFIED.value and file_path:
        return f"Modified {friendly_file(file_path)} to continue ProjectPulse development."
    if et == EventType.FILE_CREATED.value and file_path:
        return f"Created {friendly_file(file_path)}."
    if et == EventType.FILE_OPENED.value and file_path:
        return f"Opened {friendly_file(file_path)}."
    if et == EventType.GIT_COMMIT.value:
        msg = _commit_message(meta, description, title)
        clause = _commit_clause(msg)
        return clause[0].upper() + clause[1:] + "."
    if et == EventType.GIT_BRANCH_CHANGED.value:
        return f"Switched to branch {branch}." if branch else "Changed Git branch."
    if et == EventType.GIT_BRANCH_CREATED.value:
        return f"Created branch {branch}." if branch else "Created a Git branch."
    if et == EventType.GIT_PUSH.value:
        return f"Pushed branch {branch}." if branch else "Pushed local Git changes."
    if et == EventType.GIT_PULL.value:
        return f"Pulled changes on {branch}." if branch else "Pulled remote Git changes."
    if et == EventType.BUILD_FAILED.value:
        return "A project build failed."
    if et == EventType.BUILD_SUCCEEDED.value:
        return "A project build succeeded."
    if et == EventType.PROJECT_SESSION_STARTED.value:
        return "Started a ProjectPulse monitoring session."
    if et == EventType.PROJECT_OPENED.value:
        return "Opened the configured project folder."
    if et == EventType.PROJECT_SESSION_ENDED.value:
        return "Ended the monitoring session."
    return title or "Project activity recorded."


def _event_meta(event) -> dict:
    meta = getattr(event, "metadata", None)
    return meta if isinstance(meta, dict) else {}


def _unique_files(events: list, event_types: set[str]) -> list[str]:
    seen: list[str] = []
    for event in events:
        if getattr(event, "event_type", None) not in event_types:
            continue
        path = str(_event_meta(event).get("file") or "")
        if path and path not in seen:
            seen.append(path)
    return seen


def _top_modules_from_files(files: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for path in files:
        module = _module_name(path)
        if not module:
            continue
        counts[module] = counts.get(module, 0) + 1
    return sorted(counts, key=counts.get, reverse=True)


def what_you_did(events: list, activity) -> list[str]:
    """Bullet list for the Developer Summary 'What you did' section."""
    if not events:
        return ["No project activity recorded today."]

    bullets: list[str] = []
    modified = _unique_files(events, {EventType.FILE_MODIFIED.value})
    created = _unique_files(events, {EventType.FILE_CREATED.value})
    all_files = _unique_files(
        events,
        {
            EventType.FILE_MODIFIED.value,
            EventType.FILE_CREATED.value,
            EventType.FILE_OPENED.value,
        },
    )
    modules = _top_modules_from_files(all_files or modified or created)

    if modules:
        phrases = []
        for module in modules[:2]:
            key = module.lower()
            if key in ("agent", "backend", "frontend"):
                phrases.append(f"the {key} module")
            else:
                phrases.append(FRIENDLY_MODULES.get(key, f"the {module} module"))
        if len(phrases) == 1:
            bullets.append(f"Worked mainly on {phrases[0]}.")
        else:
            bullets.append(f"Worked mainly on {phrases[0]} and {phrases[1]}.")

    for path in modified[:4]:
        bullets.append(f"Modified {friendly_file(path)}.")

    created_count = getattr(activity, "files_created", 0) or len(created)
    if created_count:
        bullets.append(
            f"Created {created_count} new project file{'s' if created_count != 1 else ''}."
        )

    commit_count = getattr(activity, "commits", 0)
    if commit_count:
        bullets.append(
            f"Made {commit_count} Git commit{'s' if commit_count != 1 else ''}."
        )

    branch_count = getattr(activity, "branch_changes", 0)
    if branch_count:
        bullets.append(
            f"Made {branch_count} branch change{'s' if branch_count != 1 else ''}."
        )

    # Deduplicate while preserving order
    unique: list[str] = []
    for item in bullets:
        if item not in unique:
            unique.append(item)
    return unique or ["Development activity recorded today."]


def narrative_summary(events: list, activity) -> str:
    """Paragraph used by dashboard and tray popup."""
    if not events:
        return "No project activity recorded today. Start coding in your configured project folder."

    modified = _unique_files(events, {EventType.FILE_MODIFIED.value})
    created = _unique_files(events, {EventType.FILE_CREATED.value})
    all_files = modified or created or _unique_files(
        events, {EventType.FILE_OPENED.value, EventType.FILE_MODIFIED.value}
    )
    modules = _top_modules_from_files(all_files)

    commit_events = [e for e in events if getattr(e, "event_type", None) == EventType.GIT_COMMIT.value]
    commit_msg = ""
    if commit_events:
        latest = commit_events[0]
        commit_msg = _commit_message(
            _event_meta(latest),
            getattr(latest, "description", ""),
            getattr(latest, "title", ""),
        )

    parts: list[str] = []

    if len(modules) >= 2:
        labels = [FRIENDLY_MODULES.get(m.lower(), f"the {m}") for m in modules[:2]]
        parts.append(f"Worked mainly on {labels[0]} and {labels[1]} modules today.")
    elif modules:
        module = modules[0].lower()
        file_names = {_file_name(p) for p in all_files if _module_name(p).lower() == module}
        if module == "agent" and "tray_app.py" in file_names:
            focus = "the background tray agent"
        elif module == "backend" and {"api.py", "database.py"} & file_names:
            focus = "the backend API and database components"
        else:
            focus = FRIENDLY_MODULES.get(module, f"the {module} module")
        if commit_msg:
            parts.append(f"Worked on {focus} and {_commit_clause(commit_msg)}.")
        else:
            parts.append(f"Worked mainly on {focus} today.")
    elif commit_msg:
        clause = _commit_clause(commit_msg)
        parts.append(clause[0].upper() + clause[1:] + ".")

    file_changes = getattr(activity, "file_modifications", 0) + getattr(activity, "files_created", 0)
    if file_changes and not parts:
        parts.append(
            f"You modified or created {file_changes} project file{'s' if file_changes != 1 else ''}."
        )

    if getattr(activity, "commits", 0) and commit_msg and not any("commit" in p.lower() for p in parts):
        parts.append(_commit_clause(commit_msg)[0].upper() + _commit_clause(commit_msg)[1:] + ".")

    return " ".join(parts) if parts else "Development activity recorded today."


def recent_activity_title(event_type: str, title: str, metadata: dict | None, description: str = "") -> str:
    """Compact recent-activity line (file path or git commit message)."""
    meta = metadata or {}
    file_path = str(meta.get("file") or "")
    et = event_type or ""
    if et == EventType.FILE_MODIFIED.value and file_path:
        return f"Modified {file_path}"
    if et == EventType.FILE_CREATED.value and file_path:
        return f"Created {file_path}"
    if et == EventType.FILE_OPENED.value and file_path:
        return f"Opened {file_path}"
    if et == EventType.GIT_COMMIT.value:
        msg = _commit_message(meta, description, title)
        if msg:
            return f'Git commit:\n"{msg}"'
        return "Git commit"
    return title or et
