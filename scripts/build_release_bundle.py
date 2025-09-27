#!/usr/bin/env python3
"""Build release-ready export bundles using the reporting pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from elmetron.reporting import exporters


def _default_stamp() -> str:
    return datetime.utcnow().strftime("release_%Y%m%d_%H%M%S")


def _resolve_summary(target_dir: Path) -> Path:
    summaries = sorted(target_dir.glob("*_archive_summary.json"))
    if not summaries:
        raise FileNotFoundError(f"No archive summary found in {target_dir}")
    return summaries[-1]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create release bundles from captured sessions")
    parser.add_argument("--outdir", type=Path, default=Path("exports/releases"))
    parser.add_argument("--stamp", type=str, default=None, help="Subdirectory name inside the output folder")
    parser.add_argument("--database", type=Path, default=Path("data/elmetron.sqlite"))
    parser.add_argument("--config", type=Path, default=Path("config/app.toml"))
    parser.add_argument("--protocols", type=Path, default=Path("config/protocols.toml"))
    parser.add_argument("--prefix", type=str, default=None, help="Custom filename prefix for exporter artefacts")
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["csv", "json", "xml", "pdf"],
        help="Export formats to include (csv json xml pdf)",
    )
    parser.add_argument("--manifest-tool-name", type=str, default="Elmetron Exporter")
    parser.add_argument("--manifest-version", type=str, default=None)
    parser.add_argument("--archive-format", choices=["zip"], default="zip")
    parser.add_argument("--no-gzip", action="store_true", help="Disable gzip compression for artefacts")

    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--session", type=int, help="Export a single session ID")
    selection.add_argument("--sessions", nargs="+", type=int, help="Export an explicit list of session IDs")
    selection.add_argument(
        "--session-range",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Export an inclusive range of session IDs",
    )
    selection.add_argument("--latest", type=int, help="Export the latest N sessions (default 1)")

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the underlying exporter command without executing it",
    )
    return parser


def _build_selection_args(args: argparse.Namespace) -> List[str]:
    if args.session is not None:
        return ["--session", str(args.session)]
    if args.sessions:
        return ["--sessions", *[str(value) for value in args.sessions]]
    if args.session_range:
        start, end = args.session_range
        return ["--session-range", str(start), str(end)]
    latest = args.latest or 1
    return ["--latest", str(latest)]


def main(argv: List[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    stamp = args.stamp or _default_stamp()
    target_dir = args.outdir / stamp
    target_dir.mkdir(parents=True, exist_ok=True)

    cmd: List[str] = [
        "export-session",
        "--database",
        str(args.database),
        "--outdir",
        str(target_dir),
        "--manifest-tool-name",
        args.manifest_tool_name,
    ]
    if args.manifest_version:
        cmd.extend(["--manifest-version", args.manifest_version])
    if args.config:
        cmd.extend(["--config", str(args.config)])
    if args.protocols:
        cmd.extend(["--protocols", str(args.protocols)])
    if args.prefix:
        cmd.extend(["--prefix", args.prefix])
    cmd.extend(["--formats", *args.formats])
    if not args.no_gzip:
        cmd.append("--gzip")
    cmd.append("--archive")
    cmd.extend(["--archive-format", args.archive_format])
    cmd.extend(_build_selection_args(args))

    if args.dry_run:
        print("Exporter argv:", " ".join(cmd))
        return 0

    status = exporters._main(cmd)  # type: ignore[attr-defined]
    if status != 0:
        return status

    summary_path = _resolve_summary(target_dir)
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))

    archive_rel = summary_payload.get("archive", {}).get("file")
    archive_path = target_dir / archive_rel if archive_rel else None

    release_info = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "target_directory": str(target_dir),
        "archive_summary": summary_payload,
        "archive_path": str(archive_path) if archive_path else None,
    }
    info_path = target_dir / "release_bundle.json"
    info_path.write_text(json.dumps(release_info, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Release bundle ready in {target_dir}")
    if archive_path and archive_path.exists():
        print(f"  Archive: {archive_path}")
    print(f"  Summary: {summary_path}")
    print(f"  Metadata: {info_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
