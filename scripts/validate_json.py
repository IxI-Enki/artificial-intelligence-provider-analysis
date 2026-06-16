#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "data" / "schemas" / "providers.schema.json"


def main() -> int:
    path = ROOT / "data" / "providers.json"
    manifest = ROOT / "data" / "manifest.json"
    if not path.exists() or not manifest.exists():
        print("[ERROR] Missing data files", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
    print("[OK] providers.json valid")
    print("[OK] manifest.json present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
