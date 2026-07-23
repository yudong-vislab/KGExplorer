# KGExplorer

KGExplorer is a Vue + D3.js + Flask prototype for a minimal paper-style knowledge graph exploration interface.

## Project Structure

```text
KGExplorer/
  frontend/   Vue + Vite + D3.js
  backend/    Python + Flask API
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vue app runs at `http://127.0.0.1:5173`.

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The Flask API runs at `http://127.0.0.1:5001`.

## Guqin Curated Data

Raw OCR, images, and triplet workbooks under `backend/data/raw` are immutable.
The application reads a reproducible curated layer with evidence-audit states:

```bash
python backend/scripts/rebuild_case1.py
python backend/scripts/build_guqin_evidence_table.py
python backend/scripts/build_guqin_curated.py
```

Generated exploration data:

```text
backend/data/curated/guqin/explorer.json
backend/data/processed/guqin_evidence/
```

Useful API routes:

```text
GET /api/case-data/guqin
GET /api/guqin/explorer?q=&source=&slot=&readiness=
GET /api/guqin/conflicts/<conflict_id>
GET /api/guqin/records/<record_id>
GET /api/text/<record_id>
GET /api/images/<record_id>
```

The UI's Corpus Explorer filters the graph, hierarchy, candidate queue, source
matrix, and evidence tray. `P1_expert_review` candidates can be adjudicated;
`P2_data_cleanup` and `P3_alignment_review` candidates expose their audit flags
and keep terminal decisions disabled until the data issue is resolved.
