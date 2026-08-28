"""Windows system tray application."""

import logging
import threading
import tkinter as tk
import webbrowser

from PIL import Image, ImageDraw
import pystray

from agent.backend_client import BackendClient
from agent.collectors import CollectorManager
from agent.config import AgentConfig
from agent.summary_popup import DeveloperSummaryPopup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _create_icon_image() -> Image.Image:
    """Simple blue pulse icon for the system tray."""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=(37, 99, 235, 255))
    draw.ellipse((22, 22, 42, 42), fill=(255, 255, 255, 255))
    return image


class TrayApp:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.backend = BackendClient(config)
        self.collectors = CollectorManager(config, self.backend)
        self._icon: pystray.Icon | None = None
        self._root: tk.Tk | None = None
        self._popup: DeveloperSummaryPopup | None = None

    @property
    def monitoring_menu_label(self) -> str:
        if not self.config.monitoring_active:
            return "● Monitoring: OFF"
        return "● Monitoring: ON"

    def _developer_dashboard_url(self) -> str:
        base = self.config.frontend_url.rstrip("/")
        params = (
            f"project_id={self.config.project_id}"
            f"&user_id={self.config.user_id}"
        )
        return f"{base}/developer?{params}"

    def _manager_dashboard_url(self) -> str:
        base = self.config.frontend_url.rstrip("/")
        return f"{base}/manager?project_id={self.config.project_id}"

    def _show_popup(self) -> None:
        if self._root and self._popup:
            self._root.after(0, self._popup.show)

    def _on_view_summary(self, _icon=None, _item=None):
        self._show_popup()

    def _on_open_dashboard(self):
        if not self.config.project_id or not self.config.user_id:
            return
        webbrowser.open(self._developer_dashboard_url())

    def _on_view_manager_dashboard(self, _icon=None, _item=None):
        if not self.config.project_id:
            return
        webbrowser.open(self._manager_dashboard_url())

    def set_monitoring(self, active: bool) -> None:
        if self.config.monitoring_active == active:
            return
        self.config.monitoring_active = active
        self.config.save()
        self.backend.set_monitoring_status(active)
        if active:
            self.collectors.restart()
        else:
            self.collectors.stop()
        self._refresh_menu()
        if self._root and self._popup:
            self._root.after(0, self._popup.refresh)

    def _on_pause_monitoring(self, _icon=None, _item=None):
        self.set_monitoring(False)

    def _on_resume_monitoring(self, _icon=None, _item=None):
        self.set_monitoring(True)

    def _on_toggle_monitoring(self):
        self.set_monitoring(not self.config.monitoring_active)

    def _on_settings(self, _icon, _item):
        import subprocess
        from pathlib import Path

        config_path = Path(__file__).resolve().parent / "config" / "agent_config.json"
        subprocess.Popen(["notepad.exe", str(config_path)])

    def _on_exit(self, _icon, _item):
        self.collectors.stop()
        if self._popup:
            if self._root:
                self._root.after(0, self._popup.destroy)
        if self._icon:
            self._icon.stop()
        if self._root:
            self._root.after(200, self._root.destroy)

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("ProjectPulse AI", None, enabled=False),
            pystray.MenuItem(lambda _: self.monitoring_menu_label, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Developer Summary", self._on_view_summary, default=True),
            pystray.MenuItem("Project Manager Dashboard", self._on_view_manager_dashboard),
            pystray.MenuItem(
                "Pause Monitoring",
                self._on_pause_monitoring,
                enabled=lambda _: self.config.monitoring_active,
            ),
            pystray.MenuItem(
                "Resume Monitoring",
                self._on_resume_monitoring,
                enabled=lambda _: not self.config.monitoring_active,
            ),
            pystray.MenuItem("Settings", self._on_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_exit),
        )

    def _refresh_menu(self):
        if self._icon:
            self._icon.menu = self._build_menu()

    def _setup_backend(self, on_ready=None):
        def _register():
            if self.backend.health_check():
                try:
                    if self.backend.ensure_registered():
                        logger.info("Backend registration complete")
                        self.backend.set_monitoring_status(self.config.monitoring_active)
                        if on_ready:
                            on_ready()
                except Exception as exc:
                    logger.warning("Registration error: %s", exc)
            else:
                logger.warning("Backend not reachable at %s", self.config.backend_url)

        threading.Thread(target=_register, daemon=True).start()

    def run(self):
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.title("ProjectPulse AI")
        self._popup = DeveloperSummaryPopup(
            self._root,
            self.config,
            self.backend,
            on_open_dashboard=self._on_open_dashboard,
            on_toggle_monitoring=self._on_toggle_monitoring,
        )

        def _start_collectors():
            self.collectors.start()
            self._refresh_menu()

        self._setup_backend(on_ready=_start_collectors)

        self._icon = pystray.Icon(
            "ProjectPulse AI",
            _create_icon_image(),
            "ProjectPulse AI",
            menu=self._build_menu(),
        )

        threading.Thread(target=self._icon.run, daemon=True).start()
        logger.info("Tray icon started — left-click opens the compact developer summary")
        self._root.mainloop()
