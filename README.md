---
title: AI Provider Landscape
description: Reference comparison of leading AI providers for developers and RAG architecture — context windows, API pricing, deployment, MCP compatibility. Astro static site with daily data refresh.
dates:
  - created: 2026-06-26
  - updated: 2026-07-01
version: 1.0.0
status: published
author:
  - name: Jan Ritt
    email: janritt.office@gmail.com
    location: Österreich
    github:
      handle: IxI-Enki
      userpage: 'https://github.com/IxI-Enki'
tags: [ ai-providers, dashboard, astro, jamstack, github-pages ]
repo: IxI-Enki/artificial-intelligence-provider-analysis
relates_to:
  - docs/data_strategy.md
---

Reference comparison of leading **AI providers** for developers and RAG architecture: context windows, API pricing, deployment type, aggregator flags, MCP client compatibility.

**Live:** [ixi-enki.github.io/artificial-intelligence-provider-analysis/](https://ixi-enki.github.io/artificial-intelligence-provider-analysis/)

**Planning spec:** [IxI-Enki/_IxI-Enki `.specify/specs/ai-provider-landscape`](https://github.com/IxI-Enki/_IxI-Enki/tree/003-ai-provider-landscape/.specify/specs/ai-provider-landscape)

## Purpose

Independent provider research dashboard — supports technology selection before building MCP/RAG systems. **Not** diploma-thesis results.

## Stack

Astro 5 static site + Svelte islands + Pagefind search. Data is baked at build time from committed JSON — no visitor-side API calls.

## Data

| File | Description |
|------|-------------|
| `data/providers.yaml` | Curated source (edit manually) |
| `data/providers.json` | Generated for the UI |
| `data/manifest.json` | `generated_at`, `stale_warning`, changelog |

Merged **daily** (02:00 UTC) via GitHub Actions.

## Local development

```powershell
pip install -r scripts/requirements.txt
python scripts/fetch_providers.py
python scripts/validate_json.py
python scripts/check_data_quality.py
pytest tests/test_fetch_providers.py

npm ci
npm run dev

```

## Production build

```powershell
npm run build          # syncs JSON, builds dist/, runs Pagefind index
npm run verify:static  # asserts no forbidden runtime fetch URLs
npm run test:unit

```

## Sister dashboard

[MTEB DE embeddings](https://ixi-enki.github.io/project-diploma-performance-analysis/) · [Portfolio](https://ixi-enki.github.io/)

## Author

Jan Ritt · [IxI-Enki](https://ixi-enki.github.io/)
