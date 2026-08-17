Approach
========

I built this project to make community-sourced knowledge about Bangalore engineering colleges reproducible and queryable.

What I ingest
-------------
- Reddit comment and post exports (normalized into `reddit_raw.jsonl`).
- Official branch and cutoff tables (`branch_packages.csv`, `cutoffs.csv`).

Core ideas
----------
- I normalize all incoming text and build a canonical knowledge graph at `data/graph/knowledge_graph.json` so queries are repeatable.
- I use conservative alias matching: prefer whole-word matches first; normalized substring fallbacks apply only for multi-character aliases; single-letter initials are ignored. This reduces false-positive mappings (e.g. "RVCE" resolves to a single college reliably).
- I compute sentiment with VADER and weight excerpt credibility by a log-based base score with exponential time decay (λ=0.15). ROI calculations are computed only when provenance (financials) exists for a branch.
- Results are cached under `data/processed/query_cache.json` to keep responses fast; use `--no-cache` when you want a fresh run.

Developer notes
---------------
- Strict build semantics: if required files are missing from `data/raw/`, the build fails so CI can't accidentally pass on incomplete inputs.
- I added diagnostic scripts under `scripts/` to inspect alias mappings and reproduce regressions.
- The test suite lives under `tests/` and is runnable via `python scripts/run_tests.py` from the repository root.

If you want me to expand any section (example commands, schema, or diagrams), tell me which part and I will add it in the same first-person voice.
