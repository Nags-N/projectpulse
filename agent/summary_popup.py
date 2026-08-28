"""Compact developer summary popup near the Windows system tray."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable

from shared.timeutil import format_display_time

if TYPE_CHECKING:
    from agent.config import AgentConfig
    from agent.backend_client import BackendClient

logger = logging.getLogger(__name__)

POPUP_WIDTH = 340
POPUP_HEIGHT = 460


def _work_area() -> tuple[int, int, int, int]:
    """Windows working area (excludes taskbar). Fallback to screen size."""
    try:
        import ctypes
        from ctypes import wintypes

        SPI_GETWORKAREA = 0x0030
        rect = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
        return rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        return 0, 0, 1280, 720


class DeveloperSummaryPopup:
    def __init__(
        self,
        root: tk.Tk,
        config: "AgentConfig",
        backend: "BackendClient",
        on_open_dashboard: Callable[[], None],
        on_toggle_monitoring: Callable[[], None],
    ):
        self.root = root
        self.config = config
        self.backend = backend
        self.on_open_dashboard = on_open_dashboard
        self.on_toggle_monitoring = on_toggle_monitoring
        self._window: tk.Toplevel | None = None
        self._poll_job: str | None = None
        self._latest_label: tk.StringVar | None = None
        self._summary_label: tk.StringVar | None = None
        self._status_label: tk.StringVar | None = None
        self._counts: dict[str, tk.StringVar] = {}
        self._pause_btn: ttk.Button | None = None

    def show(self) -> None:
        if self._window and self._window.winfo_exists():
            self._position(self._window)
            self._window.deiconify()
            self._window.lift()
            self._window.focus_force()
            self.refresh()
            return
        self._build()
        self.refresh()
        self._schedule_poll()

    def hide(self) -> None:
        if self._poll_job:
            try:
                self.root.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        if self._window and self._window.winfo_exists():
            self._window.withdraw()

    def destroy(self) -> None:
        self.hide()
        if self._window and self._window.winfo_exists():
            self._window.destroy()
        self._window = None

    def _position(self, window: tk.Toplevel) -> None:
        left, top, right, bottom = _work_area()
        x = max(left + 8, right - POPUP_WIDTH - 12)
        y = max(top + 8, bottom - POPUP_HEIGHT - 12)
        window.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}+{x}+{y}")

    def _build(self) -> None:
        win = tk.Toplevel(self.root)
        self._window = win
        win.title("ProjectPulse AI")
        win.resizable(False, False)
        win.configure(bg="#f8fafc")
        win.protocol("WM_DELETE_WINDOW", self.hide)
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass
        self._position(win)

        header = tk.Frame(win, bg="#1e293b", height=42)
        header.pack(fill="x")
        tk.Label(
            header,
            text="ProjectPulse AI",
            bg="#1e293b",
            fg="#f8fafc",
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=10)

        body = tk.Frame(win, bg="#f8fafc", padx=14, pady=10)
        body.pack(fill="both", expand=True)

        self._status_label = tk.StringVar(value="Monitoring: ● …")
        tk.Label(
            body,
            textvariable=self._status_label,
            bg="#f8fafc",
            fg="#166534",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        tk.Label(
            body,
            text="Today's Activity",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        stats = tk.Frame(body, bg="#f8fafc")
        stats.pack(fill="x", pady=(4, 12))
        for key, label in (
            ("file_modifications", "Files Modified"),
            ("files_created", "Files Created"),
            ("commits", "Git Commits"),
        ):
            row = tk.Frame(stats, bg="#f8fafc")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, bg="#f8fafc", fg="#475569", font=("Segoe UI", 9), anchor="w").pack(side="left")
            var = tk.StringVar(value="0")
            self._counts[key] = var
            tk.Label(row, textvariable=var, bg="#f8fafc", fg="#0f172a", font=("Segoe UI", 9, "bold"), anchor="e").pack(side="right")

        tk.Label(
            body,
            text="Latest Activity",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")
        self._latest_label = tk.StringVar(value="No activity yet")
        tk.Label(
            body,
            textvariable=self._latest_label,
            bg="#f8fafc",
            fg="#334155",
            font=("Segoe UI", 9),
            wraplength=300,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(2, 10))

        tk.Label(
            body,
            text="Summary",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")
        self._summary_label = tk.StringVar(value="Waiting for developer activity.")
        tk.Label(
            body,
            textvariable=self._summary_label,
            bg="#f8fafc",
            fg="#334155",
            font=("Segoe UI", 9),
            wraplength=300,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(2, 12))

        buttons = tk.Frame(body, bg="#f8fafc")
        buttons.pack(fill="x", side="bottom")
        ttk.Button(buttons, text="Open Dashboard", command=self.on_open_dashboard).pack(fill="x", pady=3)
        self._pause_btn = ttk.Button(buttons, text="Pause Monitoring", command=self._on_toggle)
        self._pause_btn.pack(fill="x", pady=3)

    def _on_toggle(self) -> None:
        self.on_toggle_monitoring()
        self.root.after(300, self.refresh)

    def _schedule_poll(self) -> None:
        if self._poll_job:
            try:
                self.root.after_cancel(self._poll_job)
            except Exception:
                pass
        self._poll_job = self.root.after(5000, self._poll)

    def _poll(self) -> None:
        if self._window and self._window.winfo_exists() and self._window.state() != "withdrawn":
            self.refresh()
            self._schedule_poll()
        else:
            self._poll_job = None

    def refresh(self) -> None:
        if not self._window or not self._window.winfo_exists():
            return
        data = self.backend.get_developer_summary()
        active = self.config.monitoring_active
        if data:
            active = bool(data.get("monitoring_active", active))
            activity = data.get("activity") or {}
            for key, var in self._counts.items():
                var.set(str(activity.get(key, 0)))
            events = data.get("recent_events") or []
            if events:
                latest = events[0]
                title = (latest.get("display_title") or latest.get("title") or "Activity").replace("\n", " ")
                when = format_display_time(latest.get("timestamp"), include_date=False) if latest.get("timestamp") else ""
                self._latest_label.set(f"{title}\n{when}".strip())
            else:
                self._latest_label.set("No activity yet")
            self._summary_label.set(data.get("narrative_summary") or "No summary yet.")
        else:
            self._summary_label.set("Could not load summary. Is the backend running?")

        if active:
            self._status_label.set("Monitoring: ● ACTIVE")
            if self._pause_btn:
                self._pause_btn.configure(text="Pause Monitoring")
        else:
            self._status_label.set("Monitoring: ○ PAUSED")
            if self._pause_btn:
                self._pause_btn.configure(text="Resume Monitoring")
