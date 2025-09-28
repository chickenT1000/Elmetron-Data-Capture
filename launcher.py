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
from typing import Optional

import tkinter as tk
from tkinter import filedialog
from tkinter import font as tkfont


ROOT = Path(__file__).resolve().parent
CAPTURES_DIR = ROOT / "captures"
CAPTURE_LOG = CAPTURES_DIR / "live_ui_dev.log"
CAPTURE_ERR = CAPTURES_DIR / "live_ui_dev.err.log"
UI_LOG = CAPTURES_DIR / "live_ui_dev_ui.log"
UI_ERR = CAPTURES_DIR / "live_ui_dev_ui.err.log"

HEALTH_URL = "http://127.0.0.1:8050/health"
UI_URL = "http://127.0.0.1:5173/"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

BG = "#FFFFFF"
COLORS = {
    "pending": "#5A5F63",
    "active": "#1C1E21",
    "success": "#7B8388",
    "error": "#B22222",
}

STATUS_FONT = ("Segoe UI", 22)
FOOTER_FONT = ("Segoe UI", 10)
LOGO_LINE_COLOR = "#C7CED3"
LOGO_MAIN_COLOR = "#1C1E21"
LOGO_SUB_COLOR = "#5A5F63"


class LauncherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Elmetron Launcher")
        self.root.geometry("640x400")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self._log_buffer: list[str] = []
        self._processes: dict[str, subprocess.Popen] = {}
        self._log_files: list = []
        self._npm_path: Optional[str] = None
        self._ellipsis_job: Optional[str] = None
        self._ellipsis_phase = 0
        self._ellipsis_base = ""
        self._auto_close_job: Optional[str] = None
        self._closing = False
        self._failed = False

        self._build_ui()

        worker = threading.Thread(target=self._launch_sequence, daemon=True)
        worker.start()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=32, pady=24)

        self.logo_canvas = tk.Canvas(container, width=540, height=150, bg=BG, highlightthickness=0)
        self.logo_canvas.pack(pady=(0, 12))
        self._draw_logo()

        self.status_var = tk.StringVar(value="Preparing launch…")
        self.status_label = tk.Label(
            container,
            textvariable=self.status_var,
            font=STATUS_FONT,
            bg=BG,
            fg=COLORS["pending"],
            wraplength=520,
            justify="center",
        )
        self.status_label.pack(pady=(12, 6))

        self.footer_label = tk.Label(
            container,
            text="Window will close automatically when services are online.",
            font=FOOTER_FONT,
            bg=BG,
            fg="#8D949A",
        )
        self.footer_label.pack(pady=(6, 0))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _draw_logo(self) -> None:
        canvas = self.logo_canvas
        canvas.delete("all")
        width = int(canvas["width"])

        main_font = tkfont.Font(family="Copperplate Gothic Bold", size=28)
        sub_font = tkfont.Font(family="Copperplate Gothic Bold", size=16)
        tracking_px = max(4, int(main_font.measure("M") * 0.08))  # 8% tracking
        chars = list("ELMETRON")
        total_width = sum(main_font.measure(ch) for ch in chars) + tracking_px * (len(chars) - 1)
        start_x = (width - total_width) / 2
        top_y = 86

        t_bbox = None
        for ch in chars:
            item = canvas.create_text(start_x, top_y, text=ch, font=main_font, fill=LOGO_MAIN_COLOR, anchor="nw")
            if ch == "T":
                t_bbox = canvas.bbox(item)
            start_x += main_font.measure(ch) + tracking_px

        line_y = top_y - 18
        margin = width * 0.12
        canvas.create_line(margin, line_y, width - margin, line_y, fill=LOGO_LINE_COLOR, width=2)

        if t_bbox:
            x1, y1, x2, _ = t_bbox
            stem_width = max(3, int(main_font.measure("I") * 0.25))
            cx = (x1 + x2) / 2
            canvas.create_rectangle(cx - stem_width / 2, line_y, cx + stem_width / 2, y1 + 1, fill=LOGO_MAIN_COLOR, outline="")

        sub_y = top_y + main_font.metrics("linespace") + 12
        canvas.create_text(width / 2, sub_y, text="Data Capture", font=sub_font, fill=LOGO_SUB_COLOR, anchor="n")

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self._log_buffer.append(entry)

    def _set_status(self, text: str, state: str = "pending", animate: bool = False) -> None:
        color = COLORS.get(state, COLORS["pending"])
        self._stop_ellipsis()
        if animate:
            self._start_ellipsis(text, color)
        else:
            self.status_var.set(text)
            self.status_label.configure(fg=color)

    def _start_ellipsis(self, base_text: str, color: str) -> None:
        self._ellipsis_base = base_text
        self.status_label.configure(fg=color)
        self._ellipsis_phase = 0
        self._tick_ellipsis()

    def _tick_ellipsis(self) -> None:
        display = f"{self._ellipsis_base}{'.' * self._ellipsis_phase}"
        self.status_var.set(display)
        self._ellipsis_phase = (self._ellipsis_phase + 1) % 4
        self._ellipsis_job = self.root.after(350, self._tick_ellipsis)

    def _stop_ellipsis(self) -> None:
        if self._ellipsis_job is not None:
            self.root.after_cancel(self._ellipsis_job)
            self._ellipsis_job = None

    def _launch_sequence(self) -> None:
        try:
            self._set_status("Checking prerequisites", "active", animate=True)
            self._prepare_environment()

            self._set_status("Starting capture service", "active", animate=True)
            self._start_capture_service()
            if not self._wait_for_url(HEALTH_URL, 40, self._processes.get("capture"), "capture service"):
                self._fail("Capture service did not respond at /health.")
                return
            self.log("Capture service online")

            self._set_status("Starting dashboard server", "active", animate=True)
            self._start_ui_server()
            if not self._wait_for_url(UI_URL, 40, self._processes.get("ui"), "UI dev server"):
                self._fail("UI server did not respond at 127.0.0.1:5173.")
                return
            self.log("Service Health UI online")

            self._set_status("Opening dashboard", "active", animate=True)
            self._open_browser()

            self._stop_ellipsis()
            self._set_status("All systems online.", "success", animate=False)
            self.log("All services online")
            self._schedule_auto_close()
        except Exception as exc:  # pragma: no cover
            self._fail(f"Launcher error: {exc}")

    def _prepare_environment(self) -> None:
        self.log("Checking prerequisites")
        self._npm_path = shutil.which("npm")
        if self._npm_path is None:
            raise RuntimeError("npm is not available on PATH.")
        self.log(f"npm resolved to {self._npm_path}")
        CAPTURES_DIR.mkdir(exist_ok=True)
        self.log("Environment ready")

    def _start_capture_service(self) -> None:
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
        self.log("Capture service launched, waiting for /health")

    def _start_ui_server(self) -> None:
        self.log("Preparing UI dashboard")
        if not self._npm_path:
            raise RuntimeError("npm path unavailable after prerequisite check.")
        ui_dir = ROOT / "ui"
        node_modules = ui_dir / "node_modules"
        if not node_modules.exists():
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
        self.log("UI dev server launching")

    def _open_browser(self) -> None:
        self.log("Opening dashboard in default browser")
        webbrowser.open(UI_URL)
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

    def _schedule_auto_close(self) -> None:
        self._auto_close_job = self.root.after(1500, self._close_success)

    def _close_success(self) -> None:
        if self._closing or self._failed:
            return
        self._closing = True
        self._stop_ellipsis()
        self.log("Launcher closing after successful start")
        self._cleanup()
        self.root.destroy()

    def _fail(self, message: str) -> None:
        if self._auto_close_job is not None:
            self.root.after_cancel(self._auto_close_job)
            self._auto_close_job = None
        self._failed = True
        self._stop_ellipsis()
        self._set_status(message, "error", animate=False)
        self.log(f"ERROR: {message}")
        self.root.after(0, lambda: ErrorDialog(self.root, self._log_buffer))

    def _on_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self._auto_close_job is not None:
            self.root.after_cancel(self._auto_close_job)
            self._auto_close_job = None
        self._stop_ellipsis()
        self.log("Launcher window closed by user")
        self._cleanup()
        self.root.destroy()

    def _cleanup(self) -> None:
        for handle in self._log_files:
            try:
                handle.close()
            except Exception:
                pass
        self._log_files.clear()

    def run(self) -> None:
        self.root.mainloop()


class ErrorDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, log_entries: list[str]) -> None:
        super().__init__(parent)
        self.title("Launch Error")
        self.configure(bg=BG)
        self.geometry("660x380")
        self.minsize(520, 320)
        self.transient(parent)
        self.grab_set()

        heading = tk.Label(
            self,
            text="Launch encountered an error",
            font=("Segoe UI", 16, "bold"),
            bg=BG,
            fg=COLORS["error"],
        )
        heading.pack(pady=(18, 6))

        sub = tk.Label(
            self,
            text="Details are available below. You can copy or save the log for support.",
            font=("Segoe UI", 10),
            bg=BG,
            fg="#5A5F63",
        )
        sub.pack(pady=(0, 12))

        text_frame = tk.Frame(self, bg=BG)
        text_frame.pack(fill="both", expand=True, padx=18)

        text_widget = tk.Text(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#F5F6F7",
            fg="#1C1E21",
            relief="flat",
        )
        text_widget.pack(fill="both", expand=True)

        log_text = "\n".join(log_entries) if log_entries else "No log output captured."
        text_widget.insert("1.0", log_text)
        text_widget.configure(state="disabled")

        button_row = tk.Frame(self, bg=BG)
        button_row.pack(pady=16)

        copy_btn = tk.Button(button_row, text="Copy Log", command=lambda: self._copy_to_clipboard(log_text))
        copy_btn.pack(side="left", padx=6)

        save_btn = tk.Button(button_row, text="Save…", command=lambda: self._save_log(log_text))
        save_btn.pack(side="left", padx=6)

        close_btn = tk.Button(button_row, text="Close", command=self.destroy)
        close_btn.pack(side="left", padx=6)

    def _copy_to_clipboard(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)

    def _save_log(self, text: str) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".log",
            filetypes=[("Log Files", "*.log"), ("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError:
            pass


def main() -> None:
    app = LauncherApp()
    app.run()


if __name__ == "__main__":
    main()


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
