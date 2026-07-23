# Curated Guqin Data

This directory is a reproducible exploration layer. Files under
`backend/data/raw` are immutable and are never rewritten by the curator.

Build order:

```bash
python backend/scripts/rebuild_case1.py
python backend/scripts/build_guqin_evidence_table.py
python backend/scripts/build_guqin_curated.py
```

`explorer.json` joins canonical artifacts, source records, conflict candidates,
source-level OCR/image evidence, alignment grades, and machine-audit readiness.
It records quality issues as review tasks rather than silently correcting the
source data. Historical truth and same-object decisions remain expert actions.
