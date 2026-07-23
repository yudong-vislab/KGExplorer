import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = "/Users/yudong/Desktop/KGExplorer";
const bundlePath = path.join(
  repoRoot,
  "backend/data/processed/guqin_evidence/guqin_case_evidence_bundle.json",
);
const outputDir = path.join(repoRoot, "outputs/guqin-evidence-audit");
const outputPath = path.join(outputDir, "Guqin_Case_Evidence_Table.xlsx");
const previewDir = path.join(outputDir, "previews");

const bundle = JSON.parse(await fs.readFile(bundlePath, "utf8"));
await fs.mkdir(previewDir, { recursive: true });

const workbook = Workbook.create();
const summarySheet = workbook.worksheets.add("Summary");
const evidenceSheet = workbook.worksheets.add("Evidence Table");
const assertionSheet = workbook.worksheets.add("Source Assertions");
const alignmentSheet = workbook.worksheets.add("Alignment Review");
const inventorySheet = workbook.worksheets.add("Record Inventory");
const rulesSheet = workbook.worksheets.add("Audit Rules");

const palette = {
  ink: "#24323C",
  blue: "#2F5D73",
  teal: "#4E8179",
  gold: "#A78649",
  rust: "#A95535",
  paleBlue: "#EAF1F4",
  paleTeal: "#E8F1EF",
  paleGold: "#F4EFE3",
  paleRust: "#F7E9E3",
  paleGray: "#F4F6F7",
  border: "#D7DEE2",
  white: "#FFFFFF",
};

function columnLetter(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    value -= 1;
    result = String.fromCharCode(65 + (value % 26)) + result;
    value = Math.floor(value / 26);
  }
  return result;
}

function setTitle(sheet, title, subtitle, endColumn) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${endColumn}1`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${endColumn}1`).format = {
    fill: palette.ink,
    font: { bold: true, color: palette.white, size: 16 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${endColumn}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endColumn}2`).format = {
    fill: palette.paleBlue,
    font: { color: palette.blue, size: 10 },
    verticalAlignment: "center",
    wrapText: true,
  };
  sheet.getRange("1:1").format.rowHeight = 30;
  sheet.getRange("2:2").format.rowHeight = 32;
}

function writeObjectTable(sheet, startRow, rows, tableName, widths = {}) {
  if (!rows.length) return { headers: [], endRow: startRow };
  const headers = Object.keys(rows[0]);
  const values = [
    headers,
    ...rows.map((row) => headers.map((header) => {
      const value = row[header];
      if (value === null || value === undefined) return "";
      if (typeof value === "boolean" || typeof value === "number") return value;
      return String(value);
    })),
  ];
  const endColumn = columnLetter(headers.length - 1);
  const endRow = startRow + values.length - 1;
  const range = sheet.getRange(`A${startRow}:${endColumn}${endRow}`);
  range.values = values;
  range.format = {
    font: { color: palette.ink, size: 9 },
    verticalAlignment: "top",
  };
  sheet.getRange(`A${startRow}:${endColumn}${startRow}`).format = {
    fill: palette.blue,
    font: { bold: true, color: palette.white, size: 9 },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: palette.border },
  };
  sheet.getRange(`A${startRow}:${endColumn}${endRow}`).format.borders = {
    insideHorizontal: { style: "thin", color: palette.border },
  };
  const table = sheet.tables.add(`A${startRow}:${endColumn}${endRow}`, true, tableName);
  table.style = "TableStyleMedium2";
  table.showBandedRows = true;
  sheet.freezePanes.freezeRows(startRow);
  sheet.freezePanes.freezeColumns(3);
  headers.forEach((header, index) => {
    const letter = columnLetter(index);
    const width = widths[header] ?? 15;
    sheet.getRange(`${letter}:${letter}`).format.columnWidth = width;
    if (width >= 22) {
      sheet.getRange(`${letter}${startRow + 1}:${letter}${endRow}`).format.wrapText = true;
    }
  });
  return { headers, endRow, endColumn };
}

setTitle(
  summarySheet,
  "Guqin Case Evidence Table",
  "Machine-audited evidence lineage for four multimodal Guqin sources. Automated checks do not replace historical adjudication.",
  "J",
);
summarySheet.getRange("A4:J4").merge();
summarySheet.getRange("A4").values = [["Corpus and processing audit"]];
summarySheet.getRange("A4:J4").format = {
  fill: palette.blue,
  font: { bold: true, color: palette.white, size: 11 },
};

const metrics = [
  ["Primary books", bundle.summary.source_books, "Scope used by the current Case 1 pipeline"],
  ["Source records", bundle.summary.records, "Artifact records represented in the canonical case"],
  ["Records with OCR text", bundle.summary.records_with_text, "Resolved text files"],
  ["Records with linked images", bundle.summary.records_with_images, "Resolved multimodal records"],
  ["Raw image files", bundle.summary.raw_image_files, "All image files under backend/data/raw/image"],
  ["Images linked to canonical records", bundle.summary.linked_image_files, "Images referenced by current processed records"],
  ["Extra or unlinked images", bundle.summary.unlinked_or_extra_image_files, "Files in extra/non-canonical record folders"],
  ["Canonical artifacts", bundle.summary.artifacts, "Current same-object grouping output"],
  ["Confirmed multi-source artifacts", bundle.summary.aligned_artifacts, "Current builder status; see Alignment Review"],
  ["Extracted assertions", bundle.summary.assertions, "Comparable and source-local statements"],
  ["Conflict candidates", bundle.summary.conflict_candidates, "Rows in Evidence Table"],
  ["Source assertions in candidates", bundle.summary.source_assertions_in_candidates, "Rows in Source Assertions"],
];
summarySheet.getRange(`A5:C${5 + metrics.length}`).values = [
  ["Metric", "Count", "Definition"],
  ...metrics,
];
summarySheet.getRange(`A5:C5`).format = {
  fill: palette.teal,
  font: { bold: true, color: palette.white },
};
summarySheet.getRange(`A6:C${4 + metrics.length}`).format.borders = {
  insideHorizontal: { style: "thin", color: palette.border },
};
summarySheet.getRange("A:A").format.columnWidth = 30;
summarySheet.getRange("B:B").format.columnWidth = 14;
summarySheet.getRange("B6:B20").format.numberFormat = "#,##0";
summarySheet.getRange("C:C").format.columnWidth = 54;
summarySheet.getRange("C6:C20").format.wrapText = true;

summarySheet.getRange("E5:J5").merge();
summarySheet.getRange("E5").values = [["Review readiness"]];
summarySheet.getRange("E5:J5").format = {
  fill: palette.teal,
  font: { bold: true, color: palette.white },
};
const readinessLabels = [
  ["P1_expert_review", "Ready for expert judgement", palette.paleTeal],
  ["P2_data_cleanup", "Clean OCR/scope/reference issues first", palette.paleRust],
  ["P3_alignment_review", "Confirm same-object alignment first", palette.paleGold],
  ["Exclude_lexical_variant", "Do not report as substantive conflict", palette.paleGray],
];
readinessLabels.forEach((item, index) => {
  const row = 6 + index;
  summarySheet.getRange(`E${row}:G${row}`).merge();
  summarySheet.getRange(`E${row}`).values = [[item[0]]];
  summarySheet.getRange(`H${row}:I${row}`).merge();
  summarySheet.getRange(`H${row}`).values = [[item[1]]];
  summarySheet.getRange(`J${row}`).formulas = [[
    `=COUNTIF('Evidence Table'!$V$4:$V$${bundle.evidence_table.length + 3},"${item[0]}")`,
  ]];
  summarySheet.getRange(`E${row}:J${row}`).format = {
    fill: item[2],
    borders: { preset: "outside", style: "thin", color: palette.border },
  };
});
summarySheet.getRange("E:E").format.columnWidth = 20;
summarySheet.getRange("H:I").format.columnWidth = 15;
summarySheet.getRange("J:J").format.columnWidth = 12;
summarySheet.getRange("J6:J9").format.numberFormat = "#,##0";

summarySheet.getRange("E11:J11").merge();
summarySheet.getRange("E11").values = [["Expert decision tracker"]];
summarySheet.getRange("E11:J11").format = {
  fill: palette.gold,
  font: { bold: true, color: palette.white },
};
const expertDecisions = [
  "Unreviewed",
  "Conflict confirmed",
  "Compatible descriptions",
  "OCR/extraction error",
  "Different objects",
  "Insufficient evidence",
];
expertDecisions.forEach((decision, index) => {
  const row = 12 + index;
  summarySheet.getRange(`E${row}:I${row}`).merge();
  summarySheet.getRange(`E${row}`).values = [[decision]];
  summarySheet.getRange(`J${row}`).formulas = [[
    `=COUNTIF('Evidence Table'!$X$4:$X$${bundle.evidence_table.length + 3},"${decision}")`,
  ]];
  summarySheet.getRange(`E${row}:J${row}`).format.borders = {
    insideHorizontal: { style: "thin", color: palette.border },
  };
});

summarySheet.getRange("A19:J19").merge();
summarySheet.getRange("A19").values = [["Verified findings and limitations"]];
summarySheet.getRange("A19:J19").format = {
  fill: palette.rust,
  font: { bold: true, color: palette.white },
};
const findings = [
  "The current pipeline contains 154 canonical source records with both OCR text and linked images.",
  "Only 23 of 74 conflict candidates pass the automated lineage checks and are ready for expert review.",
  "46 candidates require data cleanup before domain interpretation; frequent causes are mixed component scope, internal entity references, placeholders, or OCR text mismatch.",
  `The raw image directory contains ${bundle.summary.raw_image_files} files, but ${bundle.summary.linked_image_files} are linked to the 154 canonical records; ${bundle.summary.unlinked_or_extra_image_files} belong to extra/non-canonical folders and must not be silently counted as case evidence.`,
  "The current graph builder omits dimensions stored in entity attributes, even though they provide strong same-object identity evidence.",
  ...bundle.summary.known_ocr_anomalies,
  "Machine audit verifies traceability and internal consistency only. Final same-object and historical conflict decisions require Guqin domain experts.",
];
summarySheet.getRange(`A20:J${19 + findings.length}`).merge(true);
summarySheet.getRange(`A20:A${19 + findings.length}`).values = findings.map((item) => [item]);
summarySheet.getRange(`A20:J${19 + findings.length}`).format = {
  wrapText: true,
  verticalAlignment: "top",
  borders: { preset: "inside", style: "thin", color: palette.border },
};
summarySheet.getRange(`20:${19 + findings.length}`).format.rowHeight = 30;
summarySheet.freezePanes.freezeRows(4);

setTitle(
  evidenceSheet,
  "Evidence Table",
  "One row per current conflict candidate. Filter Review Readiness before selecting paper examples; fill the three expert columns only after reviewing source assertions and images.",
  "AA",
);
const evidenceWidths = {
  case_row_id: 11, conflict_id: 22, artifact_id: 18, artifact_name: 22,
  record_ids: 28, source_count: 10, sources: 17, identity_grade: 14,
  alignment_status: 14, slot: 17, slot_label: 14, conflict_type: 19,
  current_status: 13, Gq_value: 26, Yjzq_value: 26, QNQY_value: 26,
  CQL_value: 26, text_support: 18, image_support: 23, subject_scope: 28,
  audit_flags: 28, review_readiness: 22, machine_audit_note: 38,
  expert_decision: 22, expert_canonical_value: 28, expert_rationale: 38,
};
const evidenceInfo = writeObjectTable(
  evidenceSheet, 3, bundle.evidence_table, "GuqinEvidenceTable", evidenceWidths,
);
const expertDecisionIndex = evidenceInfo.headers.indexOf("expert_decision");
const expertDecisionLetter = columnLetter(expertDecisionIndex);
evidenceSheet.getRange(
  `${expertDecisionLetter}4:${expertDecisionLetter}${evidenceInfo.endRow}`,
).dataValidation = {
  rule: { type: "list", values: expertDecisions },
};
const readinessIndex = evidenceInfo.headers.indexOf("review_readiness");
const readinessLetter = columnLetter(readinessIndex);
const readinessRange = evidenceSheet.getRange(
  `${readinessLetter}4:${readinessLetter}${evidenceInfo.endRow}`,
);
readinessRange.conditionalFormats.add("containsText", {
  text: "P1_expert_review",
  format: { fill: palette.paleTeal, font: { color: palette.teal, bold: true } },
});
readinessRange.conditionalFormats.add("containsText", {
  text: "P2_data_cleanup",
  format: { fill: palette.paleRust, font: { color: palette.rust, bold: true } },
});
readinessRange.conditionalFormats.add("containsText", {
  text: "P3_alignment_review",
  format: { fill: palette.paleGold, font: { color: palette.gold, bold: true } },
});
evidenceSheet.getRange(`A4:${evidenceInfo.endColumn}${evidenceInfo.endRow}`).format.rowHeight = 34;

setTitle(
  assertionSheet,
  "Source Assertions",
  "Source-level values, OCR support, snippets, and image paths for every conflict row. These rows provide the direct evidence trail behind the compact Evidence Table.",
  "V",
);
const assertionInfo = writeObjectTable(
  assertionSheet,
  3,
  bundle.source_assertions,
  "GuqinSourceAssertions",
  {
    conflict_id: 22, artifact_id: 18, artifact_name: 20, slot: 16,
    slot_label: 14, source_id: 10, source_title: 14, record_id: 13,
    record_name: 18, raw_values: 30, normalized_values: 30, subject_parts: 28,
    text_support: 18, value_support_detail: 34, text_snippet: 52,
    text_path: 54, image_support: 23, preferred_image: 19, image_count: 10,
    image_directory: 48, audit_flags: 30,
  },
);
assertionSheet.getRange(`A4:${assertionInfo.endColumn}${assertionInfo.endRow}`).format.rowHeight = 44;

setTitle(
  alignmentSheet,
  "Alignment Review",
  "Pairwise same-object evidence. Dimensions and inscriptions are independent anchors; name-only matches are not sufficient, especially for unnamed instruments.",
  "S",
);
const alignmentInfo = writeObjectTable(
  alignmentSheet,
  3,
  bundle.alignment_review,
  "GuqinAlignmentReview",
  {
    artifact_id: 18, artifact_name: 22, alignment_status: 15,
    left_record: 13, left_source: 11, right_record: 13, right_source: 11,
    grade: 14, same_name: 11, left_dimensions: 34, right_dimensions: 34,
    exact_dimension_fields: 24, dimension_conflicts: 28,
    inscription_similarity: 14, flags: 28, current_alignment_evidence: 38,
    expert_same_object: 22, expert_note: 38,
  },
);
const sameObjectIndex = alignmentInfo.headers.indexOf("expert_same_object");
const sameObjectLetter = columnLetter(sameObjectIndex);
alignmentSheet.getRange(
  `${sameObjectLetter}4:${sameObjectLetter}${alignmentInfo.endRow}`,
).dataValidation = {
  rule: { type: "list", values: ["Unreviewed", "Same object", "Different objects", "Insufficient evidence"] },
};
alignmentSheet.getRange(`A4:${alignmentInfo.endColumn}${alignmentInfo.endRow}`).format.rowHeight = 34;

setTitle(
  inventorySheet,
  "Record Inventory",
  "Flat inventory of the 154 canonical source records and their resolved OCR, image, dimension, and entity-attribute evidence.",
  "O",
);
const inventoryInfo = writeObjectTable(
  inventorySheet,
  3,
  bundle.record_inventory,
  "GuqinRecordInventory",
  {
    record_id: 13, source_id: 10, source_title: 15, record_name: 20,
    normalized_name: 20, text_exists: 11, text_characters: 13, image_count: 11,
    dimension_signature: 36, entity_attribute_count: 15, asset_status: 14,
    text_path: 54, image_directory: 48,
  },
);
inventorySheet.getRange(`A4:${inventoryInfo.endColumn}${inventoryInfo.endRow}`).format.rowHeight = 28;

setTitle(
  rulesSheet,
  "Audit Rules",
  "Definitions used by the automated audit. Keep these rules visible in the research package so that paper examples remain reproducible and falsifiable.",
  "F",
);
const rulesRows = [];
for (const [code, definition] of Object.entries(bundle.audit_rules.identity_grades)) {
  rulesRows.push({ category: "Identity grade", code, definition });
}
for (const [code, definition] of Object.entries(bundle.audit_rules.review_readiness)) {
  rulesRows.push({ category: "Review readiness", code, definition });
}
rulesRows.push(
  {
    category: "Text support",
    code: "supported",
    definition: "All extracted values were found exactly, after normalization, or by high-confidence fuzzy matching in the record OCR text.",
  },
  {
    category: "Text support",
    code: "structural_problem",
    definition: "At least one extracted value is a placeholder or an unresolved internal entity identifier.",
  },
  {
    category: "Scope",
    code: "mixed_subject_scope",
    definition: "Values for a slot came from multiple subjects/components and must be separated before comparison.",
  },
  {
    category: "Image support",
    code: "attribute_linked",
    definition: "A crop filename matches the disputed visual attribute category; this is availability evidence, not proof of the claim.",
  },
  {
    category: "Expert boundary",
    code: "machine-audited",
    definition: "The workbook verifies file alignment, internal consistency, and candidate readiness; a Guqin expert must adjudicate historical truth.",
  },
);
const rulesInfo = writeObjectTable(
  rulesSheet, 3, rulesRows, "GuqinAuditRules",
  { category: 22, code: 27, definition: 88 },
);
rulesSheet.getRange(`A4:${rulesInfo.endColumn}${rulesInfo.endRow}`).format.rowHeight = 38;

const previewSpecs = [
  ["Summary", "A1:J31"],
  ["Evidence Table", "A1:Z18"],
  ["Source Assertions", "A1:U15"],
  ["Alignment Review", "A1:R18"],
  ["Record Inventory", "A1:M18"],
  ["Audit Rules", "A1:C18"],
];
for (const [sheetName, range] of previewSpecs) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  const safeName = sheetName.toLowerCase().replaceAll(" ", "_");
  await fs.writeFile(
    path.join(previewDir, `${safeName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const summaryInspect = await workbook.inspect({
  kind: "table",
  range: "Summary!A1:J31",
  include: "values,formulas",
  tableMaxRows: 31,
  tableMaxCols: 10,
});
await fs.writeFile(path.join(outputDir, "summary_inspect.ndjson"), summaryInspect.ndjson);
const errorInspect = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
await fs.writeFile(path.join(outputDir, "formula_errors.ndjson"), errorInspect.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, previewDir }, null, 2));
