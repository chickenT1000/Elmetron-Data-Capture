"""Capture process lifecycle and authenticated owner-side controls."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from .paths import prepare, configuration, read_status, RESOURCE_ROOT
from .config import StorageConfig
from .storage.database import Database
from .storage.session_buffer import SessionBuffer


def publish_status(home, payload):
    import logging
    import tempfile
    path = Path(home)/'captures/status.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as stream:
        stream.write(json.dumps(payload,ensure_ascii=False));temporary=Path(stream.name)
    try:
        for attempt in range(100):
            try:
                os.replace(temporary,path)
                return True
            except PermissionError:
                if attempt==99:
                    logging.warning('Status publication delayed by Windows file sharing; measurements remain durable')
                    return False
                time.sleep(.01)
    finally:
        temporary.unlink(missing_ok=True)


def command_prefix():
    if getattr(sys, 'frozen', False):
        return [str(Path(sys.executable).with_name('elmetron-cli.exe'))]
    return [sys.executable, '-m', 'elmetron.cli.app']


class InstanceLock:
    def __init__(self, path):
        self.path = Path(path)
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open('a+b')
        self.handle.write(b'0'); self.handle.flush(); self.handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.handle.close()
            raise RuntimeError('An Elmetron instance is already using this data directory.') from exc
        return self

    def __exit__(self, *args):
        if self.handle:
            self.handle.close()


class InstallGuard:
    """Inno checks this Windows mutex before replacing a running capture service."""
    def __enter__(self):
        self.handle = None
        if os.name == 'nt':
            import ctypes
            self.kernel = ctypes.WinDLL('kernel32',use_last_error=True)
            self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p]
            self.kernel.CreateMutexW.restype = ctypes.c_void_p
            self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            self.handle = self.kernel.CreateMutexW(None,False,'Local\\ElmetronDataCapture')
            if not self.handle:
                raise OSError(ctypes.get_last_error(),'Cannot create installation guard')
        return self

    def __exit__(self,*args):
        if self.handle:
            self.kernel.CloseHandle(self.handle)


class CaptureController:
    def __init__(self, home):
        self.home = Path(home)
        self.process = None
        self._lock = threading.RLock()
        self.log = None
        self.default_operator = configuration(home).acquisition.default_operator

    def start(self, demo=False, name=None, operator=None):
        with self._lock:
            if self.process and self.process.poll() is None:
                raise ValueError('Capture is already running')
            if self.process and self.process.poll() is not None and self.process.stdin:
                self.process.stdin.close()
            if self.log:
                self.log.close(); self.log = None
            target = self.home/'demo' if demo else self.home
            cfg = prepare(target)
            if not demo:
                if cfg.device.profile != 'cx505' or cfg.device.transport != 'ftdi':
                    raise ValueError('This beta supports the CX-505 FTDI profile only')
                from .hardware.device_manager import list_devices
                devices = list_devices()
                if not devices:
                    raise ValueError('CX-505 not connected. Archive and demonstration are available.')
            self.log = (self.home/'captures/worker.log').open('a', encoding='utf-8')
            cmd = [*command_prefix(), '--data-dir', str(self.home), 'capture-worker']
            if demo:
                cmd.append('--demo')
            if name:
                cmd.extend(['--name', name])
            cmd.extend(['--operator', operator if operator is not None else self.default_operator])
            publish_status(self.home, {'state':'starting', 'mode':'demo' if demo else 'live', 'frames':0,
                                      'updated_at':time.time()})
            self.process = subprocess.Popen(cmd, cwd=str(RESOURCE_ROOT), stdin=subprocess.PIPE,
                                            stdout=self.log, stderr=self.log, text=True, encoding='utf-8',
                                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            return self.status()

    def stop(self):
        with self._lock:
            if self.process and self.process.poll() is None:
                try:
                    self.process.stdin.write('stop\n'); self.process.stdin.flush()
                except (BrokenPipeError,OSError):
                    pass
                try:
                    self.process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    raise RuntimeError('Capture did not acknowledge stop; journal retained. Do not update until it exits.')
            if self.log:
                self.log.close(); self.log = None
            return self.status()

    def rotate(self, name, operator=None):
        mode = self.status().get('mode')
        if mode not in ('live', 'demo'):
            raise ValueError('Start capture before creating a new capture session')
        self.stop()
        return self.start(mode == 'demo', name, operator)

    def status(self):
        status = read_status(self.home)
        if status.get('state') in ('running', 'starting', 'reconnecting') and time.time()-status.get('updated_at',0) > 5:
            status.update(state='stale', detail='Capture heartbeat expired')
        if self.process and self.process.poll() is not None and status.get('state') not in ('stopped','error'):
            status.update(state='error', detail=f'Capture exited with code {self.process.returncode}')
        status['live_capture_active'] = status.get('state') == 'running'
        status['device_connected'] = status['live_capture_active'] and status.get('mode') != 'demo'
        status.setdefault('mode','archive')
        status['last_update'] = status.get('last_frame_at')
        return status


def capture_worker(home, demo=False, name=None, operator=None):
    from .hardware.device_manager import create_interface
    from .protocols.registry import load_registry
    from .ingestion.pipeline import FrameIngestor
    from .storage.database import DeviceMetadata
    from .analytics.engine import AnalyticsEngine
    target = Path(home)/'demo' if demo else Path(home)
    cfg = prepare(target)
    if demo:
        cfg.device.profile = 'cx505_sim'
    registry = load_registry(target/'config/protocols.toml')
    registry.apply_to_device(cfg.device)
    from .config import validate_effective_config
    validate_effective_config(cfg)
    if cfg.device.transport != ('sim' if demo else 'ftdi'):
        raise ValueError('Real capture requires FTDI; use Start demo for simulated measurements')
    # No experimental commands are executed by the release capture worker.
    cfg.acquisition.startup_commands = []
    cfg.acquisition.scheduled_commands = []
    stop = threading.Event()
    def controls():
        for line in sys.stdin:
            if line.strip() == 'stop':
                stop.set(); return
        stop.set()  # Parent died or pipe closed: finish the session gracefully.
    threading.Thread(target=controls, daemon=True).start()
    database = Database(cfg.storage)
    session = journal = interface = None
    status = {'state':'starting', 'mode':'demo' if demo else 'live', 'frames':0, 'bytes_read':0,
              'operator_name':operator or None, 'current_session_id':None, 'last_frame_at':None, 'updated_at':time.time()}
    error = None
    def update():
        status['updated_at'] = time.time()
        publish_status(home,status)
    try:
        with InstanceLock(target/'captures/device.lock'):
            database.initialise()
            recovery = SessionBuffer.recover_orphaned_buffers(target/'captures', database)
            if recovery['failed_recoveries']:
                raise RuntimeError('Capture journals require recovery; inspect retained journal files before starting.')
            status['recovery'] = recovery
            while not stop.is_set():
                try:
                    interface = create_interface(cfg.device)
                    device = interface.open()
                    if session is None:
                        metadata = DeviceMetadata(device.serial,device.description,'CX-505')
                        session = database.start_session(datetime.utcnow(),metadata,{'demo':demo},operator or None)
                        if name:
                            with database.connect() as conn:
                                conn.execute('UPDATE sessions SET note=? WHERE id=?',(name,session.id))
                        journal = SessionBuffer(cfg.storage,session.id,target/'captures')
                        journal.create(datetime.utcnow(),{'serial':device.serial,'model':'CX-505','description':device.description})
                        ingestor = FrameIngestor(cfg.ingestion,session,analytics=AnalyticsEngine(cfg.analytics),session_buffer=journal)
                        status['current_session_id'] = session.id
                        status['instrument'] = {'serial':device.serial,'model':'CX-505'}
                    elif device.serial != status['instrument']['serial']:
                        raise RuntimeError('A different instrument was connected; stop capture before switching devices')
                    opened_at = time.time()
                    status.update(state='running',detail=None);update()
                    def frame(data):
                        decoded = ingestor.handle_frame(data)
                        if decoded:
                            m = decoded.get('measurement',{})
                            now = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                            status['frames'] += 1;status['bytes_read'] += len(data)
                            status['last_frame_at'] = now
                            status['latest_measurement'] = {**m,'unit':m.get('value_unit') or m.get('unit'),
                                'captured_at':now,'timestamp':now,'measurement_id':decoded['storage']['measurement_id']}
                            update()
                    while not stop.is_set():
                        interface.run_window(1.0,frame)
                        if time.time() - (datetime.fromisoformat(status['last_frame_at'].replace('Z','+00:00')).timestamp() if status['last_frame_at'] else opened_at) > 5:
                            raise RuntimeError('No recent measurement frames')
                        update()
                except (RuntimeError,OSError) as exc:
                    status.update(state='reconnecting',detail=str(exc));update()
                    if interface:
                        interface.close();interface=None
                    if stop.wait(2):
                        break
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        try:
            if journal:
                journal.close(datetime.utcnow())
            if session:
                session.close(datetime.utcnow())
            if interface:
                interface.close()
        finally:
            database.close()
            status.update(state='error' if error else 'stopped',detail=error)
            update()
