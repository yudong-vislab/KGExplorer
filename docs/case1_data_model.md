# Case 1 Data Model

`backend/data/processed/case1_guqin.json` is the canonical processed dataset for
the Guqin case. The raw triplet workbooks, OCR text, and image folders remain
unchanged.

## Layers

1. `source_catalog`: source title, availability, modality, and analysis role.
2. `records`: one source-local instrument record per workbook artifact.
3. `assertions`: attribute values extracted from a source record, retaining raw
   values, normalized comparison values, OCR references, and image assets.
4. `artifacts`: canonical object projections. `caus` is the curated analysis
   projection; `all_slots` retains the complete mapped attribute index.
5. `alignment_candidates`: same-name records that need identity review.
6. `conflicts`: attribute-level differences for the analysis projection.

## Source roles

The four sources with triplets, OCR, and instrument images are the primary
multimodal corpus: `Gq`, `Yjzq`, `QNQY`, and `CQL`. `Gggq`, `GCGQ`, and `WXAC`
are text-only contextual sources. `Zggq` is registered but currently lacks
processable assets. Context sources are retained in `source_catalog` and are
not counted as primary image evidence.

## Alignment policy

An exact normalized name is only an alignment candidate. Records are confirmed
as one object when independent identity evidence also agrees, such as holder,
inscription, provenance, form, or dating. Unnamed instruments are never merged
automatically. Ambiguous records remain source-local and retain their candidate
links.

## Analysis projection

The main graph and conflict queue use attributes with clear verification value:
dating, form, lacquer, ash, duanwen, material, inscriptions, provenance,
current holder, and restoration. Auxiliary relations such as person mentions,
bibliography, and component detail remain in `relations`, `all_slots`, and the
complete `assertions` index without generating noise in the primary graph.

## Rebuild and audit

```bash
cd backend
python3 scripts/rebuild_case1.py
```

The script writes `processed/case1_guqin.json` and
`processed/case1_audit.json`. The audit reports missing assets, duplicate image
hashes, unresolved same-name candidates, and relations that are preserved but
not yet assigned to a comparison slot.
