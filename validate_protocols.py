from __future__ import annotations

import argparse
import sys
from pathlib import Path

from elmetron.protocols.validator import ValidationIssue, validate_registry_file


def _format_issue(issue: ValidationIssue) -> str:
    return f"[{issue.level}] {issue.location}: {issue.message}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate protocol registry definitions")
    parser.add_argument("registry", type=Path, help="Path to protocols registry (TOML/JSON/YAML)")
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Exit with status 1 if warnings are encountered",
    )
    args = parser.parse_args(argv)

    result = validate_registry_file(args.registry)
    errors = result.errors
    warnings = result.warnings

    for issue in result.issues:
        print(_format_issue(issue))

    print(f"Summary: {len(errors)} error(s), {len(warnings)} warning(s)")

    if errors or (args.warnings_as_errors and warnings):
        if not errors and warnings:
            print("Warnings treated as errors")
        return 1

    print("Validation OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
