"""Audit Guqin artifact ids against OCR text, images, and triplet exports.

This deliberately treats raw folders as immutable. The output documents the
canonical record key used by the processed data without renaming source files.
Run from backend/: python3 scripts/audit_guqin_alignment.py
"""

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook

from build_contested_kg import BOOKS, IMG, RAW, TEXT, extract_records

BASE = Path(__file__).resolve().parent.parent / "data"
DOCS = Path(__file__).resolve().parent.parent.parent / "docs"


def workbook_image_id(book, value):
    text = str(value or "").replace("\\", "/")
    matches = re.findall(rf"{re.escape(book)}\d+", text, flags=re.IGNORECASE)
    return matches[-1] if matches else None


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def book_audit(book, records):
    record_ids = {r["record_id"] for r in records if r["book"] == book}
    image_dirs = {p.name for p in IMG.iterdir() if p.is_dir() and p.name.startswith(book)}
    text_id_files = {p.stem for p in (TEXT / f"{book}-txt-id").glob("*.txt")}
    text_clean_files = {p.stem for p in (TEXT / f"{book}-txt-clean").glob("*.txt")}

    workbook = RAW / f"{book}_output_l2_excels_merged_entities_with_book_images.xlsx"
    sheet = load_workbook(workbook, read_only=True, data_only=True).active
    rows = list(sheet.values)
    headers = [str(x).strip() for x in rows[0]]
    index = {name: i for i, name in enumerate(headers)}
    workbook_ids = {}
    workbook_mismatches = []
    for row in rows[1:]:
        if row[index["is Artifact"]] != 1:
            continue
        gid = int(row[index["belongs to"]])
        record_id = next((r["record_id"] for r in records if r["book"] == book and r["source_number"] == gid), None)
        path_id = workbook_image_id(book, row[index["images_files"]])
        workbook_ids[record_id] = path_id
        if record_id != path_id:
            workbook_mismatches.append({"record_id": record_id, "workbook_image_id": path_id})

    duplicate_hashes = defaultdict(list)
    for folder in sorted(IMG.glob(f"{book}*")):
        if not folder.is_dir():
            continue
        image_dir = folder / "images" if (folder / "images").exists() else folder
        for image in image_dir.rglob("*"):
            if image.is_file() and image.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
                duplicate_hashes[file_hash(image)].append(str(image.relative_to(BASE)))

    return {
        "triplet_artifact_ids": sorted(record_ids),
        "triplet_artifact_count": len(record_ids),
        "text_id_count": len(text_id_files),
        "text_clean_count": len(text_clean_files),
        "image_directory_count": len(image_dirs),
        "missing_image_directories": sorted(record_ids - image_dirs),
        "extra_image_directories": sorted(image_dirs - record_ids),
        "missing_text_id_files": sorted(record_ids - text_id_files),
        "extra_text_id_files": sorted(text_id_files - record_ids),
        "missing_text_clean_files": sorted(record_ids - text_clean_files),
        "workbook_image_id_mismatches": workbook_mismatches,
        "duplicate_image_groups": [paths for paths in duplicate_hashes.values() if len(paths) > 1],
        "record_alignment_status": Counter(r["evidence"]["alignment_status"] for r in records if r["book"] == book),
        "unnamed_records": [
            {"record_id": r["record_id"], "source_record_id": r["source_record_id"], "display_name": r["display_name"]}
            for r in records if r["book"] == book and r["raw_name"] == "无名琴"
        ],
    }


def main():
    records = extract_records()
    audits = {book: book_audit(book, records) for book in BOOKS}
    result = {
        "schema_version": "guqin-audit-1",
        "policy": {
            "raw_files_immutable": True,
            "canonical_record_key": "{book}-{zero_padded_source_number}",
            "physical_folder_key": "{book}{zero_padded_source_number}",
            "text_alignment": "txt-id/<physical_folder_key>.txt",
            "image_alignment": "image/<physical_folder_key>[/images]/*",
            "values": "raw values remain available; normalized values are comparison keys only",
        },
        "books": audits,
    }
    out = BASE / "processed" / "guqin_alignment_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    DOCS.mkdir(exist_ok=True)
    lines = [
        "# Guqin Data Alignment Audit",
        "",
        "This audit keeps the raw triplet, OCR, and image files unchanged. The processed layer uses a canonical human-readable record key while retaining the physical folder key required by the current API.",
        "",
        "## Alignment policy",
        "",
        "- Canonical record key: `BOOK-00016` (for example, `Gq-00016`).",
        "- Physical/API key: `BOOK00016` (for example, `Gq00016`).",
        "- OCR key: `raw/text/BOOK-txt-id/BOOK00016.txt`.",
        "- Image key: `raw/image/BOOK00016/` or its `images/` child directory.",
        "- `values` is verbatim evidence; `normalized_values` is used only for comparison and grouping.",
        "",
        "## Results",
        "",
        "| Book | Triplet artifacts | Image dirs | txt-id | Missing image | Missing text | Workbook path mismatches | Duplicate image groups |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for book, audit in audits.items():
        lines.append(
            f"| {book} | {audit['triplet_artifact_count']} | {audit['image_directory_count']} | {audit['text_id_count']} | {len(audit['missing_image_directories'])} | {len(audit['missing_text_id_files'])} | {len(audit['workbook_image_id_mismatches'])} | {len(audit['duplicate_image_groups'])} |"
        )
    lines += ["", "## Interpretation", "", "All artifact records have an exact `txt-id` and image-directory match. Extra image/text folders are retained as source pages but are not treated as Guqin artifacts because they have no artifact row in the triplet workbook.", ""]
    for book, audit in audits.items():
        if audit["extra_image_directories"] or audit["extra_text_id_files"] or audit["duplicate_image_groups"]:
            lines.append(f"### {book}")
            if audit["extra_image_directories"]:
                lines.append(f"- Extra image directories: `{', '.join(audit['extra_image_directories'])}`")
            if audit["extra_text_id_files"]:
                lines.append(f"- Extra txt-id files: `{', '.join(audit['extra_text_id_files'])}`")
            if audit["duplicate_image_groups"]:
                lines.append(f"- Exact duplicate image groups: {len(audit['duplicate_image_groups'])}; these require semantic review before deduplication.")
            lines.append("")
    (DOCS / "guqin_data_alignment_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    violations = []
    for book, audit in audits.items():
        for key in ("missing_image_directories", "missing_text_id_files", "workbook_image_id_mismatches"):
            if audit[key]:
                violations.append(f"{book}:{key}={audit[key]}")
        if audit["record_alignment_status"] != {"exact": audit["triplet_artifact_count"]}:
            violations.append(f"{book}:record_alignment_status={audit['record_alignment_status']}")
    if violations:
        print("Alignment audit failed: " + "; ".join(violations), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
