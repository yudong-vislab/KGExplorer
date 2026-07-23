import { reactive } from 'vue';

export const CLASS_COLORS = {
  A: '#9f4328',
  B: '#8f6b2f',
  C: '#435d73',
  consensus: '#2f7268',
  single: '#8a979d',
  missing: '#b7c1c5',
};

export const CLASS_LABELS = {
  A: 'differ · 待考订',
  B: 'overlap · 部分重叠',
  C: 'suspected · 疑似讹误',
  consensus: '一致',
  single: 'single-source · 仅一源',
  missing: '缺失',
};

const BOOK_COLORS = {
  Gq: '#1f5a7a',
  Yjzq: '#a45c1d',
  QNQY: '#6b4e9b',
  CQL: '#2d7a6b',
};

export const store = reactive({
  loaded: false,
  error: null,
  title: '',
  caseNote: '',
  caseLabel: '',
  caseId: '',
  sources: {},
  artifacts: [],
  stats: {},
  evidenceAudit: {},
  qualityIssues: [],
});

export function worstClass(artifact) {
  if (!artifact.slots.length) return 'consensus';
  if (artifact.slots.some((s) => s.cls === 'A')) return 'A';
  if (artifact.slots.some((s) => s.cls === 'C')) return 'C';
  if (artifact.slots.some((s) => s.cls === 'B')) return 'B';
  return 'consensus';
}

const STATUS_TO_CLS = {
  differ: 'A',
  overlap: 'B',
  evidence: 'consensus',
  consensus: 'consensus',
  single_source: 'single',
};

function beliefFrom(assertions) {
  const present = assertions.filter((a) => (a.values || []).length);
  if (!present.length) return [];
  const counts = new Map();
  present.forEach((a) => {
    const key = a.values.join('、');
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return [...counts.entries()]
    .map(([value, n]) => ({ value, p: n / present.length }))
    .sort((x, y) => y.p - x.p);
}

function adaptArtifact(raw) {
  const sourceAssertions = (a) => {
    const scopedValues = a.scope
      ? a.scope.object_values || []
      : a.audit?.object_values
        ? a.audit.object_values
        : null;
    const values = scopedValues === null ? a.values || [] : scopedValues;
    return {
      source: a.source ?? a.book,
      recordId: a.record_id ?? a.recordId,
      recordName: a.record_name ?? a.recordName,
      values,
      normalizedValues: scopedValues || a.normalized_values || a.normalizedValues || values,
      valueDetails: a.value_details || a.valueDetails || [],
      raw: values.length ? values.join('、') : null,
      imagePath: a.image_path || a.imagePath || null,
      metadata: a.metadata || {},
      audit: a.audit || null,
    };
  };
  const caus = raw.caus || raw.slots || [];
  const consensusSlots = caus.filter((c) => c.status === 'consensus');
  const entities = [];
  ['form', 'dating'].forEach((slotId) => {
    const cau = caus.find((c) => c.slot === slotId);
    const firstPresent = cau?.assertions.find((a) => (a.values || []).length);
    if (firstPresent) entities.push(firstPresent.values[0]);
  });
  return {
    id: raw.artifact_id,
    name: raw.name,
    aligned: raw.aligned,
    alignmentStatus: raw.alignment_status || (raw.aligned && raw.books?.length > 1
      ? 'confirmed'
      : raw.books?.length > 1
        ? 'candidate'
        : raw.books?.length === 1
          ? 'source-local'
          : 'unresolved'),
    sources: raw.books,
    records: raw.records,
    imagesByBook: raw.images || {},
    entities: raw.entities?.length ? raw.entities : entities,
    consensusCount: consensusSlots.length,
    alignmentCandidates: raw.alignment_candidates || [],
    auditIdentityGrade: raw.audit_identity_grade || 'source_local',
    auditReadinessCounts: raw.audit_readiness_counts || {},
    slots: caus.map((c) => ({
      id: c.slot,
      label: c.label,
      status: c.status,
      conflictType: c.conflict_type || c.conflictType || null,
      cls: STATUS_TO_CLS[c.status],
      assertions: c.assertions.map(sourceAssertions),
      audit: c.audit || null,
      reviewReadiness: c.audit?.review_readiness || null,
      auditFlags: c.audit?.audit_flags || [],
      belief: beliefFrom(c.assertions),
      note:
        c.audit?.machine_audit_note
          ? c.audit.machine_audit_note
          : c.status === 'differ'
          ? '自动检测:不同标本来源的名称存在差异,进入冲突候选。'
          : c.status === 'single_source'
            ? '仅有一个来源记录该属性，不代表跨来源共识。'
            : c.status === 'consensus'
              ? '多个来源取值一致，可作为当前共识观察。'
              : c.status === 'evidence'
                ? '对象证据:该对象已关联多个来源记录,可逐一查看图像、原文和来源元数据。'
                : '自动检测:取值部分重叠,疑为详略差异,可考虑合并。',
    })),
  };
}

function resetStore() {
  store.loaded = false;
  store.error = null;
  store.title = '';
  store.caseNote = '';
  store.caseLabel = '';
  store.caseId = '';
  Object.keys(store.sources).forEach((key) => delete store.sources[key]);
  store.artifacts.splice(0, store.artifacts.length);
  store.stats = {};
  store.evidenceAudit = {};
  store.qualityIssues = [];
}

export async function loadStore() {
  resetStore();
  try {
    const res = await fetch('/api/case-data/guqin');
    if (!res.ok) throw new Error(`API ${res.status}`);
    const data = await res.json();
    Object.entries(data.books).forEach(([id, title]) => {
      store.sources[id] = { id, title, color: BOOK_COLORS[id] || '#a58e63' };
    });
    const adapted = data.artifacts.map(adaptArtifact);
    // Keep the complete corpus in the graph. Unaligned records are still
    // valid source-local knowledge and provide the context around contested
    // objects; alignment is an analytic state, not a visibility filter.
    store.artifacts.splice(0, store.artifacts.length, ...adapted);
    const defaults = {
      title: 'Guqin Heritage Knowledge Revision',
      note: 'Multisource guqin books with scanned-part evidence',
      label: 'Case 1 · Guqin',
    };
    store.title = data.case?.title || defaults.title;
    store.caseNote = data.case?.note || defaults.note;
    store.caseLabel = data.case?.label || defaults.label;
    store.caseId = 'guqin';
    store.unalignedCount = adapted.filter((artifact) => artifact.alignmentStatus !== 'confirmed').length;
    store.stats = data.stats;
    store.evidenceAudit = data.evidence_audit || {};
    store.qualityIssues = data.quality_issues || [];
    store.loaded = true;
  } catch (err) {
    store.error = String(err);
  }
}
