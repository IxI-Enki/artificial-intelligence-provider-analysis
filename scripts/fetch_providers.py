#!/usr/bin/env python3
"""Merge curated providers.yaml into providers.json with live OpenRouter pricing."""
from __future__ import annotations

import copy
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
YAML_FILE = ROOT / "data" / "providers.yaml"
OUT_FILE = ROOT / "data" / "providers.json"
MANIFEST = ROOT / "data" / "manifest.json"

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
USER_AGENT = "die-farm-provider-fetch/1.0 (+https://github.com/IxI-Enki/artificial-intelligence-provider-analysis)"

# Provider id -> OpenRouter model slug (verified against /api/v1/models)
PROVIDER_MODEL_MAP: dict[str, str] = {
    "google_gemini": "google/gemini-2.5-pro",
    "anthropic_claude": "anthropic/claude-opus-4.6",
    "openai": "openai/gpt-4.1",
    "x_grok": "x-ai/grok-4.20",
    "mistral": "mistralai/mistral-medium-3",
    "meta_llama": "meta-llama/llama-4-maverick",
    "perplexity": "perplexity/sonar-pro",
}

LIVE_FIELDS = ("context_tokens", "api_input_per_million", "api_output_per_million")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_openrouter_models() -> tuple[dict[str, dict[str, Any]], str | None]:
    """Fetch OpenRouter model catalog. Returns (slug -> model, error message)."""
    req = urllib.request.Request(
        OPENROUTER_MODELS_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {}, f"OpenRouter fetch failed: {exc}"

    models = payload.get("data")
    if not isinstance(models, list):
        return {}, "OpenRouter response missing data array"

    by_id = {m["id"]: m for m in models if isinstance(m, dict) and "id" in m}
    return by_id, None


def per_million_usd(per_token: str | float | int | None) -> float | None:
    if per_token is None:
        return None
    try:
        return round(float(per_token) * 1_000_000, 4)
    except (TypeError, ValueError):
        return None


def source_entry(
    value: Any,
    *,
    source: str,
    fetched_at: str,
    model_slug: str,
) -> dict[str, Any]:
    return {
        "value": value,
        "source": source,
        "model_slug": model_slug,
        "fetched_at": fetched_at,
    }


def merge_live_fields(
    provider: dict[str, Any],
    model: dict[str, Any],
    *,
    model_slug: str,
    fetched_at: str,
) -> None:
    pricing = model.get("pricing") or {}
    live_values: dict[str, Any] = {}

    context = model.get("context_length")
    if context is not None:
        try:
            live_values["context_tokens"] = int(context)
        except (TypeError, ValueError):
            pass

    inp = per_million_usd(pricing.get("prompt"))
    if inp is not None:
        live_values["api_input_per_million"] = inp

    out = per_million_usd(pricing.get("completion"))
    if out is not None:
        live_values["api_output_per_million"] = out

    if not live_values:
        return

    field_sources = provider.setdefault("field_sources", {})
    for key, value in live_values.items():
        provider[key] = value
        field_sources[key] = source_entry(
            value,
            source="openrouter",
            fetched_at=fetched_at,
            model_slug=model_slug,
        )


def apply_live_data(
    providers: list[dict[str, Any]],
    models_by_id: dict[str, dict[str, Any]],
    fetched_at: str,
) -> tuple[int, list[str]]:
    matched = 0
    missing: list[str] = []

    for provider in providers:
        pid = provider.get("id", "")
        slug = PROVIDER_MODEL_MAP.get(pid)
        if not slug:
            continue
        model = models_by_id.get(slug)
        if not model:
            missing.append(slug)
            continue
        merge_live_fields(provider, model, model_slug=slug, fetched_at=fetched_at)
        matched += 1

    return matched, missing


def build_manifest(
    *,
    generated_at: str,
    schema_version: Any,
    live_ok: bool,
    live_fetched_at: str | None,
    models_matched: int,
    models_missing: list[str],
    fetch_error: str | None,
) -> dict[str, Any]:
    live_fetch: dict[str, Any] = {
        "source": "openrouter",
        "url": OPENROUTER_MODELS_URL,
        "ok": live_ok,
        "fetched_at": live_fetched_at,
        "models_matched": models_matched,
        "models_missing": models_missing,
    }
    if fetch_error:
        live_fetch["error"] = fetch_error

    stale_warning: str | None = None
    if not live_ok:
        stale_warning = (
            "Live pricing/context fetch failed; charts use last curated YAML values."
        )

    manifest: dict[str, Any] = {
        "schema_version": schema_version,
        "generated_at": generated_at,
        "source": "curated_yaml+openrouter" if live_ok and models_matched else "curated_yaml",
        "live_fetch": live_fetch,
        "files": ["providers.json"],
        "changelog": [
            {
                "at": generated_at,
                "note": (
                    f"Merged providers.yaml + OpenRouter ({models_matched} models)"
                    if live_ok and models_matched
                    else "Merged providers.yaml (live fetch skipped or partial)"
                ),
            }
        ],
    }
    if stale_warning:
        manifest["stale_warning"] = stale_warning

    if MANIFEST.exists():
        try:
            old = json.loads(MANIFEST.read_text(encoding="utf-8"))
            for entry in old.get("changelog", [])[:4]:
                manifest["changelog"].append(entry)
        except json.JSONDecodeError:
            pass

    return manifest


def main() -> int:
    if not YAML_FILE.exists():
        print(f"[ERROR] Missing {YAML_FILE}", file=sys.stderr)
        return 1

    raw = yaml.safe_load(YAML_FILE.read_text(encoding="utf-8"))
    generated_at = utc_now_iso()

    providers = copy.deepcopy(raw.get("providers", []))
    models_by_id, fetch_error = fetch_openrouter_models()
    live_fetched_at = generated_at if not fetch_error else None
    live_ok = fetch_error is None and bool(models_by_id)

    models_matched = 0
    models_missing: list[str] = []
    if live_ok:
        models_matched, models_missing = apply_live_data(
            providers, models_by_id, generated_at
        )
        if models_missing:
            print(
                f"[WARN] OpenRouter slugs not found: {', '.join(models_missing)}",
                file=sys.stderr,
            )
    else:
        print(f"[WARN] {fetch_error}", file=sys.stderr)

    payload: dict[str, Any] = {
        "schema_version": raw.get("schema_version", 1),
        "generated_at": generated_at,
        "verified_at": raw.get("verified_at"),
        "mcp_last_reviewed": raw.get("mcp_last_reviewed"),
        "source": "curated_yaml+openrouter" if live_ok and models_matched else "curated_yaml",
        "live_fetch": {
            "source": "openrouter",
            "ok": live_ok and models_matched > 0,
            "fetched_at": live_fetched_at,
            "models_matched": models_matched,
            "model_map": PROVIDER_MODEL_MAP,
        },
        "providers": providers,
        "mcp_clients": raw.get("mcp_clients", []),
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    manifest = build_manifest(
        generated_at=generated_at,
        schema_version=payload["schema_version"],
        live_ok=live_ok and models_matched > 0,
        live_fetched_at=live_fetched_at,
        models_matched=models_matched,
        models_missing=models_missing,
        fetch_error=fetch_error,
    )
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(
        f"[OK] Wrote {OUT_FILE} ({len(providers)} providers, "
        f"{models_matched} live from OpenRouter)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
