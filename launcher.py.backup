"""Graphical launcher for CX-505 capture service and UI dashboard."""

from __future__ import annotations

import enum
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Dict, IO, List, Optional

import tkinter as tk
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import ttk
import ctypes
import ctypes.wintypes as wintypes


ROOT = Path(__file__).resolve().parent
CAPTURES_DIR = ROOT / "captures"
LOCKFILE = CAPTURES_DIR / ".launcher.lock"
CAPTURE_LOG = CAPTURES_DIR / "live_ui_dev.log"
CAPTURE_ERR = CAPTURES_DIR / "live_ui_dev.err.log"
UI_LOG = CAPTURES_DIR / "live_ui_dev_ui.log"
UI_ERR = CAPTURES_DIR / "live_ui_dev_ui.err.log"

HEALTH_URL = "http://127.0.0.1:8050/health"
UI_URL = "http://127.0.0.1:5173/"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

STATUS_PALETTE = {
    "pending": "#5A5F63",
    "waiting": "#c87d0a",
    "success": "#1d6d1f",
    "error": "#B22222",
}

__all__ = ["LauncherApp", "LauncherState"]




def check_hardware_connected() -> HardwareStatus:
    """Check if Elmetron CX-505 hardware is connected via FTDI and if it's available."""
    try:
        # Try to load ftd2xx.dll
        ftd2xx = ctypes.WinDLL('ftd2xx.dll')
        
        # Define function signatures for device enumeration
        _ft_create_list = ftd2xx.FT_CreateDeviceInfoList
        _ft_create_list.argtypes = [ctypes.POINTER(ctypes.c_ulong)]
        _ft_create_list.restype = ctypes.c_ulong
        
        # Define FT_Open to test if device can be opened
        _ft_open = ftd2xx.FT_Open
        _ft_open.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.wintypes.HANDLE)]
        _ft_open.restype = ctypes.c_ulong
        
        # Define FT_Close to close test connection
        _ft_close = ftd2xx.FT_Close
        _ft_close.argtypes = [ctypes.wintypes.HANDLE]
        _ft_close.restype = ctypes.c_ulong
        
        # Call FT_CreateDeviceInfoList to get device count
        count = ctypes.c_ulong()
        status = _ft_create_list(ctypes.byref(count))
        
        # Check if enumeration succeeded and devices found
        if status != 0 or count.value == 0:
            return HardwareStatus.NOT_FOUND
        
        # Device(s) found - try to open first device to check availability
        handle = ctypes.wintypes.HANDLE()
        open_status = _ft_open(0, ctypes.byref(handle))  # Try to open device index 0
        
        if open_status == 0:
            # Successfully opened - device is available
            # Close immediately so we don't hold it
            _ft_close(handle)
            return HardwareStatus.AVAILABLE
        elif open_status in (3, 4):
            # FT_DEVICE_NOT_OPENED (3) or FT_IO_ERROR (4) = device busy/in use
            return HardwareStatus.IN_USE
        else:
            # Other error
            return HardwareStatus.UNKNOWN
            
    except (OSError, AttributeError) as e:
        # ftd2xx.dll not found or function failed
        return HardwareStatus.NOT_FOUND
    except Exception as e:
        # Unexpected error
        return HardwareStatus.UNKNOWN

class LauncherState(enum.Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"

class HardwareStatus(enum.Enum):
    """Hardware connection status."""
    NOT_FOUND = "not_found"
    AVAILABLE = "available"
    IN_USE = "in_use"
    UNKNOWN = "unknown"




class LauncherCommand(enum.Enum):
    START = "start"
    STOP = "stop"
    RESET = "reset"
    SHUTDOWN = "shutdown"


class StatusLabel:
    def __init__(self, parent: ttk.Frame, title: str, row: int) -> None:
        ttk.Label(parent, text=title, font=("Segoe UI", 11, "bold")).grid(
            row=row,
            column=0,
            sticky="w",
            pady=(0, 2),
        )
        self._value = tk.StringVar(value="Pending...")
        self._label = ttk.Label(parent, textvariable=self._value)
        self._label.grid(row=row, column=1, sticky="w")

    def set(self, text: str, color: str) -> None:
        self._value.set(text)
        self._label.configure(foreground=color)


class LauncherApp:
    def __init__(self, auto_start: bool = True) -> None:
        # Check for existing instance
        if not self._acquire_lock():
            messagebox.showerror(
                "Elmetron Launch Monitor",
                "Another instance of the launcher is already running.\n\n"
                "Please close the existing launcher window before starting a new one."
            )
            sys.exit(1)
        
        self.root = tk.Tk()
        self.root.title("Elmetron Launch Monitor")
        self.root.geometry("700x480")
        self.root.resizable(False, False)

        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        self._state = LauncherState.IDLE
        self._queue: queue.Queue[LauncherCommand] = queue.Queue()
        self._queue_lock = threading.Lock()
        self._queue_active = True
        self._processes: Dict[str, subprocess.Popen] = {}
        self._logs: Dict[str, tuple[IO[str], IO[str]]] = {}
        self._data_monitor_active = False
        self._data_monitor_thread: Optional[threading.Thread] = None
        self._log_history: List[str] = []
        self._npm_path: Optional[str] = None
        self._closing = False

        self._build_ui()
        self._update_controls()

        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

        if auto_start:
            self.start()


    def _acquire_lock(self) -> bool:
        """Try to acquire single-instance lock."""
        CAPTURES_DIR.mkdir(exist_ok=True)
        if LOCKFILE.exists():
            # Check if the PID in lockfile is still running
            try:
                with open(LOCKFILE, "r") as f:
                    old_pid = int(f.read().strip())
                
                # Try to check if process is still running on Windows
                import ctypes.wintypes as wintypes
                PROCESS_QUERY_INFORMATION = 0x0400
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, old_pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return False  # Process still running
                # Process not running, remove stale lock
                LOCKFILE.unlink()
            except (ValueError, FileNotFoundError, OSError):
                # Stale or invalid lockfile, remove it
                try:
                    LOCKFILE.unlink()
                except FileNotFoundError:
                    pass
        
        # Write current PID to lockfile
        try:
            with open(LOCKFILE, "w") as f:
                f.write(str(os.getpid()))
            return True
        except OSError:
            return False
    
    def _release_lock(self) -> None:
        """Release single-instance lock."""
        try:
            if LOCKFILE.exists():
                LOCKFILE.unlink()
        except OSError:
            pass

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(9, weight=1)

        ttk.Label(
            main,
            text="Preparing CX-505 live session",
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(
            main,
            text="Use the controls below to start, stop, or reset the capture service and dashboard.",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.status_rows: Dict[str, StatusLabel] = {
            "hardware": StatusLabel(main, "CX-505 Hardware", 2),
            "prereq": StatusLabel(main, "Prerequisites", 3),
            "capture": StatusLabel(main, "Capture Service", 4),
            "ui": StatusLabel(main, "Service Health UI", 5),
            "browser": StatusLabel(main, "Dashboard", 6),
            "system": StatusLabel(main, "Overall Status", 7),
        }

        button_row = ttk.Frame(main)
        button_row.grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 6))

        self.start_button = ttk.Button(button_row, text="Start", command=self.start)
        self.start_button.pack(side="left", padx=(0, 8))

        self.stop_button = ttk.Button(button_row, text="Stop", command=self.stop)
        self.stop_button.pack(side="left", padx=(0, 8))

        self.reset_button = ttk.Button(button_row, text="Reset", command=self.reset)
        self.reset_button.pack(side="left", padx=(0, 8))
        
        # Separator
        ttk.Separator(button_row, orient="vertical").pack(side="left", fill="y", padx=8)
        
        self.hw_refresh_button = ttk.Button(button_row, text="Refresh Hardware", command=self._refresh_hardware)
        self.hw_refresh_button.pack(side="left", padx=(0, 8))
        
        # Reopen Browser button
        self.reopen_browser_button = ttk.Button(button_row, text="Reopen Browser", command=self._reopen_browser)
        self.reopen_browser_button.pack(side="left", padx=(0, 8))

        ttk.Label(main, text="Activity log", font=("Segoe UI", 11, "bold")).grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(12, 4),
        )

        self.log_box = scrolledtext.ScrolledText(
            main,
            width=80,
            height=12,
            font=("Consolas", 10),
            wrap="word",
            state="normal",
            takefocus=True,
        )
        self.log_box.grid(row=10, column=0, columnspan=2, sticky="nsew")
        self.log_box.bind("<Key>", self._on_log_key)
        self.log_box.bind("<Control-a>", self._select_all)
        self.log_box.bind("<Button-3>", self._show_context_menu)

        self._context_menu = tk.Menu(self.root, tearoff=0)
        self._context_menu.add_command(label="Copy", command=lambda: self.root.focus_get().event_generate("<<Copy>>"))
        self._context_menu.add_command(label="Select All", command=lambda: self._select_all(None))

        ttk.Label(
            main,
            text="Closing this window will automatically stop all running services and release the CX-505 device.",
            font=("Segoe UI", 9),
        ).grid(row=11, column=0, columnspan=2, sticky="w", pady=(12, 10))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._set_initial_statuses()

    def start(self) -> None:
        self._enqueue(LauncherCommand.START, "start button")

    def stop(self) -> None:
        self._enqueue(LauncherCommand.STOP, "stop button")

    def reset(self) -> None:
        self._enqueue(LauncherCommand.RESET, "reset button")

    def _enqueue(self, command: LauncherCommand, source: str) -> None:
        with self._queue_lock:
            if not self._queue_active:
                return
            if command is LauncherCommand.START and self._state in {LauncherState.STARTING, LauncherState.RUNNING}:
                self._log(f"Ignoring start request from {source}; services are {self._state.value}.")
                return
            if command is LauncherCommand.STOP and self._state in {LauncherState.IDLE, LauncherState.STOPPING}:
                self._log(f"Ignoring stop request from {source}; services are {self._state.value}.")
                return
            if command is LauncherCommand.RESET and self._state in {LauncherState.STARTING, LauncherState.STOPPING}:
                self._log(f"Ignoring reset request from {source}; services are {self._state.value}.")
                return
            self._log(f"Queueing {command.value} request ({source}).")
            self._queue.put(command)

    def _worker_loop(self) -> None:
        while True:
            command = self._queue.get()
            try:
                if command is LauncherCommand.SHUTDOWN:
                    return
                if command is LauncherCommand.START:
                    self._do_start()
                elif command is LauncherCommand.STOP:
                    self._do_stop()
                elif command is LauncherCommand.RESET:
                    self._do_reset()
            finally:
                self._queue.task_done()


    def _check_hardware(self) -> HardwareStatus:
        """Check hardware connection status and update UI. Returns the detected status."""
        hw_status = check_hardware_connected()
        
        if hw_status == HardwareStatus.AVAILABLE:
            self._set_status("hardware", "CX-505 connected and available", "success")
        
        elif hw_status == HardwareStatus.IN_USE:
            # Check if our capture service is running
            if "capture" in self._processes and self._state == LauncherState.RUNNING:
                # Expected - our service has it
                self._set_status("hardware", "CX-505 in use by capture service", "success")
            else:
                # Unexpected - something else has it
                self._set_status("hardware", "CX-505 in use by another process", "error")
                self._log("WARNING: CX-505 is in use by another process (check Task Manager for python.exe or other Elmetron software)")
        
        elif hw_status == HardwareStatus.NOT_FOUND:
            self._set_status("hardware", "CX-505 not detected (OK for archived sessions)", "waiting")
            self._log("WARNING: CX-505 device not detected (check USB connection and FTDI drivers)")
        
        else:  # UNKNOWN
            self._set_status("hardware", "CX-505 status unknown", "waiting")
            self._log("WARNING: CX-505 status could not be determined")
        
        return hw_status


    def _refresh_hardware(self) -> None:
        """Manually refresh hardware status."""
        self._log("Refreshing hardware status...")
        hw_status = self._check_hardware()
        
        # Log the result
        if hw_status == HardwareStatus.AVAILABLE:
            self._log("Hardware refresh complete: CX-505 is available")
        elif hw_status == HardwareStatus.IN_USE:
            if "capture" in self._processes and self._state == LauncherState.RUNNING:
                self._log("Hardware refresh complete: CX-505 in use by our service")
            else:
                self._log("Hardware refresh complete: CX-505 in use by another process")
        elif hw_status == HardwareStatus.NOT_FOUND:
            self._log("Hardware refresh complete: CX-505 not detected")
        else:  # UNKNOWN
            self._log("Hardware refresh complete: CX-505 status unknown")


    def _reopen_browser(self) -> None:
        """Reopen the browser tab with the UI dashboard."""
        if self._state != LauncherState.RUNNING:
            self._log("[Browser] Cannot reopen browser - service not started")
            messagebox.showwarning(
                "Service Not Running",
                "The capture service must be running to open the dashboard.\n\nPlease click 'Start' first."
            )
            return
        
        self._log("[Browser] Reopening dashboard in browser...")
        try:
            webbrowser.open(UI_URL)
            self.status_rows["browser"].set("Dashboard opened", STATUS_PALETTE["success"])
            self._browser_opened = True
            self._log("[Browser] Dashboard opened successfully")
        except Exception as e:
            self._log(f"[Browser] Failed to open dashboard: {e}")
            self.status_rows["browser"].set(f"Failed: {e}", STATUS_PALETTE["error"])
    def _do_start(self) -> None:
        self._transition_to(LauncherState.STARTING)
        self._set_initial_statuses()
        try:
            # Check hardware first
            self._check_hardware()
            
            self._set_status("prereq", "Checking prerequisites...", "waiting")
            self._prepare_environment()
            self._set_status("prereq", "Prerequisites ready", "success")

            self._set_status("capture", "Starting capture service...", "waiting")
            self._start_capture_service()
            if not self._wait_for_url(HEALTH_URL, 40, "capture"):
                raise RuntimeError("Capture service did not respond at /health.")
            self._set_status("capture", "Capture service online", "success")

            self._set_status("ui", "Starting Service Health UI...", "waiting")
            self._start_ui_server()
            if not self._wait_for_url(UI_URL, 40, "ui"):
                raise RuntimeError("UI server did not respond at 127.0.0.1:5173.")
            self._set_status("ui", "Service Health UI online", "success")

            self._set_status("browser", "Opening dashboard...", "waiting")
            self._open_browser()
            self._set_status("browser", "Dashboard opened", "success")

            self._set_status("system", "All services online", "success")
            self._transition_to(LauncherState.RUNNING)
        except Exception as exc:
            self._log(f"ERROR: {exc}")
            self._terminate_processes()
            self._set_status("prereq", "Prerequisites failed", "error")
            self._set_status("system", f"Startup failed: {exc}", "error")
            self._set_status("capture", "Capture service offline", "error")
            self._set_status("ui", "Service Health UI offline", "error")
            self._set_status("browser", "Dashboard offline", "error")
            self._transition_to(LauncherState.FAILED)
            self._post(lambda: messagebox.showerror("Elmetron Launch Monitor", str(exc)))

    def _do_stop(self) -> None:
        if not self._processes and not self._logs:
            self._log("Services already stopped (no active resources).")
            self._mark_idle_statuses()
            self._transition_to(LauncherState.IDLE)
            return
        self._transition_to(LauncherState.STOPPING)
        self._set_status("system", "Stopping services...", "waiting")
        
        # Stop data monitoring
        self._stop_data_monitoring()
        
        # Log resource state before cleanup for debugging
        self._log_resource_state()
        
        errors = self._terminate_processes()
        if errors:
            for error in errors:
                self._log(f"ERROR: {error}")
            self._set_status("system", "Stop completed with errors", "error")
            self._transition_to(LauncherState.FAILED)
        else:
            self._mark_idle_statuses()
            self._set_status("system", "Services stopped", "pending")
            self._transition_to(LauncherState.IDLE)

    def _do_reset(self) -> None:
        self._log("Executing reset: stop then start.")
        was_running = self._state == LauncherState.RUNNING
        
        # Force cleanup regardless of current state
        self._do_stop()
        
        # Check if stop succeeded
        if self._state not in {LauncherState.IDLE, LauncherState.FAILED}:
            self._log("Reset aborted; stop did not complete cleanly.")
            return
        
        # Force cleanup of any lingering resources if in failed state
        if self._state == LauncherState.FAILED:
            self._log("Forcing resource cleanup after failed state.")
            self._force_cleanup()
        
        # Reset to IDLE before starting
        self._transition_to(LauncherState.IDLE)
        self._set_initial_statuses()
        
        if not was_running:
            self._log("Reset requested while idle; starting services.")
        self._do_start()

    def _prepare_environment(self) -> None:
        npm_path = shutil.which("npm")
        if npm_path is None:
            raise RuntimeError("npm is not available on PATH.")
        self._npm_path = npm_path
        CAPTURES_DIR.mkdir(exist_ok=True)

    def _start_capture_service(self) -> None:
        log = CAPTURE_LOG.open("a", encoding="utf-8")
        err = CAPTURE_ERR.open("a", encoding="utf-8")
        self._logs["capture"] = (log, err)

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
        self._log("Capture service launched; waiting for /health.")

    def _start_ui_server(self) -> None:
        if not self._npm_path:
            raise RuntimeError("npm path unavailable after prerequisite check.")
        ui_dir = ROOT / "ui"
        self._ensure_ui_dependencies(ui_dir)

        log = UI_LOG.open("a", encoding="utf-8")
        err = UI_ERR.open("a", encoding="utf-8")
        self._logs["ui"] = (log, err)

        env = os.environ.copy()
        env["VITE_API_BASE_URL"] = "http://127.0.0.1:8050"
        env.setdefault("VITE_HEALTH_BASE_URL", env["VITE_API_BASE_URL"])
        self._log(f"UI base URL set to {env['VITE_API_BASE_URL']}")

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
        self._log("UI dev server launching.")

    def _ensure_ui_dependencies(self, ui_dir: Path) -> None:
        node_modules = ui_dir / "node_modules"
        if node_modules.exists():
            return
        if not self._npm_path:
            raise RuntimeError("npm path unavailable after prerequisite check.")
        self._log("Installing UI dependencies (npm install).")
        result = subprocess.run(
            [self._npm_path, "install"],
            cwd=str(ui_dir),
            creationflags=CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            raise RuntimeError("npm install failed. See console for details.")
        self._log("UI dependencies installed.")

    def _open_browser(self) -> None:
        self._set_status("browser", "Opening UI in web browser...", "waiting")
        self._log("Opening UI in web browser in 3 seconds...")
        time.sleep(3)
        self._log("Opening dashboard in default browser.")
        webbrowser.open(UI_URL, new=0, autoraise=True)
        self._browser_opened = True  # Mark that we opened the browser

    def _wait_for_url(self, url: str, attempts: int, process_key: str) -> bool:
        for _ in range(attempts):
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if 200 <= response.getcode() < 300:
                        return True
            except urllib.error.URLError:
                pass
            process = self._processes.get(process_key)
            if process is not None and process.poll() is not None:
                self._log(f"Process {process_key} exited with code {process.poll()}")
                return False
            self._log(f"Waiting for {url}")
            time.sleep(1)
        return False

    def _terminate_processes(self) -> List[str]:
        errors: List[str] = []
        for name, process in list(self._processes.items()):
            try:
                # Verify process object is valid
                pid = getattr(process, 'pid', None)
                if pid is None:
                    self._log(f"Skipping {name}: invalid process object.")
                    self._processes.pop(name, None)
                    continue
                
                self._log(f"Stopping {name} (pid {pid}).")
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self._log(f"{name} did not exit in time; forcing termination.")
                        process.kill()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            errors.append(f"{name} process did not exit after kill().")
                exit_code = process.poll()
                self._log(f"{name} stopped with code {exit_code}.")
            except OSError as exc:
                errors.append(f"Failed to terminate {name}: {exc}")
            finally:
                self._processes.pop(name, None)
        self._close_logs()
        return errors

    def _close_logs(self) -> None:
        for handles in self._logs.values():
            for handle in handles:
                try:
                    handle.close()
                except OSError:
                    pass
        self._logs.clear()
    def _force_cleanup(self) -> None:
        """Force cleanup of all resources, even if partially initialized."""
        self._log("Forcing complete resource cleanup.")
        
        # Close any open log handles
        self._close_logs()
        
        # Kill any lingering processes
        for name, process in list(self._processes.items()):
            try:
                pid = getattr(process, "pid", None)
                if pid is not None and process.poll() is None:
                    self._log(f"Force killing {name} (pid {pid}).")
                    process.kill()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self._log(f"WARNING: {name} did not exit after force kill.")
            except (OSError, AttributeError) as exc:
                self._log(f"WARNING: Exception during force cleanup of {name}: {exc}")
            finally:
                self._processes.pop(name, None)
        
        # Clear process dictionary
        self._processes.clear()
        self._log("Resource cleanup completed.")
    def _log_resource_state(self) -> None:
        """Log current state of processes and log handles for debugging."""
        self._log(f"Resource state: {len(self._processes)} processes, {len(self._logs)} log handles")
        for name, process in self._processes.items():
            poll_result = process.poll()
            status = "running" if poll_result is None else f"exited({poll_result})"
            pid = getattr(process, "pid", "unknown")
            self._log(f"  Process '{name}' (pid {pid}): {status}")

    def _set_initial_statuses(self) -> None:
        self._set_status("hardware", "Hardware status unknown", "pending")
        self._set_status("prereq", "Awaiting prerequisite check", "pending")
        self._set_status("capture", "Capture service offline", "pending")
        self._set_status("ui", "Service Health UI offline", "pending")
        self._set_status("browser", "Dashboard closed", "pending")
        self._set_status("system", "Awaiting command", "pending")

    def _mark_idle_statuses(self) -> None:
        self._set_status("capture", "Capture service offline", "pending")
        self._set_status("ui", "Service Health UI offline", "pending")
        self._set_status("browser", "Dashboard closed", "pending")

    def _set_status(self, key: str, text: str, tone: str) -> None:
        color = STATUS_PALETTE.get(tone, STATUS_PALETTE["pending"])
        self._post(lambda: self.status_rows[key].set(text, color))

    def _update_controls(self) -> None:
        state = self._state
        start_enabled = state in {LauncherState.IDLE, LauncherState.FAILED}
        stop_enabled = state == LauncherState.RUNNING
        reset_enabled = state in {LauncherState.RUNNING, LauncherState.FAILED, LauncherState.IDLE}
        self._post(lambda: self.start_button.configure(state="normal" if start_enabled else "disabled"))
        self._post(lambda: self.stop_button.configure(state="normal" if stop_enabled else "disabled"))
        self._post(lambda: self.reset_button.configure(state="normal" if reset_enabled else "disabled"))

    def _transition_to(self, state: LauncherState) -> None:
        self._state = state
        self._update_controls()

    def _log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self._log_history.append(entry)
        self._post(lambda: self._append_log(entry))

    def _append_log(self, entry: str) -> None:
        self.log_box.insert(tk.END, entry + "\n")
        self.log_box.see(tk.END)

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

    def _post(self, func) -> None:
        try:
            self.root.after(0, func)
        except tk.TclError:
            pass



    def _get_current_session_file(self) -> str:
        """Get current session database file name."""
        try:
            db_path = ROOT / "data" / "elmetron.sqlite"
            if db_path.exists():
                return f"data/elmetron.sqlite ({db_path.stat().st_size / 1024 / 1024:.1f} MB)"
            return "data/elmetron.sqlite (new session)"
        except Exception:
            return "data/elmetron.sqlite"

    def _on_close(self) -> None:
        """Handle window close - stop services if running, then exit."""
        # If browser was opened, show confirmation dialog
        if self._browser_opened and self._state == LauncherState.RUNNING:
            session_file = self._get_current_session_file()
            
            message = (
                "Closing the launcher will stop all services.\n\n"
                f"Session data file: {session_file}\n\n"
                "⚠️ Any unsaved work in the browser (exports, charts, etc.) will be lost.\n\n"
                "The captured measurement data is automatically saved to the database.\n\n"
                "📌 The browser tab will detect the offline state and close automatically.\n\n""Are you sure you want to close?"
            )
            
            response = messagebox.askyesno(
                "Confirm Close",
                message,
                icon="warning",
                default="no"
            )
            
            if not response:
                return  # User cancelled
        
        # If services are running, stop them first and wait for completion
        if self._state == LauncherState.RUNNING:
            self._log("Closing launcher - stopping services...")
            
            # Directly terminate processes instead of using the queue
            # (queue won't process after we set _closing = True)
            self._terminate_processes()
            
            # Wait for processes to actually terminate (up to 3 seconds)
            max_wait = 30  # 3 seconds (30 * 0.1)
            for _ in range(max_wait):
                all_stopped = all(
                    p.poll() is not None 
                    for p in self._processes.values()
                )
                if all_stopped:
                    break
                time.sleep(0.1)
            
            # Force kill any remaining
            for name, proc in list(self._processes.items()):
                if proc.poll() is None:
                    self._log(f"Force killing {name}...")
                    proc.kill()
            
            self._processes.clear()
            self._log("All services stopped")
            
            # Remind user to close browser
            if self._browser_opened:
                self._log("Browser tab will auto-close after detecting offline state")
        
        self._closing = True
        with self._queue_lock:
            self._queue_active = False
        self._queue.put(LauncherCommand.SHUTDOWN)
        self._release_lock()
        self.root.destroy()

    def run(self) -> None:
        try:
            self.root.mainloop()
        finally:
            self._closing = True
            with self._queue_lock:
                self._queue_active = False
            self._queue.put(LauncherCommand.SHUTDOWN)
            self._release_lock()

    def join(self) -> None:
       self._queue.join()

def main() -> None:
    app = LauncherApp()
    app.run()


if __name__ == "__main__":
    main()
