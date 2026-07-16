# Conflict-aware Provenance Force

KGExplorer's graph layout should make the provenance of a disagreement visible,
not merely distribute nodes across a canvas. The proposed layout is a
two-level force-directed model:

1. The global view contains primary object nodes and provenance source nodes.
   A link means that a book, catalogue, or herbarium collection contributes an
   assertion or image to the object. Source coverage is also encoded by the
   object's segmented ring.
2. The local view contains one selected object and its source-specific value
   nodes. Support links connect the object to assertions. Contradictory values
   receive conflict links and an additional repulsive force.

For a source link `e`, the link distance is longer than the object collision
radius, so multi-source objects remain spatially separated. For local conflict
links, the custom force applies:

`F_conflict = alpha * max(0, d_target - d_current) * unit_vector`

to contradictory assertion pairs. Agreement pairs do not receive this force;
they remain clustered by the ordinary support links. The result is still a
force-directed layout, but its geometry is tied to evidence provenance and
conflict structure.

This distinction is important for interpretation:

- object node: the plant or guqin entity under review;
- source node: a book or herbarium collection contributing evidence;
- assertion node: a source-specific value or statement;
- conflict link: values that require expert comparison, not an automatic final
  verdict.

The implementation prototype is in
`frontend/src/components/KnowledgeGraphView.vue`.
