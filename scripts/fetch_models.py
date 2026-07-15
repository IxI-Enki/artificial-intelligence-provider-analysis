#!/usr/bin/env python3
"""Build data/models.json catalog from OpenRouter /api/v1/models."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = ROOT / "data" / "models.json"
MANIFEST = ROOT / "data" / "manifest.json"

# Vendors that ship closed API-only models (no public HF weights).
CLOSED_VENDORS = frozenset(
    {
        "openai",
        "anthropic",
        "google",
        "x-ai",
        "perplexity",
        "cohere",
    }
)

DESCRIPTION_MAX = 240


def import_fetch_helpers():
    scripts = ROOT / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import fetch_providers as fp  # noqa: E402

    return fp


def short_name(display_name: str) -> str:
    if ": " in display_name:
        return display_name.split(": ", 1)[1].strip()
    return display_name.strip()


def weight_access(vendor: str, hugging_face_id: str | None) -> str:
    if hugging_face_id:
        return "open"
    if vendor in CLOSED_VENDORS:
        return "closed"
    return "unknown"


def normalize_model(raw: dict[str, Any]) -> dict[str, Any] | None:
    model_id = raw.get("id")
    if not isinstance(model_id, str) or "/" not in model_id:
        return None

    vendor, _slug = model_id.split("/", 1)
    display_name = raw.get("name") if isinstance(raw.get("name"), str) else model_id
    pricing = raw.get("pricing") if isinstance(raw.get("pricing"), dict) else {}
    architecture = raw.get("architecture") if isinstance(raw.get("architecture"), dict) else {}
    top_provider = raw.get("top_provider") if isinstance(raw.get("top_provider"), dict) else {}
    supported = raw.get("supported_parameters")
    if not isinstance(supported, list):
        supported = []

    fp = import_fetch_helpers()
    input_m = fp.per_million_usd(pricing.get("prompt"))
    output_m = fp.per_million_usd(pricing.get("completion"))
    cache_read_m = fp.per_million_usd(pricing.get("input_cache_read"))

    context = raw.get("context_length")
    try:
        context_tokens = int(context) if context is not None else None
    except (TypeError, ValueError):
        context_tokens = None

    max_out = top_provider.get("max_completion_tokens")
    try:
        max_output_tokens = int(max_out) if max_out is not None else None
    except (TypeError, ValueError):
        max_output_tokens = None

    hf_id = raw.get("hugging_face_id")
    hf_id = hf_id if isinstance(hf_id, str) and hf_id.strip() else None

    description = raw.get("description")
    if isinstance(description, str) and len(description) > DESCRIPTION_MAX:
        description = description[: DESCRIPTION_MAX - 1].rstrip() + "…"

    created = raw.get("created")
    try:
        created_at = int(created) if created is not None else None
    except (TypeError, ValueError):
        created_at = None

    is_free = input_m == 0 and output_m == 0

    return {
        "id": model_id,
        "vendor": vendor,
        "name": short_name(display_name),
        "display_name": display_name,
        "context_tokens": context_tokens,
        "max_output_tokens": max_output_tokens,
        "api_input_per_million": input_m,
        "api_output_per_million": output_m,
        "api_cache_read_per_million": cache_read_m,
        "modality": architecture.get("modality"),
        "weight_access": weight_access(vendor, hf_id),
        "hugging_face_id": hf_id,
        "supports_tools": "tools" in supported,
        "supports_structured_outputs": "structured_outputs" in supported,
        "knowledge_cutoff": raw.get("knowledge_cutoff"),
        "description": description if isinstance(description, str) else None,
        "created_at": created_at,
        "is_free": is_free,
    }


def patch_manifest(*, generated_at: str, model_count: int, vendor_count: int, ok: bool) -> None:
    manifest: dict[str, Any] = {}
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    files = manifest.setdefault("files", [])
    if "models.json" not in files:
        files.append("models.json")

    manifest["catalog"] = {
        "source": "openrouter",
        "generated_at": generated_at,
        "model_count": model_count,
        "vendor_count": vendor_count,
        "ok": ok,
    }

    live_fetch = manifest.setdefault("live_fetch", {})
    sources = live_fetch.setdefault("sources", {})
    sources["openrouter_catalog"] = {
        "ok": ok,
        "model_count": model_count,
        "vendor_count": vendor_count,
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    fp = import_fetch_helpers()
    fetched_at = fp.utc_now_iso()
    models_by_id, err = fp.fetch_openrouter_models()

    if err:
        print(f"[ERROR] {err}", file=sys.stderr)
        if OUT_FILE.exists():
            print("[WARN] Keeping previous models.json", file=sys.stderr)
            patch_manifest(
                generated_at=json.loads(OUT_FILE.read_text(encoding="utf-8")).get(
                    "generated_at", fetched_at
                ),
                model_count=0,
                vendor_count=0,
                ok=False,
            )
            return 1
        return 1

    normalized: list[dict[str, Any]] = []
    for raw in models_by_id.values():
        if not isinstance(raw, dict):
            continue
        row = normalize_model(raw)
        if row:
            normalized.append(row)

    normalized.sort(key=lambda m: (m["vendor"], m["name"].lower()))
    vendors = sorted({m["vendor"] for m in normalized})

    payload = {
        "schema_version": 1,
        "generated_at": fetched_at,
        "source": "openrouter",
        "model_count": len(normalized),
        "vendor_count": len(vendors),
        "vendors": vendors,
        "models": normalized,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    patch_manifest(
        generated_at=fetched_at,
        model_count=len(normalized),
        vendor_count=len(vendors),
        ok=True,
    )

    print(
        f"[OK] Wrote {OUT_FILE} ({len(normalized)} models, {len(vendors)} vendors)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
