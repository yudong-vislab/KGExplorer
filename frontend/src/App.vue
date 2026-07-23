<script setup>
import { computed, onMounted, ref } from 'vue';
import KnowledgeGraphView from './components/KnowledgeGraphView.vue';
import AdjudicationPanel from './components/AdjudicationPanel.vue';
import { store, loadStore, CLASS_COLORS } from './data/store.js';

async function loadCaseIntoView() {
  await loadStore();
  const preferred = store.artifacts
    .flatMap((artifact) => artifact.slots.map((slot) => ({ artifact, slot })))
    .find(({ slot }) => slot.reviewReadiness === 'P1_expert_review')
    || store.artifacts
      .flatMap((artifact) => artifact.slots.map((slot) => ({ artifact, slot })))
      .find(({ slot }) => ['A', 'B', 'C'].includes(slot.cls));
  const first = preferred?.artifact || store.artifacts[0];
  selectedArtifactId.value = first?.id || null;
  selectedSlotId.value = preferred?.slot.id || first?.slots[0]?.id || null;
}

onMounted(loadCaseIntoView);

const SOURCES = computed(() => store.sources);
const CLS_ORDER = { A: 0, C: 1, B: 2 };
const READINESS_LABELS = {
  P1_expert_review: 'Ready for expert review',
  P2_data_cleanup: 'Data cleanup required',
  P3_alignment_review: 'Alignment review required',
  Exclude_lexical_variant: 'Lexical variant',
};

const searchText = ref('');
const sourceFilter = ref('all');
const slotFilter = ref('all');
const readinessFilter = ref('all');

const availableSlots = computed(() => {
  const map = new Map();
  store.artifacts.forEach((artifact) => {
    artifact.slots.forEach((slot) => map.set(slot.id, slot.label));
  });
  return [...map.entries()]
    .map(([id, label]) => ({ id, label }))
    .sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'));
});

const visibleArtifacts = computed(() => {
  const query = searchText.value.trim().toLowerCase();
  return store.artifacts.filter((artifact) => {
    if (sourceFilter.value !== 'all' && !artifact.sources.includes(sourceFilter.value)) return false;
    if (
      readinessFilter.value !== 'all'
      && !artifact.slots.some((slot) => slot.reviewReadiness === readinessFilter.value)
    ) return false;
    if (slotFilter.value !== 'all' && !artifact.slots.some((slot) => slot.id === slotFilter.value)) return false;
    if (!query) return true;
    const text = [
      artifact.name,
      ...artifact.records,
      ...artifact.slots.flatMap((slot) => [
        slot.label,
        ...slot.assertions.flatMap((assertion) => assertion.values),
      ]),
    ].join(' ').toLowerCase();
    return text.includes(query);
  });
});

const visibleArtifactIds = computed(() => visibleArtifacts.value.map((artifact) => artifact.id));

function resetExplorerFilters() {
  searchText.value = '';
  sourceFilter.value = 'all';
  slotFilter.value = 'all';
  readinessFilter.value = 'all';
}

const worklist = computed(() =>
  visibleArtifacts.value
    .flatMap((a) => a.slots.map((s) => ({ artifact: a, slot: s })))
    .filter((x) => ['A', 'B', 'C'].includes(x.slot.cls))
    .filter(
      (x) => readinessFilter.value === 'all'
        || x.slot.reviewReadiness === readinessFilter.value,
    )
    .filter((x) => slotFilter.value === 'all' || x.slot.id === slotFilter.value)
    .filter(
      (x) => sourceFilter.value === 'all'
        || x.slot.assertions.some((assertion) => assertion.source === sourceFilter.value && assertion.raw),
    )
    .sort((x, y) => CLS_ORDER[x.slot.cls] - CLS_ORDER[y.slot.cls]),
);

const attrFacets = computed(() => {
  const map = new Map();
  worklist.value.forEach((w) => {
    const e = map.get(w.slot.label) || { label: w.slot.label, count: 0 };
    e.count += 1;
    map.set(w.slot.label, e);
  });
  return [...map.values()].sort((a, b) => b.count - a.count);
});

const entityGroups = computed(() => {
  const specs = [
    {
      name: '形制',
      slots: ['form'],
      accept: (value) => /式(?:变体)?$/.test(value),
      normalize: (value) => value,
    },
    {
      name: '年代',
      slots: ['dating', 'dating_assessment'],
      accept: (value) => /唐|宋|元|明|清|民国|五代|年/.test(value),
      normalize: (value) => value
        .replace(/\([^)]*\)/g, '')
        .replace(/^(唐|宋|元|明|清)$/, '$1代'),
    },
    {
      name: '馆藏',
      slots: ['current_holder'],
      accept: (value) => /博物馆|博物院|艺术研究院/.test(value),
      normalize: (value) => value,
    },
  ];
  return specs.map((spec) => {
    const values = new Map();
    visibleArtifacts.value.forEach((artifact) => {
      artifact.slots
        .filter((slot) => spec.slots.includes(slot.id))
        .flatMap((slot) => slot.assertions.flatMap((assertion) => assertion.normalizedValues))
        .forEach((value) => {
          if (!value || !spec.accept(value)) return;
          const normalized = spec.normalize(value);
          const artifacts = values.get(normalized) || [];
          if (!artifacts.some((item) => item.id === artifact.id)) artifacts.push(artifact);
          values.set(normalized, artifacts);
        });
    });
    return {
      name: spec.name,
      items: [...values.entries()]
        .map(([name, artifacts]) => ({ name, artifacts }))
        .sort((a, b) => b.artifacts.length - a.artifacts.length),
    };
  });
});

const checkedAttrs = ref([]);
const checkedEntities = ref([]);

function toggleIn(listRef, value) {
  const i = listRef.value.indexOf(value);
  if (i >= 0) listRef.value.splice(i, 1);
  else listRef.value.push(value);
}

const filteredWorklist = computed(() =>
  worklist.value.filter(
    (w) => !checkedAttrs.value.length || checkedAttrs.value.includes(w.slot.label),
  ),
);

const splitMode = ref(false);
const leftW = ref(300);
const rightW = ref(270);
const paneRatio = ref(0.5);
const dockH = ref(190);
const workbenchEl = ref(null);
const activeStage = ref('overview');

let dragKind = null;
let dragStart = 0;
let dragStartVal = 0;

function startDrag(kind, e) {
  dragKind = kind;
  dragStart = kind === 'dock' ? e.clientY : e.clientX;
  dragStartVal =
    kind === 'left' ? leftW.value
    : kind === 'right' ? rightW.value
    : kind === 'pane' ? paneRatio.value
    : dockH.value;
  window.addEventListener('mousemove', onDragMove);
  window.addEventListener('mouseup', endDrag);
  e.preventDefault();
}

function onDragMove(e) {
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  if (dragKind === 'left') {
    leftW.value = clamp(dragStartVal + e.clientX - dragStart, 220, 460);
  } else if (dragKind === 'right') {
    rightW.value = clamp(dragStartVal - (e.clientX - dragStart), 220, 440);
  } else if (dragKind === 'pane') {
    const w = workbenchEl.value?.getBoundingClientRect().width || 1000;
    paneRatio.value = clamp(dragStartVal + (e.clientX - dragStart) / w, 0.25, 0.75);
  } else if (dragKind === 'dock') {
    dockH.value = clamp(dragStartVal - (e.clientY - dragStart), 120, 380);
  }
}

function endDrag() {
  dragKind = null;
  window.removeEventListener('mousemove', onDragMove);
  window.removeEventListener('mouseup', endDrag);
}

const corpusStats = computed(() => ({
  sources: store.stats.records ? Object.keys(store.sources).length : 0,
  sourceLabel: 'books',
  artifacts: store.stats.artifacts || 0,
  contested: (store.stats.differ || 0) + (store.stats.overlap || 0),
  unresolved: (store.stats.differ || 0) + (store.stats.overlap || 0),
}));

const sourceHierarchy = computed(() =>
  Object.values(store.sources).map((source) => ({
    ...source,
    artifacts: visibleArtifacts.value.filter((artifact) => artifact.sources.includes(source.id)),
  })),
);

const artifactHierarchy = computed(() => entityGroups.value);

const conflictHierarchy = computed(() =>
  [
    { cls: 'A', name: '记载不一致', desc: '各来源取值不同,待考订' },
    { cls: 'B', name: '部分重叠', desc: '取值有交集,疑详略差异' },
    { cls: 'C', name: '疑似讹误', desc: '规则触发(待接入)' },
  ].map((group) => ({
    ...group,
    slots: worklist.value.filter((w) => w.slot.cls === group.cls),
  })),
);

const selectedArtifactId = ref(null);
const selectedSlotId = ref(null);

function onSelectArtifact(id) {
  selectedArtifactId.value = id;
  const artifact = store.artifacts.find((x) => x.id === id);
  selectedSlotId.value = artifact?.slots[0]?.id || null;
  activeStage.value = 'focus';
}

function onSelectSlot(id) {
  selectedSlotId.value = id;
  activeStage.value = 'evidence';
}

function selectCandidate(artifactId, slotId) {
  selectedArtifactId.value = artifactId;
  selectedSlotId.value = slotId;
  activeStage.value = 'evidence';
}

const globalTabs = ref([
  { id: 'global', title: 'Global KG', active: true },
  { id: 'lens', title: 'Lens View', active: false },
]);

const derivedTabs = ref([
  { id: 'compare', title: 'Attribute Matrix', active: true },
  { id: 'edit', title: 'Editing', active: false },
  { id: 'ledger', title: 'Ledger', active: false },
]);

const dockSlot = computed(() => {
  const a = store.artifacts.find((x) => x.id === selectedArtifactId.value);
  const s = a?.slots.find((x) => x.id === selectedSlotId.value);
  if (!a || !s) return null;
  return { artifact: a, slot: s };
});

const PART_PREFS = {
  duanwen: ['qimian', 'qindi', 'qincemian'],
  lacquer: ['qimian', 'qindi'],
  ash: ['qindi', 'qimian'],
  inscriber: ['mingwen'],
  dating: ['mingwen', 'qintou'],
  form: ['qintou', 'qimian', 'qinwei'],
  material: ['qindi', 'qimian'],
  collection: ['mingwen'],
  craft: ['qimian', 'qintou'],
};

function dockImage(assertion) {
  if (assertion.imagePath) return assertion.imagePath;
  if (!dockSlot.value || !assertion.recordId) return null;
  const files = dockSlot.value.artifact.imagesByBook[assertion.source] || [];
  if (!files.length) return null;
  const prefs = PART_PREFS[dockSlot.value.slot.id] || [];
  for (const pref of prefs) {
    const hit = files.find((f) => f.startsWith(pref));
    if (hit) return `/api/image/${assertion.recordId}/${hit}`;
  }
  return `/api/image/${assertion.recordId}/${files[0]}`;
}

function imageEvidenceLabel(assertion) {
  const stored = assertion.metadata?.image_match || assertion.metadata?.imageMatch;
  if (stored === 'attribute-linked') return 'attribute-linked image';
  if (stored === 'record-level-fallback') return 'record-level fallback image';
  if (stored === 'missing') return 'no image evidence';
  const files = assertion.metadata?.image_files || assertion.metadata?.imageFiles || [];
  if (!files.length) return 'no image evidence';
  const prefs = PART_PREFS[dockSlot.value?.slot.id] || [];
  const matched = files.some((file) => prefs.some((pref) => file.toLowerCase().startsWith(pref)));
  return matched ? 'attribute-linked image' : 'record-level fallback image';
}


const uploadedName = ref('');
const viewerImage = ref(null);
const viewerText = ref(null);

function openEvidenceImage(src, title) {
  if (!src) return;
  viewerImage.value = { src, title };
}

function closeEvidenceImage() {
  viewerImage.value = null;
}

async function openEvidenceText(assertion) {
  if (!assertion.recordId) return;
  viewerText.value = {
    title: `${SOURCES.value[assertion.source]?.title || assertion.source} · ${assertion.recordId}`,
    text: 'Loading OCR text…',
  };
  try {
    const response = await fetch(`/api/text/${assertion.recordId}`);
    if (!response.ok) throw new Error(`API ${response.status}`);
    viewerText.value.text = await response.text();
  } catch (error) {
    viewerText.value.text = `Unable to load OCR text: ${error}`;
  }
}

function closeEvidenceText() {
  viewerText.value = null;
}

async function handleUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  uploadedName.value = file.name;
  const form = new FormData();
  form.append('archive', file);
  try {
    await fetch('/api/ingest', { method: 'POST', body: form });
  } catch {
    /* backend not wired yet */
  }
  event.target.value = '';
}

function tabArr(tabs) {
  return Array.isArray(tabs) ? tabs : tabs.value;
}

function activateTab(tabs, id) {
  tabArr(tabs).forEach((tab) => {
    tab.active = tab.id === id;
  });
}

function closeTab(tabs, id) {
  const arr = tabArr(tabs);
  if (arr.length === 1) return;
  const idx = arr.findIndex((tab) => tab.id === id);
  if (idx < 0) return;
  const wasActive = arr[idx].active;
  arr.splice(idx, 1);
  if (wasActive) arr[0].active = true;
}

let tabSeq = 0;
function addTab(tabs) {
  const arr = tabArr(tabs);
  tabSeq += 1;
  arr.forEach((tab) => {
    tab.active = false;
  });
  arr.push({ id: `custom-${tabSeq}`, title: `View ${tabSeq}`, active: true });
}

function activeTabId(tabs) {
  return tabArr(tabs).find((t) => t.active)?.id;
}

const pinned = ref([]);

function pinArtifact(id) {
  const a = store.artifacts.find((x) => x.id === id);
  if (!a || pinned.value.some((p) => p.key === `a:${id}`)) return;
  pinned.value.push({ key: `a:${id}`, kind: 'artifact', label: a.name, artifactId: id });
}

function pinSlot(artifactId, slotId) {
  const a = store.artifacts.find((x) => x.id === artifactId);
  const s = a?.slots.find((x) => x.id === slotId);
  if (!s || pinned.value.some((p) => p.key === `s:${artifactId}:${slotId}`)) return;
  pinned.value.push({
    key: `s:${artifactId}:${slotId}`,
    kind: 'slot',
    label: `${a.name} · ${s.label}`,
    cls: s.cls,
    artifactId,
    slotId,
  });
}

function unpin(key) {
  pinned.value = pinned.value.filter((p) => p.key !== key);
}

function recallPin(p) {
  selectedArtifactId.value = p.artifactId;
  selectedSlotId.value = p.slotId || null;
  activeStage.value = p.slotId ? 'evidence' : 'focus';
}

const ledger = ref([]);

function onAdjudicated(payload) {
  const a = store.artifacts.find((x) => x.id === selectedArtifactId.value);
  const s = a?.slots.find((x) => x.id === payload.slotId);
  ledger.value.unshift({
    id: `adj-${ledger.value.length + 1}`,
    time: new Date().toLocaleString(),
    artifact: a?.name || '',
    slot: s?.label || '',
    cls: s?.cls,
    action: payload.action,
    text: payload.text,
    evidence: pinned.value.map((p) => p.label),
    supersedes:
      ledger.value.find((e) => e.artifact === a?.name && e.slot === s?.label)?.id || null,
  });
  activeStage.value = 'decision';
}
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <h1>KGExplorer: Knowledge Graph Visual Analytics System</h1>
      <div class="case-switcher">
        <span>Case</span>
        <strong>Case 1 · Guqin</strong>
      </div>
    </header>

    <section class="workspace" aria-label="Main workspace">
      <aside class="panel left-panel" aria-label="Workspace panel">
        <header class="panel-title">KG Workspace</header>

        <div class="left-content">
          <section class="control-card explorer-card" aria-label="Corpus explorer">
            <div class="explorer-head">
              <h2>Corpus Explorer</h2>
              <button type="button" title="Reset filters" @click="resetExplorerFilters">Reset</button>
            </div>
            <input
              v-model="searchText"
              class="explorer-search"
              type="search"
              placeholder="Search object, record, or value"
            />
            <div class="explorer-filters">
              <select v-model="sourceFilter" aria-label="Filter by source">
                <option value="all">All sources</option>
                <option v-for="source in Object.values(SOURCES)" :key="source.id" :value="source.id">
                  {{ source.title }}
                </option>
              </select>
              <select v-model="slotFilter" aria-label="Filter by attribute">
                <option value="all">All attributes</option>
                <option v-for="slot in availableSlots" :key="slot.id" :value="slot.id">
                  {{ slot.label }}
                </option>
              </select>
              <select v-model="readinessFilter" aria-label="Filter by audit readiness">
                <option value="all">All audit states</option>
                <option v-for="(label, id) in READINESS_LABELS" :key="id" :value="id">
                  {{ label }}
                </option>
              </select>
            </div>
            <div class="explorer-result">
              <strong>{{ visibleArtifacts.length }}</strong> / {{ store.artifacts.length }} objects
              <span v-if="store.caseId === 'guqin'">· {{ worklist.length }} conflict candidates</span>
            </div>
          </section>

          <section class="control-card stats-card" aria-label="Corpus statistics">
            <h2>Corpus</h2>
            <p v-if="store.caseLabel" class="case-label">{{ store.caseLabel }}</p>
            <p v-if="store.title" class="case-caption">{{ store.title }}</p>
            <div class="stat-grid">
              <div><b>{{ corpusStats.sources }}</b><span>{{ corpusStats.sourceLabel }}</span></div>
              <div><b>{{ corpusStats.artifacts }}</b><span>artifacts</span></div>
              <div><b>{{ corpusStats.contested }}</b><span>contested</span></div>
              <div><b>{{ corpusStats.unresolved - ledger.length >= 0 ? corpusStats.unresolved - ledger.length : 0 }}</b><span>open</span></div>
            </div>
            <div
              v-if="store.caseId === 'guqin' && store.evidenceAudit.ready_for_expert_review !== undefined"
              class="audit-strip"
            >
              <span><b>{{ store.evidenceAudit.ready_for_expert_review }}</b> expert-ready</span>
              <span><b>{{ store.evidenceAudit.requires_data_cleanup }}</b> cleanup</span>
              <span><b>{{ store.qualityIssues.length }}</b> OCR checks</span>
            </div>
          </section>

          <section class="control-card hierarchy-card" aria-label="Knowledge hierarchies">
            <h2>Knowledge Hierarchies</h2>
            <div class="hierarchy-columns">
              <section>
                <h3>Sources</h3>
                <ul class="folder-tree">
                  <li v-for="source in sourceHierarchy" :key="source.id" class="open">
                    <span class="folder-name" :style="{ color: source.color }">《{{ source.title }}》</span>
                    <ul>
                      <li
                        v-for="artifact in source.artifacts"
                        :key="source.id + artifact.id"
                        :class="{ 'tree-active': artifact.id === selectedArtifactId }"
                      >
                        <span class="tree-artifact" @click="onSelectArtifact(artifact.id)">{{ artifact.name }}</span>
                      </li>
                    </ul>
                  </li>
                </ul>
              </section>
              <section>
                <h3>Entities</h3>
                <ul class="folder-tree">
                  <li v-for="group in artifactHierarchy" :key="group.name" class="open">
                    <span class="folder-name">{{ group.name }}</span>
                    <ul>
                      <li v-for="item in group.items" :key="item.name" class="open">
                        <span>{{ item.name }}<i class="tree-badge">{{ item.artifacts.length }}</i></span>
                      </li>
                    </ul>
                  </li>
                </ul>
              </section>
              <section>
                <h3>Issue Types</h3>
                <ul class="folder-tree conflict-tree">
                  <li v-for="group in conflictHierarchy" :key="group.cls" class="open">
                    <span>
                      <i class="chip-dot" :data-cls="group.cls"></i>
                      {{ group.cls }} · {{ group.name }}
                      <i class="tree-badge">{{ group.slots.length }}</i>
                    </span>
                    <ul>
                      <li
                        v-for="w in group.slots"
                        :key="group.cls + w.artifact.id + w.slot.id"
                        :class="{ 'tree-active': w.artifact.id === selectedArtifactId && w.slot.id === selectedSlotId }"
                      >
                        <span
                          class="tree-artifact"
                          @click="selectCandidate(w.artifact.id, w.slot.id)"
                        >{{ w.artifact.name }} · {{ w.slot.label }}</span>
                      </li>
                    </ul>
                  </li>
                </ul>
              </section>
            </div>
          </section>

          <section class="control-card worklist-card" aria-label="Conflict worklist">
            <h2>Candidate Queue</h2>
            <ul class="worklist">
              <li
                v-for="w in worklist"
                :key="w.artifact.id + w.slot.id"
                :class="{ active: w.artifact.id === selectedArtifactId && w.slot.id === selectedSlotId }"
                @click="selectCandidate(w.artifact.id, w.slot.id)"
              >
                <i class="chip-dot" :data-cls="w.slot.cls"></i>
                <span class="wl-name">{{ w.artifact.name }} · {{ w.slot.label }}</span>
                <em
                  v-if="w.slot.reviewReadiness"
                  class="readiness-tag"
                  :data-state="w.slot.reviewReadiness"
                >
                  {{ w.slot.reviewReadiness.replace('P1_', '').replace('P2_', '').replace('P3_', '').replace('Exclude_', '') }}
                </em>
                <em v-else>candidate</em>
              </li>
            </ul>
          </section>
        </div>
      </aside>

      <section class="panel center-panel" aria-label="Main visualization view">
        <header class="panel-toolbar">
          <h2>Global KG Explorer</h2>
          <div class="graph-legend" aria-label="Graph legend">
            <span title="One individual artifact record from the corpus"><i class="legend-object"></i>artifact record</span>
            <span title="Normalized attribute value shared by at least two artifact records"><i style="background:#7c9aae"></i>attribute value</span>
            <span title="Outer ring sectors encode which books contain this record; books are not graph nodes"><i style="background:#b29a62"></i>source coverage ring</span>
            <span v-for="source in Object.values(SOURCES)" :key="source.id" :title="source.title"><i :style="{ background: source.color }"></i>{{ source.id }}</span>
            <span title="Aligned across multiple sources"><i style="background:#5d8c82"></i>confirmed</span>
            <span title="Potential cross-source match"><i style="background:#b29a62"></i>candidate</span>
            <span title="Present in one source only"><i style="background:#aab4ba"></i>single-source</span>
            <span title="Unresolved or conflicting evidence"><i style="background:#b86f3d"></i>unresolved</span>
            <span><i :style="{ background: CLASS_COLORS.A }"></i>A</span>
            <span><i :style="{ background: CLASS_COLORS.C }"></i>C</span>
            <span><i :style="{ background: CLASS_COLORS.B }"></i>B</span>
            <span><i :style="{ background: CLASS_COLORS.consensus }"></i>OK</span>
          </div>
          <button class="save-button" type="button">Save</button>
        </header>
        <div class="graph-workbench">
          <section class="graph-pane" aria-label="Global knowledge graph">
            <div class="browser-tabs">
              <button
                v-for="tab in globalTabs"
                :key="tab.id"
                :class="['browser-tab', { active: tab.active }]"
                type="button"
                @click="activateTab(globalTabs, tab.id)"
              >
                <span>{{ tab.title }}</span>
                <i @click.stop="closeTab(globalTabs, tab.id)">×</i>
              </button>
              <button class="new-tab" type="button" @click="addTab(globalTabs)">＋</button>
            </div>
            <KnowledgeGraphView
              v-if="activeTabId(globalTabs) === 'global'"
              variant="global"
              :selected-artifact-id="selectedArtifactId"
              :selected-slot-id="selectedSlotId"
              :visible-artifact-ids="visibleArtifactIds"
              @select-artifact="onSelectArtifact"
              @select-slot="onSelectSlot"
              @pin-artifact="pinArtifact"
            />
            <div v-else class="tab-placeholder">
              Lens controls
            </div>
          </section>

          <section class="graph-pane" aria-label="Interaction-derived knowledge graph">
            <div class="browser-tabs">
              <button
                v-for="tab in derivedTabs"
                :key="tab.id"
                :class="['browser-tab', { active: tab.active }]"
                type="button"
                @click="activateTab(derivedTabs, tab.id)"
              >
                <span>{{ tab.title }}</span>
                <i @click.stop="closeTab(derivedTabs, tab.id)">×</i>
              </button>
              <button class="new-tab" type="button" @click="addTab(derivedTabs)">＋</button>
            </div>
            <KnowledgeGraphView
              v-if="activeTabId(derivedTabs) === 'compare'"
              variant="derived"
              :selected-artifact-id="selectedArtifactId"
              :selected-slot-id="selectedSlotId"
              :visible-artifact-ids="visibleArtifactIds"
              @select-slot="onSelectSlot"
            />
            <div v-else-if="activeTabId(derivedTabs) === 'ledger'" class="ledger-view">
              <p v-if="!ledger.length" class="ledger-empty">No adjudications yet. Decisions made in the right panel are recorded here, append-only.</p>
              <article v-for="e in ledger" :key="e.id" class="ledger-entry">
                <header>
                  <i class="chip-dot" :data-cls="e.cls"></i>
                  <strong>{{ e.artifact }} · {{ e.slot }}</strong>
                  <span class="ledger-action">{{ e.action }}</span>
                  <span class="ledger-time">{{ e.time }}</span>
                </header>
                <p class="ledger-text">{{ e.text }}</p>
                <p v-if="e.evidence.length" class="ledger-evidence">Evidence cited: {{ e.evidence.join(' / ') }}</p>
                <p v-if="e.supersedes" class="ledger-supersedes">supersedes {{ e.supersedes }}</p>
              </article>
            </div>
            <div v-else class="tab-placeholder">
              {{ activeTabId(derivedTabs) === 'edit' ? 'Contested assertion workspace (V3) — planned' : 'Empty view' }}
            </div>
          </section>
        </div>

        <div class="evidence-dock" aria-label="Evidence tray" :style="{ height: dockH + 'px' }">
          <div class="dock-resizer" title="Resize evidence tray" @mousedown="startDrag('dock', $event)"></div>
          <div class="dock-head">
            <span class="tray-title">Evidence Tray</span>
            <span v-if="dockSlot" class="dock-context">{{ dockSlot.artifact.name }} · {{ dockSlot.slot.label }}</span>
            <div class="dock-pins">
              <div v-for="p in pinned" :key="p.key" class="tray-chip" @click="recallPin(p)">
                <i v-if="p.cls" class="chip-dot" :data-cls="p.cls"></i>
                {{ p.label }}
                <b @click.stop="unpin(p.key)">×</b>
              </div>
            </div>
            <button v-if="pinned.length" class="tray-clear" type="button" @click="pinned = []">Clear</button>
          </div>
          <div v-if="dockSlot" class="dock-body">
            <article
              v-for="a in dockSlot.slot.assertions"
              :key="`${a.source}:${a.recordId}`"
              class="dock-card"
              :class="{ silent: !a.raw }"
            >
              <header :style="{ color: SOURCES[a.source]?.color }">{{ SOURCES[a.source]?.title }}</header>
              <img
                v-if="dockImage(a)"
                class="dock-photo"
                :src="dockImage(a)"
                :alt="`${SOURCES[a.source]?.title} · ${dockSlot.slot.label}`"
                loading="lazy"
                title="Open full-size evidence image"
                @click="openEvidenceImage(dockImage(a), `${SOURCES[a.source]?.title} · ${dockSlot.slot.label}`)"
              />
              <div v-else class="dock-thumb part" :data-kind="a.raw ? 'part' : 'none'">
                <span v-if="a.raw">no image evidence for this record</span>
                <span v-else>not recorded</span>
              </div>
              <small v-if="a.raw" class="dock-image-status" :data-kind="imageEvidenceLabel(a)">{{ imageEvidenceLabel(a) }}</small>
              <div v-if="a.audit" class="dock-audit">
                <span :data-state="a.audit.text_support">{{ a.audit.text_support }}</span>
                <span :data-state="a.audit.image_support">{{ a.audit.image_support }}</span>
              </div>
              <p class="dock-raw">{{ a.raw || '该书未记载' }}</p>
              <p v-if="a.audit?.text_snippet" class="dock-snippet">{{ a.audit.text_snippet }}</p>
              <div v-if="a.raw" class="dock-card-actions">
                <button type="button" @click="openEvidenceText(a)">OCR text</button>
                <button type="button" @click="pinSlot(dockSlot.artifact.id, dockSlot.slot.id)">Pin evidence</button>
              </div>
            </article>
          </div>
          <div v-else class="dock-empty">No evidence selected.</div>
        </div>
      </section>

      <aside class="panel right-panel" aria-label="Evidence and adjudication">
        <header class="panel-title">Evidence &amp; Adjudication</header>
        <AdjudicationPanel
          :selected-artifact-id="selectedArtifactId"
          :selected-slot-id="selectedSlotId"
          @select-slot="onSelectSlot"
          @pin-slot="pinSlot"
          @adjudicated="onAdjudicated"
        />
      </aside>
    </section>

    <Teleport to="body">
      <div v-if="viewerImage" class="evidence-lightbox" role="dialog" aria-modal="true" @click.self="closeEvidenceImage">
        <div class="lightbox-panel">
          <header>
            <strong>{{ viewerImage.title }}</strong>
            <button type="button" aria-label="Close image viewer" @click="closeEvidenceImage">×</button>
          </header>
          <div class="lightbox-stage">
            <img :src="viewerImage.src" :alt="viewerImage.title" />
          </div>
          <p>Click outside the image or close the viewer to return to the evidence tray.</p>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="viewerText" class="evidence-lightbox" role="dialog" aria-modal="true" @click.self="closeEvidenceText">
        <div class="lightbox-panel text-viewer">
          <header>
            <strong>{{ viewerText.title }}</strong>
            <button type="button" aria-label="Close OCR viewer" @click="closeEvidenceText">×</button>
          </header>
          <pre>{{ viewerText.text }}</pre>
        </div>
      </div>
    </Teleport>
  </main>
</template>
