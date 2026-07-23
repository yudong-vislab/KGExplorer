<script setup>
import { computed, ref, watch } from 'vue';
import { store, CLASS_COLORS, CLASS_LABELS } from '../data/store.js';
const ARTIFACTS = store.artifacts;
const SOURCES = store.sources;

const props = defineProps({
  selectedArtifactId: { type: String, default: null },
  selectedSlotId: { type: String, default: null },
});
const emit = defineEmits(['select-slot', 'adjudicated', 'pin-slot']);

const artifact = computed(() => ARTIFACTS.find((a) => a.id === props.selectedArtifactId) || null);
const slot = computed(() => artifact.value?.slots.find((s) => s.id === props.selectedSlotId) || null);
const canAdjudicate = computed(
  () => !slot.value?.reviewReadiness || slot.value.reviewReadiness === 'P1_expert_review',
);
const readinessLabel = computed(() => ({
  P1_expert_review: 'Ready for expert review',
  P2_data_cleanup: 'Data cleanup required',
  P3_alignment_review: 'Alignment review required',
  Exclude_lexical_variant: 'Lexical variant only',
}[slot.value?.reviewReadiness] || 'Not machine-audited'));
const valueGroups = computed(() => {
  if (!slot.value) return [];
  const groups = new Map();
  slot.value.assertions.forEach((assertion) => {
    const value = assertion.raw || 'not recorded';
    const group = groups.get(value) || { value, sources: [] };
    group.sources.push(SOURCES[assertion.source]?.title || assertion.source);
    groups.set(value, group);
  });
  return [...groups.values()].sort((a, b) => b.sources.length - a.sources.length);
});

const draft = ref('');

watch(slot, (s) => {
  draft.value = s
    ? `待专家核验: 该属性在${s.assertions.filter((a) => a.raw).length}个来源中出现可疑差异。初步解释: ${s.note}${s.belief[0]?.value ? ` 可作为修订候选: ${s.belief[0].value}。` : ''}`
    : '';
});

function decide(action) {
  if (!slot.value) return;
  if (!canAdjudicate.value && action !== 'keep_open') return;
  emit('adjudicated', { slotId: slot.value.id, action, text: draft.value });
}
</script>

<template>
  <div class="adjudication-body">
    <p v-if="!artifact" class="adj-empty">No selection.</p>

    <template v-else>
      <div class="adj-artifact">
        <strong>{{ artifact.name }}</strong>
        <span>{{ artifact.sources.length }} source(s) · {{ artifact.slots.filter((s) => ['A', 'B', 'C'].includes(s.cls)).length }} candidate(s)</span>
      </div>

      <ul class="adj-slot-list">
        <li
          v-for="s in artifact.slots"
          :key="s.id"
          :class="{ active: s.id === selectedSlotId }"
          @click="emit('select-slot', s.id)"
        >
          <i :style="{ background: CLASS_COLORS[s.cls] }"></i>
          {{ s.label }}
          <em>{{ s.reviewReadiness ? s.reviewReadiness.replace('P1_', '').replace('P2_', '').replace('P3_', '').replace('Exclude_', '') : CLASS_LABELS[s.cls] }}</em>
        </li>
      </ul>

      <template v-if="slot">
        <h3>Current attribute</h3>
        <div class="adj-focus-card">
          <strong>{{ slot.label }}</strong>
          <span>{{ slot.assertions.filter((a) => a.raw).length }} recorded · {{ slot.assertions.filter((a) => !a.raw).length }} missing</span>
          <p>{{ slot.note }}</p>
        </div>

        <div v-if="slot.audit" class="adj-audit-card" :data-state="slot.reviewReadiness">
          <header>
            <strong>{{ readinessLabel }}</strong>
            <span>{{ slot.audit.identity_grade }}</span>
          </header>
          <p>{{ slot.audit.machine_audit_note }}</p>
          <div v-if="slot.auditFlags.length">
            <span v-for="flag in slot.auditFlags" :key="flag">{{ flag }}</span>
          </div>
        </div>

        <h3>Observed value groups</h3>
        <ul class="adj-value-groups">
          <li v-for="group in valueGroups" :key="group.value">
            <strong>{{ group.value }}</strong>
            <span>{{ group.sources.length }} source(s): {{ group.sources.join(' · ') }}</span>
          </li>
        </ul>

        <p class="adj-evidence-hint">Full source text and image evidence are shown in the Evidence Tray below. The matrix is the comparison overview; this panel is for adjudication.</p>

        <h3>Interpretation hypotheses</h3>
        <div class="adj-belief">
          <div
            v-for="b in slot.belief"
            :key="b.value"
            :style="{ width: Math.round(b.p * 100) + '%', background: CLASS_COLORS[slot.cls] }"
            :class="{ minor: b.p < 0.5 }"
          >
            {{ b.value }} {{ Math.round(b.p * 100) }}%
          </div>
        </div>
        <p class="adj-note">{{ slot.note }}</p>

        <h3>Evidence-grounded revision draft</h3>
        <textarea v-model="draft" rows="4"></textarea>

        <div class="adj-actions">
          <button type="button" :disabled="!canAdjudicate" @click="decide('adopt')">采信修订</button>
          <button type="button" :disabled="!canAdjudicate" @click="decide('compatible')">标注兼容</button>
          <button type="button" :disabled="!canAdjudicate" @click="decide('flag_error')">标记讹误</button>
          <button type="button" @click="decide('keep_open')">存疑待考</button>
          <button type="button" @click="emit('pin-slot', artifact.id, slot.id)">加入证据托盘</button>
        </div>
      </template>

    </template>
  </div>
</template>
