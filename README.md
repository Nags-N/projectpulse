# ProjectPulse AI

An AI-Powered Project Intelligence and Workflow Monitoring System.

**Phase 1 — Milestone 3:** Git activity collector for commits, branches, pull, and push (project repo only).

## Architecture

```
Developer Laptop
       ↓
Background Agent (Windows tray)
       ↓
Privacy Filter (allowlist)
       ↓
Event Normalizer
       ↓
FastAPI Backend
       ↓
SQLite Database
```

## Project Structure

```
├── agent/                  # Windows background agent
│   ├── main.py             # Agent entry point
│   ├── tray_app.py         # System tray UI
│   ├── config.py           # Allowlist configuration
│   ├── backend_client.py   # API client
│   ├── normalizer.py       # Event normalizer
│   ├── privacy_filter.py   # Privacy allowlist filter
│   ├── event_queue.py      # Buffers events until backend ready
│   ├── collectors/
│   │   ├── base.py         # Base collector interface
│   │   ├── file_watcher.py # VS Code file activity watcher
│   │   ├── git_watcher.py  # Git activity collector
│   │   └── git_parser.py   # Git reflog parser
│   └── config/
│       └── agent_config.json
├── backend/                # FastAPI backend
│   ├── main.py             # API entry point
│   ├── database.py         # SQLite setup
│   ├── models/             # ORM + Pydantic schemas
│   ├── routers/            # API routes
│   └── services/           # Business logic
├── shared/
│   └── events.py           # Common ProjectEvent schema
└── requirements.txt
```

## Setup

```powershell
cd "e:\projects\major project 7th"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Backend

```powershell
cd "e:\projects\major project 7th"
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

## Run Agent (Windows Tray)

```powershell
cd "e:\projects\major project 7th"
.\.venv\Scripts\Activate.ps1
python -m agent.main
```

Look for the blue pulse icon in the Windows system tray.

## Configure Project (Allowlist)

Edit `agent/config/agent_config.json`:

```json
{
  "project_name": "Food Delivery Application",
  "project_folder": "C:/Projects/FoodDelivery",
  "backend_url": "http://127.0.0.1:8000",
  "monitoring_active": true
}
```

The agent monitors **only** the configured folder. No desktop-wide monitoring.

## Milestone 2 — File Watcher

The agent now watches your configured project folder and emits:

| Event | Trigger |
|-------|---------|
| `PROJECT_SESSION_STARTED` | Agent starts monitoring |
| `PROJECT_OPENED` | Project folder opened for monitoring |
| `FILE_OPENED` | New file first seen in session |
| `FILE_MODIFIED` | File saved/changed (2s debounce) |
| `PROJECT_SESSION_ENDED` | Agent stops or exits |

**Privacy safeguards:**
- Only paths inside `project_folder` are watched
- Ignores `.git`, `node_modules`, `__pycache__`, `.venv`, build artifacts
- Never reads or sends file contents — path + file type only

**Test Milestone 2** (backend must be running):

```powershell
.\.venv\Scripts\python.exe scripts\test_milestone2.py
```

## Milestone 3 — Git Activity

Monitors **only** the `.git` folder inside your configured project:

| Event | Trigger |
|-------|---------|
| `GIT_COMMIT` | New commit in project repo |
| `GIT_BRANCH_CREATED` | New branch ref created |
| `GIT_BRANCH_CHANGED` | Checkout / branch switch |
| `GIT_PULL` | Fetch/pull updates (`FETCH_HEAD`) |
| `GIT_PUSH` | Push via project-local pre-push hook |

Example event:

```json
{
  "event_type": "GIT_COMMIT",
  "source": "GIT",
  "title": "Commit on feature/payment",
  "metadata": {
    "branch": "feature/payment",
    "commit_hash": "abc123...",
    "project": "Food Delivery Application"
  }
}
```

**Privacy safeguards:**
- Only the configured project's `.git` directory is watched
- No access to other repos or global Git config
- No source code or commit diffs collected — hash + branch only
- Pre-push hook is project-local; existing hooks are preserved (chained)

**Test Milestone 3** (backend must be running, Git required):

```powershell
.\.venv\Scripts\python.exe scripts\test_milestone3.py
```

**Manual test:**

```powershell
# Terminal 1 — backend
.\scripts\run_backend.ps1

# Terminal 2 — agent
.\scripts\run_agent.ps1

# Terminal 3 — git activity in your configured project folder
cd "E:\projects\major project 7th"
git init
git add .
git commit -m "Test commit"
git checkout -b feature/test-branch
git commit --allow-empty -m "Branch commit"
```

Then open http://127.0.0.1:8000/docs → `GET /api/events` to see Git events.

## API Endpoints (Milestone 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/users` | Register user |
| POST | `/api/projects` | Register project |
| POST | `/api/events` | Ingest normalized event |
| GET | `/api/events` | List events |
| GET | `/api/projects/{id}/events` | Project events |
| GET | `/api/projects/{id}/summary` | Developer summary |
| GET | `/api/projects/{id}/dashboard` | Manager dashboard |

## Privacy

- Allowlist-only project folder monitoring
- No screenshots, keystrokes, clipboard, or desktop monitoring
- No file contents — metadata only
- Pause monitoring anytime from the tray menu

## Next Milestones

- ~~**M2:** VS Code file watcher collector~~ ✅
- ~~**M3:** Git activity collector~~ ✅
- **M4:** Build/terminal activity detection
- **M5:** Developer summary UI window
- **M6:** Project Manager dashboard UI
