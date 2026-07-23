"""Build a machine-audited Guqin Case Evidence Table.

This script does not rewrite the immutable raw exports or make historical
judgements. It verifies data lineage, record alignment evidence, OCR/text
support, image availability, and extraction risks, then emits flat tables for
expert review and paper case selection.

Run from the repository root:
    python backend/scripts/build_guqin_evidence_table.py
"""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
OUT = PROCESSED / "guqin_evidence"
CASE_PATH = PROCESSED / "case1_guqin.json"

SOURCE_META = {
    "Gq": {"title": "古琴", "pad": 5},
    "Yjzq": {"title": "一见钟琴", "pad": 5},
    "QNQY": {"title": "千年清音", "pad": 3},
    "CQL": {"title": "藏琴录", "pad": 3},
}
SOURCE_ORDER = list(SOURCE_META)
PLACEHOLDERS = {"未提及", "未明确", "不详", "未知", "无考", "未记录", "待考"}
INTERNAL_REF = re.compile(r"^\d+[_-].+")
ATTR_TOKEN = re.compile(r"([^:;；]+):(.+?)(?:\(L\d\))?(?=$|[;；]\s*)")
NUMBER_CM = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:厘米|公分|cm)", re.I)

VISUAL_SLOT_HINTS = {
    "form": ("qimian", "qintou", "qinwei"),
    "lacquer": ("qimian", "qindi", "qincemian"),
    "lacquer_repair": ("qimian", "qindi", "qincemian"),
    "ash": ("qimian", "qindi", "qincemian"),
    "ash_repair": ("qimian", "qindi", "qincemian"),
    "duanwen": ("qimian", "qindi", "qincemian"),
    "duanwen_repair": ("qimian", "qindi", "qincemian"),
    "material": ("qimian", "qindi", "qincemian"),
    "component_material": ("qintou", "qinwei", "qindi", "qimian", "yanzu"),
    "inscription": ("mingwen",),
    "inscriber": ("mingwen",),
    "inscription_script": ("mingwen",),
    "inscription_color": ("mingwen",),
}


def clean(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("籟", "籁").replace("鳳", "凤").replace("龍", "龙")
    text = re.sub(r"\s+", "", text)
    return "" if text.lower() == "nan" else text


def text_key(value: object) -> str:
    text = clean(value).lower()
    text = text.replace("～", "~").replace("—", "-").replace("–", "-")
    text = re.sub(r"[《》“”\"'‘’（）()\[\]【】,，。；;:：、·\s]", "", text)
    text = text.replace("代", "")
    return text


def join(values: list[object] | set[object] | tuple[object, ...]) -> str:
    return " | ".join(str(value) for value in values if str(value).strip())


def source_record_id(source: str, number: object) -> str:
    return f"{source}{int(float(number)):0{SOURCE_META[source]['pad']}d}"


def parse_attributes(value: object) -> list[tuple[str, str]]:
    text = str(value or "")
    if text.lower() == "nan":
        return []
    return [(clean(key), clean(val)) for key, val in ATTR_TOKEN.findall(text)]


def load_entity_evidence() -> tuple[dict, dict]:
    dimensions: dict[str, dict[str, float]] = defaultdict(dict)
    entity_attributes: dict[str, list[dict]] = defaultdict(list)
    for source in SOURCE_ORDER:
        path = RAW / "triplet" / f"{source}_output_l2_excels_merged_entities_with_book.xlsx"
        frame = pd.read_excel(path)
        for _, row in frame.iterrows():
            belongs = row.get("belongs_to")
            if pd.isna(belongs):
                continue
            entity = clean(row.get("实体"))
            number_match = re.match(r"^(\d+)[_-]", entity)
            if number_match:
                number = number_match.group(1)
            elif re.fullmatch(r"\d+(?:\.0+)?", str(belongs).strip()):
                number = belongs
            else:
                continue
            rid = source_record_id(source, number)
            for key, value in parse_attributes(row.get("属性")):
                item = {"entity": entity, "key": key, "value": value}
                entity_attributes[rid].append(item)
                match = NUMBER_CM.search(value)
                if "尺寸" in entity and match:
                    dimension_key = (
                        "length" if key in {"通体长", "琴长", "长"}
                        else "shoulder_width" if key == "肩宽"
                        else "thickness" if key in {"厚", "肩厚", "最厚"}
                        else "effective_length" if key in {"隐间", "隐间长"}
                        else "head_width" if key == "额宽"
                        else "tail_width" if key == "尾宽"
                        else "tail_thickness" if key == "尾厚"
                        else key
                    )
                    dimensions[rid][dimension_key] = float(match.group(1))
    return dict(dimensions), dict(entity_attributes)


def load_text(record: dict) -> tuple[str, Path]:
    rel = record.get("evidence", {}).get("text", {}).get("id_path", "")
    path = DATA / rel
    if not path.exists():
        return "", path
    return path.read_text(encoding="utf-8", errors="replace"), path


def value_text_support(value: str, text: str) -> tuple[str, float]:
    raw = clean(value)
    if not raw:
        return "empty", 0.0
    if raw in PLACEHOLDERS:
        return "placeholder", 0.0
    if INTERNAL_REF.match(raw):
        return "entity_reference", 0.0
    if raw in clean(text):
        return "supported_exact", 1.0
    needle = text_key(raw)
    haystack = text_key(text)
    if needle and needle in haystack:
        return "supported_normalized", 0.95
    if not needle or not haystack:
        return "not_found", 0.0
    best = 0.0
    window = max(len(needle), 8)
    step = max(1, window // 4)
    for start in range(0, max(1, len(haystack) - window + 1), step):
        best = max(best, SequenceMatcher(None, needle, haystack[start:start + window]).ratio())
    if best >= 0.82:
        return "supported_fuzzy", round(best, 3)
    if best >= 0.55:
        return "partial", round(best, 3)
    return "not_found", round(best, 3)


def text_snippet(text: str, values: list[str], width: int = 180) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return ""
    for value in values:
        token = clean(value)
        pos = clean(compact).find(token)
        if pos >= 0:
            return compact[max(0, pos - 50):pos + len(token) + 100]
    return compact[:width]


def image_evidence(record: dict, slot: str) -> tuple[str, str, int]:
    images = record.get("evidence", {}).get("images", [])
    files = [image.get("file", "") for image in images]
    hints = VISUAL_SLOT_HINTS.get(slot)
    if not images:
        return "missing", "", 0
    if not hints:
        return "record_images_non_diagnostic", files[0], len(files)
    matched = [file for file in files if any(hint in file.lower() for hint in hints)]
    if matched:
        return "attribute_linked", matched[0], len(files)
    return "record_images_only", files[0], len(files)


def dimension_signature(values: dict[str, float]) -> str:
    labels = {
        "length": "L", "effective_length": "E", "shoulder_width": "W",
        "thickness": "T", "head_width": "HW", "tail_width": "TW",
        "tail_thickness": "TT",
    }
    return "; ".join(f"{labels.get(key, key)}={value:g}cm" for key, value in values.items())


def dimension_comparison(left: dict[str, float], right: dict[str, float]) -> dict:
    shared = sorted(set(left) & set(right))
    exact = []
    anomalies = []
    conflicts = []
    for key in shared:
        a, b = left[key], right[key]
        if abs(a - b) <= 0.15:
            exact.append(key)
        elif min(abs(a), abs(b)) > 0 and abs(max(abs(a), abs(b)) / min(abs(a), abs(b)) - 10) <= 0.15:
            anomalies.append(f"{key}: decimal shift {a:g}/{b:g}")
        else:
            conflicts.append(f"{key}: {a:g}/{b:g}")
    if left.get("length") and right.get("shoulder_width"):
        if abs(left["length"] - right["shoulder_width"]) <= 0.15:
            anomalies.append("length/shoulder_width swapped")
    if left.get("shoulder_width") and right.get("length"):
        if abs(left["shoulder_width"] - right["length"]) <= 0.15:
            anomalies.append("shoulder_width/length swapped")
    return {"shared": shared, "exact": exact, "anomalies": anomalies, "conflicts": conflicts}


def inscription_text(attributes: list[dict]) -> str:
    values = [
        item["value"] for item in attributes
        if "铭文" in item["key"] or item["key"] in {"落款", "题刻", "墨书"}
    ]
    return join(values)


def identity_audit(left_id: str, right_id: str, records: dict, dimensions: dict, attrs: dict) -> dict:
    left_dims, right_dims = dimensions.get(left_id, {}), dimensions.get(right_id, {})
    comp = dimension_comparison(left_dims, right_dims)
    left_inscription = inscription_text(attrs.get(left_id, []))
    right_inscription = inscription_text(attrs.get(right_id, []))
    inscription_similarity = (
        SequenceMatcher(None, text_key(left_inscription), text_key(right_inscription)).ratio()
        if left_inscription and right_inscription else 0.0
    )
    same_name = clean(records[left_id]["normalized_name"]) == clean(records[right_id]["normalized_name"])
    if len(comp["exact"]) >= 2 or inscription_similarity >= 0.8:
        grade = "A_strong"
    elif len(comp["exact"]) == 1 or inscription_similarity >= 0.6:
        grade = "B_supported"
    elif same_name:
        grade = "C_name_only"
    else:
        grade = "D_weak"
    flags = list(comp["anomalies"])
    if comp["conflicts"] and not comp["anomalies"]:
        flags.append("dimension disagreement")
    return {
        "grade": grade,
        "same_name": same_name,
        "left_dimensions": dimension_signature(left_dims),
        "right_dimensions": dimension_signature(right_dims),
        "exact_dimension_fields": join(comp["exact"]),
        "dimension_conflicts": join(comp["conflicts"]),
        "inscription_similarity": round(inscription_similarity, 3),
        "flags": join(flags),
    }


def pair_key(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted((left, right)))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    records = {record["record_id"]: record for record in case["records"]}
    artifacts = {artifact["artifact_id"]: artifact for artifact in case["artifacts"]}
    assertions = {assertion["assertion_id"]: assertion for assertion in case["assertions"]}
    dimensions, entity_attributes = load_entity_evidence()

    record_inventory = []
    for rid, record in records.items():
        text, text_path = load_text(record)
        images = record.get("evidence", {}).get("images", [])
        record_inventory.append({
            "record_id": rid,
            "source_id": record["source_id"],
            "source_title": SOURCE_META[record["source_id"]]["title"],
            "record_name": record["display_name"],
            "normalized_name": record["normalized_name"],
            "text_exists": text_path.exists(),
            "text_characters": len(text),
            "image_count": len(images),
            "dimension_signature": dimension_signature(dimensions.get(rid, {})),
            "entity_attribute_count": len(entity_attributes.get(rid, [])),
            "asset_status": "complete" if text_path.exists() and images else "incomplete",
            "text_path": str(text_path),
            "image_directory": str(RAW / "image" / rid),
        })

    alignment_rows = []
    seen_pairs: set[tuple[str, str]] = set()
    for artifact in case["artifacts"]:
        for left, right in combinations(artifact["records"], 2):
            key = pair_key(left, right)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            audit = identity_audit(left, right, records, dimensions, entity_attributes)
            alignment_rows.append({
                "artifact_id": artifact["artifact_id"],
                "artifact_name": artifact["name"],
                "alignment_status": artifact["alignment_status"],
                "left_record": left,
                "left_source": records[left]["source_id"],
                "right_record": right,
                "right_source": records[right]["source_id"],
                **audit,
                "current_alignment_evidence": join(artifact.get("alignment_evidence", [])),
                "expert_same_object": "",
                "expert_note": "",
            })
    for candidate in case.get("alignment_candidates", []):
        left, right = candidate["left_record"], candidate["right_record"]
        key = pair_key(left, right)
        if key in seen_pairs or left not in records or right not in records:
            continue
        seen_pairs.add(key)
        audit = identity_audit(left, right, records, dimensions, entity_attributes)
        alignment_rows.append({
            "artifact_id": "",
            "artifact_name": candidate.get("normalized_name", ""),
            "alignment_status": candidate.get("status", "candidate"),
            "left_record": left,
            "left_source": records[left]["source_id"],
            "right_record": right,
            "right_source": records[right]["source_id"],
            **audit,
            "current_alignment_evidence": join(candidate.get("reasons", [])),
            "expert_same_object": "",
            "expert_note": "",
        })

    artifact_identity = {}
    for artifact in case["artifacts"]:
        pairs = [
            row for row in alignment_rows
            if row["artifact_id"] == artifact["artifact_id"]
        ]
        grades = [row["grade"] for row in pairs]
        artifact_identity[artifact["artifact_id"]] = (
            "A_strong" if "A_strong" in grades
            else "B_supported" if "B_supported" in grades
            else "C_name_only" if "C_name_only" in grades
            else "source_local" if len(artifact["records"]) == 1
            else "D_weak"
        )

    source_assertion_rows = []
    evidence_rows = []
    for conflict in case["conflicts"]:
        artifact = artifacts[conflict["artifact_id"]]
        slot_entry = next(
            slot for slot in artifact["all_slots"]
            if slot["slot"] == conflict["slot"]
        )
        source_values = {source: "" for source in SOURCE_ORDER}
        source_support = []
        row_flags: set[str] = set()
        scope_parts: set[str] = set()
        image_states = []

        for assertion_id in conflict["assertion_ids"]:
            assertion = assertions[assertion_id]
            rid = assertion["record_id"]
            record = records[rid]
            values = list(assertion.get("values", []))
            source_values[assertion["source"]] = join(values)
            text, text_path = load_text(record)
            support_results = [value_text_support(value, text) for value in values]
            statuses = [item[0] for item in support_results]
            scores = [item[1] for item in support_results]
            assertion_flags: set[str] = set()
            if statuses and all(status.startswith("supported") for status in statuses):
                overall_support = "supported"
            elif any(status in {"entity_reference", "placeholder"} for status in statuses):
                overall_support = "structural_problem"
            elif any(status.startswith("supported") for status in statuses):
                overall_support = "partial"
            else:
                overall_support = "not_found"
            source_support.append(overall_support)
            parts = assertion.get("metadata", {}).get("slot_parts", [])
            scope_parts.update(parts)
            if len(parts) > 1:
                row_flags.add("mixed_subject_scope")
                assertion_flags.add("mixed_subject_scope")
            if "entity_reference" in statuses:
                row_flags.add("internal_entity_reference")
                assertion_flags.add("internal_entity_reference")
            if "placeholder" in statuses:
                row_flags.add("placeholder_as_value")
                assertion_flags.add("placeholder_as_value")
            if "not_found" in statuses:
                row_flags.add("value_not_found_in_text")
                assertion_flags.add("value_not_found_in_text")
            image_status, preferred_image, image_count = image_evidence(record, conflict["slot"])
            image_states.append(image_status)
            source_assertion_rows.append({
                "conflict_id": conflict["conflict_id"],
                "artifact_id": artifact["artifact_id"],
                "artifact_name": artifact["name"],
                "slot": conflict["slot"],
                "slot_label": conflict["label"],
                "source_id": assertion["source"],
                "source_title": SOURCE_META[assertion["source"]]["title"],
                "record_id": rid,
                "record_name": record["display_name"],
                "raw_values": join(values),
                "normalized_values": join(assertion.get("normalized_values", [])),
                "subject_parts": join(parts),
                "text_support": overall_support,
                "value_support_detail": join(
                    f"{value} [{status}:{score:g}]"
                    for value, (status, score) in zip(values, support_results)
                ),
                "text_snippet": text_snippet(text, values),
                "text_path": str(text_path),
                "image_support": image_status,
                "preferred_image": preferred_image,
                "image_count": image_count,
                "image_directory": str(RAW / "image" / rid),
                "audit_flags": join(sorted(assertion_flags)),
            })

        identity_grade = artifact_identity[artifact["artifact_id"]]
        if identity_grade in {"C_name_only", "D_weak"}:
            row_flags.add("identity_needs_review")
        if conflict["conflict_type"] == "lexical_variant":
            row_flags.add("lexical_only")
        if all(state == "record_images_non_diagnostic" for state in image_states):
            image_summary = "non_diagnostic_for_slot"
        elif any(state == "attribute_linked" for state in image_states):
            image_summary = "attribute_linked_available"
        else:
            image_summary = "record_images_only"

        if {"internal_entity_reference", "placeholder_as_value", "mixed_subject_scope"} & row_flags:
            readiness = "P2_data_cleanup"
        elif identity_grade in {"C_name_only", "D_weak"}:
            readiness = "P3_alignment_review"
        elif conflict["conflict_type"] == "lexical_variant":
            readiness = "Exclude_lexical_variant"
        elif source_support and all(status == "supported" for status in source_support):
            readiness = "P1_expert_review"
        else:
            readiness = "P2_data_cleanup"

        note_parts = []
        if "mixed_subject_scope" in row_flags:
            note_parts.append("整琴与构件属性可能被合并，需按主语拆分")
        if "internal_entity_reference" in row_flags:
            note_parts.append("内部实体编号被当作值，需解析实体")
        if "placeholder_as_value" in row_flags:
            note_parts.append("缺失占位符不应构成冲突")
        if "value_not_found_in_text" in row_flags:
            note_parts.append("至少一个抽取值未在当前 OCR 文本中定位")
        if "identity_needs_review" in row_flags:
            note_parts.append("跨来源同物对齐证据不足")
        if not note_parts:
            note_parts.append("数据链路完整，可进入领域专家核验")

        evidence_rows.append({
            "case_row_id": f"GQ-{len(evidence_rows) + 1:03d}",
            "conflict_id": conflict["conflict_id"],
            "artifact_id": artifact["artifact_id"],
            "artifact_name": artifact["name"],
            "record_ids": join(artifact["records"]),
            "source_count": conflict["source_count"],
            "sources": join(artifact["books"]),
            "identity_grade": identity_grade,
            "alignment_status": artifact["alignment_status"],
            "slot": conflict["slot"],
            "slot_label": conflict["label"],
            "conflict_type": conflict["conflict_type"],
            "current_status": conflict["status"],
            "Gq_value": source_values["Gq"],
            "Yjzq_value": source_values["Yjzq"],
            "QNQY_value": source_values["QNQY"],
            "CQL_value": source_values["CQL"],
            "text_support": join(sorted(set(source_support))),
            "image_support": image_summary,
            "subject_scope": join(sorted(scope_parts)),
            "audit_flags": join(sorted(row_flags)),
            "review_readiness": readiness,
            "machine_audit_note": "；".join(note_parts),
            "expert_decision": "Unreviewed",
            "expert_canonical_value": "",
            "expert_rationale": "",
        })

    readiness_counts = Counter(row["review_readiness"] for row in evidence_rows)
    support_counts = Counter(row["text_support"] for row in source_assertion_rows)
    identity_counts = Counter(row["identity_grade"] for row in evidence_rows)
    raw_image_files = sum(
        1 for path in (RAW / "image").rglob("*")
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    )
    linked_image_files = sum(row["image_count"] for row in record_inventory)
    summary = {
        "scope": "Four primary multimodal Guqin books; automated consistency audit, not historical adjudication",
        "generated_from": str(CASE_PATH),
        "source_books": len(SOURCE_ORDER),
        "records": len(records),
        "records_with_text": sum(row["text_exists"] for row in record_inventory),
        "records_with_images": sum(row["image_count"] > 0 for row in record_inventory),
        "raw_image_files": raw_image_files,
        "linked_image_files": linked_image_files,
        "unlinked_or_extra_image_files": raw_image_files - linked_image_files,
        "artifacts": len(artifacts),
        "aligned_artifacts": case["stats"]["aligned_artifacts"],
        "candidate_artifacts": case["stats"]["candidate_artifacts"],
        "source_local_artifacts": case["stats"]["source_local_artifacts"],
        "assertions": len(case["assertions"]),
        "conflict_candidates": len(evidence_rows),
        "source_assertions_in_candidates": len(source_assertion_rows),
        "readiness_counts": dict(readiness_counts),
        "identity_counts": dict(identity_counts),
        "text_support_counts": dict(support_counts),
        "known_ocr_anomalies": [
            "韵磬: shoulder width 19.1 cm (Gq00034) vs 9.1 cm (Yjzq00033)",
            "瀑飞: length 121.2 cm (Gq00056) vs 1212 cm (Yjzq00061)",
            "Yjzq00023: length/shoulder width appear swapped (20.4/119.8 cm)",
            "霜天月: length 124.1 cm (Gq00026) vs 154.1 cm (Yjzq00025)",
        ],
        "limitations": [
            "Automated audit verifies lineage and internal consistency, not historical truth.",
            "The current case builder omits entity-attribute dimensions from the canonical graph.",
            "Some current conflicts are inflated by mixing whole-instrument and component subjects.",
            "Visual evidence availability does not prove that a crop is diagnostic for the disputed attribute.",
        ],
    }

    evidence_rows.sort(key=lambda row: (
        {"P1_expert_review": 0, "P2_data_cleanup": 1, "P3_alignment_review": 2, "Exclude_lexical_variant": 3}.get(row["review_readiness"], 9),
        row["artifact_name"],
        row["slot_label"],
    ))
    source_assertion_rows.sort(key=lambda row: (row["artifact_name"], row["slot_label"], row["source_id"]))
    alignment_rows.sort(key=lambda row: (row["grade"], row["artifact_name"], row["left_record"], row["right_record"]))
    record_inventory.sort(key=lambda row: (SOURCE_ORDER.index(row["source_id"]), row["record_id"]))

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "guqin_case_evidence_table.csv", evidence_rows)
    write_csv(OUT / "guqin_source_assertions.csv", source_assertion_rows)
    write_csv(OUT / "guqin_alignment_review.csv", alignment_rows)
    write_csv(OUT / "guqin_record_inventory.csv", record_inventory)
    bundle = {
        "summary": summary,
        "audit_rules": {
            "identity_grades": {
                "A_strong": "At least two matching dimensions or highly similar inscription evidence.",
                "B_supported": "One matching dimension or moderately similar inscription evidence.",
                "C_name_only": "Alignment depends mainly on the normalized name.",
                "D_weak": "Alignment has weak or conflicting independent evidence.",
                "source_local": "Only one source record is currently linked.",
            },
            "review_readiness": {
                "P1_expert_review": "Evidence is traceable and machine checks passed; ready for domain judgement.",
                "P2_data_cleanup": "OCR, entity-reference, placeholder, text-support, or scope issue must be cleaned first.",
                "P3_alignment_review": "Same-object alignment must be confirmed before judging the attribute.",
                "Exclude_lexical_variant": "Normalization/wording-only difference; do not present as substantive conflict.",
            },
        },
        "evidence_table": evidence_rows,
        "source_assertions": source_assertion_rows,
        "alignment_review": alignment_rows,
        "record_inventory": record_inventory,
    }
    (OUT / "guqin_case_evidence_bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "guqin_evidence_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
