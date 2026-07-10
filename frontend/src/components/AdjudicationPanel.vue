<script setup>
import { computed, ref, watch } from 'vue';
import { ARTIFACTS, SOURCES, CLASS_COLORS, CLASS_LABELS } from '../data/guqinSeed.js';

const props = defineProps({
  selectedArtifactId: { type: String, default: null },
  selectedSlotId: { type: String, default: null },
});
const emit = defineEmits(['select-slot', 'adjudicated']);

const artifact = computed(() => ARTIFACTS.find((a) => a.id === props.selectedArtifactId) || null);
const slot = computed(() => artifact.value?.slots.find((s) => s.id === props.selectedSlotId) || null);

const draft = ref('');
const log = ref([]);

watch(slot, (s) => {
  draft.value = s
    ? `综合${s.assertions.filter((a) => a.raw).length}源记载:${s.note} 建议修订表述:${s.belief[0].value}。`
    : '';
});

function decide(action) {
  if (!slot.value) return;
  log.value.unshift({
    time: new Date().toLocaleTimeString(),
    artifact: artifact.value.name,
    slot: slot.value.label,
    action,
    text: draft.value,
  });
  emit('adjudicated', { slotId: slot.value.id, action });
}
</script>

<template>
  <div class="adjudication-body">
    <p v-if="!artifact" class="adj-empty">Select an artifact glyph, then a contested slot, to review evidence.</p>

    <template v-else>
      <div class="adj-artifact">
        <strong>{{ artifact.name }}</strong>
        <span>{{ artifact.slots.length }} contested slot(s)</span>
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
          <em>{{ CLASS_LABELS[s.cls] }}</em>
        </li>
      </ul>

      <template v-if="slot">
        <h3>Source assertions</h3>
        <article v-for="a in slot.assertions" :key="a.source" class="adj-assertion">
          <header :style="{ color: SOURCES[a.source]?.color }">《{{ SOURCES[a.source]?.title }}》</header>
          <p v-if="a.raw">{{ a.raw }}</p>
          <p v-else class="adj-missing">— 该书未记载 —</p>
        </article>

        <h3>Belief</h3>
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

        <h3>LLM revision draft</h3>
        <textarea v-model="draft" rows="4"></textarea>

        <div class="adj-actions">
          <button type="button" @click="decide('adopt')">采信修订</button>
          <button type="button" @click="decide('compatible')">标注兼容</button>
          <button type="button" @click="decide('flag_error')">标记讹误</button>
          <button type="button" @click="decide('keep_open')">存疑待考</button>
        </div>
      </template>

      <template v-if="log.length">
        <h3>Adjudication log</h3>
        <ul class="adj-log">
          <li v-for="(entry, i) in log" :key="i">
            <span>{{ entry.time }}</span> {{ entry.artifact }} · {{ entry.slot }} → <strong>{{ entry.action }}</strong>
          </li>
        </ul>
      </template>
    </template>
  </div>
</template>
