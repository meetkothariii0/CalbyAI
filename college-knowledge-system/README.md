# college-knowledge-system

I built this Python project to collect Reddit discussions and official cutoff data for Bangalore engineering colleges, transform them into a canonical knowledge graph, and answer concise user questions about colleges and programs.

Quick start
-----------
1. Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Place your raw inputs in `data/raw/`. Example files the pipeline expects:
- `reddit_raw.jsonl`
- `branch_packages.csv`
- `cutoffs.csv`

3. Rebuild the canonical knowledge graph:

```powershell
python src\graph\build_graph.py
```

This writes the canonical snapshot to `data/graph/knowledge_graph.json`.

CLI
---
I exposed a small CLI for queries. Example:

```powershell
$env:PYTHONPATH='.'; python src\cli.py situation --text "How is the CS program at Xenon Institute?"
```

Add `--render` to any `situation` or `rank` command to print a human-readable paragraph with cited excerpts.

Notes
-----
- I prefer conservative alias matching to avoid false positives. The `approach.md` describes my choices and trade-offs.
- The pipeline fails in strict mode if `data/raw/` is missing any required inputs — this keeps builds reproducible.
