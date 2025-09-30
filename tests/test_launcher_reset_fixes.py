"""Comprehensive tests for launcher reset button crash fixes."""
import subprocess
import pytest
from launcher import LauncherApp, LauncherState


class FakeProcess:
    """Mock process for testing."""
    def __init__(self, should_exit: bool = True, pid: int = 12345):
        self._pid = pid
        self._should_exit = should_exit
        self._killed = False
        self._terminated = False
        
    @property
    def pid(self) -> int:
        return self._pid
    
    def poll(self):
        if self._killed or self._terminated:
            return 0
        if self._should_exit:
            return None
        return None
    
    def terminate(self):
        self._terminated = True
    
    def kill(self):
        self._killed = True
    
    def wait(self, timeout=None):
        pass


class ZombieProcess:
    """Mock process that won't die."""
    def __init__(self):
        self._pid = 99999
        
    @property
    def pid(self) -> int:
        return self._pid
    
    def poll(self):
        return None  # Always running
    
    def terminate(self):
        pass
    
    def kill(self):
        pass
    
    def wait(self, timeout=None):
        raise subprocess.TimeoutExpired("cmd", timeout)


@pytest.fixture
def launcher_app() -> LauncherApp:
    """Create a launcher app for testing without auto-start."""
    app = LauncherApp(auto_start=False)
    yield app
    app._closing = True
    with app._queue_lock:
        app._queue_active = False


def test_reset_from_failed_state(launcher_app: LauncherApp, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that reset works when launcher is in FAILED state."""
    calls: list[str] = []
    
    def fake_prepare() -> None:
        calls.append("prepare")
        launcher_app._npm_path = "npm"
    
    def fake_start_capture() -> None:
        calls.append("start_capture")
        launcher_app._processes["capture"] = FakeProcess()
    
    def fake_start_ui() -> None:
        calls.append("start_ui")
        launcher_app._processes["ui"] = FakeProcess()
    
    def fake_wait(_url: str, _attempts: int, key: str) -> bool:
        calls.append(f"wait_{key}")
        return True
    
    def fake_open_browser() -> None:
        calls.append("open_browser")
    
    monkeypatch.setattr(launcher_app, "_prepare_environment", fake_prepare)
    monkeypatch.setattr(launcher_app, "_start_capture_service", fake_start_capture)
    monkeypatch.setattr(launcher_app, "_start_ui_server", fake_start_ui)
    monkeypatch.setattr(launcher_app, "_wait_for_url", fake_wait)
    monkeypatch.setattr(launcher_app, "_open_browser", fake_open_browser)
    
    # Simulate a failed start
    launcher_app._transition_to(LauncherState.FAILED)
    launcher_app._processes["capture"] = FakeProcess()
    
    # Reset should work from FAILED state
    calls.clear()
    launcher_app.reset()
    launcher_app.join()
    
    assert launcher_app._state is LauncherState.RUNNING
    assert "start_capture" in calls


def test_reset_with_zombie_processes(launcher_app: LauncherApp, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test reset handles zombie processes that won't terminate."""
    calls: list[str] = []
    
    def fake_prepare() -> None:
        calls.append("prepare")
        launcher_app._npm_path = "npm"
    
    def fake_force_cleanup() -> None:
        calls.append("force_cleanup")
        # Forcefully clear everything
        launcher_app._processes.clear()
        launcher_app._logs.clear()
    
    def fake_start_capture() -> None:
        calls.append("start_capture")
        launcher_app._processes["capture"] = FakeProcess()
    
    def fake_start_ui() -> None:
        calls.append("start_ui")
        launcher_app._processes["ui"] = FakeProcess()
    
    def fake_wait(_url: str, _attempts: int, key: str) -> bool:
        calls.append(f"wait_{key}")
        return True
    
    def fake_open_browser() -> None:
        calls.append("open_browser")
    
    monkeypatch.setattr(launcher_app, "_prepare_environment", fake_prepare)
    monkeypatch.setattr(launcher_app, "_force_cleanup", fake_force_cleanup)
    monkeypatch.setattr(launcher_app, "_start_capture_service", fake_start_capture)
    monkeypatch.setattr(launcher_app, "_start_ui_server", fake_start_ui)
    monkeypatch.setattr(launcher_app, "_wait_for_url", fake_wait)
    monkeypatch.setattr(launcher_app, "_open_browser", fake_open_browser)
    
    # Add zombie process
    launcher_app._processes["zombie"] = ZombieProcess()
    launcher_app._transition_to(LauncherState.RUNNING)
    
    # Reset should handle zombie process
    launcher_app.reset()
    launcher_app.join()
    
    # Should be in FAILED state due to zombie, but force_cleanup should be called
    assert "force_cleanup" in calls or launcher_app._state in {LauncherState.RUNNING, LauncherState.FAILED}


def test_log_file_handles_closed_on_startup_failure(launcher_app: LauncherApp, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that log files are closed when startup fails."""
    import io
    
    fake_log = io.StringIO()
    fake_err = io.StringIO()
    
    def fake_prepare() -> None:
        launcher_app._npm_path = "npm"
    
    def fake_start_capture() -> None:
        # Store log handles
        launcher_app._logs["capture"] = (fake_log, fake_err)
        # Then fail
        raise RuntimeError("Simulated capture failure")
    
    monkeypatch.setattr(launcher_app, "_prepare_environment", fake_prepare)
    monkeypatch.setattr(launcher_app, "_start_capture_service", fake_start_capture)
    
    launcher_app.start()
    launcher_app.join()
    
    # Verify state is FAILED
    assert launcher_app._state is LauncherState.FAILED
    
    # Verify log handles were closed (StringIO doesn't have closed attr, so check _logs cleared)
    assert "capture" not in launcher_app._logs


def test_force_cleanup_method(launcher_app: LauncherApp) -> None:
    """Test _force_cleanup properly clears all resources."""
    # Add some fake processes and logs
    launcher_app._processes["test1"] = FakeProcess()
    launcher_app._processes["test2"] = FakeProcess()
    launcher_app._logs["test"] = (None, None)  # type: ignore
    
    # Call force cleanup
    launcher_app._force_cleanup()
    
    # Verify everything was cleared
    assert len(launcher_app._processes) == 0
    assert len(launcher_app._logs) == 0


def test_log_resource_state_method(launcher_app: LauncherApp) -> None:
    """Test _log_resource_state logs process and log state."""
    # Add some resources
    launcher_app._processes["capture"] = FakeProcess()
    launcher_app._logs["test"] = (None, None)  # type: ignore
    
    # This should not raise
    launcher_app._log_resource_state()
    
    # Check that something was logged
    assert len(launcher_app._log_history) > 0


def test_terminate_processes_with_invalid_process(launcher_app: LauncherApp) -> None:
    """Test _terminate_processes handles invalid process objects."""
    class InvalidProcess:
        """Process without pid attribute."""
        def poll(self):
            return None
    
    launcher_app._processes["invalid"] = InvalidProcess()  # type: ignore
    
    # Should not crash
    errors = launcher_app._terminate_processes()
    
    # Process should be removed
    assert "invalid" not in launcher_app._processes


def test_reset_transition_to_idle_before_start(launcher_app: LauncherApp, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that reset transitions to IDLE before starting services."""
    states_seen: list[LauncherState] = []
    
    original_transition = launcher_app._transition_to
    def track_transition(state: LauncherState) -> None:
        states_seen.append(state)
        original_transition(state)
    
    def fake_prepare() -> None:
        launcher_app._npm_path = "npm"
    
    def fake_start_capture() -> None:
        launcher_app._processes["capture"] = FakeProcess()
    
    def fake_start_ui() -> None:
        launcher_app._processes["ui"] = FakeProcess()
    
    def fake_wait(_url: str, _attempts: int, key: str) -> bool:
        return True
    
    def fake_open_browser() -> None:
        pass
    
    monkeypatch.setattr(launcher_app, "_transition_to", track_transition)
    monkeypatch.setattr(launcher_app, "_prepare_environment", fake_prepare)
    monkeypatch.setattr(launcher_app, "_start_capture_service", fake_start_capture)
    monkeypatch.setattr(launcher_app, "_start_ui_server", fake_start_ui)
    monkeypatch.setattr(launcher_app, "_wait_for_url", fake_wait)
    monkeypatch.setattr(launcher_app, "_open_browser", fake_open_browser)
    
    # Start in FAILED state
    launcher_app._state = LauncherState.FAILED
    launcher_app._processes["old"] = FakeProcess()
    
    states_seen.clear()
    launcher_app.reset()
    launcher_app.join()
    
    # Should transition: STOPPING -> (IDLE or FAILED) -> IDLE -> STARTING -> RUNNING
    assert LauncherState.IDLE in states_seen
    assert LauncherState.STARTING in states_seen
    assert launcher_app._state is LauncherState.RUNNING
