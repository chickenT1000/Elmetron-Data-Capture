"""Export utilities for captured measurement datasets."""
from __future__ import annotations

import argparse
import csv
import getpass
import gzip
import hashlib
import json
import platform
import shutil
import socket
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING
import xml.etree.ElementTree as ET

from .session import iter_session_measurements, load_session_summary

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from elmetron.config import ExportConfig

DEFAULT_COMPACT_FIELDS: Tuple[str, ...] = (
    "measurement_id",
    "measurement_timestamp",
    "captured_at",
    "value",
    "unit",
    "temperature",
    "temperature_unit",
    "analytics_moving_average",
    "analytics_stability_index",
    "analytics_temperature_compensation_adjusted_value",
)

CONTENT_TYPE_MAP: dict[str, str] = {
    "csv": "text/csv",
    "json": "application/json",
    "xml": "application/xml",
    "pdf": "application/pdf",
}


def export_csv(
    records: Iterable[Mapping[str, object]],
    output: Path,
    fields: Optional[Sequence[str]] = None,
) -> Path:
    """Write the given *records* to *output* as CSV."""

    output.parent.mkdir(parents=True, exist_ok=True)
    iterator = list(records)
    if not iterator:
        output.write_text("", encoding="utf-8")
        return output

    def _normalise(row: Mapping[str, object]) -> Mapping[str, object]:
        normalised: dict[str, object] = {}
        for key, value in row.items():
            if isinstance(value, (dict, list, tuple)):
                normalised[key] = json.dumps(value, ensure_ascii=False)
            else:
                normalised[key] = value
        return normalised

    fieldnames = list(fields) if fields else sorted({key for record in iterator for key in record.keys()})
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in iterator:
            writer.writerow(_normalise(record))
    return output


@dataclass(slots=True)
class CsvExportOptions:
    """Behavioural toggles for session CSV exports."""

    include_payload_json: bool = True
    include_analytics_json: bool = True
    flatten_payload_paths: Optional[Tuple[str, ...]] = None
    flatten_analytics_paths: Optional[Tuple[str, ...]] = None
    payload_prefix: str = "payload_"
    analytics_prefix: str = "analytics_"
    compact: bool = False
    compact_fields: Tuple[str, ...] = DEFAULT_COMPACT_FIELDS

    def __post_init__(self) -> None:
        if self.flatten_payload_paths is None:
            self.flatten_payload_paths = ()
        if self.flatten_analytics_paths is None:
            self.flatten_analytics_paths = ()
        if self.compact:
            if not self.flatten_analytics_paths:
                self.flatten_analytics_paths = (
                    "moving_average",
                    "stability_index",
                    "temperature_compensation.adjusted_value",
                )
            if not self.flatten_payload_paths:
                self.flatten_payload_paths = (
                    "measurement.mode",
                )
            if self.include_payload_json:
                self.include_payload_json = False
            if self.include_analytics_json:
                self.include_analytics_json = False
            if not self.compact_fields:
                self.compact_fields = DEFAULT_COMPACT_FIELDS


def csv_options_from_config(config: "ExportConfig") -> CsvExportOptions:
    """Build CSV export options from an `ExportConfig` instance."""

    options = CsvExportOptions(
        include_payload_json=config.csv_include_payload_json,
        include_analytics_json=config.csv_include_analytics_json,
        flatten_payload_paths=tuple(config.csv_flatten_payload),
        flatten_analytics_paths=tuple(config.csv_flatten_analytics),
        payload_prefix=config.csv_payload_prefix,
        analytics_prefix=config.csv_analytics_prefix,
        compact=config.csv_mode == "compact",
        compact_fields=tuple(config.csv_compact_fields),
    )
    return options

@dataclass(slots=True)
class ExportArtifact:
    """Represents an artefact produced by an export run."""

    session_id: int
    format: str
    path: Path
    relative_path: str
    size_bytes: int
    checksum: Optional[str] = None
    compressed: bool = False
    content_type: Optional[str] = None



def export_session_csv(
    database_path: Path,
    session_id: int,
    output: Path,
    fields: Optional[Sequence[str]] = None,
    *,
    options: Optional[CsvExportOptions] = None,
) -> Path:
    """Export a capture session to CSV at *output*."""

    opt = options or CsvExportOptions()
    records = list(iter_session_measurements(database_path, session_id))
    flattened: List[Mapping[str, object]] = []
    for record in records:
        flattened.append(_prepare_csv_row(record, opt))
    if opt.compact and not fields:
        fields = list(opt.compact_fields)
    return export_csv(flattened, output, fields)


def export_session_json(
    database_path: Path,
    session_id: int,
    output: Path,
    indent: int = 2,
) -> Path:
    """Export a capture session to JSON, including analytics payloads when present."""

    output.parent.mkdir(parents=True, exist_ok=True)
    records = list(iter_session_measurements(database_path, session_id))
    output.write_text(json.dumps(records, ensure_ascii=False, indent=indent), encoding="utf-8")
    return output


def export_session_lims_xml(
    database_path: Path,
    session_id: int,
    output: Path,
    template: Optional[Path] = None,
) -> Path:
    """Generate a LIMS-friendly XML export for the capture session."""

    output.parent.mkdir(parents=True, exist_ok=True)
    summary = load_session_summary(database_path, session_id)
    measurements = list(iter_session_measurements(database_path, session_id))
    generated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    root = _build_lims_xml_tree(session_id, summary, measurements)
    if template:
        default_xml = ET.tostring(root, encoding="unicode")
        measurements_el = root.find("Measurements")
        metadata_el = root.find("Metadata")
        context = {
            "session_id": session_id,
            "summary": summary or {},
            "measurements": measurements,
            "recent_measurements": measurements[:10],
            "generated_at": generated_at,
            "default_xml": default_xml,
            "metadata_xml": _stringify_element(metadata_el) if metadata_el is not None else "",
            "measurements_xml": _stringify_children(measurements_el) if measurements_el is not None else "",
        }
        rendered = _render_template(template, context, expect_xml=True)
        output.write_text(rendered, encoding="utf-8")
        return output
    tree = ET.ElementTree(root)
    tree.write(output, encoding="utf-8", xml_declaration=True)
    return output


def export_session_pdf(
    database_path: Path,
    session_id: int,
    output: Path,
    template: Optional[Path] = None,
    recent_limit: int = 10,
) -> Path:
    """Render a lightweight PDF summary for the capture session."""

    summary = load_session_summary(database_path, session_id)
    records = list(iter_session_measurements(database_path, session_id))
    generated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    recent = records[:recent_limit]
    default_lines = _build_default_pdf_lines(session_id, summary, records, generated_at, recent_limit)
    if template:
        context = {
            "session_id": session_id,
            "summary": summary or {},
            "measurements": records,
            "recent_measurements": recent,
            "generated_at": generated_at,
            "recent_limit": recent_limit,
            "default_lines": default_lines,
        }
        rendered = _render_template(template, context)
        lines = [line.rstrip("\n") for line in rendered.splitlines()]
    else:
        lines = default_lines
    _write_simple_pdf(lines, output)
    return output


def _prepare_csv_row(record: Mapping[str, Any], options: CsvExportOptions) -> Mapping[str, Any]:
    row = dict(record)
    payload = row.pop("payload", {}) or {}
    analytics = row.pop("analytics", None)
    if options.include_payload_json:
        row["payload_json"] = json.dumps(payload, ensure_ascii=False)
    if options.include_analytics_json and analytics is not None:
        row["analytics_json"] = json.dumps(analytics, ensure_ascii=False)
    for path in options.flatten_payload_paths or ():
        column = f"{options.payload_prefix}{_normalise_path(path)}"
        row[column] = _extract_path(payload, path)
    for path in options.flatten_analytics_paths or ():
        column = f"{options.analytics_prefix}{_normalise_path(path)}"
        row[column] = _extract_path(analytics or {}, path)
    return row


def _normalise_path(path: str | Sequence[str]) -> str:
    if isinstance(path, str):
        return path.replace(".", "_")
    return "_".join(path)


def _extract_path(data: Any, path: str | Sequence[str]) -> Any:
    if data is None:
        return None
    if isinstance(path, str):
        parts = [segment for segment in path.split(".") if segment]
    else:
        parts = list(path)
    current: Any = data
    for part in parts:
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return None
    return current


def _build_lims_xml_tree(
    session_id: int,
    summary: Optional[Mapping[str, Any]],
    measurements: Sequence[Mapping[str, Any]],
) -> ET.Element:
    root = ET.Element("Session", attrib={"id": str(session_id)})
    if summary:
        meta = ET.SubElement(root, "Metadata")
        meta.set("started_at", summary.get("started_at") or "")
        meta.set("ended_at", summary.get("ended_at") or "")
        instrument = summary.get("instrument") or {}
        instrument_el = ET.SubElement(meta, "Instrument")
        instrument_el.set("serial", instrument.get("serial") or "")
        instrument_el.set("description", instrument.get("description") or "")
        instrument_el.set("model", instrument.get("model") or "")
        meta.set("measurement_count", str(summary.get("measurements", 0)))
        metadata = summary.get("metadata") or {}
        if metadata:
            metadata_el = ET.SubElement(meta, "Tags")
            for key, value in sorted(metadata.items()):
                tag_el = ET.SubElement(metadata_el, "Tag", attrib={"key": key})
                tag_el.text = value
    measurements_el = ET.SubElement(root, "Measurements")
    for record in measurements:
        measurement_el = ET.SubElement(
            measurements_el,
            "Measurement",
            attrib={
                "id": str(record.get("measurement_id")),
                "frame_id": str(record.get("frame_id")),
                "timestamp": record.get("measurement_timestamp") or "",
            },
        )
        value = record.get("value")
        ET.SubElement(measurement_el, "Value").text = "" if value is None else str(value)
        ET.SubElement(measurement_el, "Unit").text = record.get("unit") or ""
        if record.get("temperature") is not None:
            temp_el = ET.SubElement(measurement_el, "Temperature")
            temp_el.text = str(record.get("temperature"))
            temp_el.set("unit", record.get("temperature_unit") or "")
        analytics = record.get("analytics")
        if analytics is not None:
            analytics_el = ET.SubElement(measurement_el, "Analytics")
            analytics_el.text = json.dumps(analytics, ensure_ascii=False)
        payload_el = ET.SubElement(measurement_el, "Payload")
        payload_el.text = json.dumps(record.get("payload", {}), ensure_ascii=False)
    return root


def _build_default_pdf_lines(
    session_id: int,
    summary: Optional[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    generated_at: str,
    recent_limit: int,
) -> List[str]:
    lines: List[str] = []
    lines.append(f"Elmetron Session Report #{session_id}")
    lines.append("")
    if summary:
        lines.append(f"Started: {summary.get('started_at') or 'n/a'}")
        lines.append(f"Ended: {summary.get('ended_at') or 'n/a'}")
        instrument = summary.get("instrument") or {}
        joined = ", ".join(
            filter(None, [instrument.get("serial"), instrument.get("model"), instrument.get("description")])
        )
        lines.append(f"Instrument: {joined}")
        lines.append(f"Measurements: {summary.get('measurements', 0)}")
    else:
        lines.append("Session summary unavailable")
    lines.append("")
    lines.append("Recent measurements:")
    for record in records[:recent_limit]:
        timestamp = record.get("measurement_timestamp") or record.get("captured_at") or "n/a"
        value = "n/a" if record.get("value") is None else f"{record['value']!r}"
        unit = record.get("unit") or ""
        lines.append(f" - {timestamp}: {value} {unit}")
    if len(records) > recent_limit:
        lines.append(f"... ({len(records) - recent_limit} more measurements)")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    return lines


def _stringify_element(element: Optional[ET.Element]) -> str:
    if element is None:
        return ""
    return ET.tostring(element, encoding="unicode")


def _stringify_children(element: Optional[ET.Element]) -> str:
    if element is None:
        return ""
    return "".join(ET.tostring(child, encoding="unicode") for child in list(element))


def _render_template(
    template_path: Path,
    context: Mapping[str, Any],
    *,
    expect_xml: bool = False,
) -> str:
    suffix = template_path.suffix.lower()
    if suffix in {".j2", ".jinja", ".jinja2"}:
        try:
            from jinja2 import Environment, FileSystemLoader  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Jinja2 is required to render templates with .j2/.jinja extensions"
            ) from exc
        env = Environment(loader=FileSystemLoader(str(template_path.parent)), autoescape=False)
        template = env.get_template(template_path.name)
        rendered = template.render(**context)
    elif suffix in {".tmpl", ".tpl"}:
        template = Template(template_path.read_text(encoding="utf-8"))
        rendered = template.safe_substitute(_flatten_context(context))
    else:
        mapping = _flatten_context(context)
        rendered = template_path.read_text(encoding="utf-8").format_map(_SafeFormatDict(mapping))
    if expect_xml:
        try:
            ET.fromstring(rendered)
        except ET.ParseError as exc:
            raise ValueError(f"Template '{template_path}' produced invalid XML: {exc}") from exc
    return rendered


def _flatten_context(context: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}

    def _walk(prefix: Optional[str], value: Any) -> None:
        key_prefix = prefix or ""
        if isinstance(value, Mapping):
            if prefix and prefix not in flattened:
                flattened[prefix] = json.dumps(value, ensure_ascii=False)
            for key, sub_val in value.items():
                next_prefix = f"{key_prefix}_{key}" if key_prefix else str(key)
                _walk(next_prefix, sub_val)
        elif isinstance(value, (list, tuple)):
            name = key_prefix or "list"
            flattened[name] = json.dumps(value, ensure_ascii=False)
            flattened[f"{name}_count"] = len(value)
            for index, item in enumerate(value):
                next_prefix = f"{key_prefix}_{index}" if key_prefix else str(index)
                _walk(next_prefix, item)
        else:
            if prefix:
                flattened[prefix] = value

    for key, val in context.items():
        if not isinstance(val, (Mapping, list, tuple)):
            flattened.setdefault(str(key), val)
        _walk(str(key), val)
    return flattened


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def _write_simple_pdf(lines: List[str], output: Path) -> Path:
    """Write *lines* to *output* as a minimal text-based PDF."""

    output.parent.mkdir(parents=True, exist_ok=True)
    escaped_lines = [_escape_pdf_text(line) for line in lines]
    content_parts = [
        "BT",
        "/F1 12 Tf",
        "14 TL",
        "72 720 Td",
    ]
    first = True
    for line in escaped_lines:
        if first:
            content_parts.append(f"({line}) Tj")
            first = False
            continue
        content_parts.append("T*")
        content_parts.append(f"({line}) Tj")
    content_parts.append("ET")
    content_stream = "\n".join(content_parts).encode("utf-8")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"",  # placeholder for stream object
    ]
    stream_header = f"5 0 obj << /Length {len(content_stream)} >> stream\n".encode("utf-8")
    stream_footer = b"\nendstream\nendobj\n"
    objects[4] = stream_header + content_stream + stream_footer
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_position = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("utf-8"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF\n"
        ).encode("utf-8")
    )
    output.write_bytes(pdf)
    return output


def _escape_pdf_text(text: str) -> str:
    """Escape characters that would break PDF text objects."""

    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")



def _handle_export_session(args: argparse.Namespace) -> int:
    database = args.database
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    if args.gzip_level < 1 or args.gzip_level > 9:
        raise ValueError("--gzip-level must be between 1 and 9")

    session_ids = _resolve_session_ids(database, args)
    if not session_ids:
        raise ValueError("No sessions matched the requested selection")
    multiple_sessions = len(session_ids) > 1

    csv_fields: Optional[List[str]] = list(args.csv_fields) if args.csv_fields else None
    csv_options = CsvExportOptions(compact=args.csv_mode == "compact")
    if args.csv_include_payload_json is not None:
        csv_options.include_payload_json = args.csv_include_payload_json
    if args.csv_include_analytics_json is not None:
        csv_options.include_analytics_json = args.csv_include_analytics_json
    if args.csv_flatten_payload:
        csv_options.flatten_payload_paths = tuple(args.csv_flatten_payload)
    if args.csv_flatten_analytics:
        csv_options.flatten_analytics_paths = tuple(args.csv_flatten_analytics)
    if args.csv_payload_prefix:
        csv_options.payload_prefix = args.csv_payload_prefix
    if args.csv_analytics_prefix:
        csv_options.analytics_prefix = args.csv_analytics_prefix



    artifacts: List[ExportArtifact] = []
    archive_entries: List[tuple[Path, str]] = []
    include_checksums = not args.no_checksums
    checksum_algorithm = args.checksum_algorithm if include_checksums else None

    config_path = args.config.expanduser() if args.config else None
    protocols_path = args.protocols.expanduser() if args.protocols else None

    for session_id in session_ids:
        prefix = _derive_prefix(args.prefix, session_id, multiple_sessions)
        for fmt in args.formats:
            if fmt == "csv":
                output = export_session_csv(
                    database,
                    session_id,
                    outdir / f"{prefix}.csv",
                    csv_fields,
                    options=csv_options,
                )
            elif fmt == "json":
                output = export_session_json(database, session_id, outdir / f"{prefix}.json")
            elif fmt == "xml":
                output = export_session_lims_xml(
                    database,
                    session_id,
                    outdir / f"{prefix}.xml",
                    template=args.lims_template,
                )
            elif fmt == "pdf":
                output = export_session_pdf(
                    database,
                    session_id,
                    outdir / f"{prefix}.pdf",
                    template=args.pdf_template,
                    recent_limit=args.pdf_recent_limit,
                )
            else:
                raise ValueError(f"Unsupported format: {fmt}")
            compressed = False
            if args.gzip:
                output = _compress_artifact(output, level=args.gzip_level)
                compressed = True
            artifact = _record_artifact(
                output,
                session_id=session_id,
                fmt=fmt,
                outdir=outdir,
                checksum_algorithm=checksum_algorithm,
                compressed=compressed,
                content_type=_guess_content_type(fmt),
            )
            artifacts.append(artifact)
            archive_entries.append((artifact.path, artifact.relative_path))

    artifact_count = len(artifacts)
    total_size_bytes = sum(item.size_bytes for item in artifacts)
    compressed_count = sum(1 for item in artifacts if item.compressed)

    tool_info = {
        "name": args.manifest_tool_name or "Elmetron Exporter",
        "version": args.manifest_version or "unknown",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "user": getpass.getuser(),
    }

    inputs: dict[str, Any] = {"database": str(database)}
    if config_path:
        inputs["app_config"] = str(config_path)
        inputs["app_config_checksum_sha256"] = _hash_file(config_path)
    if protocols_path:
        inputs["protocols"] = str(protocols_path)
        inputs["protocols_checksum_sha256"] = _hash_file(protocols_path)

    summary = {
        "artifact_count": artifact_count,
        "compressed_artifacts": compressed_count,
        "total_size_bytes": total_size_bytes,
        "checksum_algorithm": checksum_algorithm,
        "manifest_checksum_sha256": None,
    }

    manifest_path: Optional[Path] = None
    manifest_checksum: Optional[str] = None
    manifest_payload: Optional[Dict[str, Any]] = None
    if not args.no_manifest:
        manifest_path, manifest_checksum, manifest_payload = _write_manifest(
            outdir,
            database=database,
            session_ids=session_ids,
            formats=args.formats,
            artifacts=artifacts,
            filename=args.manifest_name,
            checksum_algorithm=checksum_algorithm,
            gzip_enabled=args.gzip,
            prefix=args.prefix,
            tool=tool_info,
            inputs=inputs,
            summary=summary,
        )
        summary["manifest_checksum_sha256"] = manifest_checksum
        archive_entries.append((manifest_path, _relative_path(outdir, manifest_path)))

    manifest_entry = None
    if manifest_path and manifest_checksum:
        manifest_entry = (manifest_checksum, _relative_path(outdir, manifest_path))

    checksum_path: Optional[Path] = None
    if include_checksums and checksum_algorithm:
        checksum_path = _write_checksums(
            outdir,
            session_ids=session_ids,
            artifacts=artifacts,
            filename=args.checksum_name,
            algorithm=checksum_algorithm,
            prefix=args.prefix,
            manifest_entry=manifest_entry,
        )
        if checksum_path:
            archive_entries.append((checksum_path, _relative_path(outdir, checksum_path)))

    if args.archive:
        if manifest_path is None or manifest_payload is None:
            raise ValueError("--archive requires manifest generation; remove --no-manifest")
        archive_format = args.archive_format.lower()
        base_token = _manifest_base(args.prefix, session_ids)
        archive_name = args.archive_name or f"{base_token}_archive.{archive_format}"
        if not archive_name.lower().endswith(f".{archive_format}"):
            archive_name = f"{archive_name}.{archive_format}"
        archive_path = _build_archive(outdir, name=archive_name, files=archive_entries, format=archive_format)
        archive_rel = _relative_path(outdir, archive_path)
        archive_stat = archive_path.stat()
        archive_checksum = _compute_checksum(archive_path, "sha256")
        _write_archive_summary(
            outdir,
            base=base_token,
            manifest_payload=manifest_payload,
            archive_relpath=archive_rel,
            archive_format=archive_format,
            archive_size_bytes=archive_stat.st_size,
            archive_checksum=archive_checksum,
        )

    return 0


def _resolve_session_ids(database: Path, args: argparse.Namespace) -> List[int]:
    if args.session is not None:
        return [args.session]
    if args.sessions:
        return sorted({int(value) for value in args.sessions})
    if args.session_range:
        start, end = args.session_range
        if end < start:
            raise ValueError("--session-range end must be greater than or equal to start")
        return list(range(start, end + 1))
    if args.latest:
        return _fetch_latest_session_ids(database, args.latest)
    raise ValueError("At least one session selection option must be provided")


def _fetch_latest_session_ids(database: Path, count: int) -> List[int]:
    if count <= 0:
        raise ValueError("--latest must be a positive integer")
    if not database.exists():
        raise FileNotFoundError(f"Database not found: {database}")
    conn = sqlite3.connect(str(database))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id FROM sessions ORDER BY COALESCE(started_at, ended_at, id) DESC, id DESC LIMIT ?",
            (count,),
        ).fetchall()
    finally:
        conn.close()
    ids = [row[0] for row in rows]
    return list(reversed(ids))


def _derive_prefix(base: Optional[str], session_id: int, multi: bool) -> str:
    if not base:
        return f"session_{session_id}"
    if not multi:
        return base
    if "{session" in base:
        try:
            return base.format(session=session_id)
        except KeyError as exc:
            raise ValueError(f"Unknown placeholder in prefix: {exc}") from exc
    return f"{base}_session_{session_id}"


def _compress_artifact(path: Path, *, level: int) -> Path:
    compressed = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as src, gzip.open(compressed, "wb", compresslevel=level) as dst:
        shutil.copyfileobj(src, dst)
    path.unlink(missing_ok=True)
    return compressed





def _record_artifact(
    path: Path,
    *,
    session_id: int,
    fmt: str,
    outdir: Path,
    checksum_algorithm: Optional[str],
    compressed: bool = False,
    content_type: Optional[str] = None,
) -> ExportArtifact:
    stat = path.stat()
    relative = _relative_path(outdir, path)
    checksum = _compute_checksum(path, checksum_algorithm) if checksum_algorithm else None
    return ExportArtifact(
        session_id=session_id,
        format=fmt,
        path=path,
        relative_path=relative,
        size_bytes=stat.st_size,
        checksum=checksum,
        compressed=compressed,
        content_type=content_type,
    )


def _relative_path(base: Path, target: Path) -> str:
    try:
        return target.relative_to(base).as_posix()
    except ValueError:
        return target.name



def _guess_content_type(fmt: str) -> Optional[str]:
    if not fmt:
        return None
    return CONTENT_TYPE_MAP.get(fmt.lower())



def _hash_file(path: Optional[Path], algorithm: str = "sha256") -> Optional[str]:
    if path is None:
        return None
    resolved = Path(path).expanduser()
    if not resolved.exists() or not resolved.is_file():
        return None
    return _compute_checksum(resolved, algorithm)


def _compute_checksum(path: Path, algorithm: Optional[str]) -> Optional[str]:
    if not algorithm:
        return None
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _manifest_base(prefix: Optional[str], session_ids: Sequence[int]) -> str:
    if prefix and "{" not in prefix:
        return prefix
    if not session_ids:
        return "export"
    if len(session_ids) == 1:
        return f"session_{session_ids[0]}"
    return f"sessions_{session_ids[0]}_{session_ids[-1]}"


def _default_manifest_name(prefix: Optional[str], session_ids: Sequence[int]) -> str:
    return f"{_manifest_base(prefix, session_ids)}_manifest.json"


def _default_checksum_name(prefix: Optional[str], session_ids: Sequence[int], algorithm: str) -> str:
    return f"{_manifest_base(prefix, session_ids)}_{algorithm}.txt"


def _write_manifest(
    outdir: Path,
    *,
    database: Path,
    session_ids: Sequence[int],
    formats: Sequence[str],
    artifacts: Sequence[ExportArtifact],
    filename: Optional[str],
    checksum_algorithm: Optional[str],
    gzip_enabled: bool,
    prefix: Optional[str],
    tool: Mapping[str, Any],
    inputs: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> tuple[Path, str, Dict[str, Any]]:
    name = filename or _default_manifest_name(prefix, session_ids)
    manifest_path = outdir / name
    payload_summary = dict(summary)
    payload_summary.setdefault("checksum_algorithm", checksum_algorithm)
    payload_summary.setdefault("manifest_checksum_sha256", None)
    payload = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "database": str(database),
        "sessions": list(session_ids),
        "formats": list(formats),
        "gzip": bool(gzip_enabled),
        "checksum_algorithm": checksum_algorithm,
        "tool": dict(tool),
        "inputs": dict(inputs),
        "summary": payload_summary,
        "artifacts": [
            {
                "session_id": artefact.session_id,
                "format": artefact.format,
                "file": artefact.relative_path,
                "size_bytes": artefact.size_bytes,
                "checksum": artefact.checksum,
                "compressed": artefact.compressed,
                "content_type": artefact.content_type,
            }
            for artefact in artifacts
        ],
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_checksum = _compute_checksum(manifest_path, "sha256") or ""
    payload_summary["manifest_checksum_sha256"] = manifest_checksum
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path, manifest_checksum, payload


def _write_checksums(
    outdir: Path,
    *,
    session_ids: Sequence[int],
    artifacts: Sequence[ExportArtifact],
    filename: Optional[str],
    algorithm: str,
    prefix: Optional[str],
    manifest_entry: Optional[tuple[str, str]] = None,
) -> Optional[Path]:
    lines = [
        f"{artefact.checksum}  {artefact.relative_path}"
        for artefact in artifacts
        if artefact.checksum
    ]
    if manifest_entry and all(manifest_entry):
        digest, rel = manifest_entry
        lines.append(f"MANIFEST {digest}  {rel}")
    if not lines:
        return None
    name = filename or _default_checksum_name(prefix, session_ids, algorithm)
    checksum_path = outdir / name
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path



def _build_archive(outdir: Path, *, name: str, files: Sequence[tuple[Path, str]], format: str) -> Path:
    if format.lower() != 'zip':
        raise ValueError(f"Unsupported archive format: {format}")
    archive_path = outdir / name
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in files:
            zf.write(path, arcname)
    return archive_path


def build_archive_manifest(
    manifest_payload: Mapping[str, Any],
    *,
    archive_file: str,
    archive_format: str,
    archive_size_bytes: int,
    archive_checksum_sha256: Optional[str],
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    timestamp = generated_at or datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    manifest_copy = json.loads(json.dumps(manifest_payload, ensure_ascii=False))
    return {
        'generated_at': timestamp,
        'manifest': manifest_copy,
        'archive': {
            'file': archive_file,
            'format': archive_format,
            'size_bytes': archive_size_bytes,
            'checksum_sha256': archive_checksum_sha256,
        },
    }


def _write_archive_summary(
    outdir: Path,
    *,
    base: str,
    manifest_payload: Mapping[str, Any],
    archive_relpath: str,
    archive_format: str,
    archive_size_bytes: int,
    archive_checksum: Optional[str],
) -> tuple[Path, Dict[str, Any]]:
    summary_payload = build_archive_manifest(
        manifest_payload,
        archive_file=archive_relpath,
        archive_format=archive_format,
        archive_size_bytes=archive_size_bytes,
        archive_checksum_sha256=archive_checksum,
    )
    summary_path = outdir / f"{base}_archive_summary.json"
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary_path, summary_payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Elmetron reporting exporters")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export-session", help="Export capture sessions")
    export_parser.add_argument("--database", type=Path, default=Path("data/elmetron.sqlite"))
    export_parser.add_argument("--config", type=Path, default=None, help="Application config file used for manifest metadata")
    export_parser.add_argument("--protocols", type=Path, default=None, help="Protocol registry file used for manifest metadata")
    export_parser.add_argument("--manifest-tool-name", type=str, default="Elmetron Exporter", help="Tool name recorded in the manifest metadata")
    export_parser.add_argument("--manifest-version", type=str, default=None, help="Tool version recorded in the manifest metadata")
    selection_group = export_parser.add_mutually_exclusive_group(required=True)
    selection_group.add_argument("--session", type=int, help="Single session ID to export")
    selection_group.add_argument(
        "--sessions",
        nargs="+",
        type=int,
        metavar="SESSION_ID",
        help="Explicit session IDs to export",
    )
    selection_group.add_argument(
        "--session-range",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Inclusive session ID range to export",
    )
    selection_group.add_argument(
        "--latest",
        type=int,
        metavar="N",
        help="Export the latest N sessions (oldest to newest)",
    )
    export_parser.add_argument("--formats", nargs="+", choices=["csv", "json", "xml", "pdf"], required=True)
    export_parser.add_argument("--outdir", type=Path, required=True)
    export_parser.add_argument("--prefix", type=str, default=None, help="Filename prefix for exported artefacts")
    export_parser.add_argument("--csv-mode", choices=["full", "compact"], default="compact")
    export_parser.add_argument("--csv-fields", nargs="*", default=None)
    export_parser.add_argument("--csv-flatten-payload", nargs="*", default=None)
    export_parser.add_argument("--csv-flatten-analytics", nargs="*", default=None)
    export_parser.add_argument("--csv-payload-prefix", type=str, default=None)
    export_parser.add_argument("--csv-analytics-prefix", type=str, default=None)
    export_parser.add_argument(
        "--csv-include-payload-json",
        dest="csv_include_payload_json",
        action="store_true",
        default=None,
        help="Include payload JSON column in CSV output",
    )
    export_parser.add_argument(
        "--csv-drop-payload-json",
        dest="csv_include_payload_json",
        action="store_false",
        help="Exclude payload JSON column from CSV output",
    )
    export_parser.add_argument(
        "--csv-include-analytics-json",
        dest="csv_include_analytics_json",
        action="store_true",
        default=None,
        help="Include analytics JSON column in CSV output",
    )
    export_parser.add_argument(
        "--csv-drop-analytics-json",
        dest="csv_include_analytics_json",
        action="store_false",
        help="Exclude analytics JSON column from CSV output",
    )
    export_parser.add_argument("--pdf-template", type=Path, default=None)
    export_parser.add_argument("--pdf-recent-limit", type=int, default=10)
    export_parser.add_argument("--manifest-name", type=str, default=None, help="Manifest filename relative to the output directory")
    export_parser.add_argument("--no-manifest", action="store_true", help="Disable manifest generation")
    export_parser.add_argument("--checksum-name", type=str, default=None, help="Checksum filename relative to the output directory")
    export_parser.add_argument("--checksum-algorithm", choices=["sha256", "sha512"], default="sha256", help="Checksum algorithm for manifest entries and checksum file")
    export_parser.add_argument("--no-checksums", action="store_true", help="Skip checksum file generation and omit hashes from the manifest")
    export_parser.add_argument("--lims-template", type=Path, default=None)
    export_parser.add_argument(
        "--gzip",
        action="store_true",
        default=False,
        help="Compress exported artefacts with gzip (adds .gz extension)",
    )
    export_parser.add_argument(
        "--gzip-level",
        type=int,
        default=6,
        help="Compression level for gzip output (1-9)",
    )
    export_parser.add_argument("--archive", action="store_true", help="Bundle exports, manifest, and checksums into an archive")
    export_parser.add_argument("--archive-format", choices=["zip"], default="zip")
    export_parser.add_argument("--archive-name", type=str, default=None, help="Archive filename relative to the output directory")
    export_parser.set_defaults(func=_handle_export_session)

    return parser


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(_main())
