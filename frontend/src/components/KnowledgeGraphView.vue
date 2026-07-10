<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import * as d3 from 'd3';

const props = defineProps({
  variant: {
    type: String,
    default: 'global',
  },
});

const rootEl = ref(null);
let resizeObserver;

const labels = {
  global: ['GPT-4o', 'LLM-Agent', 'Task Planning', 'OpenAI', 'Query Expansion', 'RAG', 'Human-AI Collaboration'],
  derived: ['GPT-4o', 'Citation-aware', 'ScholarQA', 'RAPTOR', 'Adaptive Retriever', 'Map Manager', 'Evaluation'],
};

function seededRandom(seed) {
  let value = seed;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function makeGraph(variant) {
  const rng = seededRandom(variant === 'global' ? 31 : 71);
  const count = variant === 'global' ? 72 : 42;
  const names = labels[variant];
  const nodes = d3.range(count).map((index) => ({
    id: `n-${index}`,
    label: index < names.length ? names[index] : `Entity ${index}`,
    group: Math.floor(rng() * 4),
    r: index === 0 ? 12 : 4 + rng() * 7,
  }));

  const links = [];
  for (let i = 1; i < count; i += 1) {
    links.push({ source: nodes[i].id, target: nodes[Math.floor(rng() * i)].id });
    if (rng() > 0.58) links.push({ source: nodes[i].id, target: nodes[Math.floor(rng() * count)].id });
  }

  return { nodes, links };
}

function render() {
  const container = rootEl.value;
  if (!container) return;

  const { width, height } = container.getBoundingClientRect();
  d3.select(container).selectAll('*').remove();

  const svg = d3
    .select(container)
    .append('svg')
    .attr('viewBox', [0, 0, width, height])
    .attr('role', 'img')
    .attr('aria-label', `${props.variant} knowledge graph`);

  const { nodes, links } = makeGraph(props.variant);
  const color = d3.scaleOrdinal(['#5078b5', '#f47b73', '#f6a04d', '#8bc5bf']);

  const graph = svg.append('g');

  graph
    .append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', '#c8cdd6')
    .attr('stroke-opacity', props.variant === 'global' ? 0.32 : 0.42)
    .attr('stroke-width', 0.9);

  const node = graph
    .append('g')
    .selectAll('g')
    .data(nodes)
    .join('g');

  node
    .append('circle')
    .attr('r', (d) => d.r)
    .attr('fill', (d) => color(d.group))
    .attr('fill-opacity', 0.9)
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 1.2);

  node
    .filter((d, index) => index < 10)
    .append('text')
    .text((d) => d.label)
    .attr('x', 9)
    .attr('y', 4)
    .attr('fill', '#59616d')
    .attr('font-size', 11)
    .attr('paint-order', 'stroke')
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 3);

  const simulation = d3
    .forceSimulation(nodes)
    .force(
      'link',
      d3
        .forceLink(links)
        .id((d) => d.id)
        .distance(props.variant === 'global' ? 46 : 60),
    )
    .force('charge', d3.forceManyBody().strength(props.variant === 'global' ? -75 : -105))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius((d) => d.r + 10));

  simulation.on('tick', () => {
    graph
      .selectAll('line')
      .attr('x1', (d) => d.source.x)
      .attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x)
      .attr('y2', (d) => d.target.y);

    node.attr('transform', (d) => {
      d.x = Math.max(18, Math.min(width - 80, d.x));
      d.y = Math.max(18, Math.min(height - 22, d.y));
      return `translate(${d.x},${d.y})`;
    });
  });

  setTimeout(() => simulation.stop(), 1800);
}

onMounted(async () => {
  await nextTick();
  render();
  resizeObserver = new ResizeObserver(render);
  resizeObserver.observe(rootEl.value);
});

watch(() => props.variant, render);

onUnmounted(() => {
  resizeObserver?.disconnect();
});
</script>

<template>
  <div ref="rootEl" class="knowledge-graph-canvas"></div>
</template>
