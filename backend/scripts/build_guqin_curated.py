"""Build the curated Guqin exploration index without modifying raw data.

Inputs:
  data/processed/case1_guqin.json
  data/processed/guqin_evidence/guqin_case_evidence_bundle.json

Output:
  data/curated/guqin/explorer.json

The curated layer records what the machine audit can verify and keeps expert
decisions explicitly unresolved. It is safe to rebuild at any time.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
import re
import unicodedata


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data"
CASE_PATH = DATA / "processed" / "case1_guqin.json"
AUDIT_PATH = DATA / "processed" / "guqin_evidence" / "guqin_case_evidence_bundle.json"
OUT_DIR = DATA / "curated" / "guqin"
OUT_PATH = OUT_DIR / "explorer.json"


KNOWN_QUALITY_ISSUES = [
    {
        "issue_id": "ocr-dimension-yjzq00033",
        "record_id": "Yjzq00033",
        "comparison_record_id": "Gq00034",
        "artifact_name": "韵磬",
        "field": "shoulder_width",
        "observed_value": "9.1 cm",
        "comparison_value": "19.1 cm",
        "issue_type": "probable_missing_digit",
        "status": "requires_scan_verification",
        "note": "The two records match on length and thickness; inspect the scanned dimension line.",
    },
    {
        "issue_id": "ocr-dimension-yjzq00061",
        "record_id": "Yjzq00061",
        "comparison_record_id": "Gq00056",
        "artifact_name": "瀑飞",
        "field": "length",
        "observed_value": "1212 cm",
        "comparison_value": "121.2 cm",
        "issue_type": "probable_decimal_loss",
        "status": "requires_scan_verification",
        "note": "The observed value is physically implausible and differs by a factor of ten.",
    },
    {
        "issue_id": "ocr-dimension-yjzq00023",
        "record_id": "Yjzq00023",
        "comparison_record_id": "Gq00023",
        "artifact_name": "无名琴",
        "field": "length_and_shoulder_width",
        "observed_value": "20.4 / 119.8 cm",
        "comparison_value": "119.8 / 20.4 cm",
        "issue_type": "probable_field_swap",
        "status": "requires_scan_verification",
        "note": "Length and shoulder width appear reversed in the extracted entity attributes.",
    },
    {
        "issue_id": "ocr-dimension-yjzq00025",
        "record_id": "Yjzq00025",
        "comparison_record_id": "Gq00026",
        "artifact_name": "霜天月",
        "field": "length",
        "observed_value": "154.1 cm",
        "comparison_value": "124.1 cm",
        "issue_type": "probable_digit_error",
        "status": "requires_scan_verification",
        "note": "Other dimensions and the instrument name support a scan-level recheck.",
    },
]


def compact_evidence_row(row: dict) -> dict:
    return {
        "case_row_id": row["case_row_id"],
        "conflict_id": row["conflict_id"],
        "artifact_id": row["artifact_id"],
        "artifact_name": row["artifact_name"],
        "slot": row["slot"],
        "slot_label": row["slot_label"],
        "source_count": row["source_count"],
        "sources": [value.strip() for value in row["sources"].split("|") if value.strip()],
        "identity_grade": row["identity_grade"],
        "alignment_status": row["alignment_status"],
        "conflict_type": row["conflict_type"],
        "current_status": row["current_status"],
        "text_support": row["text_support"],
        "image_support": row["image_support"],
        "subject_scope": row["subject_scope"],
        "audit_flags": [value.strip() for value in row["audit_flags"].split("|") if value.strip()],
        "review_readiness": row["review_readiness"],
        "machine_audit_note": row["machine_audit_note"],
        "expert_decision": row["expert_decision"],
    }


def clean(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", "", text)


def relation_scope(record: dict, slot: str) -> dict:
    names = {
        clean(record.get("raw_name")),
        clean(record.get("normalized_name")),
        clean(record.get("display_name", "").split("·")[0]),
    }
    names.discard("")
    object_values = []
    component_values: dict[str, list[str]] = defaultdict(list)
    for relation in record.get("relations", []):
        if relation.get("slot") != slot:
            continue
        subject = clean(re.sub(r"^\d+[_-]", "", relation.get("subject", "")))
        value = relation.get("object", "")
        if subject in names:
            if value not in object_values:
                object_values.append(value)
        elif value not in component_values[relation.get("subject", "")]:
            component_values[relation.get("subject", "")].append(value)
    if object_values and component_values:
        status = "mixed_object_and_component"
    elif object_values:
        status = "object_only"
    elif component_values:
        status = "component_only"
    else:
        status = "no_scoped_relations"
    return {
        "scope_status": status,
        "object_values": object_values,
        "component_values": [
            {"subject": subject, "values": values}
            for subject, values in component_values.items()
        ],
    }


def compact_assertion(row: dict, record: dict) -> dict:
    scope = relation_scope(record, row["slot"])
    return {
        "conflict_id": row["conflict_id"],
        "artifact_id": row["artifact_id"],
        "slot": row["slot"],
        "source_id": row["source_id"],
        "source_title": row["source_title"],
        "record_id": row["record_id"],
        "record_name": row["record_name"],
        "raw_values": row["raw_values"],
        "normalized_values": row["normalized_values"],
        "subject_parts": row["subject_parts"],
        "text_support": row["text_support"],
        "value_support_detail": row["value_support_detail"],
        "text_snippet": row["text_snippet"],
        "text_url": f"/api/text/{row['record_id']}",
        "image_support": row["image_support"],
        "preferred_image": row["preferred_image"],
        "preferred_image_url": (
            f"/api/image/{row['record_id']}/{row['preferred_image']}"
            if row["preferred_image"] else None
        ),
        "image_count": row["image_count"],
        "audit_flags": [value.strip() for value in row["audit_flags"].split("|") if value.strip()],
        **scope,
    }


def main() -> None:
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    case_records = {record["record_id"]: record for record in case["records"]}

    evidence_rows = [compact_evidence_row(row) for row in audit["evidence_table"]]
    assertions = [
        compact_assertion(row, case_records[row["record_id"]])
        for row in audit["source_assertions"]
    ]
    assertion_by_conflict: dict[str, list[dict]] = defaultdict(list)
    audit_by_artifact_slot = {}
    for assertion in assertions:
        assertion_by_conflict[assertion["conflict_id"]].append(assertion)
    for row in evidence_rows:
        row["assertions"] = assertion_by_conflict[row["conflict_id"]]
        audit_by_artifact_slot[(row["artifact_id"], row["slot"])] = row

    conflict_counts: dict[str, Counter] = defaultdict(Counter)
    identity_grades: dict[str, list[str]] = defaultdict(list)
    for row in evidence_rows:
        conflict_counts[row["artifact_id"]][row["review_readiness"]] += 1
        identity_grades[row["artifact_id"]].append(row["identity_grade"])

    artifact_index = []
    record_to_artifact = {}
    for artifact in case["artifacts"]:
        grades = identity_grades.get(artifact["artifact_id"], [])
        identity_grade = (
            "A_strong" if "A_strong" in grades
            else "B_supported" if "B_supported" in grades
            else "C_name_only" if "C_name_only" in grades
            else "source_local"
        )
        audited_slots = [
            audit_by_artifact_slot[(artifact["artifact_id"], slot["slot"])]
            for slot in artifact.get("caus", [])
            if (artifact["artifact_id"], slot["slot"]) in audit_by_artifact_slot
        ]
        artifact_item = {
            "artifact_id": artifact["artifact_id"],
            "name": artifact["name"],
            "records": artifact["records"],
            "sources": artifact["books"],
            "source_count": len(artifact["books"]),
            "alignment_status": artifact["alignment_status"],
            "identity_grade": identity_grade,
            "conflict_count": len(audited_slots),
            "readiness_counts": dict(conflict_counts[artifact["artifact_id"]]),
            "slots": [
                {
                    "slot": row["slot"],
                    "label": row["slot_label"],
                    "conflict_id": row["conflict_id"],
                    "review_readiness": row["review_readiness"],
                    "conflict_type": row["conflict_type"],
                    "text_support": row["text_support"],
                    "image_support": row["image_support"],
                    "audit_flags": row["audit_flags"],
                }
                for row in audited_slots
            ],
        }
        artifact_index.append(artifact_item)
        for record_id in artifact["records"]:
            record_to_artifact[record_id] = {
                "artifact_id": artifact["artifact_id"],
                "artifact_name": artifact["name"],
            }

    record_index = []
    quality_by_record: dict[str, list[dict]] = defaultdict(list)
    for issue in KNOWN_QUALITY_ISSUES:
        quality_by_record[issue["record_id"]].append(issue)
    for row in audit["record_inventory"]:
        item = dict(row)
        item.update(record_to_artifact.get(row["record_id"], {}))
        item["text_url"] = f"/api/text/{row['record_id']}"
        item["image_list_url"] = f"/api/images/{row['record_id']}"
        item["quality_issues"] = quality_by_record.get(row["record_id"], [])
        record_index.append(item)

    source_summaries = []
    for source_id, title in case["books"].items():
        source_records = [row for row in record_index if row["source_id"] == source_id]
        source_summaries.append({
            "source_id": source_id,
            "title": title,
            "record_count": len(source_records),
            "image_count": sum(row["image_count"] for row in source_records),
            "records_with_dimensions": sum(bool(row["dimension_signature"]) for row in source_records),
            "quality_issue_count": sum(len(row["quality_issues"]) for row in source_records),
        })

    explorer = {
        "schema_version": "guqin-curated-explorer-1",
        "case": case["case"],
        "generated_from": {
            "case": str(CASE_PATH.relative_to(ROOT)),
            "audit": str(AUDIT_PATH.relative_to(ROOT)),
            "raw_policy": "immutable",
        },
        "summary": {
            **audit["summary"],
            "ready_for_expert_review": sum(
                row["review_readiness"] == "P1_expert_review" for row in evidence_rows
            ),
            "requires_data_cleanup": sum(
                row["review_readiness"] == "P2_data_cleanup" for row in evidence_rows
            ),
            "requires_alignment_review": sum(
                row["review_readiness"] == "P3_alignment_review" for row in evidence_rows
            ),
        },
        "sources": source_summaries,
        "artifacts": artifact_index,
        "conflicts": evidence_rows,
        "records": record_index,
        "alignment_review": audit["alignment_review"],
        "quality_issues": KNOWN_QUALITY_ISSUES,
        "audit_rules": audit["audit_rules"],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(explorer, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT_PATH),
        "sources": len(source_summaries),
        "records": len(record_index),
        "artifacts": len(artifact_index),
        "conflicts": len(evidence_rows),
        "quality_issues": len(KNOWN_QUALITY_ISSUES),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
