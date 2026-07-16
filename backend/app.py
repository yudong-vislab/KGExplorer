import json
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATA = Path(__file__).resolve().parent / "data"
PROCESSED = DATA / "processed" / "contested_kg.json"
IMAGE_ROOT = DATA / "raw" / "image"
QUERCUS_ROOT = DATA / "case2_quercus"
QUERCUS_MANIFEST = QUERCUS_ROOT / "source_manifest.json"


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "KGExplorer Flask API"})


def guqin_data():
    if not PROCESSED.exists():
        abort(404)
    return json.loads(PROCESSED.read_text(encoding="utf-8"))


def quercus_data():
    manifest = json.loads(QUERCUS_MANIFEST.read_text(encoding="utf-8"))
    specimens_path = QUERCUS_ROOT / "raw" / "specimens" / "quercus_specimens.json"
    specimens = json.loads(specimens_path.read_text(encoding="utf-8"))["records"] if specimens_path.exists() else []
    books, grouped = {}, {}
    for row in specimens:
        institution = row.get("institution") or "unknown collection"
        source_id = f"specimen:{institution}"
        books[source_id] = f"{institution.upper()} herbarium specimens"
        scientific = row.get("scientific_name") or row.get("canonical_name") or "Quercus"
        parts = scientific.split()
        concept = " ".join(parts[:2]) if len(parts) >= 2 else scientific
        grouped.setdefault(concept, []).append((source_id, row))

    artifacts = []
    for concept, entries in sorted(grouped.items()):
        assertions, sources, images = [], [], {}
        for source_id, row in entries:
            if source_id in sources:
                continue
            sources.append(source_id)
            image_name = Path(row["local_image"]).name if row.get("local_image") else ""
            image_path = f"/api/case2/quercus/specimens/{row['record_uuid']}/{image_name}" if image_name else None
            values = [row.get("scientific_name") or concept]
            if row.get("state"):
                values.append(row["state"])
            assertions.append({"book": source_id, "record_id": row["record_uuid"], "values": values, "image_path": image_path})
            if image_name:
                images[source_id] = [image_name]
        names = {a["values"][0] for a in assertions}
        status = "differ" if len(names) > 1 else "evidence"
        artifacts.append({
            "artifact_id": f"q-species-{concept.lower().replace(' ', '-')}",
            "name": concept.title(), "aligned": True, "books": sources,
            "records": [a["record_id"] for a in assertions], "entities": ["Quercus", concept],
            "images": images,
            "caus": [{"slot": "taxon_name", "label": "Specimen evidence", "status": status, "assertions": assertions}],
        })
    return {"books": books, "artifacts": artifacts, "stats": {
        "records": len(specimens), "artifacts": len(artifacts),
        "differ": sum(1 for a in artifacts if any(c["status"] == "differ" for c in a["caus"])), "overlap": 0,
        "case_status": "evidence_indexed",
    }, "case": {"id": "quercus", "title": "Quercus Historical Flora Corpus",
        "note": "Source-specific scanned pages indexed; taxonomic conflicts pending triple extraction."}}


@app.get("/api/contested-kg")
def contested_kg():
    return jsonify(guqin_data())


@app.get("/api/case-data/<case_id>")
def case_data(case_id):
    if case_id == "guqin":
        return jsonify(guqin_data())
    if case_id == "quercus" and QUERCUS_MANIFEST.exists():
        return jsonify(quercus_data())
    return jsonify({"error": "unknown case"}), 404


@app.get("/api/case2/quercus/<source_id>/<path:filename>")
def quercus_evidence(source_id, filename):
    manifest = json.loads(QUERCUS_MANIFEST.read_text(encoding="utf-8"))
    source = next((s for s in manifest["sources"] if s["ia_id"] == source_id), None)
    if not source:
        abort(404)
    folder = QUERCUS_ROOT / source["quercus_page_images"]
    return send_from_directory(folder, filename)


@app.get("/api/case2/quercus/specimens/<record_id>/<path:filename>")
def quercus_specimen_image(record_id, filename):
    folder = QUERCUS_ROOT / "raw" / "specimens" / "images" / record_id
    return send_from_directory(folder, filename)


@app.get("/api/image/<record_id>/<path:filename>")
def artifact_image(record_id, filename):
    folder = IMAGE_ROOT / record_id
    if not folder.exists():
        return jsonify({"error": "no images for record"}), 404
    image_folder = folder / "images" if (folder / "images").exists() else folder
    return send_from_directory(image_folder, filename)


@app.get("/api/images/<record_id>")
def artifact_image_list(record_id):
    folder = IMAGE_ROOT / record_id
    if not folder.exists():
        return jsonify([])
    image_folder = folder / "images" if (folder / "images").exists() else folder
    return jsonify(sorted(p.name for p in image_folder.glob("*.jpg")))


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "")
    return jsonify({"reply": f"LLM placeholder received: {message}", "source": "placeholder"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
