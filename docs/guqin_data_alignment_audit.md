# Guqin Data Alignment Audit

This audit keeps the raw triplet, OCR, and image files unchanged. The processed layer uses a canonical human-readable record key while retaining the physical folder key required by the current API.

## Alignment policy

- Canonical record key: `BOOK-00016` (for example, `Gq-00016`).
- Physical/API key: `BOOK00016` (for example, `Gq00016`).
- OCR key: `raw/text/BOOK-txt-id/BOOK00016.txt`.
- Image key: `raw/image/BOOK00016/` or its `images/` child directory.
- `values` is verbatim evidence; `normalized_values` is used only for comparison and grouping.

## Results

| Book | Triplet artifacts | Image dirs | txt-id | Missing image | Missing text | Workbook path mismatches | Duplicate image groups |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gq | 42 | 44 | 44 | 0 | 0 | 0 | 0 |
| Yjzq | 51 | 104 | 51 | 0 | 0 | 0 | 0 |
| QNQY | 40 | 46 | 46 | 0 | 0 | 0 | 0 |
| CQL | 21 | 22 | 22 | 0 | 0 | 0 | 0 |

## Interpretation

All artifact records have an exact `txt-id` and image-directory match. Extra image/text folders are retained as source pages but are not treated as Guqin artifacts because they have no artifact row in the triplet workbook.

### Gq
- Extra image directories: `Gq00050, Gq00062`
- Extra txt-id files: `Gq00050, Gq00062`

### Yjzq
- Extra image directories: `Yjzq00001, Yjzq00002, Yjzq00007, Yjzq00009, Yjzq00012, Yjzq00014, Yjzq00015, Yjzq00016, Yjzq00018, Yjzq00020, Yjzq00021, Yjzq00022, Yjzq00026, Yjzq00027, Yjzq00030, Yjzq00032, Yjzq00034, Yjzq00036, Yjzq00038, Yjzq00041, Yjzq00044, Yjzq00045, Yjzq00046, Yjzq00049, Yjzq00051, Yjzq00054, Yjzq00055, Yjzq00056, Yjzq00057, Yjzq00059, Yjzq00062, Yjzq00064, Yjzq00067, Yjzq00071, Yjzq00072, Yjzq00073, Yjzq00075, Yjzq00077, Yjzq00080, Yjzq00084, Yjzq00094, Yjzq00096, Yjzq00098, Yjzq00100, Yjzq00101, Yjzq00103, Yjzq00104, Yjzq00105, Yjzq00106, Yjzq00107, Yjzq00108, Yjzq00110, Yjzq00113`

### QNQY
- Extra image directories: `QNQY055, QNQY057, QNQY075, QNQY078, QNQY079, QNQY083`
- Extra txt-id files: `QNQY055, QNQY057, QNQY075, QNQY078, QNQY079, QNQY083`

### CQL
- Extra image directories: `CQL090`
- Extra txt-id files: `CQL090`
