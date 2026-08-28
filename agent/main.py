"""ProjectPulse AI — Windows background agent entry point."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.config import AgentConfig
from agent.tray_app import TrayApp


def main():
    config = AgentConfig.load()
    app = TrayApp(config)
    app.run()


if __name__ == "__main__":
    main()
# Live tracking test