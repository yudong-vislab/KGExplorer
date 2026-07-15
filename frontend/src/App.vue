<script setup>
import { computed, ref } from 'vue';
import KnowledgeGraphView from './components/KnowledgeGraphView.vue';
import AdjudicationPanel from './components/AdjudicationPanel.vue';
import { ARTIFACTS, SOURCES, CLASS_COLORS } from './data/guqinSeed.js';

const CLS_ORDER = { A: 0, C: 1, B: 2 };
const worklist = ARTIFACTS.flatMap((a) =>
  a.slots.map((s) => ({ artifact: a, slot: s })),
).sort((x, y) => CLS_ORDER[x.slot.cls] - CLS_ORDER[y.slot.cls]);

const attrFacets = (() => {
  const map = new Map();
  worklist.forEach((w) => {
    const e = map.get(w.slot.label) || { label: w.slot.label, count: 0 };
    e.count += 1;
    map.set(w.slot.label, e);
  });
  return [...map.values()].sort((a, b) => b.count - a.count);
})();

const entityGroups = (() => {
  const all = [...new Set(ARTIFACTS.flatMap((a) => a.entities))];
  const groupOf = (e) =>
    e.endsWith('式') ? '形制' : /博物馆|博物院/.test(e) ? '馆藏' : '年代';
  const groups = { 形制: [], 年代: [], 馆藏: [] };
  all.forEach((e) => groups[groupOf(e)].push(e));
  return Object.entries(groups).map(([name, items]) => ({ name, items }));
})();

const checkedAttrs = ref([]);
const checkedEntities = ref([]);

function toggleIn(listRef, value) {
  const i = listRef.value.indexOf(value);
  if (i >= 0) listRef.value.splice(i, 1);
  else listRef.value.push(value);
}

const filteredWorklist = computed(() =>
  worklist.filter(
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

const workflowStages = [
  { id: 'overview', label: 'Overview' },
  { id: 'focus', label: 'Focus' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'decision', label: 'Decision' },
];

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

const corpusStats = {
  sources: Object.keys(SOURCES).length,
  artifacts: ARTIFACTS.length,
  contested: worklist.length,
  unresolved: worklist.length,
};

const sourceHierarchy = Object.values(SOURCES).map((source) => ({
  ...source,
  artifacts: ARTIFACTS.filter((artifact) => artifact.sources.includes(source.id)),
}));

const artifactHierarchy = entityGroups.map((group) => ({
  name: group.name,
  items: group.items.map((item) => ({
    name: item,
    artifacts: ARTIFACTS.filter((artifact) => artifact.entities.includes(item)),
  })),
}));

const conflictHierarchy = [
  { cls: 'A', name: '实质分歧', desc: '年代、尺寸、事实判断冲突' },
  { cls: 'B', name: '表述差异', desc: '同一事实的口径或转写差异' },
  { cls: 'C', name: '疑似讹误', desc: '排印、OCR、外部知识触发' },
].map((group) => ({
  ...group,
  slots: worklist.filter((w) => w.slot.cls === group.cls),
}));

const selectedArtifactId = ref(null);
const selectedSlotId = ref(null);

function onSelectArtifact(id) {
  selectedArtifactId.value = id;
  selectedSlotId.value = null;
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
  { id: 'compare', title: 'Comparison', active: true },
  { id: 'edit', title: 'Editing', active: false },
  { id: 'ledger', title: 'Ledger', active: false },
]);

const dockSlot = computed(() => {
  const a = ARTIFACTS.find((x) => x.id === selectedArtifactId.value);
  const s = a?.slots.find((x) => x.id === selectedSlotId.value);
  if (!a || !s) return null;
  return { artifact: a, slot: s };
});


const uploadedName = ref('');

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
  const a = ARTIFACTS.find((x) => x.id === id);
  if (!a || pinned.value.some((p) => p.key === `a:${id}`)) return;
  pinned.value.push({ key: `a:${id}`, kind: 'artifact', label: a.name, artifactId: id });
}

function pinSlot(artifactId, slotId) {
  const a = ARTIFACTS.find((x) => x.id === artifactId);
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
  const a = ARTIFACTS.find((x) => x.id === selectedArtifactId.value);
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
    </header>

    <section class="workspace" aria-label="Main workspace">
      <aside class="panel left-panel" aria-label="Workspace panel">
        <header class="panel-title">KG Workspace</header>

        <div class="left-content">
          <section class="control-card upload-card" aria-label="Corpus upload">
            <h2>Corpus Upload</h2>
            <label class="upload-drop">
              <input type="file" accept=".zip,.rar,.7z" @change="handleUpload" hidden />
              <span v-if="!uploadedName">Choose scanned-book archive</span>
              <span v-else>{{ uploadedName }}</span>
            </label>
          </section>

          <section class="control-card stats-card" aria-label="Corpus statistics">
            <h2>Corpus</h2>
            <div class="stat-grid">
              <div><b>{{ corpusStats.sources }}</b><span>sources</span></div>
              <div><b>{{ corpusStats.artifacts }}</b><span>artifacts</span></div>
              <div><b>{{ corpusStats.contested }}</b><span>contested</span></div>
              <div><b>{{ corpusStats.unresolved - ledger.length >= 0 ? corpusStats.unresolved - ledger.length : 0 }}</b><span>open</span></div>
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
                <em>candidate</em>
              </li>
            </ul>
          </section>
        </div>
      </aside>

      <section class="panel center-panel" aria-label="Main visualization view">
        <header class="panel-toolbar">
          <h2>Global KG Explorer</h2>
          <div class="graph-legend" aria-label="Graph legend">
            <span><i :style="{ background: CLASS_COLORS.A }"></i>A</span>
            <span><i :style="{ background: CLASS_COLORS.C }"></i>C</span>
            <span><i :style="{ background: CLASS_COLORS.B }"></i>B</span>
            <span><i :style="{ background: CLASS_COLORS.consensus }"></i>OK</span>
          </div>
          <button class="save-button" type="button">Save</button>
        </header>
        <div class="workflow-strip" aria-label="Analysis workflow">
          <button
            v-for="(stage, index) in workflowStages"
            :key="stage.id"
            :class="{ active: activeStage === stage.id }"
            type="button"
            @click="activeStage = stage.id"
          >
            <b>{{ index + 1 }}</b>{{ stage.label }}
          </button>
        </div>
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
              :key="a.source"
              class="dock-card"
              :class="{ silent: !a.raw }"
            >
              <header :style="{ color: SOURCES[a.source]?.color }">《{{ SOURCES[a.source]?.title }}》</header>
              <div class="dock-thumb" :data-kind="a.raw ? 'scan' : 'none'">
                <span v-if="a.raw">scan page · {{ dockSlot.slot.label }}</span>
                <span v-else>—</span>
              </div>
              <div class="dock-thumb part" :data-kind="a.raw ? 'part' : 'none'">
                <span v-if="a.raw">part photo · texture detail</span>
                <span v-else>not recorded</span>
              </div>
              <p class="dock-raw">{{ a.raw || '该书未记载' }}</p>
              <button v-if="a.raw" type="button" class="dock-pin" @click="pinSlot(dockSlot.artifact.id, dockSlot.slot.id)">add to evidence tray</button>
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
  </main>
</template>
