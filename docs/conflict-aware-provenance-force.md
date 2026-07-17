# Conflict-aware Provenance Force

KGExplorer's graph layout should make the provenance of a disagreement visible,
not merely distribute nodes across a canvas. The current prototype uses a
provenance-aware force-directed model:

1. The global view contains primary object nodes and provenance source nodes.
   A link means that a book, catalogue, or herbarium collection contributes an
   assertion or image to the object. Source coverage is also encoded by the
   object's segmented ring.
2. A shared-value node is created only when the same extracted value is
   attached to at least two distinct objects for the same attribute. Dashed
   links therefore mean value reuse, rather than an invented semantic edge.
3. The local view contains one selected object and its source-specific values
   in the attribute matrix and evidence tray, where contradictory values can
   be inspected at full provenance resolution.

Source nodes are anchored to a top provenance rail, while object nodes are
given weak status bands for disagreement, partial overlap, and cross-source
agreement. The result remains force-directed, but its geometry is tied to
evidence provenance and conflict status instead of a universal corpus hub.

This distinction is important for interpretation:

- object node: the plant or guqin entity under review;
- source node: a book or herbarium collection contributing evidence;
- shared-value node: an extracted value reused by multiple objects;
- attribute matrix cell: a source-specific value that requires expert
  comparison, not an automatic final verdict.

The implementation prototype is in
`frontend/src/components/KnowledgeGraphView.vue`.
