#!/usr/bin/env python3
"""Merge curated providers.yaml into providers.json with live aggregator sources."""
from __future__ import annotations

import copy
import json
import re
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

# OpenRouter vendor prefix per curated provider id.
VENDOR_PREFIX: dict[str, str] = {
    "google_gemini": "google/",
    "anthropic_claude": "anthropic/",
    "openai": "openai/",
    "x_grok": "x-ai/",
    "mistral": "mistralai/",
    "meta_llama": "meta-llama/",
    "perplexity": "perplexity/",
}

EXCLUDED_SLUG_RE = (
    r"(?:^|:)free\b|guard|embed|vision-instruct|codestral|devstral|"
    r"ministral|lyria|nano\b|search-preview|build-|"
    r"(?:-fast\b|multi-agent|image|customtools|voxtral|gemma|flash-lite)"
)

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

# Populated only by live fetch — never keep stale YAML fallbacks
LIVE_ONLY_FIELDS = (
    "context_tokens",
    "api_input_per_million",
    "api_output_per_million",
)


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


def strip_live_only_fields(provider: dict[str, Any]) -> None:
    """Remove curated pricing/context numbers — live merge is the sole source."""
    for key in LIVE_ONLY_FIELDS:
        provider.pop(key, None)
        fs = provider.get("field_sources")
        if isinstance(fs, dict):
            fs.pop(key, None)


def finalize_live_fields(
    provider: dict[str, Any],
    *,
    model_slug: str | None,
    fetched_at: str,
) -> None:
    """Mark pricing/context as missing when no aggregator supplied a value."""
    field_sources = provider.setdefault("field_sources", {})
    for key in LIVE_ONLY_FIELDS:
        if key in field_sources:
            continue
        provider[key] = None
        field_sources[key] = source_entry(
            None,
            source="openrouter",
            source_quality="missing",
            fetched_at=fetched_at,
            model_slug=model_slug,
        )


def openrouter_display_name(model: dict[str, Any]) -> str | None:
    """Strip vendor prefix from OpenRouter model name for UI display."""
    raw = model.get("name")
    if not isinstance(raw, str) or not raw.strip():
        return None
    if ": " in raw:
        return raw.split(": ", 1)[1].strip()
    return raw.strip()


def _slug_tail(slug: str) -> str:
    return slug.split("/")[-1].lower()


def _version_parts(slug: str) -> tuple[int, ...]:
    nums = re.findall(r"(\d+)", _slug_tail(slug))
    return tuple(int(n) for n in nums) if nums else (0,)


def flagship_score(provider_id: str, slug: str, model: dict[str, Any]) -> tuple[int, int]:
    """Higher = newer/more flagship. Sort key: (tier, openrouter created)."""
    tail = _slug_tail(slug)
    tier = 0

    if provider_id == "anthropic_claude":
        if "sonnet-5" in tail:
            tier = 220
        elif "opus-4.8" in tail:
            tier = 215
        elif "fable-5" in tail:
            tier = 210
        elif "opus-4.7" in tail:
            tier = 200
        elif "sonnet-4.6" in tail:
            tier = 190
        elif "opus-4.6" in tail:
            tier = 185
        elif "sonnet-4.5" in tail:
            tier = 180
        elif "opus-4.5" in tail:
            tier = 175
        elif "opus-4" in tail:
            tier = 160
        elif "sonnet-4" in tail:
            tier = 150
    elif provider_id == "openai":
        if "gpt-5.6" in tail:
            tier = 230
        elif "gpt-5.5" in tail:
            tier = 220
        elif "gpt-5.4" in tail:
            tier = 210
        elif "gpt-5" in tail:
            tier = 200
        elif "gpt-4.1" in tail:
            tier = 150
        elif "gpt-4o" in tail:
            tier = 140
        if "-pro" in tail:
            tier += 25
        if "sol-pro" in tail:
            tier += 12
        elif "terra-pro" in tail:
            tier += 10
        elif "luna-pro" in tail:
            tier += 8
        elif re.search(r"gpt-5\.6-(sol|terra|luna)", tail):
            tier += 5
    elif provider_id == "google_gemini":
        if "gemini-3.1-pro" in tail:
            tier = 225
        elif "gemini-3.5" in tail and "flash" in tail:
            tier = 220
        elif "gemini-3-flash" in tail:
            tier = 200
        elif "gemini-2.5-pro" in tail and "preview" not in tail:
            tier = 180
        elif "gemini-2.5-flash" in tail:
            tier = 170
    elif provider_id == "x_grok":
        tier = 1
    elif provider_id == "mistral":
        if "mistral-medium-3-5" in tail:
            tier = 220
        elif "mistral-large-2512" in tail:
            tier = 210
        elif "mistral-large" in tail:
            tier = 200
        elif "mistral-medium" in tail:
            tier = 180
    elif provider_id == "meta_llama":
        if "llama-4-maverick" in tail:
            tier = 220
        elif "llama-4-scout" in tail:
            tier = 215
        elif "llama-4" in tail:
            tier = 200
        elif "llama-3.3" in tail:
            tier = 150
    elif provider_id == "perplexity":
        if "sonar-pro-search" in tail:
            tier = 220
        elif "sonar-pro" in tail:
            tier = 210
        elif "sonar-reasoning-pro" in tail:
            tier = 200
        elif "sonar-deep-research" in tail:
            tier = 190
        elif tail == "sonar":
            tier = 150

    created = model.get("created")
    try:
        created_val = int(created)
    except (TypeError, ValueError):
        created_val = 0
    return tier, created_val


def resolve_model_slug(
    provider: dict[str, Any],
    models_by_id: dict[str, dict[str, Any]],
) -> str | None:
    """Pick newest flagship OpenRouter slug for this provider."""
    pid = provider.get("id", "")
    override = provider.get("openrouter_slug")
    if isinstance(override, str) and override in models_by_id:
        return override

    prefix = VENDOR_PREFIX.get(pid)
    if not prefix:
        return None

    candidates: list[tuple[tuple[int, int], str]] = []
    for slug, model in models_by_id.items():
        if not slug.startswith(prefix):
            continue
        if re.search(EXCLUDED_SLUG_RE, slug, re.IGNORECASE):
            continue
        score = flagship_score(pid, slug, model)
        if score[0] <= 0:
            continue
        candidates.append((score, slug))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


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

    display = openrouter_display_name(model)
    if display:
        provider["flagship_model"] = display
        field_sources["flagship_model"] = source_entry(
            display,
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
        strip_live_only_fields(p)
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
            slug = resolve_model_slug(provider, models_by_id)
            if slug and models_by_id:
                model = models_by_id.get(slug)
                if model:
                    merge_openrouter_fields(
                        provider, model, model_slug=slug, fetched_at=fetched_at
                    )
                    models_matched += 1
                else:
                    models_missing.append(slug)
            elif slug is None and VENDOR_PREFIX.get(pid):
                models_missing.append(f"{VENDOR_PREFIX[pid]}*")
            if slug and litellm:
                merge_litellm_fields(
                    provider, litellm, model_slug=slug, fetched_at=fetched_at
                )
            merge_embedding_dimensions(provider, fetched_at=fetched_at, hf_dims=hf_dims)
            finalize_live_fields(
                provider,
                model_slug=slug,
                fetched_at=fetched_at,
            )

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
