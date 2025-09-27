"""Export utilities for captured measurement datasets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping


def export_json(records: Iterable[Mapping], output: Path) -> Path:
    """Write *records* to *output* as newline-delimited JSON."""

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write('\n')
    return output
