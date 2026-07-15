<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import * as d3 from 'd3';
import { ARTIFACTS, SOURCES, CLASS_COLORS, worstClass } from '../data/guqinSeed.js';

const props = defineProps({
  variant: { type: String, default: 'global' },
  selectedArtifactId: { type: String, default: null },
  selectedSlotId: { type: String, default: null },
});

const emit = defineEmits(['select-artifact', 'select-slot', 'pin-artifact']);

const rootEl = ref(null);
let resizeObserver;

function ringArc(radius, startFrac, endFrac, pad = 0.03) {
  return d3.arc()
    .innerRadius(radius - 3)
    .outerRadius(radius + 3)
    .startAngle((startFrac + pad) * 2 * Math.PI)
    .endAngle((endFrac - pad) * 2 * Math.PI)();
}

function drawContentionGlyph(g, artifact, r) {
  const cls = worstClass(artifact);
  const n = artifact.sources.length;
  artifact.sources.forEach((sid, i) => {
    const involved = artifact.slots.some((s) =>
      s.assertions.some((a) => a.source === sid && a.raw));
    g.append('path')
      .attr('d', ringArc(r + 5, i / n, (i + 1) / n))
      .attr('fill', artifact.slots.length === 0 ? CLASS_COLORS.consensus
        : involved ? CLASS_COLORS[cls] : CLASS_COLORS.missing)
      .append('title')
      .text(SOURCES[sid]?.title || sid);
  });
  g.append('circle')
    .attr('r', r)
    .attr('fill', '#faf7f1')
    .attr('stroke', CLASS_COLORS[cls])
    .attr('stroke-width', 1.4)
    .attr('stroke-dasharray', cls === 'A' ? '4 2.5' : null);
  if (artifact.slots.length) {
    g.append('text')
      .text(artifact.slots.length)
      .attr('text-anchor', 'middle')
      .attr('dy', 4)
      .attr('font-size', 11)
      .attr('font-weight', 700)
      .attr('fill', CLASS_COLORS[cls]);
  }
}

function renderGlobal(container, width, height) {
  const svg = d3.select(container).append('svg')
    .attr('viewBox', [0, 0, width, height])
    .attr('role', 'img')
    .attr('aria-label', 'Global contested knowledge graph');

  const entityNames = [...new Set(ARTIFACTS.flatMap((a) => a.entities))];
  const nodes = [
    ...ARTIFACTS.map((a) => ({
      id: `artifact:${a.id}`,
      kind: 'artifact',
      artifact: a,
      r: 15 + Math.min(6, a.slots.length * 2),
    })),
    ...ARTIFACTS.flatMap((artifact) =>
      artifact.slots.map((slot) => ({
        id: `issue:${artifact.id}:${slot.id}`,
        kind: 'issue',
        artifact,
        slot,
        label: slot.label,
        r: 7,
      }))),
    ...entityNames.map((e) => ({ id: `entity:${e}`, kind: 'entity', label: e, r: 5 })),
  ];
  nodes.forEach((n) => {
    if (n.kind === 'artifact') {
      n.x = width * 0.45;
      n.y = height * 0.5;
    } else if (n.kind === 'issue') {
      n.x = width * 0.28;
      n.y = height * 0.5;
    } else {
      n.x = width * 0.72;
      n.y = height * 0.5;
    }
  });
  const links = [
    ...ARTIFACTS.flatMap((artifact) =>
      artifact.entities.map((entity) => ({
        source: `artifact:${artifact.id}`,
        target: `entity:${entity}`,
        kind: 'context',
      }))),
    ...ARTIFACTS.flatMap((artifact) =>
      artifact.slots.map((slot) => ({
        source: `artifact:${artifact.id}`,
        target: `issue:${artifact.id}:${slot.id}`,
        kind: 'issue',
        cls: slot.cls,
      }))),
  ];

  const graph = svg.append('g');
  const link = graph.append('g').selectAll('line').data(links).join('line')
    .attr('stroke', (d) => (d.kind === 'issue' ? CLASS_COLORS[d.cls] : '#d3cbbd'))
    .attr('stroke-opacity', (d) => (d.kind === 'issue' ? 0.72 : 0.35))
    .attr('stroke-width', (d) => (d.kind === 'issue' ? 1.4 : 0.8));

  const node = graph.append('g').selectAll('g').data(nodes).join('g')
    .attr('cursor', (d) => (d.kind === 'artifact' || d.kind === 'issue' ? 'pointer' : 'grab'))
    .on('click', (event, d) => {
      if (event.defaultPrevented) return;
      if (d.kind === 'artifact') emit('select-artifact', d.artifact.id);
      if (d.kind === 'issue') {
        emit('select-artifact', d.artifact.id);
        emit('select-slot', d.slot.id);
      }
    })
    .on('dblclick', (event, d) => {
      if (d.kind === 'artifact') emit('pin-artifact', d.artifact.id);
    });

  node.filter((d) => d.kind === 'entity')
    .append('circle')
    .attr('r', (d) => d.r)
    .attr('fill', '#b4b2a9')
    .attr('fill-opacity', 0.85);

  node.filter((d) => d.kind === 'issue')
    .append('rect')
    .attr('class', 'issue-mark')
    .attr('x', -7)
    .attr('y', -7)
    .attr('width', 14)
    .attr('height', 14)
    .attr('rx', 3)
    .attr('fill', (d) => CLASS_COLORS[d.slot.cls])
    .attr('stroke', (d) => (d.artifact.id === props.selectedArtifactId && d.slot.id === props.selectedSlotId ? '#4a4438' : '#ffffff'))
    .attr('stroke-width', (d) => (d.artifact.id === props.selectedArtifactId && d.slot.id === props.selectedSlotId ? 2.2 : 1.1));

  node.filter((d) => d.kind === 'issue')
    .append('text')
    .text((d) => d.label)
    .attr('x', 11)
    .attr('y', 4)
    .attr('fill', '#4a4438')
    .attr('font-size', 10.5)
    .attr('font-weight', 650)
    .attr('paint-order', 'stroke')
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 3);

  node.filter((d) => d.kind === 'artifact').each(function drawEach(d) {
    drawContentionGlyph(d3.select(this), d.artifact, d.r);
  });

  node.filter((d) => d.kind === 'artifact')
    .append('text').text((d) => d.artifact.name)
    .attr('x', 24).attr('y', 4)
    .attr('fill', '#4a4438').attr('font-size', 11).attr('font-weight', 600)
    .attr('paint-order', 'stroke').attr('stroke', '#ffffff').attr('stroke-width', 3);

  node.filter((d) => d.kind === 'artifact')
    .append('circle')
    .attr('class', 'sel-ring')
    .attr('r', (d) => d.r + 9)
    .attr('fill', 'none')
    .attr('stroke', '#6e5335')
    .attr('stroke-width', (d) => (d.artifact.id === props.selectedArtifactId ? 1.6 : 0))
    .attr('stroke-dasharray', '2 3');

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id((d) => d.id).distance((d) => (d.kind === 'issue' ? 54 : 92)))
    .force('charge', d3.forceManyBody().strength((d) => (d.kind === 'artifact' ? -360 : -150)))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('x', d3.forceX((d) => {
      if (d.kind === 'issue') return width * 0.3;
      if (d.kind === 'entity') return width * 0.72;
      return width * 0.48;
    }).strength(0.12))
    .force('y', d3.forceY(height / 2).strength(0.07))
    .force('collision', d3.forceCollide().radius((d) => (d.kind === 'artifact' ? 58 : d.r + 22)));

  node.call(
    d3.drag()
      .on('start', (event, d) => {
        simulation.alphaTarget(0.12).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        simulation.alphaTarget(0);
      }),
  );

  simulation.on('tick', () => {
    nodes.forEach((d) => {
      const rightPad = d.kind === 'artifact' || d.kind === 'issue' ? 112 : 24;
      d.x = Math.max(26, Math.min(width - rightPad, d.x));
      d.y = Math.max(26, Math.min(height - 26, d.y));
    });
    link.attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y);
    node.attr('transform', (d) => `translate(${d.x},${d.y})`);
  });
  setTimeout(() => simulation.stop(), 1800);
}

function renderComparison(container, width, height) {
  const svg = d3.select(container).append('svg')
    .attr('viewBox', [0, 0, width, height])
    .attr('role', 'img')
    .attr('aria-label', 'Contested slots of selected artifact');

  const artifact = ARTIFACTS.find((a) => a.id === props.selectedArtifactId);
  if (!artifact) {
    svg.append('text')
      .text('Select artifact')
      .attr('x', width / 2).attr('y', height / 2)
      .attr('text-anchor', 'middle').attr('fill', '#9a9284').attr('font-size', 12.5);
    return;
  }

  const cx = width / 2;
  const cy = height / 2;
  const g = svg.append('g');

  const center = g.append('g').attr('transform', `translate(${cx},${cy})`);
  drawContentionGlyph(center, artifact, 20);
  center.append('text').text(artifact.name)
    .attr('text-anchor', 'middle').attr('y', 42)
    .attr('font-size', 12).attr('font-weight', 700).attr('fill', '#4a4438');

  const slots = artifact.slots;
  if (!slots.length) {
    svg.append('text').text('全部属性两书记载一致,无争议槽位。')
      .attr('x', cx).attr('y', cy + 70)
      .attr('text-anchor', 'middle').attr('fill', '#1d9e75').attr('font-size', 12);
    return;
  }

  const orbit = Math.min(width, height) * 0.32;
  slots.forEach((slot, i) => {
    const angle = (i / slots.length) * 2 * Math.PI - Math.PI / 2;
    const sx = cx + orbit * Math.cos(angle);
    const sy = cy + orbit * Math.sin(angle);

    g.append('line')
      .attr('x1', cx).attr('y1', cy).attr('x2', sx).attr('y2', sy)
      .attr('stroke', CLASS_COLORS[slot.cls]).attr('stroke-width', 1.1)
      .attr('stroke-dasharray', slot.cls === 'A' ? '5 3' : null)
      .attr('stroke-opacity', 0.7);

    const sg = g.append('g')
      .attr('transform', `translate(${sx},${sy})`)
      .attr('cursor', 'pointer')
      .on('click', () => emit('select-slot', slot.id));

    const n = artifact.sources.length;
    artifact.sources.forEach((sid, k) => {
      const assertion = slot.assertions.find((a) => a.source === sid);
      sg.append('path')
        .attr('d', ringArc(17, k / n, (k + 1) / n))
        .attr('fill', assertion && assertion.raw ? CLASS_COLORS[slot.cls] : CLASS_COLORS.missing)
        .append('title').text(SOURCES[sid]?.title || sid);
    });
    sg.append('circle').attr('r', 12)
      .attr('fill', props.selectedSlotId === slot.id ? '#f5efe4' : '#ffffff')
      .attr('stroke', CLASS_COLORS[slot.cls])
      .attr('stroke-width', props.selectedSlotId === slot.id ? 2.2 : 1.2);
    sg.append('text').text(slot.cls)
      .attr('text-anchor', 'middle').attr('dy', 4)
      .attr('font-size', 10.5).attr('font-weight', 700)
      .attr('fill', CLASS_COLORS[slot.cls]);
    sg.append('text').text(slot.label)
      .attr('text-anchor', 'middle').attr('y', 32)
      .attr('font-size', 11).attr('fill', '#4a4438').attr('font-weight', 600)
      .attr('paint-order', 'stroke').attr('stroke', '#ffffff').attr('stroke-width', 3);
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
    .selectAll('.issue-mark')
    .attr('stroke', (d) => (d.artifact.id === props.selectedArtifactId && d.slot.id === props.selectedSlotId ? '#4a4438' : '#ffffff'))
    .attr('stroke-width', (d) => (d.artifact.id === props.selectedArtifactId && d.slot.id === props.selectedSlotId ? 2.2 : 1.1));
}

watch(() => props.variant, render);
watch(
  () => [props.selectedArtifactId, props.selectedSlotId],
  () => {
    if (props.variant === 'global') updateGlobalSelection();
    else render();
  },
);

onUnmounted(() => {
  resizeObserver?.disconnect();
});
</script>

<template>
  <div ref="rootEl" class="knowledge-graph-canvas"></div>
</template>
