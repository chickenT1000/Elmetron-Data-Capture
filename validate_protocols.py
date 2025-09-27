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
    for issue in result.issues:
        print(_format_issue(issue))

    if result.errors or (args.warnings_as_errors and result.warnings):
        if not result.errors:
            print("Warnings treated as errors")
        return 1

    print(f"Validation OK ({len(result.warnings)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
