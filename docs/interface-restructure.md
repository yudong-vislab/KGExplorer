# KGExplorer Interface Restructure

## Paper-Oriented System Framing

KGExplorer should not be presented as a knowledge graph browser. Its paper-facing role is:

**An evidence-centered visual analytics system for discovering, inspecting, and adjudicating uncertain cultural-heritage knowledge claims extracted from scanned catalogues.**

The system should therefore avoid directly presenting conflicts as final facts. It should guide experts through a workflow from corpus evidence to candidate issues, then to side-by-side evidence comparison, and only finally to adjudicated KG updates.

## Proposed View Content

### 1. Global KG Overview

Purpose: help experts explore the full cultural-heritage KG before selecting a suspicious region.

Current implementation:
- `KnowledgeGraphView.vue`
- Global graph with artifacts, semantic entities, source coverage, and contention glyphs.
- The graph is the overview, because the target data is graph-structured and expected to scale.

Design intent:
- This should become the first view experts see.
- It frames conflicts as suspicious graph regions and uncertain evidence patterns, not as precomputed conclusions.
- It should support graph aggregation, filtering, semantic zoom, neighborhood expansion, and evidence-aware glyphs.
- Small pairwise relation summaries are not suitable for the global view because they do not scale well to large, heterogeneous KG topology.

### 2. Knowledge Hierarchies

Purpose: provide analytical entry points, not a static dump of all database contents.

Current organization:
- Sources: catalogue/book -> artifacts.
- Entities: form, period, collection.
- Conflicts: candidate issue classes.

Design intent:
- The hierarchy is meaningful only if it helps experts enter the analysis from different scholarly contexts.
- It should remain a navigation lens, not a result view.

### 3. Candidate Issue Queue

Purpose: collect suspicious or high-uncertainty items for expert inspection.

Design intent:
- Avoid wording that implies the system has already fully determined the conflict.
- Queue items are candidates created by extraction, OCR confidence, source disagreement, missing evidence, or domain-rule triggers.
- Future versions should include uncertainty scores and explanations of why an item is surfaced.

### 4. Global KG / Local Comparison

Purpose: connect overview patterns to entity-level and attribute-level inspection.

Current implementation:
- Global KG shows artifacts, entities, and contention glyphs.
- Comparison KG shows a selected artifact and its candidate attribute issues.

Design intent:
- The global KG is for orientation and selection.
- The comparison view is for narrowing from artifact to claim.
- The views should not replace evidence inspection; they should route users into the Evidence Tray.

### 5. Evidence Tray

Purpose: core contribution area for evidence-grounded adjudication.

Current content:
- Source-level cards.
- OCR/raw text.
- Placeholder scan page and local detail views.
- Pinning selected evidence into a tray.

Design intent:
- This should become visually and functionally central.
- It should support scan pages, OCR blocks, Markdown chunks, image crops, texture/detail comparison, and source metadata.
- Experts should be able to cite exact evidence used in a final decision.

### 6. Decision Workspace

Purpose: transform inspected evidence into a provenance-preserving KG update.

Current content:
- Source assertions.
- Interpretation hypotheses.
- Evidence-grounded revision draft.
- Adjudication actions.

Design intent:
- This should not feel like an automatic answer panel.
- It should be a structured authoring and provenance workspace.
- The adjudication log should be secondary and append-only, not the main right-panel logic.

## Near-Term Visualization Directions

1. Scalable global KG overview:
   - Use graph aggregation, semantic zoom, local expansion, filtering, and uncertainty glyphs.
   - The global view should reveal suspicious regions without enumerating all conflicts as final answers.
   - Source coverage and evidence provenance should be encoded on graph nodes/edges, not separated into a small pairwise summary view.

2. Evidence-quality overview:
   - Encode OCR confidence, missing images, image-text alignment, and extraction uncertainty.
   - Helps avoid directly showing conflict classes as final labels.

3. Artifact contention glyph:
   - Current ring glyph can be developed into a compact uncertainty glyph.
   - Encode number of sources, missingness, candidate conflict classes, and adjudication state.

4. Evidence tray comparison:
   - Add scan page, OCR block, Markdown segment, image crop, and detail texture comparison.
   - This should be the strongest application-specific contribution.

5. Provenance ledger:
   - Store decisions with cited evidence and supersession links.
   - Move ledger into a secondary tab, not the primary adjudication interface.
