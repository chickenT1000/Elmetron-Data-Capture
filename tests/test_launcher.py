import pytest

pytest.importorskip("tkinter")

from launcher import LauncherApp, LauncherState


class FakeProcess:
    def __init__(self) -> None:
        self.pid = 1234
        self._exit_code: int | None = None

    def poll(self) -> int | None:
        return self._exit_code

    def terminate(self) -> None:
        self._exit_code = 0

    def wait(self, timeout: float | None = None) -> int | None:  # noqa: ARG002
        return self._exit_code

    def kill(self) -> None:
        self._exit_code = -9


@pytest.fixture
def launcher_app(monkeypatch: pytest.MonkeyPatch) -> LauncherApp:
    monkeypatch.setattr("launcher.messagebox.showerror", lambda *args, **kwargs: None)
    app = LauncherApp(auto_start=False)
    try:
        yield app
    finally:
        if app._state == LauncherState.RUNNING:
            app.stop()
            app.join()
        if app.root.winfo_exists():  # type: ignore[attr-defined]
            app._on_close()
            app.join()


def test_start_flow_transitions_to_running(launcher_app: LauncherApp, monkeypatch: pytest.MonkeyPatch) -> None:
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

    launcher_app.start()
    launcher_app.join()

    assert launcher_app._state is LauncherState.RUNNING
    assert calls == [
        "prepare",
        "start_capture",
        "wait_capture",
        "start_ui",
        "wait_ui",
        "open_browser",
    ]


def test_reset_runs_stop_before_restart(launcher_app: LauncherApp, monkeypatch: pytest.MonkeyPatch) -> None:
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

    def fake_terminate() -> list[str]:
        calls.append("terminate")
        launcher_app._processes.clear()
        return []

    monkeypatch.setattr(launcher_app, "_prepare_environment", fake_prepare)
    monkeypatch.setattr(launcher_app, "_start_capture_service", fake_start_capture)
    monkeypatch.setattr(launcher_app, "_start_ui_server", fake_start_ui)
    monkeypatch.setattr(launcher_app, "_wait_for_url", fake_wait)
    monkeypatch.setattr(launcher_app, "_open_browser", fake_open_browser)
    monkeypatch.setattr(launcher_app, "_terminate_processes", fake_terminate)

    launcher_app.start()
    launcher_app.join()
    assert launcher_app._state is LauncherState.RUNNING

    calls.clear()
    launcher_app.reset()
    launcher_app.join()

    assert launcher_app._state is LauncherState.RUNNING
    assert calls == [
        "terminate",
        "prepare",
        "start_capture",
        "wait_capture",
        "start_ui",
        "wait_ui",
        "open_browser",
    ]
