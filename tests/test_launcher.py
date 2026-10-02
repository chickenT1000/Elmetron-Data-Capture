import io
import json
import pytest
import launcher


def response(home):
    return io.BytesIO(json.dumps({'service':'elmetron','data_home':str(home.resolve())}).encode())


def test_existing_server_is_reused(tmp_path,monkeypatch):
    opened=[]
    monkeypatch.setattr(launcher.urllib.request,'urlopen',lambda *a,**k:response(tmp_path))
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda *a,**k:pytest.fail('Should reuse server'))
    monkeypatch.setattr(launcher.webbrowser,'open',opened.append)
    launcher.launch(tmp_path)
    assert opened==['http://127.0.0.1:8050/']


def test_other_data_directory_is_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr(launcher.urllib.request,'urlopen',lambda *a,**k:response(tmp_path/'other'))
    with pytest.raises(RuntimeError,match='Another Elmetron'):
        launcher.launch(tmp_path)


def test_failed_start_reports_log_location(tmp_path,monkeypatch):
    def unavailable(*a,**k): raise OSError('Port occupied')
    monkeypatch.setattr(launcher.urllib.request,'urlopen',unavailable)
    class Failed:
        def poll(self): return 1
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda *a,**k:Failed())
    with pytest.raises(RuntimeError,match='server.log'):
        launcher.launch(tmp_path)
