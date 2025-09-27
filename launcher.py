"""Graphical launcher for CX-505 capture service and UI dashboard."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Dict, Optional

import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox


ROOT = Path(__file__).resolve().parent
CAPTURES_DIR = ROOT / "captures"
CAPTURE_LOG = CAPTURES_DIR / "live_ui_dev.log"
CAPTURE_ERR = CAPTURES_DIR / "live_ui_dev.err.log"
UI_LOG = CAPTURES_DIR / "live_ui_dev_ui.log"
UI_ERR = CAPTURES_DIR / "live_ui_dev_ui.err.log"

HEALTH_URL = "http://127.0.0.1:8050/health"
UI_URL = "http://127.0.0.1:5173/"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class StatusLabel:
    def __init__(self, parent: tk.Widget, title: str, row: int) -> None:
        ttk.Label(parent, text=title, font=("Segoe UI", 11, "bold"), anchor="w").grid(
            row=row, column=0, sticky="we", pady=(4, 0), padx=(0, 12)
        )
        self._status_var = tk.StringVar(value="Pending")
        self._label = ttk.Label(parent, textvariable=self._status_var, font=("Segoe UI", 10), anchor="w")
        self._label.configure(width=34)
        self._label.grid(row=row, column=1, sticky="we", padx=12)

    def set(self, text: str, color: str) -> None:
        self._status_var.set(text)
        self._label.configure(foreground=color)


class LauncherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Elmetron Launch Monitor")
        self.root.geometry("640x420")
        self.root.resizable(False, False)

        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1, minsize=260)
        main.rowconfigure(8, weight=1)

        ttk.Label(main, text="Preparing CX-505 live session", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(main, text="This window keeps running checks until all services are online.").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.status_rows: Dict[str, StatusLabel] = {
            "prereq": StatusLabel(main, "Prerequisites", 2),
            "capture": StatusLabel(main, "Capture Service", 3),
            "ui": StatusLabel(main, "Service Health UI", 4),
            "browser": StatusLabel(main, "Dashboard", 5),
            "system": StatusLabel(main, "Overall Status", 6),
        }

        ttk.Label(main, text="Activity log", font=("Segoe UI", 11, "bold")).grid(row=7, column=0, columnspan=2, sticky="w", pady=(12, 4))

        self.log_box = scrolledtext.ScrolledText(
            main,
            width=70,
            height=10,
            font=("Consolas", 10),
            wrap="word",
            state="normal",
            takefocus=True,
        )
        self.log_box.grid(row=8, column=0, columnspan=2, sticky="nsew")
        self.log_box.bind("<Key>", self._on_log_key)
        self.log_box.bind("<Control-a>", self._select_all)
        self.log_box.bind("<Button-3>", self._show_context_menu)

        self._context_menu = tk.Menu(self.root, tearoff=0)
        self._context_menu.add_command(label="Copy", command=lambda: self.root.focus_get().event_generate("<<Copy>>"))
        self._context_menu.add_command(label="Select All", command=lambda: self._select_all(None))

        note = ttk.Label(
            main,
            text="You can copy the log text above. Closing this window does not stop the services (Ctrl+C in each terminal).",
            font=("Segoe UI", 9),
            wraplength=460,
        )
        note.grid(row=9, column=0, columnspan=2, sticky="w", pady=(12, 0))

        self.ok_button = ttk.Button(main, text="OK", command=self._on_close, state="disabled")
        self.ok_button.grid(row=10, column=0, columnspan=2, pady=(18, 0))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._processes: Dict[str, subprocess.Popen] = {}
        self._log_files = []
        self._npm_path: Optional[str] = None

        worker = threading.Thread(target=self._launch_sequence, daemon=True)
        worker.start()

    def _set_status(self, key: str, text: str, color: str) -> None:
        self.root.after(0, lambda: self.status_rows[key].set(text, color))

    def _append_log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_box.see(tk.END)

    def log(self, message: str) -> None:
        self.root.after(0, lambda: self._append_log(message))

    def _enable_ok(self) -> None:
        self.root.after(0, lambda: self.ok_button.configure(state="normal"))

    def _fail(self, message: str) -> None:
        self._set_status("system", message, "#b22222")
        self.log(f"ERROR: {message}")
        self._enable_ok()
        self.root.after(0, lambda: messagebox.showerror("Elmetron Launch Monitor", message))

    def _launch_sequence(self) -> None:
        try:
            self._prepare_environment()
            self._start_capture_service()
            if not self._wait_for_url(HEALTH_URL, 40, self._processes.get("capture"), "capture service"):
                self._fail("Capture service did not respond at /health.")
                return
            self._set_status("capture", "Capture service online", "#1d6d1f")
            self.log("Capture service online")

            self._start_ui_server()
            if not self._wait_for_url(UI_URL, 40, self._processes.get("ui"), "UI dev server"):
                self._fail("UI server did not respond at 127.0.0.1:5173.")
                return
            self._set_status("ui", "Service Health UI online", "#1d6d1f")
            self.log("Service Health UI online")

            self._open_browser()

            self._set_status("system", "All services online", "#1d6d1f")
            self.log("All services online")
            self._enable_ok()
        except Exception as exc:  # pragma: no cover
            self._fail(f"Launcher error: {exc}")

    def _prepare_environment(self) -> None:
        self._set_status("prereq", "Checking prerequisites...", "#c87d0a")
        self.log("Checking prerequisites")
        self._npm_path = shutil.which("npm")
        if self._npm_path is None:
            raise RuntimeError("npm is not available on PATH.")
        self.log(f"npm resolved to {self._npm_path}")
        CAPTURES_DIR.mkdir(exist_ok=True)
        self._set_status("prereq", "Environment ready", "#1d6d1f")
        self.log("Environment ready")

    def _start_capture_service(self) -> None:
        self._set_status("capture", "Starting capture service...", "#c87d0a")
        self.log("Starting capture service")
        log = CAPTURE_LOG.open("a", encoding="utf-8")
        err = CAPTURE_ERR.open("a", encoding="utf-8")
        self._log_files.extend([log, err])

        cmd = [
            sys.executable,
            str(ROOT / "cx505_capture_service.py"),
            "--config",
            str(ROOT / "config" / "app.toml"),
            "--protocols",
            str(ROOT / "config" / "protocols.toml"),
            "--health-api-port",
            "8050",
            "--watchdog-timeout",
            "30",
            "--health-log",
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=err,
                cwd=str(ROOT),
                creationflags=CREATE_NO_WINDOW,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"Failed to start capture service ({exc})") from exc
        self._processes["capture"] = process
        self._set_status("capture", "Waiting for telemetry...", "#c87d0a")
        self.log("Capture service launched, waiting for /health")

    def _start_ui_server(self) -> None:
        self._set_status("ui", "Preparing UI dashboard...", "#c87d0a")
        self.log("Preparing UI dashboard")
        if not self._npm_path:
            raise RuntimeError("npm path unavailable after prerequisite check.")
        ui_dir = ROOT / "ui"
        node_modules = ui_dir / "node_modules"
        if not node_modules.exists():
            self._set_status("ui", "Installing UI dependencies...", "#c87d0a")
            self.log("Installing UI dependencies (npm install)")
            result = subprocess.run(
                [self._npm_path, "install"],
                cwd=str(ui_dir),
                creationflags=CREATE_NO_WINDOW,
            )
            if result.returncode != 0:
                raise RuntimeError("npm install failed. See console for details.")
            self.log("UI dependencies installed")

        log = UI_LOG.open("a", encoding="utf-8")
        err = UI_ERR.open("a", encoding="utf-8")
        self._log_files.extend([log, err])

        env = os.environ.copy()
        env["VITE_API_BASE_URL"] = "http://127.0.0.1:8050"
        env.setdefault("VITE_HEALTH_BASE_URL", env["VITE_API_BASE_URL"])
        self.log(f"UI base URL set to {env['VITE_API_BASE_URL']}")

        cmd = [
            self._npm_path,
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            "5173",
            "--strictPort",
        ]

        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(ui_dir),
                env=env,
                stdout=log,
                stderr=err,
                creationflags=CREATE_NO_WINDOW,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"Failed to start UI server ({exc})") from exc
        self._processes["ui"] = process
        self._set_status("ui", "Starting UI dev server...", "#c87d0a")
        self.log("UI dev server launching")

    def _open_browser(self) -> None:
        self._set_status("browser", "Opening dashboard...", "#1d6d1f")
        self.log("Opening dashboard in default browser")
        webbrowser.open(UI_URL)
        self._set_status("browser", "Dashboard opened", "#1d6d1f")
        self.log("Dashboard opened")

    def _wait_for_url(
        self,
        url: str,
        attempts: int,
        process: Optional[subprocess.Popen],
        process_name: str,
    ) -> bool:
        for _ in range(attempts):
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if 200 <= response.getcode() < 300:
                        return True
            except urllib.error.URLError:
                pass
            if process is not None and process.poll() is not None:
                self.log(f"{process_name} exited with code {process.poll()}")
                return False
            self.log(f"Waiting for {url}")
            time.sleep(1)
        return False

    def _on_log_key(self, event: tk.Event) -> str | None:
        if event.state & 0x0004:  # Control key held
            if event.keysym.lower() in {"c", "insert"}:
                return None
            if event.keysym.lower() == "a":
                self._select_all(event)
                return "break"
        return "break"

    def _select_all(self, _event: tk.Event | None) -> str:
        self.log_box.tag_add("sel", "1.0", "end-1c")
        return "break"

    def _show_context_menu(self, event: tk.Event) -> None:
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _on_close(self) -> None:
        for handle in self._log_files:
            try:
                handle.close()
            except Exception:
                pass
        self.log("Launcher window closed")
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = LauncherApp()
    app.run()


if __name__ == "__main__":
    main()
