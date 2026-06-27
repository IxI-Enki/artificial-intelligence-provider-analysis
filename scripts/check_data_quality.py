#!/usr/bin/env python3
"""Data quality gate — SC-002 field population check."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "data" / "providers.json"
THRESHOLD = 0.90


def main() -> int:
    if not PROVIDERS.exists():
        print("[ERROR] Missing providers.json", file=sys.stderr)
        return 1

    data = json.loads(PROVIDERS.read_text(encoding="utf-8"))
    providers = data.get("providers", [])
    if not providers:
        print("[ERROR] No providers", file=sys.stderr)
        return 1

    ok_context = ok_deploy = 0
    for p in providers:
        ctx = p.get("context_tokens")
        if ctx is not None or "context_tokens" in (p.get("field_sources") or {}):
            ok_context += 1
        dt = p.get("deployment_type")
        if dt in ("api", "self_hosted", "both"):
            ok_deploy += 1

    n = len(providers)
    ctx_ratio = ok_context / n
    deploy_ratio = ok_deploy / n

    print(f"[INFO] context_tokens coverage: {ok_context}/{n} ({ctx_ratio:.0%})")
    print(f"[INFO] deployment_type coverage: {ok_deploy}/{n} ({deploy_ratio:.0%})")

    if ctx_ratio < THRESHOLD or deploy_ratio < THRESHOLD:
        print(
            f"[ERROR] Coverage below {THRESHOLD:.0%} threshold",
            file=sys.stderr,
        )
        return 1

    print("[OK] Data quality gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
