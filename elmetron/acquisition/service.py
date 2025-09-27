"""Acquisition service orchestrating hardware, ingestion, and storage."""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from typing import Any, Callable, Dict, Optional

from ..analytics.engine import AnalyticsEngine
from ..config import AppConfig, ScheduledCommandConfig
from ..commands.executor import CommandDefinition, CommandResult, execute_command
from ..hardware import DeviceInterface, ListedDevice, create_interface
from ..ingestion.pipeline import FrameIngestor
from ..storage.database import Database, DeviceMetadata, SessionHandle


@dataclass(slots=True)
class ServiceStats:
    frames: int = 0
    bytes_read: int = 0
    last_window_bytes: int = 0
    last_window_started: Optional[datetime] = None
    last_frame_at: Optional[datetime] = None






@dataclass(slots=True)
class CommandExecutionContext:
    definition: CommandDefinition
    retries: int
    backoff_s: float
    calibration_label: Optional[str]
    category: str
    schedule_payload: Dict[str, Any]


@dataclass(slots=True)
class _CommandTask:
    state_index: int
    source: str
    context: CommandExecutionContext


@dataclass(slots=True)
class CommandExecutionEvent:
    state_index: int
    source: str
    success: bool
    expectation_mismatch: bool
    attempts: int
    result: Optional[CommandResult]
    error: Optional[str]
    completed_at: float


class CommandExecutionFailure(RuntimeError):
    '''Raised when a command fails after exhausting retries.'''

    def __init__(self, original: Exception, attempts: int) -> None:
        super().__init__(str(original))
        self.original = original
        self.attempts = attempts


class CommandExpectationError(RuntimeError):
    '''Raised when a command response does not match the expected bytes.'''

    def __init__(self, result: CommandResult, attempts: int) -> None:
        super().__init__('Command result did not match expected bytes')
        self.result = result
        self.attempts = attempts


@dataclass(slots=True)
class ScheduledCommandState:
    '''Runtime state for a configured scheduled command.'''

    config: ScheduledCommandConfig
    next_due: Optional[float] = None
    runs: int = 0
    last_error: Optional[str] = None
    active: bool = True
    in_flight: bool = False
    pending_source: Optional[str] = None
    pending_context: Optional[CommandExecutionContext] = None

    def reset(self, base_time: float) -> None:
        self.runs = 0
        self.last_error = None
        self.active = self.config.enabled
        self.in_flight = False
        self.pending_source = None
        self.pending_context = None
        if not self.active:
            self.next_due = None
            return
        if self.config.interval_s is not None:
            delay = max(self.config.first_delay_s, 0.0)
            self.next_due = base_time + delay
        else:
            self.next_due = None

    def mark_attempt(self, now: float, success: bool) -> None:
        self.runs += 1
        self.last_error = None if success else 'failure'
        if self.config.max_runs is not None and self.runs >= self.config.max_runs:
            self.active = False
            self.next_due = None
            return
        if self.config.interval_s is not None:
            self.next_due = now + self.config.interval_s
        else:
            self.active = False
            self.next_due = None

    def disable(self) -> None:
        self.active = False
        self.next_due = None
        self.in_flight = False
        self.pending_source = None
        self.pending_context = None

class AcquisitionService:
    """Run the background capture loop according to the specification."""

    def __init__(
        self,
        config: AppConfig,
        database: Database,
        interface_factory: Optional[Callable[[], DeviceInterface]] = None,
        command_definitions: Optional[Dict[str, CommandDefinition]] = None,
        command_runner: Optional[Callable[[DeviceInterface, CommandDefinition], CommandResult]] = None,
        *,
        use_async_commands: bool = True,
    ) -> None:
        self._config = config
        self._database = database
        self._interface_factory = interface_factory or (lambda: create_interface(config.device))
        self._command_definitions = command_definitions or {}
        self._command_runner = command_runner or (lambda interface, definition: execute_command(interface, definition))
        self._use_async_commands = use_async_commands
        self._stop_requested = False
        self._stats = ServiceStats()
        self._interface_lock = threading.RLock()
        self._command_queue: Queue[_CommandTask | None] = Queue()
        self._command_results: Queue[CommandExecutionEvent] = Queue()
        self._command_worker: Optional[threading.Thread] = None
        self._command_worker_stop = threading.Event()
        self._scheduled_states = [ScheduledCommandState(command) for command in config.acquisition.scheduled_commands]

    @property
    def stats(self) -> ServiceStats:
        return self._stats

    @property
    def database(self) -> Database:
        return self._database

    def command_metrics(self) -> Dict[str, Any]:
        """Return a snapshot of command queue and schedule state for diagnostics."""

        metrics: Dict[str, Any] = {
            'queue_depth': None,
            'result_backlog': None,
            'inflight': 0,
            'scheduled': [],
            'worker_running': bool(self._command_worker and self._command_worker.is_alive()),
            'async_enabled': self._use_async_commands,
        }

        try:
            metrics['queue_depth'] = self._command_queue.qsize()
        except Exception:  # pragma: no cover - Queue may not support qsize()
            metrics['queue_depth'] = None
        try:
            metrics['result_backlog'] = self._command_results.qsize()
        except Exception:  # pragma: no cover
            metrics['result_backlog'] = None

        inflight = 0
        scheduled_payload = []
        for state in self._scheduled_states:
            if state.in_flight:
                inflight += 1
            next_due_iso = None
            if state.next_due is not None:
                try:
                    next_due_iso = datetime.utcfromtimestamp(state.next_due).isoformat() + 'Z'
                except (OverflowError, OSError, ValueError):  # pragma: no cover - timestamp edge cases
                    next_due_iso = None
            scheduled_payload.append({
                'name': state.config.name,
                'active': state.active,
                'in_flight': state.in_flight,
                'runs': state.runs,
                'last_error': state.last_error,
                'next_due_epoch': state.next_due,
                'next_due_iso': next_due_iso,
                'pending_source': state.pending_source,
                'pending_category': state.pending_context.category if state.pending_context else None,
            })
        metrics['inflight'] = inflight
        metrics['scheduled'] = scheduled_payload

        return metrics

    def _reset_schedule(self, base_time: float) -> None:
        for state in self._scheduled_states:
            state.reset(base_time)

    def _ingest_command_result(self, result: CommandResult, ingestor: Optional[FrameIngestor]) -> None:
        self._stats.bytes_read += result.bytes_read
        if not ingestor or not result.frames:
            return
        for frame in result.frames:
            record = ingestor.handle_frame(frame)
            if record is None:
                continue
            self._stats.frames = ingestor.frames
            self._stats.last_frame_at = datetime.utcnow()


    def _build_command_context(
        self,
        state: ScheduledCommandState,
        definition: CommandDefinition,
    ) -> CommandExecutionContext:
        retries = state.config.max_retries
        if retries is None:
            retries = definition.default_max_retries or 0
        try:
            retries_value = int(retries)
        except (TypeError, ValueError):
            retries_value = 0
        retries_value = max(retries_value, 0)

        backoff = state.config.retry_backoff_s
        if backoff is None:
            backoff = definition.default_retry_backoff_s or 1.0
        try:
            backoff_value = float(backoff)
        except (TypeError, ValueError):
            backoff_value = 1.0
        backoff_value = max(backoff_value, 0.0)

        calibration_label = state.config.calibration_label or definition.calibration_label
        category = definition.category or 'command'
        if calibration_label or (definition.category and 'calibration' in definition.category.lower()):
            category = 'calibration'

        schedule_payload = state.config.to_dict()

        return CommandExecutionContext(
            definition=definition,
            retries=retries_value,
            backoff_s=backoff_value,
            calibration_label=calibration_label,
            category=category,
            schedule_payload=schedule_payload,
        )

    def _queue_command_task(
        self,
        state_index: int,
        state: ScheduledCommandState,
        source: str,
        context: CommandExecutionContext,
    ) -> None:
        if not self._use_async_commands:
            raise RuntimeError('Async command queue requested while disabled')
        state.in_flight = True
        state.pending_source = source
        state.pending_context = context
        self._command_queue.put(_CommandTask(state_index=state_index, source=source, context=context))

    def _command_worker_loop(self, interface: DeviceInterface) -> None:
        while not self._command_worker_stop.is_set():
            try:
                task = self._command_queue.get(timeout=0.2)
            except Empty:
                continue
            if task is None:
                self._command_queue.task_done()
                break
            context = task.context
            try:
                with self._interface_lock:
                    result, attempts = self._execute_command_with_policy(
                        interface,
                        context.definition,
                        context.retries,
                        context.backoff_s,
                    )
            except CommandExpectationError as exc:
                event = CommandExecutionEvent(
                    state_index=task.state_index,
                    source=task.source,
                    success=False,
                    expectation_mismatch=True,
                    attempts=exc.attempts,
                    result=exc.result,
                    error='expectation mismatch',
                    completed_at=time.time(),
                )
            except CommandExecutionFailure as exc:
                event = CommandExecutionEvent(
                    state_index=task.state_index,
                    source=task.source,
                    success=False,
                    expectation_mismatch=False,
                    attempts=exc.attempts,
                    result=None,
                    error=str(exc.original),
                    completed_at=time.time(),
                )
            except Exception as exc:  # pylint: disable=broad-except
                event = CommandExecutionEvent(
                    state_index=task.state_index,
                    source=task.source,
                    success=False,
                    expectation_mismatch=False,
                    attempts=1,
                    result=None,
                    error=str(exc),
                    completed_at=time.time(),
                )
            else:
                event = CommandExecutionEvent(
                    state_index=task.state_index,
                    source=task.source,
                    success=True,
                    expectation_mismatch=False,
                    attempts=attempts,
                    result=result,
                    error=None,
                    completed_at=time.time(),
                )
            finally:
                self._command_queue.task_done()
            self._command_results.put(event)
        self._command_worker_stop.set()

    def _start_command_worker(self, interface: DeviceInterface) -> None:
        if not self._use_async_commands or self._command_worker is not None:
            return
        self._command_worker_stop.clear()
        worker = threading.Thread(
            target=self._command_worker_loop,
            name='cx505-command-worker',
            args=(interface,),
            daemon=True,
        )
        self._command_worker = worker
        worker.start()

    def _shutdown_command_worker(self) -> None:
        if not self._use_async_commands:
            return
        if self._command_worker is None:
            return
        self._command_worker_stop.set()
        self._command_queue.put(None)
        self._command_worker.join(timeout=2.0)
        self._command_worker = None
        while True:
            try:
                event = self._command_results.get_nowait()
            except Empty:
                break
            self._command_results.task_done()

    def _drain_command_results(
        self,
        session_handle: SessionHandle,
        ingestor: Optional[FrameIngestor],
    ) -> None:
        if not self._use_async_commands:
            return
        while True:
            try:
                event = self._command_results.get_nowait()
            except Empty:
                break
            try:
                state = self._scheduled_states[event.state_index]
            except IndexError:
                self._command_results.task_done()
                continue
            context = state.pending_context
            if context is None or state.pending_source != event.source:
                state.in_flight = False
                state.pending_source = None
                state.pending_context = None
                self._command_results.task_done()
                continue
            self._finalise_command_event(event, state, context, session_handle, ingestor)
            self._command_results.task_done()

    def _finalise_command_event(
        self,
        event: CommandExecutionEvent,
        state: ScheduledCommandState,
        context: CommandExecutionContext,
        session_handle: SessionHandle,
        ingestor: Optional[FrameIngestor],
    ) -> None:
        quiet = self._config.acquisition.quiet
        name = context.definition.name
        label = 'Startup' if event.source == 'startup' else 'Scheduled'
        calibration_label = context.calibration_label
        category = context.category
        base_payload: Dict[str, Any] = {
            'command': name,
            'source': event.source,
            'attempts': event.attempts,
            'schedule': context.schedule_payload,
        }

        state.in_flight = False
        state.pending_source = None
        state.pending_context = None

        if event.success and event.result is not None:
            result = event.result
            self._ingest_command_result(result, ingestor)
            state.mark_attempt(event.completed_at, True)
            payload = {
                **base_payload,
                'written_bytes': result.written_bytes,
                'bytes_read': result.bytes_read,
                'duration_s': result.duration_s,
                'frames': result.frames_as_hex,
                'matched_expectation': result.matched_expectation,
                'runs_completed': state.runs,
                'next_due': state.next_due,
            }
            if calibration_label:
                payload['calibration_label'] = calibration_label
            session_handle.log_event('info', category, f'{label} command executed', payload)
            if not quiet:
                status = 'ok' if result.matched_expectation is not False else 'mismatch'
                print(
                    f"{label} command '{name}' completed in {result.duration_s:.2f}s "
                    f"({event.attempts} attempt(s), {status})"
                )
            return

        if event.expectation_mismatch and event.result is not None:
            result = event.result
            self._ingest_command_result(result, ingestor)
            state.mark_attempt(event.completed_at, False)
            state.last_error = 'expectation mismatch'
            payload = {
                **base_payload,
                'written_bytes': result.written_bytes,
                'bytes_read': result.bytes_read,
                'duration_s': result.duration_s,
                'frames': result.frames_as_hex,
                'expected_hex': result.expected_hex,
                'matched_expectation': result.matched_expectation,
            }
            if calibration_label:
                payload['calibration_label'] = calibration_label
            session_handle.log_event('warning', category, f'{label} command expectation mismatch', payload)
            if not quiet:
                print(f"{label} command '{name}' expectation mismatch after {event.attempts} attempt(s)")
            return

        state.mark_attempt(event.completed_at, False)
        state.last_error = event.error or 'failure'
        payload = {**base_payload, 'error': event.error or 'unknown error'}
        if calibration_label:
            payload['calibration_label'] = calibration_label
        session_handle.log_event('warning', category, f'{label} command failed', payload)
        if not quiet:
            print(
                f"{label} command '{name}' failed after {event.attempts} attempt(s): "
                f"{event.error or 'unknown error'}"
            )

    def _execute_command_with_policy(
        self,
        interface: DeviceInterface,
        definition: CommandDefinition,
        max_retries: int,
        backoff_s: float,
    ) -> tuple[CommandResult, int]:
        retries = max(int(max_retries), 0) if isinstance(max_retries, int) else 0
        try:
            delay = float(backoff_s)
        except (TypeError, ValueError):
            delay = 0.0
        delay = max(delay, 0.0)
        attempts = 0
        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                result = self._command_runner(interface, definition)
            except Exception as exc:  # pylint: disable=broad-except
                last_error = exc
            else:
                if result.expected_hex and result.matched_expectation is False:
                    last_error = CommandExpectationError(result, attempt + 1)
                else:
                    return result, attempt + 1
            attempts = attempt + 1
            if attempt < retries and delay > 0:
                time.sleep(delay * max(attempt + 1, 1))
        if isinstance(last_error, CommandExpectationError):
            raise last_error
        if last_error is None:
            last_error = RuntimeError(f"Command '{definition.name}' failed without diagnostic detail")
        raise CommandExecutionFailure(last_error, attempts)

    def _process_scheduled_commands(
        self,
        interface: DeviceInterface,
        session_handle: SessionHandle,
        ingestor: FrameIngestor,
        now: float,
    ) -> None:
        if not self._scheduled_states:
            return
        if self._use_async_commands:
            self._drain_command_results(session_handle, ingestor)
        for index, state in enumerate(self._scheduled_states):
            if not state.active or state.next_due is None or now < state.next_due:
                continue
            if state.in_flight:
                continue
            self._execute_scheduled_command(
                interface,
                session_handle,
                ingestor,
                state,
                now,
                source='schedule',
                state_index=index,
            )

    def _execute_scheduled_command(
        self,
        interface: DeviceInterface,
        session_handle: SessionHandle,
        ingestor: FrameIngestor,
        state: ScheduledCommandState,
        now: float,
        *,
        source: str,
        state_index: Optional[int] = None,
    ) -> None:
        quiet = self._config.acquisition.quiet
        name = state.config.name
        label = 'Startup' if source == 'startup' else 'Scheduled'
        definition = self._command_definitions.get(name)
        schedule_payload = state.config.to_dict()
        if definition is None:
            session_handle.log_event(
                'warning',
                'command',
                f'{label} command not defined',
                {'command': name, 'source': source, 'schedule': schedule_payload},
            )
            if not quiet:
                profile = self._config.device.profile or '<unspecified>'
                print(f"{label} command '{name}' not defined for profile {profile}")
            state.disable()
            return

        context = self._build_command_context(state, definition)

        if self._use_async_commands and source != 'startup':
            if state_index is None:
                raise ValueError('state_index is required for async command execution')
            if state.in_flight:
                return
            state.last_error = None
            self._queue_command_task(state_index, state, source, context)
            return

        try:
            result, attempts = self._execute_command_with_policy(
                interface,
                context.definition,
                context.retries,
                context.backoff_s,
            )
        except CommandExpectationError as exc:
            result = exc.result
            self._ingest_command_result(result, ingestor)
            state.mark_attempt(now, False)
            state.last_error = 'expectation mismatch'
            payload = {
                'command': name,
                'source': source,
                'attempts': exc.attempts,
                'written_bytes': result.written_bytes,
                'bytes_read': result.bytes_read,
                'duration_s': result.duration_s,
                'frames': result.frames_as_hex,
                'expected_hex': result.expected_hex,
                'matched_expectation': result.matched_expectation,
                'schedule': context.schedule_payload,
            }
            if context.calibration_label:
                payload['calibration_label'] = context.calibration_label
            session_handle.log_event('warning', context.category, f'{label} command expectation mismatch', payload)
            if not quiet:
                print(f"{label} command '{name}' expectation mismatch after {exc.attempts} attempt(s)")
            return
        except CommandExecutionFailure as exc:
            state.mark_attempt(now, False)
            state.last_error = str(exc.original)
            payload = {
                'command': name,
                'source': source,
                'attempts': exc.attempts,
                'error': str(exc.original),
                'schedule': context.schedule_payload,
            }
            if context.calibration_label:
                payload['calibration_label'] = context.calibration_label
            session_handle.log_event('warning', context.category, f'{label} command failed', payload)
            if not quiet:
                print(f"{label} command '{name}' failed after {exc.attempts} attempt(s): {exc.original}")
            return

        self._ingest_command_result(result, ingestor)
        state.mark_attempt(now, True)
        payload = {
            'command': name,
            'source': source,
            'attempts': attempts,
            'written_bytes': result.written_bytes,
            'bytes_read': result.bytes_read,
            'duration_s': result.duration_s,
            'frames': result.frames_as_hex,
            'matched_expectation': result.matched_expectation,
            'schedule': context.schedule_payload,
            'runs_completed': state.runs,
            'next_due': state.next_due,
        }
        if context.calibration_label:
            payload['calibration_label'] = context.calibration_label
        session_handle.log_event('info', context.category, f'{label} command executed', payload)
        if not quiet:
            status = 'ok' if result.matched_expectation is not False else 'mismatch'
            print(
                f"{label} command '{name}' completed in {result.duration_s:.2f}s "
                f"({attempts} attempt(s), {status})"
            )

    def _run_startup_commands(
        self,
        interface: DeviceInterface,
        session_handle,
        ingestor: Optional[FrameIngestor],
    ) -> None:
        acquisition_cfg = self._config.acquisition
        quiet = acquisition_cfg.quiet
        commands = acquisition_cfg.startup_commands
        if commands:
            for name in commands:
                definition = self._command_definitions.get(name)
                if definition is None:
                    session_handle.log_event(
                        'warning',
                        'command',
                        'Startup command not defined',
                        {'command': name},
                    )
                    if not quiet:
                        profile = self._config.device.profile or '<unspecified>'
                        print(f"Startup command '{name}' not defined for profile {profile}")
                    continue
                retries = definition.default_max_retries or 0
                backoff = definition.default_retry_backoff_s or 1.0
                try:
                    result, attempts = self._execute_command_with_policy(interface, definition, retries, backoff)
                except CommandExpectationError as exc:
                    result = exc.result
                    self._ingest_command_result(result, ingestor)
                    payload = {
                        'command': name,
                        'attempts': exc.attempts,
                        'written_bytes': result.written_bytes,
                        'bytes_read': result.bytes_read,
                        'duration_s': result.duration_s,
                        'frames': result.frames_as_hex,
                        'expected_hex': result.expected_hex,
                        'matched_expectation': result.matched_expectation,
                    }
                    session_handle.log_event('warning', 'command', 'Startup command expectation mismatch', payload)
                    if not quiet:
                        print(f"Startup command '{name}' expectation mismatch after {exc.attempts} attempt(s)")
                    continue
                except CommandExecutionFailure as exc:
                    payload = {
                        'command': name,
                        'attempts': exc.attempts,
                        'error': str(exc.original),
                    }
                    session_handle.log_event('warning', 'command', 'Startup command failed', payload)
                    if not quiet:
                        print(f"Startup command '{name}' failed after {exc.attempts} attempt(s): {exc.original}")
                    continue
                self._ingest_command_result(result, ingestor)
                event_payload = {
                    'command': result.name,
                    'attempts': attempts,
                    'written_bytes': result.written_bytes,
                    'bytes_read': result.bytes_read,
                    'duration_s': result.duration_s,
                    'frames': result.frames_as_hex,
                }
                if result.expected_hex:
                    event_payload['expected_hex'] = result.expected_hex
                    event_payload['matched_expectation'] = result.matched_expectation
                session_handle.log_event('info', 'command', 'Startup command executed', event_payload)
                if not quiet:
                    status = 'ok' if result.matched_expectation is not False else 'mismatch'
                    print(
                        f"Startup command '{result.name}' completed ({result.bytes_read} byte(s) read, {status})"
                    )
        if not self._scheduled_states or ingestor is None:
            return
        for index, state in enumerate(self._scheduled_states):
            if not state.active or not state.config.run_on_startup:
                continue
            now = time.time()
            self._execute_scheduled_command(
                interface,
                session_handle,
                ingestor,
                state,
                now,
                source='startup',
                state_index=index,
            )

    def run(self) -> None:
        acquisition_cfg = self._config.acquisition
        device_cfg = self._config.device
        self._database.initialise()
        interface = self._interface_factory()
        self._start_command_worker(interface)
        listed: Optional[ListedDevice] = None
        session_handle = None
        ingestor: Optional[FrameIngestor] = None
        analytics_engine: Optional[AnalyticsEngine] = None
        start_time = time.time()
        next_status: Optional[float] = (
            time.time() + acquisition_cfg.status_interval_s
            if acquisition_cfg.status_interval_s > 0
            else None
        )
        try:
            while not self._stop_requested:
                if acquisition_cfg.max_runtime_s > 0 and (time.time() - start_time) >= acquisition_cfg.max_runtime_s:
                    break
                if listed is None:
                    with self._interface_lock:
                        listed = interface.open()
                    metadata = DeviceMetadata(
                        serial=listed.serial,
                        description=listed.description,
                        model=None,
                    )
                    session_context: Dict[str, Any] = {
                        'device.profile': device_cfg.profile,
                        'device.poll_hex': device_cfg.poll_hex,
                        'device.poll_interval_s': device_cfg.poll_interval_s,
                        'device.baud': device_cfg.baud,
                        'device.data_bits': device_cfg.data_bits,
                        'device.stop_bits': device_cfg.stop_bits,
                        'device.parity': device_cfg.parity,
                        'device.latency_timer_ms': device_cfg.latency_timer_ms,
                    }
                    session_handle = self._database.start_session(datetime.utcnow(), metadata, session_context)
                    analytics_engine = None
                    if getattr(self._config, 'analytics', None) and self._config.analytics.enabled:
                        analytics_engine = AnalyticsEngine(self._config.analytics)
                    ingestor = FrameIngestor(self._config.ingestion, session_handle, analytics=analytics_engine)
                    self._reset_schedule(time.time())
                    session_handle.log_event(
                        'info',
                        'session',
                        'Session started',
                        {
                            'device_index': device_cfg.index,
                            'device_serial': device_cfg.serial or listed.serial,
                            'profile': device_cfg.profile,
                        },
                    )
                    if not acquisition_cfg.quiet:
                        label = listed.description or listed.serial or f"index {listed.index}"
                        print(f"Session {session_handle.id} started for device {label}")
                assert session_handle is not None
                assert ingestor is not None
                self._run_startup_commands(interface, session_handle, ingestor)
                self._stats.last_window_started = datetime.utcnow()

                def _handle(frame: bytes) -> None:
                    record = ingestor.handle_frame(frame)
                    if record is None:
                        return
                    self._stats.frames = ingestor.frames
                    self._stats.last_frame_at = datetime.utcnow()

                try:
                    lock_acquired = False
                    if self._use_async_commands:
                        lock_acquired = self._interface_lock.acquire(blocking=False)
                        if not lock_acquired:
                            time.sleep(0.05)
                            if self._use_async_commands and session_handle is not None:
                                self._drain_command_results(session_handle, ingestor)
                            continue
                    else:
                        self._interface_lock.acquire()
                        lock_acquired = True
                    try:
                        bytes_read = interface.run_window(
                            acquisition_cfg.window_s,
                            frame_handler=_handle,
                            log_path=None,
                            print_raw=False,
                        )
                    finally:
                        if lock_acquired:
                            self._interface_lock.release()
                    self._stats.bytes_read += bytes_read
                    self._stats.last_window_bytes = bytes_read
                    if bytes_read:
                        session_handle.log_event(
                            'debug',
                            'capture',
                            'Window captured data',
                            {
                                'bytes': bytes_read,
                                'frames_total': self._stats.frames,
                            },
                        )
                    if self._use_async_commands:
                        self._drain_command_results(session_handle, ingestor)
                    self._process_scheduled_commands(interface, session_handle, ingestor, time.time())

                except KeyboardInterrupt:
                    self.request_stop()
                    session_handle.log_event('info', 'session', 'Session interrupted by user')
                    break
                except Exception as exc:  # pylint: disable=broad-except
                    with self._interface_lock:
                        interface.close()
                    if session_handle is not None:
                        session_handle.log_event(
                            'warning',
                            'capture',
                            'Capture window failed',
                            {
                                'error': str(exc),
                                'restart_delay_s': acquisition_cfg.restart_delay_s,
                            },
                        )
                    listed = None
                    if not acquisition_cfg.quiet:
                        print(
                            f"Warning: capture window failed: {exc}. Retrying after {acquisition_cfg.restart_delay_s}s",
                        )
                    time.sleep(max(acquisition_cfg.restart_delay_s, 0.5))
                    continue
                if acquisition_cfg.idle_s > 0:
                    time.sleep(acquisition_cfg.idle_s)
                    if self._use_async_commands:
                        self._drain_command_results(session_handle, ingestor)
                    self._process_scheduled_commands(interface, session_handle, ingestor, time.time())
                if next_status and time.time() >= next_status and not acquisition_cfg.quiet:
                    print(
                        f"Frames: {ingestor.frames}, Bytes: {self._stats.bytes_read}, Session: {session_handle.id}",
                    )
                    next_status = time.time() + acquisition_cfg.status_interval_s
        finally:
            if session_handle is not None:
                if self._use_async_commands and ingestor is not None:
                    self._drain_command_results(session_handle, ingestor)
                session_handle.log_event('info', 'session', 'Session closing')
                session_handle.close(datetime.utcnow())
            self._shutdown_command_worker()
            analytics_engine = None
            with self._interface_lock:
                interface.close()
