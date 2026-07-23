import json
import re
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATA = Path(__file__).resolve().parent / "data"
PROCESSED = DATA / "processed" / "case1_guqin.json"
GUQIN_CURATED = DATA / "curated" / "guqin" / "explorer.json"
IMAGE_ROOT = DATA / "raw" / "image"
TEXT_ROOT = DATA / "raw" / "text"


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "KGExplorer Flask API"})


def assertion_scope(record, slot):
    """Recover whole-object values separately from component-level values."""
    names = {
        re.sub(r"\s+", "", str(record.get(key, "")).split("·")[0])
        for key in ("raw_name", "normalized_name", "display_name")
    }
    names.discard("")
    object_values = []
    component_values = {}
    for relation in record.get("relations", []):
        if relation.get("slot") != slot:
            continue
        subject = re.sub(r"^\d+[_-]", "", str(relation.get("subject", "")))
        subject = re.sub(r"\s+", "", subject)
        value = relation.get("object", "")
        if subject in names:
            if value not in object_values:
                object_values.append(value)
        else:
            component_values.setdefault(relation.get("subject", ""), [])
            if value not in component_values[relation.get("subject", "")]:
                component_values[relation.get("subject", "")].append(value)
    return {
        "object_values": object_values,
        "component_values": [
            {"subject": subject, "values": values}
            for subject, values in component_values.items()
        ],
    }


def guqin_data():
    if not PROCESSED.exists():
        abort(404)
    data = json.loads(PROCESSED.read_text(encoding="utf-8"))
    record_index = {record["record_id"]: record for record in data["records"]}
    for artifact in data["artifacts"]:
        for slot in artifact.get("caus", []):
            for assertion in slot.get("assertions", []):
                record = record_index.get(assertion.get("record_id"))
                if record:
                    assertion["scope"] = assertion_scope(record, slot["slot"])
    if GUQIN_CURATED.exists():
        curated = json.loads(GUQIN_CURATED.read_text(encoding="utf-8"))
        artifact_audit = {
            artifact["artifact_id"]: artifact for artifact in curated["artifacts"]
        }
        conflict_audit = {
            (conflict["artifact_id"], conflict["slot"]): conflict
            for conflict in curated["conflicts"]
        }
        for artifact in data["artifacts"]:
            audit_artifact = artifact_audit.get(artifact["artifact_id"], {})
            artifact["audit_identity_grade"] = audit_artifact.get("identity_grade", "source_local")
            artifact["audit_readiness_counts"] = audit_artifact.get("readiness_counts", {})
            for slot in artifact.get("caus", []):
                audit = conflict_audit.get((artifact["artifact_id"], slot["slot"]))
                if not audit:
                    continue
                slot["audit"] = {
                    key: audit[key] for key in (
                        "case_row_id", "conflict_id", "identity_grade",
                        "review_readiness", "text_support", "image_support",
                        "audit_flags", "machine_audit_note",
                    )
                }
                source_audit = {
                    (assertion["source_id"], assertion["record_id"]): assertion
                    for assertion in audit["assertions"]
                }
                for assertion in slot.get("assertions", []):
                    key = (assertion.get("source"), assertion.get("record_id"))
                    if key in source_audit:
                        assertion["audit"] = source_audit[key]
        data["evidence_audit"] = curated["summary"]
        data["quality_issues"] = curated["quality_issues"]
    data["case"] = {
        "id": "guqin",
        "number": 1,
        "label": "Case 1 · Guqin",
        "title": "Guqin Heritage Knowledge Revision",
        "note": "Four scanned guqin books with OCR, extracted attributes, and instrument images.",
    }
    return data


def curated_guqin_data():
    if not GUQIN_CURATED.exists():
        abort(404)
    return json.loads(GUQIN_CURATED.read_text(encoding="utf-8"))


@app.get("/api/contested-kg")
def contested_kg():
    return jsonify(guqin_data())


@app.get("/api/case-data/<case_id>")
def case_data(case_id):
    if case_id == "guqin":
        return jsonify(guqin_data())
    return jsonify({"error": "unknown case"}), 404


@app.get("/api/guqin/explorer")
def guqin_explorer():
    """Search the curated Guqin evidence index without changing raw values."""
    data = curated_guqin_data()
    query = request.args.get("q", "").strip().lower()
    source = request.args.get("source", "").strip()
    slot = request.args.get("slot", "").strip()
    readiness = request.args.get("readiness", "").strip()

    conflicts = data["conflicts"]
    if source:
        conflicts = [
            row for row in conflicts
            if source in row["sources"]
            or any(item["source_id"] == source for item in row["assertions"])
        ]
    if slot:
        conflicts = [row for row in conflicts if row["slot"] == slot]
    if readiness:
        allowed = {value.strip() for value in readiness.split(",") if value.strip()}
        conflicts = [row for row in conflicts if row["review_readiness"] in allowed]
    if query:
        def conflict_text(row):
            assertion_text = " ".join(
                f"{item['record_id']} {item['raw_values']} {item['text_snippet']}"
                for item in row["assertions"]
            )
            return (
                f"{row['artifact_name']} {row['slot_label']} "
                f"{row['machine_audit_note']} {assertion_text}"
            ).lower()

        conflicts = [row for row in conflicts if query in conflict_text(row)]

    artifact_ids = {row["artifact_id"] for row in conflicts}
    artifacts = [
        artifact for artifact in data["artifacts"]
        if artifact["artifact_id"] in artifact_ids
    ]
    record_ids = {
        assertion["record_id"]
        for conflict in conflicts
        for assertion in conflict["assertions"]
    }
    records = [record for record in data["records"] if record["record_id"] in record_ids]
    return jsonify({
        "schema_version": data["schema_version"],
        "summary": data["summary"],
        "sources": data["sources"],
        "filters": {
            "q": query,
            "source": source,
            "slot": slot,
            "readiness": readiness,
        },
        "result_counts": {
            "artifacts": len(artifacts),
            "conflicts": len(conflicts),
            "records": len(records),
        },
        "artifacts": artifacts,
        "conflicts": conflicts,
        "records": records,
        "quality_issues": data["quality_issues"],
    })


@app.get("/api/guqin/conflicts/<path:conflict_id>")
def guqin_conflict(conflict_id):
    data = curated_guqin_data()
    conflict = next(
        (row for row in data["conflicts"] if row["conflict_id"] == conflict_id),
        None,
    )
    if not conflict:
        abort(404)
    return jsonify(conflict)


@app.get("/api/guqin/records/<record_id>")
def guqin_record(record_id):
    data = curated_guqin_data()
    record = next(
        (row for row in data["records"] if row["record_id"] == record_id),
        None,
    )
    if not record:
        abort(404)
    return jsonify(record)


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
