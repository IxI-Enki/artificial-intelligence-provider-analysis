#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS_SCHEMA = ROOT / "data" / "schemas" / "providers.schema.json"
MODELS_SCHEMA = ROOT / "data" / "schemas" / "models.schema.json"


def validate_file(path: Path, schema_path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
    print(f"[OK] {label} valid")


def main() -> int:
    manifest = ROOT / "data" / "manifest.json"
    if not manifest.exists():
        print("[ERROR] Missing manifest.json", file=sys.stderr)
        return 1
    try:
        validate_file(ROOT / "data" / "providers.json", PROVIDERS_SCHEMA, "providers.json")
        validate_file(ROOT / "data" / "models.json", MODELS_SCHEMA, "models.json")
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except jsonschema.ValidationError as exc:
        print(f"[ERROR] Schema validation failed: {exc.message}", file=sys.stderr)
        return 1
    print("[OK] manifest.json present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
