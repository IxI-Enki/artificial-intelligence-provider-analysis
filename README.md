# AI Provider Landscape

Reference comparison of leading **AI providers** for developers and RAG architecture: context windows, API pricing, privacy, MCP client compatibility.

**Live:** [ixi-enki.github.io/artificial-intelligence-provider-analysis/](https://ixi-enki.github.io/artificial-intelligence-provider-analysis/)

## Purpose

Independent provider research dashboard — supports technology selection before building MCP/RAG systems. **Not** diploma-thesis results.

## Data

| File | Description |
|------|-------------|
| `data/providers.yaml` | Curated source (edit manually) |
| `data/providers.json` | Generated for the UI |
| `data/manifest.json` | `generated_at`, changelog |

Merged **weekly** (Monday 06:00 UTC) via GitHub Actions.

## Local refresh

```powershell
pip install -r scripts/requirements.txt
python scripts/fetch_providers.py
python scripts/validate_json.py
```

## Sister dashboard

[MTEB DE embeddings](https://ixi-enki.github.io/project-diploma-performance-analysis/)

## Author

Jan Ritt · [IxI-Enki](https://ixi-enki.github.io/)
