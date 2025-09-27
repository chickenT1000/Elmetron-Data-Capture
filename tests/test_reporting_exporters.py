from __future__ import annotations

import argparse
import gzip
import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from elmetron.config import StorageConfig
from elmetron.reporting import exporters
from elmetron.storage.database import Database, DeviceMetadata


@pytest.fixture
def sample_database(tmp_path: Path) -> tuple[Path, list[int]]:
    """Create a populated SQLite database with three capture sessions."""

    db_path = tmp_path / "elmetron.sqlite"
    storage = StorageConfig(database_path=db_path, ensure_directories=True)
    database = Database(storage)
    database.initialise()
    metadata = DeviceMetadata(serial="SN123", description="CX-505", model="CX-505")
    base = datetime(2025, 9, 1, 12, 0, 0)
    session_ids: list[int] = []

    for offset in range(3):
        started_at = base + timedelta(hours=offset)
        handle = database.start_session(started_at, metadata, {"operator": f"tech{offset}"})
        capture_time = base + timedelta(hours=offset, minutes=offset)
        handle.store_capture(
            captured_at=capture_time,
            raw_frame=b"\x01\x02",
            decoded={
                "captured_at": capture_time.isoformat(),
                "raw_hex": "0102",
                "measurement": {
                    "timestamp": capture_time.isoformat(),
                    "value": 7.0 + offset,
                    "unit": "pH",
                    "temperature": 23.5,
                    "temperature_unit": "C",
                },
            },
            derived_metrics={
                "moving_average": 7.1 + offset,
                "stability_index": 0.2 + offset * 0.01,
            },
        )
        handle.close(capture_time + timedelta(minutes=5))
        session_ids.append(handle.id)

    database.close()
    return db_path, session_ids


def _namespace(**overrides: object) -> argparse.Namespace:
    payload = {
        "session": None,
        "sessions": None,
        "session_range": None,
        "latest": None,
    }
    payload.update(overrides)
    return argparse.Namespace(**payload)


def test_resolve_session_ids_modes(sample_database: tuple[Path, list[int]], tmp_path: Path) -> None:
    db_path, session_ids = sample_database

    single = exporters._resolve_session_ids(db_path, _namespace(session=session_ids[0]))
    assert single == [session_ids[0]]

    many = exporters._resolve_session_ids(
        db_path,
        _namespace(sessions=[session_ids[2], session_ids[0], session_ids[1], session_ids[0]]),
    )
    assert many == sorted({session_ids[0], session_ids[1], session_ids[2]})

    ranged = exporters._resolve_session_ids(
        db_path,
        _namespace(session_range=[session_ids[0], session_ids[2]]),
    )
    assert ranged == list(range(session_ids[0], session_ids[2] + 1))

    latest = exporters._resolve_session_ids(db_path, _namespace(latest=2))
    assert latest == session_ids[1:]

    with pytest.raises(ValueError):
        exporters._resolve_session_ids(db_path, _namespace(session_range=[3, 1]))

    missing_db = tmp_path / "missing.sqlite"
    with pytest.raises(FileNotFoundError):
        exporters._resolve_session_ids(missing_db, _namespace(latest=1))


def test_derive_prefix_handles_templates() -> None:
    assert exporters._derive_prefix(None, 5, True) == "session_5"
    assert exporters._derive_prefix("batch", 5, True) == "batch_session_5"
    assert exporters._derive_prefix("batch", 5, False) == "batch"
    assert exporters._derive_prefix("report_{session:03d}", 7, True) == "report_007"


def test_handle_export_session_supports_gzip(sample_database: tuple[Path, list[int]], tmp_path: Path) -> None:
    db_path, session_ids = sample_database
    outdir = tmp_path / "exports"

    parser = exporters._build_parser()
    config_file = tmp_path / "app.toml"
    config_file.write_text("device_index = 0\n", encoding="utf-8")
    protocols_file = tmp_path / "protocols.toml"
    protocols_file.write_text("[profiles]", encoding="utf-8")
    args = parser.parse_args(
        [
            "export-session",
            "--database",
            str(db_path),
            "--sessions",
            str(session_ids[0]),
            str(session_ids[1]),
            "--formats",
            "csv",
            "json",
            "--outdir",
            str(outdir),
            "--prefix",
            "batch",
            "--gzip",
            "--gzip-level",
            "7",
            "--config",
            str(config_file),
            "--protocols",
            str(protocols_file),
            "--archive",
            "--archive-format",
            "zip",
        ]
    )
    assert args.func is exporters._handle_export_session

    result = exporters._handle_export_session(args)
    assert result == 0

    for session_id in session_ids[:2]:
        csv_gz = outdir / f"batch_session_{session_id}.csv.gz"
        json_gz = outdir / f"batch_session_{session_id}.json.gz"
        assert csv_gz.exists()
        assert json_gz.exists()
        assert not (outdir / f"batch_session_{session_id}.csv").exists()

        with gzip.open(csv_gz, "rt", encoding="utf-8") as handle:
            csv_content = handle.read().strip().splitlines()
        assert csv_content
        assert "measurement_id" in csv_content[0]

        with gzip.open(json_gz, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            assert payload.get("session", {}).get("session_id") == session_id
            assert payload.get("measurements")
        else:
            assert isinstance(payload, list)
            assert payload
            assert all(record.get("session_id") == session_id for record in payload)


    manifest_path = outdir / "batch_manifest.json"
    assert manifest_path.exists()
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["checksum_algorithm"] == "sha256"
    assert manifest_payload["gzip"] is True
    assert sorted(manifest_payload["sessions"]) == sorted(session_ids[:2])

    tool_info = manifest_payload["tool"]
    assert tool_info["name"] == "Elmetron Exporter"
    assert tool_info["version"] == "unknown"
    assert tool_info["python_version"]
    assert tool_info["platform"]

    expected_files = {
        f"batch_session_{session_ids[0]}.csv.gz",
        f"batch_session_{session_ids[0]}.json.gz",
        f"batch_session_{session_ids[1]}.csv.gz",
        f"batch_session_{session_ids[1]}.json.gz",
    }

    summary = manifest_payload["summary"]
    assert summary["artifact_count"] == len(expected_files)
    assert summary["compressed_artifacts"] == len(expected_files)
    assert summary["total_size_bytes"] > 0
    assert summary["checksum_algorithm"] == "sha256"
    assert len(summary["manifest_checksum_sha256"]) == 64

    inputs = manifest_payload["inputs"]
    assert inputs["database"] == str(db_path)
    assert inputs["app_config"] == str(config_file)
    assert len(inputs["app_config_checksum_sha256"]) == 64
    assert inputs["protocols"] == str(protocols_file)
    assert len(inputs["protocols_checksum_sha256"]) == 64

    files = {item["file"]: item for item in manifest_payload["artifacts"]}
    assert set(files) == expected_files
    for name, entry in files.items():
        assert entry["session_id"] in session_ids[:2]
        assert entry["format"] in {"csv", "json"}
        assert entry["size_bytes"] > 0
        assert entry.get("checksum")
        assert entry["compressed"] is True
        assert entry["content_type"] in {"text/csv", "application/json"}

    checksum_path = outdir / "batch_sha256.txt"
    assert checksum_path.exists()
    checksum_lines = checksum_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(checksum_lines) == len(expected_files) + 1
    manifest_lines = [line for line in checksum_lines if line.startswith("MANIFEST ")]
    assert len(manifest_lines) == 1
    manifest_line = manifest_lines[0]
    _, manifest_rest = manifest_line.split(" ", 1)
    manifest_digest, _, manifest_filename = manifest_rest.partition("  ")
    assert len(manifest_digest) == 64
    assert manifest_filename == "batch_manifest.json"

    artifact_lines = [line for line in checksum_lines if not line.startswith("MANIFEST ")]
    assert len(artifact_lines) == len(expected_files)
    for line in artifact_lines:
        digest, _, filename = line.partition("  ")
        assert len(digest) == 64
        assert filename in expected_files


    archive_path = outdir / "batch_archive.zip"
    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, 'r') as zf:
        members = set(zf.namelist())
    assert members == expected_files.union({"batch_manifest.json", "batch_sha256.txt"})

    summary_path = outdir / "batch_archive_summary.json"
    assert summary_path.exists()
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_payload["manifest"] == manifest_payload
    archive_info = summary_payload["archive"]
    assert archive_info["file"] == "batch_archive.zip"
    assert archive_info["format"] == "zip"
    assert archive_info["size_bytes"] == archive_path.stat().st_size
    assert len(archive_info["checksum_sha256"]) == 64


def test_handle_export_session_can_disable_packaging(sample_database: tuple[Path, list[int]], tmp_path: Path) -> None:
    db_path, session_ids = sample_database
    outdir = tmp_path / "exports-disabled"

    parser = exporters._build_parser()
    args = parser.parse_args(
        [
            "export-session",
            "--database",
            str(db_path),
            "--session",
            str(session_ids[0]),
            "--formats",
            "csv",
            "--outdir",
            str(outdir),
            "--no-manifest",
            "--no-checksums",
        ]
    )
    result = exporters._handle_export_session(args)
    assert result == 0

    csv_path = outdir / f"session_{session_ids[0]}.csv"
    assert csv_path.exists()
    assert not any(outdir.glob('*manifest.json'))
    assert not any(outdir.glob('*sha256.txt'))
    assert not any(outdir.glob('*sha512.txt'))


def test_build_archive_manifest_helper() -> None:
    manifest_payload = {"status": "ok"}
    archive_data = exporters.build_archive_manifest(
        manifest_payload,
        archive_file="bundle.zip",
        archive_format="zip",
        archive_size_bytes=1024,
        archive_checksum_sha256="a" * 64,
    )
    assert archive_data["manifest"] == manifest_payload
    assert archive_data["archive"]["file"] == "bundle.zip"
    assert archive_data["archive"]["format"] == "zip"
    assert archive_data["archive"]["size_bytes"] == 1024
    assert archive_data["archive"]["checksum_sha256"] == "a" * 64
