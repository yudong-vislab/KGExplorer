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
