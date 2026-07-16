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
  // A fixed source axis makes glyphs comparable across objects. Missing
  // sources occupy their stable sector instead of shrinking the circle.
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
      .text(SOURCES[sid]?.title || sid);
  });
  const slots = artifact.slots.length ? artifact.slots : [{ label: 'no indexed attributes', cls: 'missing' }];
  slots.forEach((slot, i) => {
    const arc = d3.arc()
      .innerRadius(Math.max(3, r - 6))
      .outerRadius(Math.max(5, r - 3))
      .startAngle((i / slots.length + 0.025) * 2 * Math.PI)
      .endAngle(((i + 1) / slots.length - 0.025) * 2 * Math.PI);
    g.append('path')
      .attr('d', arc())
      .attr('fill', CLASS_COLORS[slot.cls] || CLASS_COLORS.missing)
      .attr('fill-opacity', 0.9)
      .append('title').text(`attribute · ${slot.label}`);
  });
  g.append('circle')
    .attr('r', r)
    .attr('fill', '#faf7f1')
    .attr('stroke', alignmentColor)
    .attr('stroke-width', 1.4)
    .attr('stroke-dasharray', cls === 'A' ? '4 2.5' : artifact.alignmentStatus === 'candidate' ? '2 2' : null);
  g.append('text')
    .text(artifact.sources.length)
    .attr('text-anchor', 'middle')
    .attr('dy', 4)
    .attr('font-size', 11)
    .attr('font-weight', 700)
    .attr('fill', alignmentColor);
}

function renderGlobal(container, width, height) {
  const svg = d3.select(container).append('svg')
    .attr('viewBox', [0, 0, width, height])
    .attr('role', 'img')
    .attr('aria-label', 'Global contested knowledge graph');

  // Overview projection: one glyph per record-level object, plus shared
  // concept nodes. Attribute values remain in the glyph and in the detail
  // lens, so the complete corpus is visible without creating a node for
  // every extracted sentence.
  const nodes = [];
  const nodeById = new Map();
  const links = [];
  const normalize = (value) => String(value || '').replace(/\s+/g, ' ').trim();
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
  ARTIFACTS.forEach((artifact) => {
    const object = addNode({
      id: `object:${artifact.id}`,
      kind: 'object',
      artifact,
      label: artifact.name,
      r: 15 + Math.min(5, artifact.slots.length),
    });
    artifact.entities.forEach((entity) => {
      const concept = addNode({ id: `concept:${normalize(entity)}`, kind: 'concept', label: entity, r: 11 });
      links.push({ source: object.id, target: concept.id, kind: 'associated concept' });
    });
  });

  const cx = width / 2;
  const cy = height / 2;
  nodes.forEach((n, i) => {
    const cached = posCache.get(`semantic-v3:${n.id}`);
    if (cached) {
      n.x = cached.x;
      n.y = cached.y;
      return;
    }
    const seed = (i * 9301 + 49297) % 233280;
    n.x = width * (-0.7 + 2.4 * (seed / 233280));
    n.y = height * (-0.7 + 2.4 * (((seed * 17) % 233280) / 233280));
  });

  const graph = svg.append('g');
  const zoom = d3.zoom()
    .scaleExtent([0.12, 8])
    .on('zoom', (event) => graph.attr('transform', event.transform));
  svg.call(zoom).on('dblclick.zoom', null);
  const link = graph.append('g').selectAll('line').data(links).join('line')
    .attr('stroke', '#7c9aae')
    .attr('stroke-opacity', 0.28)
    .attr('stroke-width', 1);
  link.append('title').text('associated concept');

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
      if (d.kind !== 'object' || d.artifact?.id !== props.selectedArtifactId) {
        d3.select(this).select('.semantic-label').attr('opacity', 0);
      }
    });

  node.filter((d) => d.kind === 'object').each(function drawEach(d) {
    drawContentionGlyph(d3.select(this), d.artifact, d.r);
  });

  node.filter((d) => d.kind === 'object')
    .append('text').text((d) => short(d.label, 28))
    .attr('class', 'semantic-label artifact-label')
    .attr('x', 25).attr('y', 4)
    .attr('fill', '#4a4438').attr('font-size', 11).attr('font-weight', 600)
    .attr('paint-order', 'stroke').attr('stroke', '#ffffff').attr('stroke-width', 3)
    .attr('opacity', (d) => d.artifact.id === props.selectedArtifactId ? 1 : 0);

  node.filter((d) => d.kind === 'concept')
    .append('circle').attr('r', (d) => d.r)
    .attr('fill', '#eaf0f3').attr('stroke', '#7c9aae').attr('stroke-width', 1.2)
    .append('title').text((d) => `concept · ${d.label}`);
  node.filter((d) => d.kind !== 'object')
    .append('text').text((d) => short(d.label, d.kind === 'value' ? 20 : 18))
    .attr('class', 'semantic-label')
    .attr('x', 12)
    .attr('y', 4).attr('fill', '#5e6870').attr('font-size', 9).attr('font-weight', 600)
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
      .distance(145).strength(0.62))
    .force('charge', d3.forceManyBody().strength((d) => d.kind === 'object' ? -430 : -150).distanceMax(Math.max(width, height) * 3))
    .force('center', d3.forceCenter(cx, cy))
    .force('collision', d3.forceCollide().radius((d) => d.kind === 'object' ? 31 : d.r + 9));

  function positionAll() {
    // Intentionally leave nodes outside the viewport; zoom and pan reveal them.
    link.attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y);
    node.attr('transform', (d) => `translate(${d.x},${d.y})`);
  }

  simulation.stop();
  simulation.tick(300);
  positionAll();
  nodes.forEach((n) => posCache.set(`semantic-v3:${n.id}`, { x: n.x, y: n.y }));

  node.call(
    d3.drag()
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
        positionAll();
      })
      .on('end', (event, d) => {
        d.fx = null;
        d.fy = null;
        posCache.set(`semantic-v3:${d.id}`, { x: d.x, y: d.y });
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
      .text('Select a plant or instrument object')
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
