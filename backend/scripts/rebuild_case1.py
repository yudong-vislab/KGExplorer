"""Build the evidence-centered Case 1 dataset from immutable raw exports.

The output keeps source-local records and assertions separate from canonical
objects.  A canonical object is only confirmed when same-name records also
share independent identity evidence; ambiguous matches remain candidates.

Run from backend/: python3 scripts/rebuild_case1.py
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parent.parent / "data"
RAW_TRIPLETS = BASE / "raw" / "triplet"
RAW_IMAGES = BASE / "raw" / "image"
RAW_TEXT = BASE / "raw" / "text"
OUT = BASE / "processed"

PRIMARY_SOURCES = {
    "Gq": {"title": "古琴", "pad": 5, "role": "multimodal_primary"},
    "Yjzq": {"title": "一见钟琴", "pad": 5, "role": "multimodal_primary"},
    "QNQY": {"title": "千年清音", "pad": 3, "role": "multimodal_primary"},
    "CQL": {"title": "藏琴录", "pad": 3, "role": "multimodal_primary"},
}

CONTEXT_SOURCES = {
    "Gggq": {"title": "故宫古琴图典", "role": "textual_context"},
    "GCGQ": {"title": "馆藏古琴整理与研究", "role": "textual_context"},
    "WXAC": {"title": "吾心安处", "role": "textual_context"},
    "Zggq": {"title": "中国古琴珍萃", "role": "unavailable_context"},
}

BOOKS = {**PRIMARY_SOURCES}
ALL_SOURCES = {**PRIMARY_SOURCES, **CONTEXT_SOURCES}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

# Relations are mapped to comparable attribute slots.  Unmapped relations are
# retained in source-local relations instead of silently disappearing.
RELATION_TO_SLOT = {
    "年代为": "dating",
    "时代为": "dating",
    "断代结论为": "dating_assessment",
    "鉴定年代为": "dating_assessment",
    "鉴定组定为": "dating_assessment",
    "形制为": "form",
    "内部形制为": "form",
    "底部形制为": "form",
    "纳音形制为": "form",
    "漆色为": "lacquer",
    "原漆色为": "lacquer",
    "修补漆色为": "lacquer_repair",
    "灰胎为": "ash",
    "修补处灰胎为": "ash_repair",
    "断纹类型为": "duanwen",
    "修补处断纹类型为": "duanwen_repair",
    "无断纹": "duanwen",
    "材质为": "material",
    "内填为": "material",
    "内侧加厚材质为": "material",
    "配件材质为": "component_material",
    "附件材质为": "component_material",
    "岳山材质为": "component_material",
    "承露材质为": "component_material",
    "命名来源为": "naming_origin",
    "号为": "alias",
    "现名为": "alias",
    "斫琴名为": "alias",
    "字为": "alias",
    "题刻者为": "inscriber",
    "刻有": "inscription",
    "铭文为": "inscription",
    "墨书铭文为": "inscription",
    "落款为": "inscription",
    "印章为": "seal",
    "雁足底刻": "inscription",
    "镶嵌有": "component",
    "冠角材质为": "component_material",
    "字体为": "inscription_script",
    "墨书者为": "inscriber",
    "镌刻有": "inscription",
    "花纹为": "surface_pattern",
    "无雕纹": "surface_pattern",
    "类别为": "category",
    "用途为": "usage",
    "字色为": "inscription_color",
    "曾收藏于": "provenance",
    "曾收藏": "provenance",
    "曾属于": "provenance",
    "所属为": "provenance",
    "现藏于": "current_holder",
    "捐赠者为": "provenance",
    "出土地为": "provenance",
    "出土于": "provenance",
    "工艺为": "craft",
    "重修者为": "restoration",
    "重修了": "restoration",
    "徽为": "component",
    "纳音为": "component",
    "凤沼为": "component",
    "龙池为": "component",
    "池沼形状为": "component",
    "包含组件": "component",
    "收录于": "bibliography",
    "著录于": "bibliography",
}

SLOT_LABELS = {
    "dating": "年代",
    "dating_assessment": "断代判断",
    "form": "形制",
    "lacquer": "漆色",
    "lacquer_repair": "修补漆色",
    "ash": "灰胎",
    "ash_repair": "修补灰胎",
    "duanwen": "断纹",
    "duanwen_repair": "修补处断纹",
    "material": "材质",
    "component_material": "配件材质",
    "naming_origin": "命名来源",
    "alias": "别名与字号",
    "inscriber": "题刻者",
    "inscription": "铭文",
    "seal": "印章",
    "provenance": "递藏与来源",
    "current_holder": "现藏单位",
    "craft": "工艺",
    "restoration": "修复信息",
    "component": "构件",
    "bibliography": "著录来源",
    "inscription_script": "铭文字体",
    "surface_pattern": "表面纹饰",
    "category": "类别",
    "usage": "用途",
    "inscription_color": "铭文颜色",
}

# Keep all extracted slots in the complete assertion index, but expose only
# high-value verification attributes through the primary graph projection.
ANALYSIS_SLOTS = {
    "dating", "dating_assessment", "form", "lacquer", "lacquer_repair",
    "ash", "ash_repair", "duanwen", "duanwen_repair", "material",
    "component_material", "inscriber", "inscription", "inscription_script",
    "inscription_color", "provenance", "current_holder", "restoration",
}

MULTI_VALUE_SLOTS = {
    "duanwen", "duanwen_repair", "material", "component_material", "alias",
    "inscriber", "inscription", "seal", "provenance", "component", "bibliography",
}

CHAR_VARIANTS = str.maketrans({
    "籟": "籁", "鳳": "凤", "龍": "龙", "壺": "壶", "鳴": "鸣",
    "韻": "韵", "飛": "飞", "萬": "万", "臺": "台", "於": "于",
})


def clean(value) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.translate(CHAR_VARIANTS)
    text = re.sub(r"\s+", "", text).strip()
    return "" if text.lower() == "nan" else text


def clean_name(value) -> str:
    return re.sub(r"^\d+[_-]", "", clean(value))


def record_id(source_id: str, number: int) -> str:
    return f"{source_id}{number:0{BOOKS[source_id]['pad']}d}"


def source_record_id(source_id: str, number: int) -> str:
    return f"{source_id}-{number:0{BOOKS[source_id]['pad']}d}"


def is_artifact(value) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true", "yes"}


def number_from(value) -> int:
    match = re.search(r"\d+", str(value))
    if not match:
        raise ValueError(f"Cannot parse artifact number: {value!r}")
    return int(match.group())


def canonical_value(slot: str, raw: str) -> dict:
    original = clean(raw)
    text = original.replace("～", "~").replace("—", "-").replace("–", "-")
    text = re.sub(r"[（(][^）)]*[）)]", "", text)
    text = re.sub(r"^(通体|遍体|面髹|底髹)", "", text)

    numeric = re.search(r"(-?\d+(?:\.\d+)?)\s*(厘米|公分|cm)", original, re.I)
    if numeric:
        number = float(numeric.group(1))
        return {
            "raw": original,
            "canonical": f"{number:g} cm",
            "group": "numeric:cm",
            "value_type": "numeric",
            "numeric_value": number,
            "unit": "cm",
        }

    if slot in {"dating", "dating_assessment"}:
        text = re.sub(r"^(唐|宋|元|明|清)$", r"\1代", text)
        group = re.match(r"^(北宋|南宋|中唐|盛唐|晚唐|唐代|宋代|元代|明代|清代|五代|民国)", text)
        return {
            "raw": original,
            "canonical": text,
            "group": ("宋代" if group and group.group(1) in {"北宋", "南宋"} else group.group(1) if group else text),
            "value_type": "temporal",
        }

    if slot in {"lacquer", "lacquer_repair"}:
        text = text.replace("黑色漆", "黑漆").replace("黑色", "黑漆")
        text = text.replace("栗壳色", "栗壳色漆").replace("枣红色漆", "枣红漆")
        text = re.sub(r"漆漆$", "漆", text)
        group = next((color for color in ("黑", "栗壳", "枣红", "朱", "紫", "褐", "红") if color in text), text)
        return {"raw": original, "canonical": text, "group": group, "value_type": "categorical"}

    if slot in {"ash", "ash_repair"}:
        if text == "鹿角霜":
            text = "鹿角霜灰"
        elif text == "鹿角灰":
            text = "鹿角灰"
        group = "鹿角灰类" if "鹿角" in text else ("瓦灰类" if "瓦灰" in text else text)
        return {"raw": original, "canonical": text, "group": group, "value_type": "categorical"}

    return {"raw": original, "canonical": text, "group": text, "value_type": "text"}


def image_inventory(rid: str) -> list[dict]:
    folder = RAW_IMAGES / rid
    image_dir = folder / "images" if (folder / "images").exists() else folder
    if not image_dir.exists():
        return []
    assets = []
    for path in sorted(image_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        rel = path.relative_to(image_dir).as_posix()
        stem = path.stem.lower()
        kind = "detail" if any(token in stem for token in ("mingwen", "qintou", "qinwei", "qindi", "qimian", "qincemian", "yanzu")) else "page_or_other"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assets.append({
            "asset_id": f"image:{rid}:{rel}",
            "file": rel,
            "kind": kind,
            "path": f"/api/image/{rid}/{rel}",
            "sha256": digest,
        })
    return assets


def text_inventory(source_id: str, rid: str) -> dict:
    id_path = RAW_TEXT / f"{source_id}-txt-id" / f"{rid}.txt"
    clean_path = RAW_TEXT / f"{source_id}-txt-clean" / f"{rid}.txt"
    path = id_path if id_path.exists() else clean_path if clean_path.exists() else None
    text = path.read_text(encoding="utf-8", errors="replace") if path else ""
    return {
        "id_path": id_path.relative_to(BASE).as_posix() if id_path.exists() else None,
        "clean_path": clean_path.relative_to(BASE).as_posix() if clean_path.exists() else None,
        "url": f"/api/text/{rid}" if id_path.exists() else None,
        "char_count": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
    }


def load_source_records(source_id: str) -> list[dict]:
    entity_path = RAW_TRIPLETS / f"{source_id}_output_l2_excels_merged_entities_with_book.xlsx"
    relation_path = RAW_TRIPLETS / f"{source_id}_output_l2_excels_merged_relations_with_book.xlsx"
    entities = pd.read_excel(entity_path)
    relations = pd.read_excel(relation_path)
    records = []

    for _, entity in entities.iterrows():
        if not is_artifact(entity.get("is Artifact")):
            continue
        number = number_from(entity.get("belongs_to"))
        rid = record_id(source_id, number)
        raw_name = clean_name(entity.get("实体"))
        sub = relations[relations["belongs_to"].apply(number_from) == number]
        raw_relations = []
        slot_values = defaultdict(list)
        slot_parts = defaultdict(list)
        for _, relation in sub.iterrows():
            predicate = clean(relation.get("关系"))
            head = clean(relation.get("头实体"))
            value = clean(relation.get("尾实体"))
            item = {
                "subject": head,
                "predicate": predicate,
                "object": value,
                "level": clean(relation.get("层级标签")),
                "slot": RELATION_TO_SLOT.get(predicate),
            }
            raw_relations.append(item)
            slot = RELATION_TO_SLOT.get(predicate)
            if slot and value:
                slot_values[slot].append(value)
                slot_parts[slot].append(head)

        images = image_inventory(rid)
        text = text_inventory(source_id, rid)
        values = {slot: sorted(set(items)) for slot, items in slot_values.items()}
        normalized = {
            slot: [canonical_value(slot, value) for value in items]
            for slot, items in values.items()
        }
        display_name = f"无名琴 · {rid}" if raw_name == "无名琴" else raw_name
        records.append({
            "record_id": rid,
            "source_record_id": source_record_id(source_id, number),
            "source_id": source_id,
            "source_number": number,
            "display_name": display_name,
            "raw_name": raw_name,
            "normalized_name": clean_name(raw_name),
            "slots": values,
            "normalized_slots": normalized,
            "slot_parts": {slot: sorted(set(parts)) for slot, parts in slot_parts.items()},
            "relations": raw_relations,
            "evidence": {
                "text": text,
                "images": images,
                "alignment_status": "exact" if text["id_path"] and images else "incomplete_assets",
            },
        })
    return records


def stable_features(record: dict) -> set[str]:
    features = set()
    for slot in ("current_holder", "provenance", "inscription", "form", "dating", "material"):
        for item in record["normalized_slots"].get(slot, []):
            value = item["canonical"]
            if value:
                features.add(f"{slot}:{value}")
    return features


def identity_feature_sets(record: dict) -> tuple[set[str], set[str]]:
    anchors = set()
    secondary = set()
    for slot in ("inscription", "inscriber", "naming_origin", "provenance", "current_holder"):
        for item in record["normalized_slots"].get(slot, []):
            if item["canonical"]:
                anchors.add(f"{slot}:{item['canonical']}")
    for slot in ("form", "dating", "dating_assessment", "material", "ash", "lacquer", "duanwen"):
        for item in record["normalized_slots"].get(slot, []):
            if item["canonical"]:
                secondary.add(f"{slot}:{item['canonical']}")
    return anchors, secondary


def alignment_score(left: dict, right: dict) -> tuple[float, list[str]]:
    if left["normalized_name"] != right["normalized_name"]:
        return 0.0, []
    unnamed = left["normalized_name"] == "无名琴"
    reasons = ["exact normalized name" if not unnamed else "both records are unnamed"]
    score = 0.25 if not unnamed else 0.08
    if unnamed:
        left_anchors, left_secondary = identity_feature_sets(left)
        right_anchors, right_secondary = identity_feature_sets(right)
        shared_anchors = left_anchors & right_anchors
        shared_secondary = left_secondary & right_secondary
        if shared_anchors:
            score += min(0.56, 0.28 * len(shared_anchors))
            reasons.extend(f"shared identity anchor {item.split(':', 1)[0]}" for item in sorted(shared_anchors))
        if shared_secondary:
            score += min(0.32, 0.08 * len(shared_secondary))
            reasons.extend(f"shared {item.split(':', 1)[0]} evidence" for item in sorted(shared_secondary))
        return min(score, 1.0), reasons
    shared = stable_features(left) & stable_features(right)
    slot_matches = {feature.split(":", 1)[0] for feature in shared}
    if shared:
        score += min(0.45, 0.12 * len(shared))
        reasons.extend(f"shared {slot} evidence" for slot in sorted(slot_matches))
    if "current_holder" in slot_matches:
        score += 0.18
    if "inscription" in slot_matches:
        score += 0.16
    if "provenance" in slot_matches:
        score += 0.12
    if {"form", "dating"}.issubset(slot_matches):
        score += 0.08
    return min(score, 1.0), reasons


class UnionFind:
    def __init__(self, items):
        self.parent = {item: item for item in items}

    def find(self, item):
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left, right):
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[b] = a


def group_records(records: list[dict]) -> tuple[list[list[dict]], list[dict]]:
    by_name = defaultdict(list)
    for record in records:
        if record["normalized_name"]:
            by_name[record["normalized_name"]].append(record)

    uf = UnionFind([record["record_id"] for record in records])
    candidates = []
    for name, group in by_name.items():
        for index, left in enumerate(group):
            for right in group[index + 1:]:
                if left["source_id"] == right["source_id"]:
                    continue
                score, reasons = alignment_score(left, right)
                minimum_candidate_score = 0.35 if name == "无名琴" else 0.25
                if score < minimum_candidate_score:
                    continue
                if score < 0.35:
                    candidates.append({
                        "left_record": left["record_id"],
                        "right_record": right["record_id"],
                        "normalized_name": name,
                        "score": round(score, 3),
                        "status": "ambiguous",
                        "reasons": reasons,
                    })
                else:
                    if name == "无名琴":
                        left_anchors, _ = identity_feature_sets(left)
                        right_anchors, _ = identity_feature_sets(right)
                        anchor_count = len(left_anchors & right_anchors)
                        status = "confirmed" if score >= 0.55 and anchor_count >= 1 else "candidate"
                    else:
                        status = "confirmed" if score >= 0.55 else "candidate"
                    candidates.append({
                        "left_record": left["record_id"],
                        "right_record": right["record_id"],
                        "normalized_name": name,
                        "score": round(score, 3),
                        "status": status,
                        "reasons": reasons,
                    })
                    if status == "confirmed":
                        uf.union(left["record_id"], right["record_id"])

    grouped = defaultdict(list)
    for record in records:
        grouped[uf.find(record["record_id"])].append(record)
    return list(grouped.values()), candidates


def preferred_image(slot: str, images: list[dict]) -> str | None:
    preferences = {
        "inscription": ("mingwen", "qimian"),
        "seal": ("mingwen",),
        "duanwen": ("qimian", "qindi", "qincemian"),
        "lacquer": ("qimian", "qindi"),
        "ash": ("qindi", "qimian"),
        "form": ("qintou", "qimian", "qinwei"),
    }.get(slot, ("qimian", "qindi", "qintou"))
    for token in preferences:
        for image in images:
            if token in image["file"].lower():
                return image["path"]
    return images[0]["path"] if images else None


def image_match_type(slot: str, images: list[dict]) -> str:
    if not images:
        return "missing"
    preferences = {
        "inscription": ("mingwen", "qimian"),
        "seal": ("mingwen",),
        "duanwen": ("qimian", "qindi", "qincemian"),
        "lacquer": ("qimian", "qindi"),
        "ash": ("qindi", "qimian"),
        "form": ("qintou", "qimian", "qinwei"),
    }.get(slot, ("qimian", "qindi", "qintou"))
    return "attribute-linked" if any(
        any(token in image["file"].lower() for token in preferences)
        for image in images
    ) else "record-level-fallback"


def classify_slot(slot: str, records: list[dict]) -> dict:
    assertions = []
    for record in records:
        values = record["slots"].get(slot, [])
        details = record["normalized_slots"].get(slot, [])
        assertions.append({
            "source": record["source_id"],
            "record_id": record["record_id"],
            "source_record_id": record["source_record_id"],
            "record_name": record["display_name"],
            "values": values,
            "normalized_values": [item["canonical"] for item in details],
            "value_details": details,
            "image_path": preferred_image(slot, record["evidence"]["images"]),
            "metadata": {
                "text_url": record["evidence"]["text"]["url"],
                "text_id_path": record["evidence"]["text"]["id_path"],
                "image_files": [image["file"] for image in record["evidence"]["images"]],
                "image_paths": [image["path"] for image in record["evidence"]["images"]],
                "image_match": image_match_type(slot, record["evidence"]["images"]),
                "slot_parts": record["slot_parts"].get(slot, []),
            },
        })

    present = [item for item in assertions if item["values"]]
    normalized_sets = [set(item["normalized_values"]) for item in present]
    if len(present) <= 1:
        status, conflict_type = "single_source", "single_source"
    elif len(set(map(tuple, normalized_sets))) == 1:
        raw_sets = [tuple(item["values"]) for item in present]
        status, conflict_type = ("consensus", "consensus") if len(set(raw_sets)) == 1 else ("overlap", "lexical_variant")
    elif slot in MULTI_VALUE_SLOTS and set.intersection(*normalized_sets):
        status, conflict_type = "overlap", "partial_overlap"
    elif all(item["value_details"] and all(detail["value_type"] == "numeric" for detail in item["value_details"]) for item in present):
        status, conflict_type = "differ", "numeric_discrepancy"
    elif slot in {"dating", "dating_assessment"} and len({item["value_details"][0].get("group") for item in present if item["value_details"]}) == 1:
        status, conflict_type = "overlap", "temporal_granularity"
    else:
        status, conflict_type = "differ", "substantive_conflict"

    return {
        "slot": slot,
        "label": SLOT_LABELS.get(slot, slot),
        "status": status,
        "conflict_type": conflict_type,
        "source_count": len(present),
        "assertions": assertions,
    }


def artifact_from_group(group: list[dict], candidates: list[dict]) -> dict:
    group_ids = [record["record_id"] for record in group]
    first = group[0]
    digest = hashlib.sha1("|".join(sorted(group_ids)).encode("utf-8")).hexdigest()[:10]
    artifact_id = f"gq-object-{digest}"
    slots = sorted({slot for record in group for slot in record["slots"]})
    all_slots = [classify_slot(slot, group) for slot in slots]
    caus = [item for item in all_slots if item["slot"] in ANALYSIS_SLOTS]
    exact_pairs = [item for item in candidates if item["left_record"] in group_ids and item["right_record"] in group_ids]
    related_candidates = [
        item for item in candidates
        if item["left_record"] in group_ids or item["right_record"] in group_ids
    ]
    status = "confirmed" if len(group) > 1 and all(item["status"] == "confirmed" for item in exact_pairs) else "source-local"
    if len(group) > 1 and status != "confirmed":
        status = "candidate"
    if len(group) == 1 and related_candidates:
        status = "candidate"
    display_name = first["display_name"]
    if len(group) > 1 and first["normalized_name"] == "无名琴":
        display_name = "无名琴 · " + " / ".join(group_ids)
    return {
        "artifact_id": artifact_id,
        "name": display_name if len(group) > 1 else first["display_name"],
        "canonical_name": first["normalized_name"],
        "raw_names": sorted({record["raw_name"] for record in group}),
        "books": sorted({record["source_id"] for record in group}),
        "records": group_ids,
        "aligned": status == "confirmed",
        "alignment_status": status,
        "alignment_evidence": exact_pairs,
        "alignment_candidates": related_candidates,
        "all_slots": all_slots,
        "caus": caus,
        "images": {
            record["source_id"]: [image["file"] for image in record["evidence"]["images"]]
            for record in group
        },
        "record_evidence": {
            record["record_id"]: record["evidence"] for record in group
        },
        "relations": {
            record["record_id"]: record["relations"] for record in group
        },
    }


def source_catalog() -> dict:
    catalog = {}
    manifest_path = BASE / "books.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    for item in manifest:
        source_id = item["id"]
        metadata = ALL_SOURCES.get(source_id, {"title": item.get("title", source_id), "role": "unclassified"})
        catalog[source_id] = {
            **item,
            "title": metadata["title"],
            "role": metadata["role"],
            "analysis_scope": "primary" if metadata["role"] == "multimodal_primary" else "context_only",
        }
    return catalog


def main() -> None:
    records = [record for source_id in BOOKS for record in load_source_records(source_id)]
    groups, candidates = group_records(records)
    artifacts = [artifact_from_group(group, candidates) for group in groups]

    assertions = []
    conflicts = []
    for artifact in artifacts:
        # The complete assertion index includes auxiliary slots.  The conflict
        # queue is intentionally restricted to the curated analysis projection.
        for cau in artifact["all_slots"]:
            for assertion in cau["assertions"]:
                assertions.append({
                    "assertion_id": f"{artifact['artifact_id']}:{cau['slot']}:{assertion['record_id']}",
                    "artifact_id": artifact["artifact_id"],
                    "slot": cau["slot"],
                    **assertion,
                })
        for cau in artifact["caus"]:
            if cau["status"] not in {"consensus", "single_source"}:
                conflicts.append({
                    "conflict_id": f"conflict:{artifact['artifact_id']}:{cau['slot']}",
                    "artifact_id": artifact["artifact_id"],
                    "slot": cau["slot"],
                    "label": cau["label"],
                    "status": cau["status"],
                    "conflict_type": cau["conflict_type"],
                    "source_count": cau["source_count"],
                    "assertion_ids": [
                        f"{artifact['artifact_id']}:{cau['slot']}:{item['record_id']}"
                        for item in cau["assertions"] if item["values"]
                    ],
                })

    source_catalog_data = source_catalog()
    image_hashes = defaultdict(list)
    for record in records:
        for image in record["evidence"]["images"]:
            image_hashes[image["sha256"]].append({
                "record_id": record["record_id"],
                "source_id": record["source_id"],
                "file": image["file"],
            })
    duplicate_images = [items for items in image_hashes.values() if len(items) > 1]
    output = {
        "schema_version": "case1-evidence-graph-1",
        "case": {
            "id": "guqin",
            "number": 1,
            "label": "Case 1 · Guqin",
            "title": "Multimodal Guqin Knowledge Conflict Corpus",
            "description": "Source-local guqin records aligned into evidence-bearing attribute assertions.",
        },
        "books": {source_id: metadata["title"] for source_id, metadata in PRIMARY_SOURCES.items()},
        "source_catalog": source_catalog_data,
        "records": records,
        "artifacts": artifacts,
        "assertions": assertions,
        "alignment_candidates": candidates,
        "conflicts": conflicts,
        "stats": {
            "records": len(records),
            "artifacts": len(artifacts),
            "aligned_artifacts": sum(item["alignment_status"] == "confirmed" for item in artifacts),
            "candidate_artifacts": sum(item["alignment_status"] == "candidate" for item in artifacts),
            "source_local_artifacts": sum(item["alignment_status"] == "source-local" for item in artifacts),
            "assertions": len(assertions),
            "conflicts": len(conflicts),
            "consensus_slots": sum(item["status"] == "consensus" for artifact in artifacts for item in artifact["caus"]),
            "single_source_slots": sum(item["status"] == "single_source" for artifact in artifacts for item in artifact["caus"]),
            "conflict_types": dict(Counter(item["conflict_type"] for item in conflicts)),
            "differ": sum(item["status"] == "differ" for artifact in artifacts for item in artifact["caus"]),
            "overlap": sum(item["status"] == "overlap" for artifact in artifacts for item in artifact["caus"]),
            "consensus": sum(item["status"] == "consensus" for artifact in artifacts for item in artifact["caus"]),
            "single_source": sum(item["status"] == "single_source" for artifact in artifacts for item in artifact["caus"]),
            "primary_sources": len(PRIMARY_SOURCES),
            "context_sources": len(CONTEXT_SOURCES),
            "records_with_text": sum(bool(record["evidence"]["text"]["id_path"]) for record in records),
            "records_with_images": sum(bool(record["evidence"]["images"]) for record in records),
            "analysis_slots": sorted(ANALYSIS_SLOTS),
        },
        "quality_policy": {
            "raw_layer_immutable": True,
            "source_is_provenance_not_entity": True,
            "unnamed_records_auto_merged": False,
            "same_name_requires_identity_evidence": True,
            "analysis_slots_are_a_curated_projection": True,
            "raw_values_preserved": True,
            "normalized_values_are_comparison_keys": True,
            "unmapped_relations_preserved": True,
            "text_only_sources_excluded_from_primary_multimodal_scope": True,
        },
    }
    OUT.mkdir(exist_ok=True)
    target = OUT / "case1_guqin.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    audit = {
        "schema_version": "case1-audit-2",
        "case": output["case"],
        "source_catalog": source_catalog_data,
        "stats": output["stats"],
        "alignment_candidates": candidates,
        "asset_issues": [
            {
                "record_id": record["record_id"],
                "source_id": record["source_id"],
                "status": record["evidence"]["alignment_status"],
                "text": record["evidence"]["text"],
                "image_count": len(record["evidence"]["images"]),
            }
            for record in records
            if record["evidence"]["alignment_status"] != "exact"
        ],
        "unmapped_relations": dict(Counter(
            relation["predicate"]
            for record in records
            for relation in record["relations"]
            if relation["slot"] is None
        )),
        "duplicate_images": duplicate_images,
    }
    (OUT / "case1_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(target), "audit": str(OUT / 'case1_audit.json'), "stats": output["stats"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
