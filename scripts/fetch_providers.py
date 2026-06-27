#!/usr/bin/env python3
"""Merge curated providers.yaml into providers.json with live aggregator sources."""
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
LITELLM_PRICES_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)
HF_CONFIG_URL = "https://huggingface.co/api/models/{repo}/revision/main"

USER_AGENT = (
    "die-farm-provider-fetch/2.0 "
    "(+https://github.com/IxI-Enki/artificial-intelligence-provider-analysis)"
)

PROVIDER_MODEL_MAP: dict[str, str] = {
    "google_gemini": "google/gemini-2.5-pro",
    "anthropic_claude": "anthropic/claude-opus-4.6",
    "openai": "openai/gpt-4.1",
    "x_grok": "x-ai/grok-4.20",
    "mistral": "mistralai/mistral-medium-3",
    "meta_llama": "meta-llama/llama-4-maverick",
    "perplexity": "perplexity/sonar-pro",
}

# Alias slugs that map to canonical provider ids during deduplication
PROVIDER_ALIASES: dict[str, str] = {
    "google": "google_gemini",
    "anthropic": "anthropic_claude",
    "x-ai": "x_grok",
    "meta-llama": "meta_llama",
}

HF_REPO_MAP: dict[str, str] = {
    "meta_llama": "meta-llama/Llama-3.1-8B",
    "mistral": "mistralai/Mistral-7B-v0.1",
}

COMMERCIAL_EMBEDDING_DIMS: dict[str, int] = {
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
}

EMBEDDING_MODEL_SLUGS: dict[str, str] = {
    "openai": "text-embedding-3-large",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def http_get_json(url: str, *, timeout: int = 90) -> tuple[Any, str | None]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, str(exc)


def fetch_openrouter_models() -> tuple[dict[str, dict[str, Any]], str | None]:
    payload, err = http_get_json(OPENROUTER_MODELS_URL)
    if err:
        return {}, f"OpenRouter fetch failed: {err}"
    models = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return {}, "OpenRouter response missing data array"
    by_id = {m["id"]: m for m in models if isinstance(m, dict) and "id" in m}
    return by_id, None


def fetch_litellm_prices() -> tuple[dict[str, dict[str, Any]], str | None]:
    payload, err = http_get_json(LITELLM_PRICES_URL, timeout=120)
    if err:
        return {}, f"LiteLLM fetch failed: {err}"
    if not isinstance(payload, dict):
        return {}, "LiteLLM response not an object"
    return payload, None


def fetch_hf_hidden_size(repo: str) -> tuple[int | None, str | None]:
    config_url = f"https://huggingface.co/{repo}/resolve/main/config.json"
    config, err = http_get_json(config_url)
    if err or not isinstance(config, dict):
        return None, err or "invalid config.json"
    hidden = config.get("hidden_size")
    if hidden is None:
        return None, "hidden_size not found"
    try:
        return int(hidden), None
    except (TypeError, ValueError):
        return None, "hidden_size not numeric"


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
    source_quality: str,
    fetched_at: str,
    model_slug: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "value": value,
        "source": source,
        "source_quality": source_quality,
        "fetched_at": fetched_at,
    }
    if model_slug:
        entry["model_slug"] = model_slug
    return entry


def normalize_field_sources(provider: dict[str, Any]) -> None:
    fs = provider.get("field_sources") or {}
    for entry in fs.values():
        if not isinstance(entry, dict) or "source_quality" in entry:
            continue
        src = entry.get("source", "")
        if src in ("openrouter", "litellm"):
            entry["source_quality"] = "aggregator"
        elif src == "huggingface":
            entry["source_quality"] = "primary"
        elif src == "static_map":
            entry["source_quality"] = "inferred"
        else:
            entry["source_quality"] = "curated"


def normalize_deployment_type(provider: dict[str, Any]) -> None:
    raw = provider.get("deployment_type")
    modes = provider.get("deployment_modes") or []
    if raw in ("api", "self_hosted", "both"):
        return
    if "api" in modes and "self_hosted" in modes:
        provider["deployment_type"] = "both"
    elif "self_hosted" in modes:
        provider["deployment_type"] = "self_hosted"
    else:
        provider["deployment_type"] = "api"


def deduplicate_providers(providers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge alias rows into canonical provider entries."""
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for provider in providers:
        pid = provider.get("id", "")
        canonical = PROVIDER_ALIASES.get(pid, pid)
        provider = copy.deepcopy(provider)
        provider["id"] = canonical

        if canonical not in by_id:
            by_id[canonical] = provider
            order.append(canonical)
            continue

        existing = by_id[canonical]
        for key, value in provider.items():
            if key == "field_sources":
                fs = existing.setdefault("field_sources", {})
                for fk, fv in (value or {}).items():
                    if fk not in fs:
                        fs[fk] = fv
                continue
            if existing.get(key) in (None, "", []) and value not in (None, "", []):
                existing[key] = value

    return [by_id[i] for i in order]


def merge_openrouter_fields(
    provider: dict[str, Any],
    model: dict[str, Any],
    *,
    model_slug: str,
    fetched_at: str,
) -> None:
    pricing = model.get("pricing") or {}
    field_sources = provider.setdefault("field_sources", {})

    context = model.get("context_length")
    if context is not None:
        try:
            val = int(context)
            provider["context_tokens"] = val
            field_sources["context_tokens"] = source_entry(
                val,
                source="openrouter",
                source_quality="aggregator",
                fetched_at=fetched_at,
                model_slug=model_slug,
            )
        except (TypeError, ValueError):
            pass

    for key, token_key in (
        ("api_input_per_million", "prompt"),
        ("api_output_per_million", "completion"),
    ):
        val = per_million_usd(pricing.get(token_key))
        if val is not None:
            provider[key] = val
            field_sources[key] = source_entry(
                val,
                source="openrouter",
                source_quality="aggregator",
                fetched_at=fetched_at,
                model_slug=model_slug,
            )


def merge_litellm_fields(
    provider: dict[str, Any],
    litellm: dict[str, dict[str, Any]],
    *,
    model_slug: str,
    fetched_at: str,
) -> None:
    model = litellm.get(model_slug)
    if not isinstance(model, dict):
        return
    field_sources = provider.setdefault("field_sources", {})

    ctx = model.get("max_tokens") or model.get("max_input_tokens")
    if ctx is not None and "context_tokens" not in field_sources:
        try:
            val = int(ctx)
            provider["context_tokens"] = val
            field_sources["context_tokens"] = source_entry(
                val,
                source="litellm",
                source_quality="aggregator",
                fetched_at=fetched_at,
                model_slug=model_slug,
            )
        except (TypeError, ValueError):
            pass

    for key, litellm_key in (
        ("api_input_per_million", "input_cost_per_token"),
        ("api_output_per_million", "output_cost_per_token"),
    ):
        if key in field_sources:
            continue
        val = per_million_usd(model.get(litellm_key))
        if val is not None:
            provider[key] = val
            field_sources[key] = source_entry(
                val,
                source="litellm",
                source_quality="aggregator",
                fetched_at=fetched_at,
                model_slug=model_slug,
            )


def merge_embedding_dimensions(
    provider: dict[str, Any],
    *,
    fetched_at: str,
    hf_dims: dict[str, int | None],
) -> None:
    pid = provider.get("id", "")
    field_sources = provider.setdefault("field_sources", {})
    if "embedding_dimensions" in field_sources:
        return

    hf_val = hf_dims.get(pid)
    if hf_val is not None:
        provider["embedding_dimensions"] = hf_val
        field_sources["embedding_dimensions"] = source_entry(
            hf_val,
            source="huggingface",
            source_quality="primary",
            fetched_at=fetched_at,
        )
        return

    slug = EMBEDDING_MODEL_SLUGS.get(pid)
    if slug and slug in COMMERCIAL_EMBEDDING_DIMS:
        val = COMMERCIAL_EMBEDDING_DIMS[slug]
        provider["embedding_dimensions"] = val
        field_sources["embedding_dimensions"] = source_entry(
            val,
            source="static_map",
            source_quality="inferred",
            fetched_at=fetched_at,
            model_slug=slug,
        )


def load_previous_outputs() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    prev_providers = prev_manifest = None
    if OUT_FILE.exists():
        try:
            prev_providers = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    if MANIFEST.exists():
        try:
            prev_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return prev_providers, prev_manifest


def build_manifest(
    *,
    generated_at: str,
    schema_version: Any,
    fetch_status: dict[str, Any],
    stale_warning: str | None,
    models_matched: int,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": schema_version,
        "generated_at": generated_at,
        "source": "curated_yaml+live_merge",
        "live_fetch": fetch_status,
        "files": ["providers.json"],
        "changelog": [
            {
                "at": generated_at,
                "note": f"Merged providers.yaml + live sources ({models_matched} OpenRouter models)",
            }
        ],
    }
    if stale_warning:
        manifest["stale_warning"] = stale_warning

    if MANIFEST.exists():
        try:
            old = json.loads(MANIFEST.read_text(encoding="utf-8"))
            for entry in old.get("changelog", [])[:4]:
                if entry not in manifest["changelog"]:
                    manifest["changelog"].append(entry)
        except json.JSONDecodeError:
            pass

    return manifest


def main() -> int:
    if not YAML_FILE.exists():
        print(f"[ERROR] Missing {YAML_FILE}", file=sys.stderr)
        return 1

    prev_providers, prev_manifest = load_previous_outputs()
    raw = yaml.safe_load(YAML_FILE.read_text(encoding="utf-8"))
    fetched_at = utc_now_iso()

    providers = deduplicate_providers(copy.deepcopy(raw.get("providers", [])))
    for p in providers:
        normalize_deployment_type(p)
        if not p.get("model_category"):
            p["model_category"] = "chat"

    errors: list[str] = []
    models_by_id, or_err = fetch_openrouter_models()

    litellm, ll_err = fetch_litellm_prices()
    optional_errors: list[str] = []
    if ll_err:
        optional_errors.append(ll_err)

    hf_dims: dict[str, int | None] = {}
    for pid, repo in HF_REPO_MAP.items():
        dim, hf_err = fetch_hf_hidden_size(repo)
        hf_dims[pid] = dim
        if hf_err:
            optional_errors.append(f"HF Hub {repo}: {hf_err}")

    openrouter_ok = or_err is None and bool(models_by_id)
    if or_err:
        errors.append(or_err)

    live_ok = openrouter_ok
    models_matched = 0
    models_missing: list[str] = []

    if live_ok:
        for provider in providers:
            pid = provider.get("id", "")
            slug = PROVIDER_MODEL_MAP.get(pid)
            if slug and models_by_id:
                model = models_by_id.get(slug)
                if model:
                    merge_openrouter_fields(
                        provider, model, model_slug=slug, fetched_at=fetched_at
                    )
                    models_matched += 1
                else:
                    models_missing.append(slug)
            if slug and litellm:
                merge_litellm_fields(
                    provider, litellm, model_slug=slug, fetched_at=fetched_at
                )
            merge_embedding_dimensions(provider, fetched_at=fetched_at, hf_dims=hf_dims)

        if models_missing:
            print(
                f"[WARN] OpenRouter slugs not found: {', '.join(models_missing)}",
                file=sys.stderr,
            )
    else:
        for err in errors:
            print(f"[WARN] {err}", file=sys.stderr)

        if prev_providers:
            print("[WARN] Live fetch failed — keeping previous providers.json", file=sys.stderr)
            prev_list = prev_providers.get("providers", [])
            prev_by_id = {p["id"]: p for p in prev_list if isinstance(p, dict) and "id" in p}
            for provider in providers:
                old = prev_by_id.get(provider.get("id", ""))
                if old:
                    for key in (
                        "context_tokens",
                        "api_input_per_million",
                        "api_output_per_million",
                        "embedding_dimensions",
                        "field_sources",
                    ):
                        if key in old:
                            provider[key] = copy.deepcopy(old[key])
        else:
            print("[WARN] No previous providers.json — using curated YAML only", file=sys.stderr)

    stale_warning: str | None = None
    if errors:
        stale_warning = (
            "Live pricing/context fetch failed; site uses last committed snapshot. "
            + "; ".join(errors[:3])
        )
    elif optional_errors:
        stale_warning = "Optional enrichments partial: " + "; ".join(optional_errors[:2])

    for provider in providers:
        normalize_field_sources(provider)

    generated_at = fetched_at if live_ok else (
        (prev_manifest or {}).get("generated_at")
        or (prev_providers or {}).get("generated_at")
        or fetched_at
    )

    payload: dict[str, Any] = {
        "schema_version": raw.get("schema_version", 1),
        "generated_at": generated_at,
        "verified_at": raw.get("verified_at"),
        "mcp_last_reviewed": raw.get("mcp_last_reviewed"),
        "source": "curated_yaml+live_merge" if live_ok else "curated_yaml",
        "live_fetch": {
            "openrouter": {"ok": or_err is None, "models_matched": models_matched},
            "litellm": {"ok": ll_err is None},
            "huggingface": {"ok": all(v is not None for v in hf_dims.values()) if hf_dims else False},
        },
        "providers": providers,
        "mcp_clients": raw.get("mcp_clients", []),
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    fetch_status = {
        "sources": payload["live_fetch"],
        "ok": live_ok,
        "fetched_at": fetched_at if live_ok else None,
        "models_matched": models_matched,
        "models_missing": models_missing,
        "errors": errors,
    }

    manifest = build_manifest(
        generated_at=generated_at,
        schema_version=payload["schema_version"],
        fetch_status=fetch_status,
        stale_warning=stale_warning,
        models_matched=models_matched,
    )
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(
        f"[OK] Wrote {OUT_FILE} ({len(providers)} providers, "
        f"{models_matched} live from OpenRouter)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
