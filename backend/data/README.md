# KGExplorer Data

Raw OCR, triplet, and image evidence are stored under `backend/data/raw`.

## Layout

- `raw/triplet/`: extracted entity and relation workbooks.
- `raw/text/`: OCR or Markdown text snippets, grouped by source folder.
- `raw/image/`: cropped image evidence, grouped by artifact id.
- `books.json`: canonical book ids and availability flags.

## Current Source Coverage

| Book ID | Title | Triplets | Text | Images |
| --- | --- | --- | --- | --- |
| QNQY | 千年清音 | yes | yes | yes |
| Yjzq | 一见钟琴 | yes | yes | yes |
| CQL | 藏琴录 | yes | yes | yes |
| Gq | 古琴 | yes | yes | yes |
| Gggq | 故宫古琴图典 | no | yes | no |
| GCGQ | 馆藏古琴整理与研究 | no | yes | no |
| WXAC | 吾心安处 | no | yes | no |
| Zggq | 中国古琴珍萃 | no | no | no |

## Notes

The raw files are intentionally kept unchanged. Backend import scripts should build derived indices into `backend/data/processed` instead of editing files in `raw`.

Artifact ids follow the source prefix plus numeric id, such as `CQL009`, `Gq00014`, `QNQY017`, and `Yjzq00011`.
