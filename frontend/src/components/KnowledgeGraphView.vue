<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import * as d3 from 'd3';
import { store, CLASS_COLORS, worstClass } from '../data/store.js';

const ARTIFACTS = store.artifacts;
const SOURCES = store.sources;

const props = defineProps({
  variant: { type: String, default: 'global' },
  selectedArtifactId: { type: String, default: null },
  selectedSlotId: { type: String, default: null },
});

const emit = defineEmits(['select-artifact', 'select-slot', 'pin-artifact']);

const rootEl = ref(null);
let resizeObserver;
const posCache = new Map();

function ringArc(radius, startFrac, endFrac, pad = 0.03) {
  return d3.arc()
    .innerRadius(radius - 3)
    .outerRadius(radius + 3)
    .startAngle((startFrac + pad) * 2 * Math.PI)
    .endAngle((endFrac - pad) * 2 * Math.PI)();
}

function drawContentionGlyph(g, artifact, r) {
  const cls = worstClass(artifact);
  // The outer ring is a fixed provenance axis. The center encodes the
  // record's current evidence state; no unexplained source/count number is
  // placed inside the node.
  const sourceIds = Object.keys(SOURCES).length
    ? Object.keys(SOURCES)
    : (artifact.sources.length ? artifact.sources : ['unknown']);
  const n = sourceIds.length;
  const alignmentColor = {
    confirmed: '#5d8c82',
    candidate: '#b29a62',
    'source-local': '#aab4ba',
    unresolved: '#b86f3d',
  }[artifact.alignmentStatus] || '#aab4ba';
  sourceIds.forEach((sid, i) => {
    const present = artifact.sources.includes(sid);
    const involved = artifact.slots.some((s) =>
      s.assertions.some((a) => a.source === sid && a.raw));
    g.append('path')
      .attr('d', ringArc(r + 5, i / n, (i + 1) / n))
      .attr('fill', sid === 'unknown' || !present ? CLASS_COLORS.missing : involved ? (SOURCES[sid]?.color || alignmentColor) : '#d3dadd')
      .append('title')
      .text(`${present ? 'source present' : 'source absent'} · ${SOURCES[sid]?.title || sid}`);
  });
  const stateColor = CLASS_COLORS[cls] || CLASS_COLORS.missing;
  g.append('circle')
    .attr('r', r)
    .attr('fill', '#ffffff')
    .attr('stroke', stateColor)
    .attr('stroke-width', 1.8)
    .attr('stroke-dasharray', cls === 'A' ? '4 2.5' : null)
    .append('title')
    .text(`${artifact.name} · ${artifact.sources.length} source(s) · ${cls}`);
  g.append('circle')
    .attr('r', Math.max(6, r * 0.32))
    .attr('fill', stateColor)
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 1);
  g.append('text')
    .attr('class', 'source-count')
    .attr('text-anchor', 'middle')
    .attr('dy', 3.5)
    .attr('fill', '#ffffff')
    .attr('font-size', Math.max(8, r * 0.54))
    .attr('font-weight', 800)
    .text(artifact.sources.length);
  g.append('text')
    .attr('class', 'source-count-label')
    .attr('x', r + 7)
    .attr('y', -r - 5)
    .attr('fill', '#5d6871')
    .attr('font-size', 8.5)
    .attr('font-weight', 700)
    .text(`${artifact.sources.length} src`);
}

function renderGlobal(container, width, height) {
  const svg = d3.select(container).append('svg')
    .attr('viewBox', [0, 0, width, height])
    .attr('role', 'img')
    .attr('aria-label', 'Global contested knowledge graph');

  // Keep the full corpus in the matrix and hierarchy. The graph starts with
  // objects that participate in cross-source matching or conflict analysis.
  const graphArtifacts = ARTIFACTS.filter((artifact) =>
    artifact.sources.length > 1
    || artifact.alignmentCandidates?.some((candidate) => candidate.score >= 0.45)
    || artifact.slots.some((slot) => ['A', 'B', 'C'].includes(slot.cls)),
  );
  svg.append('text')
    .attr('x', 16)
    .attr('y', 20)
    .attr('fill', '#56636d')
    .attr('font-size', 10)
    .attr('font-weight', 700)
    .text(`cross-source view · ${graphArtifacts.length} of ${ARTIFACTS.length} records`)
    .append('title')
    .text('The matrix and source folders retain the complete corpus; the global view foregrounds linked or contested records.');
  const nodes = [];
  const nodeById = new Map();
  const links = [];
  const short = (value, max = 24) => {
    const text = String(value || '');
    return text.length > max ? `${text.slice(0, max - 1)}…` : text;
  };
  const addNode = (nodeData) => {
    if (!nodeById.has(nodeData.id)) {
      nodeById.set(nodeData.id, nodeData);
      nodes.push(nodeData);
    }
    return nodeById.get(nodeData.id);
  };
  const sourceIds = Object.keys(SOURCES);

  graphArtifacts.forEach((artifact) => addNode({
    id: `object:${artifact.id}`,
    kind: 'object',
    artifact,
    label: artifact.name,
    r: 14 + Math.min(6, artifact.slots.filter((slot) => slot.cls === 'A' || slot.cls === 'B').length),
  }));

  // A value node is a normalized attribute value shared by at least two
  // artifact records. Singletons remain in the evidence matrix but do not
  // create noise in the global relational backbone.
  const sharedValues = new Map();
  graphArtifacts.forEach((artifact) => {
    artifact.slots.forEach((slot) => {
      slot.assertions.forEach((assertion) => {
        const values = assertion.normalizedValues?.length ? assertion.normalizedValues : assertion.values;
        values.forEach((value, valueIndex) => {
          const canonical = String(value || '').replace(/\s+/g, ' ').trim();
          if (!canonical || canonical.length > 120) return;
          const key = `${slot.id}:${canonical.toLowerCase()}`;
          const group = sharedValues.get(key) || {
            key,
            slot,
            label: canonical,
            artifacts: new Set(),
            recordsByArtifact: new Map(),
            rawLabels: new Set(),
          };
          group.artifacts.add(artifact.id);
          const sources = group.recordsByArtifact.get(artifact.id) || new Set();
          sources.add(assertion.source);
          group.recordsByArtifact.set(artifact.id, sources);
          const detail = assertion.valueDetails?.find((item) => item.canonical === value);
          if (detail?.raw) group.rawLabels.add(detail.raw);
          else if (assertion.values?.[valueIndex]) group.rawLabels.add(assertion.values[valueIndex]);
          sharedValues.set(key, group);
        });
      });
    });
  });
  sharedValues.forEach((group) => {
    if (group.artifacts.size < 2) return;
    const value = addNode({
      id: `value:${group.key}`,
      kind: 'value',
      label: group.label,
      slotLabel: group.slot.label,
      rawLabels: [...group.rawLabels],
      support: group.artifacts.size,
      r: 5 + Math.min(3, Math.sqrt(group.artifacts.size)),
    });
    group.recordsByArtifact.forEach((sourceSet, artifactId) => {
      const artifact = graphArtifacts.find((item) => item.id === artifactId);
      const slot = artifact?.slots.find((item) => item.id === group.slot.id);
      links.push({
        source: `object:${artifactId}`,
        target: value.id,
        kind: 'asserts value',
        slotLabel: group.slot.label,
        sources: [...sourceSet],
        status: slot?.cls || 'single',
      });
    });
  });

  nodes.forEach((n, i) => {
    const cached = posCache.get(`clean-kg-v1:${n.id}`);
    if (cached) {
      n.x = cached.x;
      n.y = cached.y;
    } else {
      const seed = (i * 9301 + 49297) % 233280;
      n.x = width * (0.24 + 0.52 * (seed / 233280));
      n.y = height * (0.24 + 0.52 * (((seed * 17) % 233280) / 233280));
    }
  });

  const graph = svg.append('g');
  const zoom = d3.zoom()
    .scaleExtent([0.12, 8])
    .on('zoom', (event) => graph.attr('transform', event.transform));
  svg.call(zoom).on('dblclick.zoom', null);
  const link = graph.append('g').selectAll('line').data(links).join('line')
    .attr('stroke', (d) => d.status === 'A' ? CLASS_COLORS.A : d.status === 'B' ? CLASS_COLORS.B : '#aab8bf')
    .attr('stroke-opacity', (d) => d.status === 'A' || d.status === 'B' ? 0.48 : 0.28)
    .attr('stroke-width', (d) => d.status === 'A' ? 1.25 : 0.9);
  link.append('title').text((d) => `${d.kind} · ${d.slotLabel} · ${d.sources.map((source) => SOURCES[source]?.title || source).join(', ')}`);

  const node = graph.append('g').selectAll('g').data(nodes).join('g')
    .attr('cursor', (d) => (d.kind === 'object' ? 'pointer' : 'grab'))
    .on('click', (event, d) => {
      if (event.defaultPrevented) return;
      if (d.kind === 'object') emit('select-artifact', d.artifact.id);
    })
    .on('dblclick', (event, d) => {
      if (d.kind === 'object') emit('pin-artifact', d.artifact.id);
    })
    .on('mouseenter', function (event, d) {
      d3.select(this).select('.semantic-label').attr('opacity', 1);
    })
    .on('mouseleave', function (event, d) {
      if ((d.kind === 'object' && d.artifact?.id === props.selectedArtifactId)) return;
      d3.select(this).select('.semantic-label').attr('opacity', 0);
    });

  node.filter((d) => d.kind === 'object').each(function drawEach(d) {
    drawContentionGlyph(d3.select(this), d.artifact, d.r);
  });
  node.filter((d) => d.kind === 'object')
    .append('text').text((d) => short(d.label, 28))
    .attr('class', 'semantic-label artifact-label')
    .attr('x', (d) => d.r + 8).attr('y', 4)
    .attr('fill', '#4a4438').attr('font-size', 11).attr('font-weight', 600)
    .attr('paint-order', 'stroke').attr('stroke', '#ffffff').attr('stroke-width', 3)
    .attr('opacity', (d) => d.artifact.id === props.selectedArtifactId ? 1 : 0);
  node.filter((d) => d.kind === 'value')
    .append('circle').attr('r', (d) => d.r)
    .attr('fill', '#ffffff').attr('stroke', '#7f9aa7').attr('stroke-width', 1.2)
    .append('title').text((d) => `attribute value · ${d.slotLabel} · ${d.label} · ${d.support} artifact records`);
  node.filter((d) => d.kind === 'value')
    .append('text').text((d) => short(d.label, 20))
    .attr('class', 'semantic-label')
    .attr('x', (d) => d.r + 7)
    .attr('y', 4).attr('fill', '#8f6b2f').attr('font-size', 8.5).attr('font-weight', 600)
    .attr('paint-order', 'stroke').attr('stroke', '#ffffff').attr('stroke-width', 3)
    .attr('opacity', 0);

  node.filter((d) => d.kind === 'object')
    .append('circle')
    .attr('class', 'sel-ring')
    .attr('r', (d) => d.r + 9)
    .attr('fill', 'none')
    .attr('stroke', '#365c78')
    .attr('stroke-width', (d) => (d.artifact.id === props.selectedArtifactId ? 1.6 : 0))
    .attr('stroke-dasharray', '2 3');

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id((d) => d.id)
      .distance(145)
      .strength(0.42))
    .force('charge', d3.forceManyBody()
      .strength((d) => d.kind === 'object' ? -460 : -150)
      .distanceMax(Math.max(width, height) * 3))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius((d) => d.kind === 'object' ? d.r + 14 : d.r + 7));

  function positionAll() {
    // Intentionally leave nodes outside the viewport; zoom and pan reveal them.
    link.attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y);
    node.attr('transform', (d) => `translate(${d.x},${d.y})`);
  }

  simulation.stop();
  simulation.tick(420);
  positionAll();
  nodes.forEach((n) => posCache.set(`clean-kg-v1:${n.id}`, { x: n.x, y: n.y }));

  node.call(
    d3.drag()
      .filter((event) => event.button === 0)
      .on('start', (event) => {
        event.sourceEvent?.stopPropagation();
      })
      .on('drag', (event, d) => {
        event.sourceEvent?.stopPropagation();
        d.fx = event.x;
        d.fy = event.y;
        positionAll();
      })
      .on('end', (event, d) => {
        event.sourceEvent?.stopPropagation();
        d.fx = null;
        d.fy = null;
        posCache.set(`clean-kg-v1:${d.id}`, { x: d.x, y: d.y });
      }),
  );
}

function renderComparison(container, width, height) {
  const svg = d3.select(container).append('svg')
    .attr('viewBox', [0, 0, width, height])
    .attr('role', 'img')
    .attr('aria-label', 'Contested slots of selected artifact');

  const artifact = ARTIFACTS.find((a) => a.id === props.selectedArtifactId);
  if (!artifact) {
    svg.append('text')
      .text('Select an object')
      .attr('x', width / 2).attr('y', height / 2)
      .attr('text-anchor', 'middle').attr('fill', '#9a9284').attr('font-size', 12.5);
    return;
  }

  const sources = artifact.sources.length ? artifact.sources : Object.keys(SOURCES);
  const rows = artifact.slots.length ? artifact.slots : [{ id: 'none', label: 'No indexed attributes', cls: 'missing', assertions: [] }];
  const left = 12;
  const top = 40;
  const labelWidth = Math.min(108, Math.max(86, width * 0.27));
  const cellWidth = Math.max(78, (width - left * 2 - labelWidth) / Math.max(1, sources.length));
  const rowHeight = Math.min(54, Math.max(34, (height - top - 18) / (rows.length + 1)));
  const short = (value, max = 18) => {
    const text = String(value || '');
    return text.length > max ? `${text.slice(0, max - 1)}…` : text;
  };
  const g = svg.append('g');
  g.append('text').text(short(artifact.name, 32)).attr('x', left).attr('y', 20)
    .attr('fill', '#294e6b').attr('font-size', 13).attr('font-weight', 750);
  g.append('text').text(`${artifact.alignmentStatus} · ${artifact.sources.length} source(s)`)
    .attr('x', left).attr('y', 34).attr('fill', '#7d8790').attr('font-size', 9.5);
  g.append('text').text('ATTRIBUTE × SOURCE EVIDENCE MATRIX').attr('x', left + labelWidth).attr('y', 16)
    .attr('fill', '#8f6b2f').attr('font-size', 9.2).attr('font-weight', 750);
  g.append('text').text('Rows = attributes · columns = sources · cells = extracted values · dot = image evidence')
    .attr('x', left + labelWidth).attr('y', 28).attr('fill', '#8a949b').attr('font-size', 7.8);
  sources.forEach((source, index) => {
    const x = left + labelWidth + index * cellWidth;
    const header = `${source} · ${short(SOURCES[source]?.title || source, 7)}`;
    g.append('text').text(header).attr('x', x + cellWidth / 2).attr('y', 40)
      .attr('text-anchor', 'middle').attr('fill', SOURCES[source]?.color || '#526774').attr('font-size', 8.5).attr('font-weight', 700)
      .append('title').text(SOURCES[source]?.title || source);
  });
  rows.forEach((row, rowIndex) => {
    const y = top + rowIndex * rowHeight;
    g.append('rect').attr('x', left).attr('y', y).attr('width', width - left * 2).attr('height', rowHeight)
      .attr('fill', row.id === props.selectedSlotId ? '#fffaf0' : rowIndex % 2 ? '#fbfcfd' : '#ffffff')
      .attr('stroke', '#e1e6eb').attr('stroke-width', row.id === props.selectedSlotId ? 1.4 : 0.7);
    g.append('rect').attr('x', left).attr('y', y).attr('width', 4).attr('height', rowHeight)
      .attr('fill', CLASS_COLORS[row.cls] || CLASS_COLORS.missing);
    g.append('text').text(short(row.label, 16)).attr('x', left + 11).attr('y', y + rowHeight / 2 + 3)
      .attr('fill', '#45515c').attr('font-size', 10).attr('font-weight', 700);
    sources.forEach((source, sourceIndex) => {
      const assertion = row.assertions.find((item) => item.source === source);
      const x = left + labelWidth + sourceIndex * cellWidth;
      const raw = assertion?.raw;
      const cell = g.append('rect').attr('x', x + 3).attr('y', y + 4).attr('width', cellWidth - 6).attr('height', rowHeight - 8)
        .attr('rx', 4).attr('fill', raw ? (row.cls === 'A' ? '#f5e2dc' : row.cls === 'B' ? '#f4eddf' : '#edf4f2') : '#f0f2f3')
        .attr('stroke', raw ? (row.cls === 'A' ? CLASS_COLORS.A : '#d6dee2') : '#d6dadd').attr('stroke-dasharray', raw ? null : '3 2');
      cell.append('title').text(`${row.label} · ${SOURCES[source]?.title || source} · ${raw || 'not recorded'}`);
      g.append('text').text(raw ? short(raw, Math.max(10, Math.floor(cellWidth / 7))) : 'not recorded')
        .attr('x', x + cellWidth / 2).attr('y', y + rowHeight / 2 + 3).attr('text-anchor', 'middle')
        .attr('fill', raw ? '#4a5058' : '#9ca5aa').attr('font-size', 8.5);
      if (assertion?.imagePath || artifact.imagesByBook[source]?.length) {
        g.append('circle').attr('cx', x + cellWidth - 10).attr('cy', y + 10).attr('r', 3)
          .attr('fill', '#294e6b').append('title').text('image evidence available');
      }
    });
  });
}

function render() {
  const container = rootEl.value;
  if (!container) return;
  const { width, height } = container.getBoundingClientRect();
  if (!width || !height) return;
  d3.select(container).selectAll('*').remove();
  if (props.variant === 'global') renderGlobal(container, width, height);
  else renderComparison(container, width, height);
}

onMounted(async () => {
  await nextTick();
  render();
  resizeObserver = new ResizeObserver(render);
  resizeObserver.observe(rootEl.value);
});

function updateGlobalSelection() {
  if (!rootEl.value) return;
  d3.select(rootEl.value)
    .selectAll('.sel-ring')
    .attr('stroke-width', (d) => (d.artifact?.id === props.selectedArtifactId ? 1.6 : 0));
  d3.select(rootEl.value)
    .selectAll('.artifact-label')
    .attr('opacity', (d) => (d.artifact?.id === props.selectedArtifactId ? 1 : 0));
  d3.select(rootEl.value)
    .selectAll('.issue-mark')
    .attr('stroke', (d) => (d.artifact.id === props.selectedArtifactId && d.slot.id === props.selectedSlotId ? '#4a4438' : '#ffffff'))
    .attr('stroke-width', (d) => (d.artifact.id === props.selectedArtifactId && d.slot.id === props.selectedSlotId ? 2.2 : 1.1));
}

watch(() => props.variant, render);
watch(() => store.artifacts.length, render);
watch(
  () => [props.selectedArtifactId, props.selectedSlotId],
  () => {
    if (props.variant === 'global') {
      updateGlobalSelection();
    } else {
      render();
    }
  },
);

onUnmounted(() => {
  resizeObserver?.disconnect();
});
</script>

<template>
  <div ref="rootEl" class="knowledge-graph-canvas"></div>
</template>
