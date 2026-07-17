import json
import re
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATA = Path(__file__).resolve().parent / "data"
PROCESSED = DATA / "processed" / "case1_guqin.json"
IMAGE_ROOT = DATA / "raw" / "image"
TEXT_ROOT = DATA / "raw" / "text"
QUERCUS_ROOT = DATA / "case2_quercus"
QUERCUS_MANIFEST = QUERCUS_ROOT / "source_manifest.json"
BIRD_ROOT = DATA / "case3_birds"
BIRD_PROCESSED = DATA / "processed" / "birds_kg.json"


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "KGExplorer Flask API"})


def guqin_data():
    if not PROCESSED.exists():
        abort(404)
    data = json.loads(PROCESSED.read_text(encoding="utf-8"))
    data["case"] = {
        "id": "guqin",
        "number": 1,
        "label": "Case 1 · Guqin",
        "title": "Guqin Heritage Knowledge Revision",
        "note": "Four scanned guqin books with OCR, extracted attributes, and instrument images.",
    }
    return data


def normalize_quercus_cluster(value):
    """Return a transparent candidate cluster, not a taxonomic verdict."""
    text = re.sub(r"\s+", " ", str(value or "Quercus")).strip()
    text = text.replace("×", " x ").replace("_", " x ")
    parts = text.split()
    return " ".join(parts[:2]) if len(parts) >= 2 else text


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
        concept = normalize_quercus_cluster(scientific)
        grouped.setdefault(concept, []).append((source_id, row))

    artifacts = []
    for concept, entries in sorted(grouped.items()):
        assertions, sources, images = [], [], {}
        for source_id, row in entries:
            if source_id not in sources:
                sources.append(source_id)
            image_name = Path(row["local_image"]).name if row.get("local_image") else ""
            image_path = f"/api/case2/quercus/specimens/{row['record_uuid']}/{image_name}" if image_name else None
            values = [row.get("scientific_name") or concept]
            assertions.append({
                "book": source_id,
                "record_id": row["record_uuid"],
                "values": values,
                "image_path": image_path,
                "metadata": {
                    "catalog_number": row.get("catalog_number", ""),
                    "state": row.get("state", ""),
                    "taxon_rank": row.get("taxon_rank", ""),
                    "collector": row.get("collector", ""),
                    "event_date": row.get("event_date", ""),
                    "source_url": row.get("image_url", ""),
                    "license": row.get("license", ""),
                },
            })
            if image_name:
                images.setdefault(source_id, []).append(image_name)
        names = {a["values"][0].strip().lower() for a in assertions if a["values"]}
        status = "differ" if len(names) > 1 else ("evidence" if len(assertions) > 1 else "single_source")
        ranks = {a["metadata"].get("taxon_rank") for a in assertions if a["metadata"].get("taxon_rank")}
        cluster_status = (
            "confirmed" if len(assertions) > 1 and len(names) == 1
            else "candidate" if len(assertions) > 1
            else "source-local"
        )
        artifacts.append({
            "artifact_id": f"q-species-{concept.lower().replace(' ', '-')}",
            "name": concept.title(), "aligned": cluster_status == "confirmed", "alignment_status": cluster_status,
            "cluster_basis": "shared genus + epithet; verify rank/hybrid markers in evidence",
            "books": sources,
            "records": [a["record_id"] for a in assertions], "entities": ["Quercus", concept],
            "images": images,
            "caus": [{
                "slot": "taxon_name",
                "label": "Taxon name",
                "status": status,
                "assertions": assertions,
                "cluster_status": cluster_status,
                "rank_values": sorted(ranks),
            }],
        })
    return {"books": books, "artifacts": artifacts, "stats": {
        "records": len(specimens), "artifacts": len(artifacts),
        "aligned_artifacts": sum(1 for a in artifacts if a["alignment_status"] == "confirmed"),
        "candidate_clusters": sum(1 for a in artifacts if a["alignment_status"] == "candidate"),
        "source_local_artifacts": sum(1 for a in artifacts if a["alignment_status"] == "source-local"),
        "differ": sum(1 for a in artifacts if any(c["status"] == "differ" for c in a["caus"])), "overlap": 0,
        "case_status": "evidence_indexed",
    }, "case": {
        "id": "quercus", "number": 2, "label": "Case 2 · Quercus",
        "title": "Quercus Herbarium Evidence Corpus",
        "note": f"{len(specimens)} specimen records from {len(books)} collections; candidate clusters preserve record-level names and images.",
    }}


def birds_data():
    if not BIRD_PROCESSED.exists():
        abort(404)
    return json.loads(BIRD_PROCESSED.read_text(encoding="utf-8"))


@app.get("/api/contested-kg")
def contested_kg():
    return jsonify(guqin_data())


@app.get("/api/case-data/<case_id>")
def case_data(case_id):
    if case_id == "guqin":
        return jsonify(guqin_data())
    if case_id == "quercus" and QUERCUS_MANIFEST.exists():
        return jsonify(quercus_data())
    if case_id == "birds":
        return jsonify(birds_data())
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
    if not folder.exists():
        abort(404)
    return send_from_directory(folder, filename)


@app.get("/api/case3/birds/pages/<source_id>/<path:filename>")
def bird_page_image(source_id, filename):
    folder = BIRD_ROOT / "raw" / "pages" / source_id
    if not folder.exists():
        abort(404)
    return send_from_directory(folder, filename)


@app.get("/api/image/<record_id>/<path:filename>")
def artifact_image(record_id, filename):
    folder = IMAGE_ROOT / record_id
    if not folder.exists():
        return jsonify({"error": "no images for record"}), 404
    image_folder = folder / "images" if (folder / "images").exists() else folder
    return send_from_directory(image_folder, filename)


@app.get("/api/text/<record_id>")
def artifact_text(record_id):
    """Serve the id-aligned OCR text for a Guqin source record."""
    match = re.match(r"^(Gq|Yjzq|QNQY|CQL)\d+$", record_id)
    if not match:
        abort(404)
    folder = TEXT_ROOT / f"{match.group(1)}-txt-id"
    filename = f"{record_id}.txt"
    if not (folder / filename).exists():
        abort(404)
    return send_from_directory(folder, filename, mimetype="text/plain; charset=utf-8")


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
