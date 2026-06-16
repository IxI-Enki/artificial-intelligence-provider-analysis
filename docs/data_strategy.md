# Data strategy — AI Provider Landscape

Three tiers keep the dashboard useful without pretending everything can be automated.

## Tier 1 — Live (automated)

**Fields:** `context_tokens`, `api_input_per_million`, `api_output_per_million`

**Source:** [OpenRouter `/api/v1/models`](https://openrouter.ai/api/v1/models) (no API key for the public catalog).

**Flow:** `scripts/fetch_providers.py` maps each curated provider id to an OpenRouter model slug, fetches pricing/context, and overwrites YAML defaults when the fetch succeeds. Each merged field gets a `field_sources` entry (`source`, `model_slug`, `fetched_at`).

**Cadence:** Weekly GitHub Actions workflow (Mon 06:00 UTC) plus manual `workflow_dispatch`.

**Failure mode:** YAML values are kept; `manifest.json` sets `stale_warning` when live fetch fails.

## Tier 2 — Curated (manual review)

**Fields:** privacy/compliance columns, MCP client matrix, pros/cons, enterprise notes, USPs.

**Source:** `data/providers.yaml` edited by hand with `verified_at` (privacy) and `mcp_last_reviewed` (MCP section).

**Cadence:** Review when providers ship policy changes or MCP specs move (target: quarterly, or after major vendor announcements).

**Why not automated:** Training defaults, zero-retention claims, and GDPR posture depend on contract tier and legal wording — not on a stable public API. MCP support changes faster than any single feed tracks reliably.

## Tier 3 — Future (optional)

Ideas if we extend the dashboard later:

- **Artificial Analysis** — benchmark scores and quality rankings (scraping or licensed API; check ToS).
- **Provider changelogs / RSS** — flagship model renames (e.g. Grok 3 → 4.x) surfaced as changelog entries.
- **LiteLLM `model_prices_and_context_window.json`** — fallback or cross-check if OpenRouter is down.
- **models.dev** — secondary catalog if it stabilizes as a public API.

## Files

| File | Role |
|------|------|
| `data/providers.yaml` | Human-edited source of truth for curated fields |
| `scripts/fetch_providers.py` | YAML merge + OpenRouter live overlay |
| `data/providers.json` | Built artifact for the static site |
| `data/manifest.json` | Build metadata, `live_fetch`, `stale_warning`, changelog |

## Provider → OpenRouter slug map

| Provider id | Flagship (YAML) | OpenRouter slug |
|-------------|-----------------|-----------------|
| `google_gemini` | Gemini 2.5 Pro | `google/gemini-2.5-pro` |
| `anthropic_claude` | Claude Opus 4 | `anthropic/claude-opus-4.6` |
| `openai` | GPT-4.1 | `openai/gpt-4.1` |
| `x_grok` | Grok 3 | `x-ai/grok-4.20` |
| `mistral` | Mistral Medium 3 | `mistralai/mistral-medium-3` |
| `meta_llama` | Llama 4 Maverick | `meta-llama/llama-4-maverick` |
| `perplexity` | Sonar Pro | `perplexity/sonar-pro` |

OpenRouter aggregates reseller pricing; numbers may differ slightly from direct vendor list prices.
