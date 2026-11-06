from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as file:
                return list(csv.DictReader(file))
        except UnicodeDecodeError:
            continue
    with path.open("r", encoding="latin-1", newline="") as file:
        return list(csv.DictReader(file))


def write_json_safe(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")

