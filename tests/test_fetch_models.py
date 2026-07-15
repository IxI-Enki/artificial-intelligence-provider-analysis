"""Tests for scripts/fetch_models.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_models as fm  # noqa: E402


def test_normalize_model_extracts_vendor_and_pricing():
    raw = {
        "id": "anthropic/claude-sonnet-5",
        "name": "Anthropic: Claude Sonnet 5",
        "context_length": 1_000_000,
        "pricing": {"prompt": "0.000002", "completion": "0.00001"},
        "architecture": {"modality": "text->text"},
        "supported_parameters": ["tools", "structured_outputs"],
        "hugging_face_id": None,
    }
    row = fm.normalize_model(raw)
    assert row is not None
    assert row["vendor"] == "anthropic"
    assert row["name"] == "Claude Sonnet 5"
    assert row["api_input_per_million"] == 2.0
    assert row["weight_access"] == "closed"
    assert row["supports_tools"] is True


def test_weight_access_open_when_hf_id_present():
    assert fm.weight_access("meta-llama", "meta-llama/Llama-3.1-8B") == "open"


def test_main_writes_catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(fm, "ROOT", tmp_path)
    monkeypatch.setattr(fm, "OUT_FILE", tmp_path / "data" / "models.json")
    monkeypatch.setattr(fm, "MANIFEST", tmp_path / "data" / "manifest.json")
    (tmp_path / "data").mkdir(parents=True)

    fake = {
        "openai/gpt-4.1": {
            "id": "openai/gpt-4.1",
            "name": "OpenAI: GPT-4.1",
            "context_length": 1000,
            "pricing": {"prompt": "0.000002", "completion": "0.000008"},
            "architecture": {"modality": "text->text"},
            "supported_parameters": [],
        }
    }

    import fetch_providers as fp  # noqa: E402

    with patch.object(fp, "fetch_openrouter_models", return_value=(fake, None)):
        assert fm.main() == 0

    payload = json.loads((tmp_path / "data" / "models.json").read_text(encoding="utf-8"))
    assert payload["model_count"] == 1
    assert payload["models"][0]["id"] == "openai/gpt-4.1"

    manifest = json.loads((tmp_path / "data" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["catalog"]["model_count"] == 1
