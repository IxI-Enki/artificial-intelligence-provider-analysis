"""Unit tests for scripts/fetch_providers.py merge pipeline."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_providers as fp  # noqa: E402


@pytest.fixture()
def tmp_data(tmp_path, monkeypatch):
    yaml_src = ROOT / "data" / "providers.yaml"
    monkeypatch.setattr(fp, "ROOT", tmp_path)
    monkeypatch.setattr(fp, "YAML_FILE", tmp_path / "data" / "providers.yaml")
    monkeypatch.setattr(fp, "OUT_FILE", tmp_path / "data" / "providers.json")
    monkeypatch.setattr(fp, "MANIFEST", tmp_path / "data" / "manifest.json")
    (tmp_path / "data").mkdir(parents=True)
    (tmp_path / "data" / "providers.yaml").write_text(
        yaml_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return tmp_path


def test_failsafe_preserves_previous_on_openrouter_failure(tmp_data):
    prev_payload = {
        "schema_version": 1,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "providers": [
            {
                "id": "openai",
                "name": "OpenAI",
                "deployment_type": "api",
                "context_tokens": 99999,
                "field_sources": {
                    "context_tokens": {
                        "value": 99999,
                        "source": "openrouter",
                        "source_quality": "aggregator",
                        "fetched_at": "2026-01-01T00:00:00+00:00",
                    }
                },
            }
        ],
        "mcp_clients": [],
    }
    prev_manifest = {
        "schema_version": 1,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source": "curated_yaml+live_merge",
        "files": ["providers.json"],
    }
    out = tmp_data / "data" / "providers.json"
    manifest = tmp_data / "data" / "manifest.json"
    out.write_text(json.dumps(prev_payload), encoding="utf-8")
    manifest.write_text(json.dumps(prev_manifest), encoding="utf-8")

    with patch.object(fp, "fetch_openrouter_models", return_value=({}, "OpenRouter down")):
        with patch.object(fp, "fetch_litellm_prices", return_value=({}, "LiteLLM down")):
            with patch.object(fp, "fetch_hf_hidden_size", return_value=(None, "HF down")):
                assert fp.main() == 0

    new_payload = json.loads(out.read_text(encoding="utf-8"))
    openai = next(p for p in new_payload["providers"] if p["id"] == "openai")
    assert openai["context_tokens"] == 99999

    new_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    assert new_manifest["generated_at"] == "2026-01-01T00:00:00+00:00"
    assert "stale_warning" in new_manifest


def test_alias_deduplication_merges_conflicting_rows():
    providers = [
        {"id": "google", "name": "Google Alias", "deployment_type": "api", "usp_en": "alias"},
        {
            "id": "google_gemini",
            "name": "Google Gemini",
            "deployment_type": "api",
            "flagship_model": "Gemini",
        },
    ]
    merged = fp.deduplicate_providers(providers)
    assert len(merged) == 1
    assert merged[0]["id"] == "google_gemini"
    assert merged[0]["flagship_model"] == "Gemini"


def test_litellm_and_hf_merge_field_sources():
    provider = {"id": "meta_llama", "name": "Meta", "deployment_type": "both"}
    litellm = {
        "meta-llama/llama-4-maverick": {
            "max_tokens": 1000000,
            "input_cost_per_token": "0.00000024",
        }
    }
    fp.merge_litellm_fields(
        provider,
        litellm,
        model_slug="meta-llama/llama-4-maverick",
        fetched_at="2026-06-27T00:00:00+00:00",
    )
    fp.merge_embedding_dimensions(
        provider,
        fetched_at="2026-06-27T00:00:00+00:00",
        hf_dims={"meta_llama": 4096},
    )
    fs = provider["field_sources"]
    assert fs["context_tokens"]["source_quality"] == "aggregator"
    assert fs["context_tokens"]["source"] == "litellm"
    assert fs["embedding_dimensions"]["source_quality"] == "primary"
    assert fs["embedding_dimensions"]["source"] == "huggingface"


def test_openrouter_miss_marks_missing_not_yaml_fallback(tmp_data):
    fake_or = {
        "google/gemini-2.5-pro": {
            "context_length": 1048576,
            "name": "Google: Gemini 2.5 Pro",
            "pricing": {"prompt": "0.00000125", "completion": "0.00001"},
        },
    }

    with patch.object(fp, "fetch_openrouter_models", return_value=(fake_or, None)):
        with patch.object(fp, "fetch_litellm_prices", return_value=({}, None)):
            with patch.object(fp, "fetch_hf_hidden_size", return_value=(4096, None)):
                assert fp.main() == 0

    payload = json.loads((tmp_data / "data" / "providers.json").read_text(encoding="utf-8"))
    google = next(p for p in payload["providers"] if p["id"] == "google_gemini")
    assert google["context_tokens"] == 1048576
    assert google["flagship_model"] == "Gemini 2.5 Pro"

    claude = next(p for p in payload["providers"] if p["id"] == "anthropic_claude")
    assert claude["context_tokens"] is None
    assert claude["api_input_per_million"] is None
    fs = claude["field_sources"]["context_tokens"]
    assert fs["source_quality"] == "missing"
    assert fs.get("model_slug") is None


def test_resolve_model_slug_prefers_yaml_override():
    provider = {"id": "openai", "openrouter_slug": "openai/gpt-4o"}
    models = {
        "openai/gpt-4.1": {"context_length": 1000},
        "openai/gpt-4o": {"context_length": 2000},
    }
    assert fp.resolve_model_slug(provider, models) == "openai/gpt-4o"


def test_resolve_model_slug_picks_newest_flagship():
    models = {
        "anthropic/claude-opus-4.6": {"context_length": 1_000_000, "created": 100},
        "anthropic/claude-opus-4.8": {"context_length": 1_000_000, "created": 200},
        "anthropic/claude-sonnet-5": {"context_length": 1_000_000, "created": 300},
    }
    provider = {"id": "anthropic_claude"}
    assert fp.resolve_model_slug(provider, models) == "anthropic/claude-sonnet-5"


def test_resolve_model_slug_picks_best_available():
    provider = {"id": "openai"}
    models = {
        "openai/gpt-4.1": {"context_length": 1000, "created": 100, "name": "OpenAI: GPT-4.1"},
        "openai/gpt-5.6-sol-pro": {"context_length": 2000, "created": 300, "name": "OpenAI: GPT-5.6 Sol Pro"},
    }
    assert fp.resolve_model_slug(provider, models) == "openai/gpt-5.6-sol-pro"


def test_openrouter_display_name_strips_vendor_prefix():
    assert fp.openrouter_display_name({"name": "Anthropic: Claude Opus 4.6"}) == "Claude Opus 4.6"


def test_commercial_embedding_dims_inferred_quality():
    provider = {"id": "openai", "name": "OpenAI", "deployment_type": "api"}
    fp.merge_embedding_dimensions(
        provider,
        fetched_at="2026-06-27T00:00:00+00:00",
        hf_dims={"openai": None},
    )
    fs = provider["field_sources"]["embedding_dimensions"]
    assert fs["source_quality"] == "inferred"
    assert provider["embedding_dimensions"] == 3072
