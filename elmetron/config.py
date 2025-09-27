"""Configuration management for the Elmetron Data Acquisition and Analysis Suite."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

DEFAULT_POLL_HEX = "01 23 30 23 30 23 30 23 03"

CONTROL_LINE_STATES = {'set', 'clear', 'ignore'}

DEFAULT_CSV_COMPACT_FIELDS = (
    'measurement_id',
    'measurement_timestamp',
    'captured_at',
    'value',
    'unit',
    'temperature',
    'temperature_unit',
    'analytics_moving_average',
    'analytics_stability_index',
    'analytics_temperature_compensation_adjusted_value',
)

DEFAULT_COMPACT_FLATTEN_ANALYTICS = (
    'moving_average',
    'stability_index',
    'temperature_compensation.adjusted_value',
)

DEFAULT_COMPACT_FLATTEN_PAYLOAD = (
    'measurement.mode',
)


def _coerce_tuple(value: Any) -> Tuple[str, ...]:
    """Return *value* as a tuple of strings, normalising `None` to `()`."""

    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    if isinstance(value, (set, frozenset)):
        return tuple(value)
    if isinstance(value, str):
        return (value,) if value else ()
    try:
        return tuple(value)  # type: ignore[arg-type]
    except TypeError:
        return (str(value),) if value is not None else ()


if TYPE_CHECKING:
    from .protocols.registry import ProtocolProfile


@dataclass(slots=True)
class DeviceConfig:
    """Low-level transport parameters for CX-505 compatible meters."""

    profile: Optional[str] = "cx505"
    use_profile_defaults: bool = True
    index: int = 0
    serial: Optional[str] = None
    transport: str = "ftdi"
    handshake: Optional[str] = None
    baud: int = 115200
    data_bits: int = 8
    stop_bits: float = 2.0
    parity: str = "E"
    read_timeout_ms: int = 500
    write_timeout_ms: int = 500
    chunk_size: int = 256
    latency_timer_ms: int = 2
    poll_hex: Optional[str] = DEFAULT_POLL_HEX
    poll_interval_s: Optional[float] = 1.0
    dtr: str = "set"
    rts: str = "set"
    open_retry_attempts: int = 5
    open_retry_backoff_s: float = 0.5
    ble_address: Optional[str] = None
    ble_read_characteristic: Optional[str] = None
    ble_write_characteristic: Optional[str] = None
    ble_notify_characteristic: Optional[str] = None
    fallback_profiles: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.dtr = self._normalise_control(self.dtr, "dtr")
        self.rts = self._normalise_control(self.rts, "rts")
        profiles: list[str] = []
        seen: set[str] = set()
        for entry in _coerce_tuple(self.fallback_profiles):
            if entry is None:
                continue
            candidate = str(entry).strip()
            if not candidate:
                continue
            lowered = candidate.lower()
            if lowered in seen:
                continue
            profiles.append(candidate)
            seen.add(lowered)
        self.fallback_profiles = tuple(profiles)
        try:
            attempts = int(self.open_retry_attempts)
        except (TypeError, ValueError):
            attempts = 1
        self.open_retry_attempts = max(attempts, 1)
        try:
            backoff = float(self.open_retry_backoff_s)
        except (TypeError, ValueError):
            backoff = 0.5
        if backoff < 0:
            backoff = 0.0
        self.open_retry_backoff_s = backoff

    @staticmethod
    def _normalise_control(value: Optional[str], label: str) -> str:
        candidate = (value or "set").lower()
        if candidate not in CONTROL_LINE_STATES:
            allowed = ", ".join(sorted(CONTROL_LINE_STATES))
            raise ValueError(f"{label} must be one of {allowed}")
        return candidate

    def apply_profile(self, profile: "ProtocolProfile") -> None:
        if profile.transport:
            self.transport = profile.transport
        if profile.handshake:
            self.handshake = profile.handshake
        if profile.poll_hex and (self.use_profile_defaults or not self.poll_hex):
            self.poll_hex = profile.poll_hex
        if profile.poll_interval_s is not None and (self.use_profile_defaults or self.poll_interval_s is None):
            self.poll_interval_s = float(profile.poll_interval_s)
        if getattr(profile, "ble_address", None) and (self.use_profile_defaults or not self.ble_address):
            self.ble_address = profile.ble_address
        if getattr(profile, "ble_read_characteristic", None) and (self.use_profile_defaults or not self.ble_read_characteristic):
            self.ble_read_characteristic = profile.ble_read_characteristic
        if getattr(profile, "ble_write_characteristic", None) and (self.use_profile_defaults or not self.ble_write_characteristic):
            self.ble_write_characteristic = profile.ble_write_characteristic
        if getattr(profile, "ble_notify_characteristic", None) and (self.use_profile_defaults or not self.ble_notify_characteristic):
            self.ble_notify_characteristic = profile.ble_notify_characteristic
        if not self.use_profile_defaults:
            return
        if profile.baud is not None:
            self.baud = int(profile.baud)
        if profile.data_bits is not None:
            self.data_bits = int(profile.data_bits)
        if profile.stop_bits is not None:
            self.stop_bits = float(profile.stop_bits)
        if profile.parity is not None:
            self.parity = str(profile.parity)
        if profile.read_timeout_ms is not None:
            self.read_timeout_ms = int(profile.read_timeout_ms)
        if profile.write_timeout_ms is not None:
            self.write_timeout_ms = int(profile.write_timeout_ms)
        if profile.chunk_size is not None:
            self.chunk_size = int(profile.chunk_size)
        if profile.latency_timer_ms is not None:
            self.latency_timer_ms = int(profile.latency_timer_ms)


@dataclass(slots=True)
class ScheduledCommandConfig:
    '''Configuration for recurring or event-driven protocol commands.'''

    name: str
    run_on_startup: bool = False
    interval_s: Optional[float] = None
    first_delay_s: float = 0.0
    max_runs: Optional[int] = None
    max_retries: Optional[int] = None
    retry_backoff_s: Optional[float] = None
    calibration_label: Optional[str] = None
    enabled: bool = True

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError('scheduled command name cannot be empty')
        if self.interval_s is not None and self.interval_s <= 0:
            raise ValueError('interval_s must be greater than 0 when provided')
        if self.first_delay_s < 0:
            self.first_delay_s = 0.0
        if self.max_runs is not None and self.max_runs <= 0:
            self.max_runs = None
        if self.max_retries is not None and self.max_retries < 0:
            self.max_retries = 0
        if self.retry_backoff_s is not None and self.retry_backoff_s <= 0:
            self.retry_backoff_s = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'run_on_startup': self.run_on_startup,
            'interval_s': self.interval_s,
            'first_delay_s': self.first_delay_s,
            'max_runs': self.max_runs,
            'max_retries': self.max_retries,
            'retry_backoff_s': self.retry_backoff_s,
            'calibration_label': self.calibration_label,
            'enabled': self.enabled,
        }


@dataclass(slots=True)
class AcquisitionConfig:
    '''Runtime behaviour of the acquisition service.'''

    window_s: float = 10.0
    idle_s: float = 0.0
    restart_delay_s: float = 2.0
    status_interval_s: float = 30.0
    max_runtime_s: float = 0.0
    quiet: bool = False
    startup_commands: list[str] = field(default_factory=list)
    scheduled_commands: list[ScheduledCommandConfig] = field(default_factory=list)
    default_command_max_retries: int = 1
    default_command_retry_backoff_s: float = 1.0
    decode_failure_threshold: int = 5
    lab_retry_enabled: bool = False
    lab_retry_max_retries: Optional[int] = None
    lab_retry_backoff_s: Optional[float] = None
    lab_retry_categories: Tuple[str, ...] = ('calibration',)
    lab_retry_commands: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.startup_commands = [cmd.strip() for cmd in self.startup_commands if isinstance(cmd, str) and cmd.strip()]
        normalised: list[ScheduledCommandConfig] = []
        for entry in self.scheduled_commands:
            if isinstance(entry, ScheduledCommandConfig):
                normalised.append(entry)
            elif isinstance(entry, dict):
                normalised.append(ScheduledCommandConfig(**entry))
            else:
                raise TypeError(f"Unsupported scheduled command payload: {type(entry).__name__}")
        self.scheduled_commands = normalised
        try:
            retries = int(self.default_command_max_retries)
        except (TypeError, ValueError):
            retries = 0
        self.default_command_max_retries = max(retries, 0)
        try:
            backoff = float(self.default_command_retry_backoff_s)
        except (TypeError, ValueError):
            backoff = 1.0
        if backoff < 0:
            backoff = 0.0
        self.default_command_retry_backoff_s = backoff
        try:
            threshold = int(self.decode_failure_threshold)
        except (TypeError, ValueError):
            threshold = 5
        self.decode_failure_threshold = max(threshold, 1)
        try:
            overrides = int(self.lab_retry_max_retries) if self.lab_retry_max_retries is not None else None
        except (TypeError, ValueError):
            overrides = None
        self.lab_retry_max_retries = overrides if overrides is None or overrides >= 0 else None
        try:
            backoff = float(self.lab_retry_backoff_s) if self.lab_retry_backoff_s is not None else None
        except (TypeError, ValueError):
            backoff = None
        if backoff is not None and backoff < 0:
            backoff = 0.0
        self.lab_retry_backoff_s = backoff
        self.lab_retry_categories = _coerce_tuple(self.lab_retry_categories)
        self.lab_retry_commands = _coerce_tuple(self.lab_retry_commands)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'window_s': self.window_s,
            'idle_s': self.idle_s,
            'restart_delay_s': self.restart_delay_s,
            'status_interval_s': self.status_interval_s,
            'max_runtime_s': self.max_runtime_s,
            'quiet': self.quiet,
            'startup_commands': self.startup_commands,
            'scheduled_commands': [config.to_dict() for config in self.scheduled_commands],
            'default_command_max_retries': self.default_command_max_retries,
            'default_command_retry_backoff_s': self.default_command_retry_backoff_s,
            'decode_failure_threshold': self.decode_failure_threshold,
            'lab_retry_enabled': self.lab_retry_enabled,
            'lab_retry_max_retries': self.lab_retry_max_retries,
            'lab_retry_backoff_s': self.lab_retry_backoff_s,
            'lab_retry_categories': self.lab_retry_categories,
            'lab_retry_commands': self.lab_retry_commands,
        }


@dataclass(slots=True)
class StorageConfig:
    """Database and retention settings."""

    database_path: Path = Path("data/elmetron.sqlite")
    ensure_directories: bool = True
    vacuum_on_start: bool = False
    retention_days: Optional[int] = 90

    def __post_init__(self) -> None:
        if isinstance(self.database_path, str):
            self.database_path = Path(self.database_path)


@dataclass(slots=True)
class IngestionConfig:
    """Controls for how frames are decoded into structured events."""

    annotate_device: bool = True
    enrich_with_timestamp: bool = True
    emit_raw_frame: bool = True


@dataclass(slots=True)
class AnalyticsConfig:
    """Configuration for derived metric calculations."""

    enabled: bool = True
    moving_average_window: int = 5
    stability_window: int = 12
    temperature_coefficient: float = 0.0
    reference_temperature: float = 25.0
    max_history: int = 256
    profiling_enabled: bool = False
    max_frames_per_minute: Optional[int] = None

    def __post_init__(self) -> None:
        if self.moving_average_window < 1:
            self.moving_average_window = 1
        if self.stability_window < 2:
            self.stability_window = 2
        if self.max_history < max(self.moving_average_window, self.stability_window):
            self.max_history = max(self.moving_average_window, self.stability_window)
        if self.max_frames_per_minute is not None and self.max_frames_per_minute <= 0:
            self.max_frames_per_minute = None


@dataclass(slots=True)
class ExportConfig:
    """Controls for CSV/JSON/LIMS style exports."""

    default_format: str = 'csv'
    export_directory: Path = Path('exports')
    csv_mode: str = 'compact'
    csv_compact_fields: Tuple[str, ...] = DEFAULT_CSV_COMPACT_FIELDS
    csv_include_payload_json: bool = False
    csv_include_analytics_json: bool = False
    csv_flatten_payload: Tuple[str, ...] = DEFAULT_COMPACT_FLATTEN_PAYLOAD
    csv_flatten_analytics: Tuple[str, ...] = DEFAULT_COMPACT_FLATTEN_ANALYTICS
    csv_payload_prefix: str = 'payload_'
    csv_analytics_prefix: str = 'analytics_'
    pdf_template: Optional[Path] = None
    pdf_recent_limit: int = 10
    lims_template: Optional[Path] = None

    def __post_init__(self) -> None:
        if isinstance(self.export_directory, str):
            self.export_directory = Path(self.export_directory)
        self.csv_mode = (self.csv_mode or 'full').lower()
        if self.csv_mode not in {'full', 'compact'}:
            raise ValueError("csv_mode must be 'full' or 'compact'")
        self.csv_compact_fields = _coerce_tuple(self.csv_compact_fields)
        self.csv_flatten_payload = _coerce_tuple(self.csv_flatten_payload)
        self.csv_flatten_analytics = _coerce_tuple(self.csv_flatten_analytics)
        if self.csv_mode == 'compact':
            if not self.csv_compact_fields:
                self.csv_compact_fields = DEFAULT_CSV_COMPACT_FIELDS
            if not self.csv_flatten_analytics:
                self.csv_flatten_analytics = DEFAULT_COMPACT_FLATTEN_ANALYTICS
            if not self.csv_flatten_payload:
                self.csv_flatten_payload = DEFAULT_COMPACT_FLATTEN_PAYLOAD
        if isinstance(self.pdf_template, str) and self.pdf_template:
            self.pdf_template = Path(self.pdf_template)
        if isinstance(self.lims_template, str) and self.lims_template:
            self.lims_template = Path(self.lims_template)
        if self.pdf_recent_limit <= 0:
            self.pdf_recent_limit = 10



@dataclass(slots=True)
class MonitoringConfig:
    """Monitoring and health-related checks."""

    log_rotation_task: Optional[str] = None
    log_rotation_max_age_minutes: int = 180
    log_rotation_probe_interval_s: int = 120

    def to_dict(self) -> Dict[str, Any]:
        return {
            'log_rotation_task': self.log_rotation_task,
            'log_rotation_max_age_minutes': self.log_rotation_max_age_minutes,
            'log_rotation_probe_interval_s': self.log_rotation_probe_interval_s,
        }


@dataclass(slots=True)
class AppConfig:
    """Top-level application configuration bundle."""

    device: DeviceConfig = field(default_factory=DeviceConfig)
    acquisition: AcquisitionConfig = field(default_factory=AcquisitionConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AppConfig":
        """Create a configuration instance from a nested dictionary."""

        def _section(name: str, factory: Any) -> Any:
            data = payload.get(name, {}) if payload else {}
            if isinstance(data, dict):
                return factory(**data)
            raise TypeError(f"Expected mapping for section '{name}', got {type(data).__name__}")

        return cls(
            device=_section("device", DeviceConfig),
            acquisition=_section("acquisition", AcquisitionConfig),
            storage=_section("storage", StorageConfig),
            ingestion=_section("ingestion", IngestionConfig),
            analytics=_section("analytics", AnalyticsConfig),
            export=_section("export", ExportConfig),
            monitoring=_section("monitoring", MonitoringConfig),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the configuration."""

        def _asdict(obj: Any) -> Dict[str, Any]:
            return {field: getattr(obj, field) for field in obj.__dataclass_fields__}  # type: ignore[attr-defined]

        acquisition_payload = (
            self.acquisition.to_dict() if hasattr(self.acquisition, 'to_dict') else _asdict(self.acquisition)
        )

        export_payload = _asdict(self.export)
        monitoring_payload = (
            self.monitoring.to_dict() if hasattr(self.monitoring, 'to_dict') else _asdict(self.monitoring)
        )

        export_payload['export_directory'] = str(self.export.export_directory)
        export_payload['csv_compact_fields'] = list(self.export.csv_compact_fields)
        export_payload['csv_flatten_payload'] = list(self.export.csv_flatten_payload)
        export_payload['csv_flatten_analytics'] = list(self.export.csv_flatten_analytics)
        export_payload['pdf_template'] = (str(self.export.pdf_template) if self.export.pdf_template else None)
        export_payload['lims_template'] = (str(self.export.lims_template) if self.export.lims_template else None)

        return {
            'device': _asdict(self.device),
            'acquisition': acquisition_payload,
            'storage': {**_asdict(self.storage), 'database_path': str(self.storage.database_path)},
            'ingestion': _asdict(self.ingestion),
            'analytics': _asdict(self.analytics),
            'export': export_payload,
            'monitoring': monitoring_payload,
        }


def load_config(path: Optional[Path]) -> AppConfig:
    """Load configuration from *path* if provided, otherwise return defaults."""

    if path is None:
        return AppConfig()
    resolved = path.expanduser()
    if not resolved.exists():
        return AppConfig()
    payload: Dict[str, Any]
    suffix = resolved.suffix.lower()
    if suffix in {".json", ".jsn"}:
        payload = _load_json(resolved)
    elif suffix in {".toml", ".tml"}:
        payload = _load_toml(resolved)
    elif suffix in {".yaml", ".yml"}:
        payload = _load_yaml(resolved)
    else:
        raise ValueError(f"Unsupported configuration format: {resolved.suffix}")
    return AppConfig.from_dict(payload)


def _load_json(path: Path) -> Dict[str, Any]:
    import json

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_toml(path: Path) -> Dict[str, Any]:
    try:
        import tomllib  # Python >= 3.11
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime guard
        raise RuntimeError("tomllib is required to parse TOML configuration files") from exc
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("PyYAML is required to parse YAML configuration files") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
