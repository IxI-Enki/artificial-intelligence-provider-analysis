---
title: Data Strategy — AI Provider Landscape
description: Four-tier data strategy — live automated fields, curated manual review, inferred enrichment, and static reference. OpenRouter, LiteLLM, Hugging Face sources.
dates:
  - created: 2026-06-26
  - updated: 2026-07-01
version: 1.0.0
status: reference
author:
  - name: Jan Ritt
    email: janritt.office@gmail.com
    location: Österreich
    github:
      handle: IxI-Enki
      userpage: 'https://github.com/IxI-Enki'
tags: [ ai-providers, data-strategy, etl, openrouter, github-actions ]
repo: IxI-Enki/artificial-intelligence-provider-analysis
relates_to:
  - ../README.md
---

Four tiers keep the dashboard useful without pretending everything can be automated.

## Tier 1 — Live (automated)

**Fields:** `context_tokens`, `api_input_per_million`, `api_output_per_million`, `embedding_dimensions`

Sources:

| Source | Role | `source_quality` |
|--------|------|------------------|
| [OpenRouter `/api/v1/models`](https://openrouter.ai/api/v1/models) | Primary pricing/context overlay | `aggregator` |
| [LiteLLM `model_prices_and_context_window.json`](https://github.com/BerriAI/litellm) | Cross-check when OpenRouter field missing | `aggregator` |
| [Hugging Face Hub `config.json`](https://huggingface.co/docs/hub/en/models) (`hidden_size`) | Open-source embedding dimensions | `primary` |
| `COMMERCIAL_EMBEDDING_DIMS` static map in `fetch_providers.py` | Commercial embedding models without public config | `inferred` |

**Flow:** `scripts/fetch_providers.py` merges curated YAML with live sources. Each merged field gets a `field_sources` entry (`source`, `source_quality`, `model_slug`, `fetched_at`).

**Cadence:** Daily GitHub Actions workflow (02:00 UTC) plus manual `workflow_dispatch`.

**Failure mode:** On OpenRouter outage, previous `providers.json` is preserved; `manifest.json` sets `stale_warning` and keeps `generated_at` unchanged (SC-003).

## Tier 2 — Curated (manual review)

**Fields:** privacy/compliance columns, MCP client matrix, pros/cons, enterprise notes, USPs, `deployment_type`, `model_category`.

**Source:** `data/providers.yaml` edited by hand with `verified_at` (privacy) and `mcp_last_reviewed` (MCP section).

**Cadence:** Review when providers ship policy changes or MCP specs move (target: quarterly).

## Tier 3 — Build-time only (JAMstack)

Astro reads `src/lib/data/*.json` copied from `data/` at `npm run prebuild`. The published site makes **zero** third-party network calls for model/pricing data (Constitution III).

## Tier 4 — Quality gates

| Script | Purpose |
|--------|---------|
| `scripts/validate_json.py` | JSON Schema gate before commit |
| `scripts/check_data_quality.py` | SC-002: >= 90% `context_tokens` + `deployment_type` coverage |
| `pytest tests/test_fetch_providers.py` | Fail-safe, dedup, merge unit tests |
| `npm run verify:static` | No forbidden URLs in built HTML |

## Files

| File | Role |
|------|------|
| `data/providers.yaml` | Human-edited source of truth for curated fields |
| `scripts/fetch_providers.py` | YAML merge + OpenRouter + LiteLLM + HF Hub overlay |
| `data/providers.json` | Built artifact for the static site |
| `data/manifest.json` | Build metadata, `live_fetch`, `stale_warning`, changelog |

## Provider → OpenRouter slug map

| Provider id | Flagship (YAML hint) | OpenRouter slug (auto, Jul 2026) |
|-------------|----------------------|----------------------------------|
| `google_gemini` | Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` |
| `anthropic_claude` | Claude Sonnet 5 | `anthropic/claude-sonnet-5` |
| `openai` | GPT-5.6 Sol Pro | `openai/gpt-5.6-sol-pro` |
| `x_grok` | Grok 4.5 | `x-ai/grok-4.5` |
| `mistral` | Mistral Medium 3.5 | `mistralai/mistral-medium-3-5` |
| `meta_llama` | Llama 4 Maverick | `meta-llama/llama-4-maverick` |
| `perplexity` | Sonar Pro Search | `perplexity/sonar-pro-search` |

`fetch_providers.py` scores all OpenRouter chat models per vendor and picks the **newest flagship** (tier + `created` timestamp). Optional per-provider override: `openrouter_slug` in `providers.yaml`. `flagship_model` display name syncs from OpenRouter on each fetch.

Example slugs after auto-select (Jul 2026): `anthropic/claude-sonnet-5`, `openai/gpt-5.6-sol-pro`, `google/gemini-3.1-pro-preview`, `x-ai/grok-4.5`, `mistralai/mistral-medium-3-5`, `meta-llama/llama-4-maverick`, `perplexity/sonar-pro-search`.

OpenRouter and LiteLLM aggregate reseller pricing; numbers may differ slightly from direct vendor list prices.
