import { reactive } from 'vue';

export const CLASS_COLORS = {
  A: '#9f4328',
  B: '#8f6b2f',
  C: '#435d73',
  consensus: '#2f7268',
  missing: '#b7c1c5',
};

export const CLASS_LABELS = {
  A: 'differ · 待考订',
  B: 'overlap · 部分重叠',
  C: 'suspected · 疑似讹误',
  consensus: '一致',
  missing: '缺失',
};

const BOOK_COLORS = {
  Gq: '#294e6b',
  Yjzq: '#48677d',
  QNQY: '#667f8d',
  CQL: '#3f6268',
};

export const store = reactive({
  loaded: false,
  error: null,
  title: '',
  caseNote: '',
  sources: {},
  artifacts: [],
  stats: {},
});

export function worstClass(artifact) {
  if (!artifact.slots.length) return 'consensus';
  if (artifact.slots.some((s) => s.cls === 'A')) return 'A';
  if (artifact.slots.some((s) => s.cls === 'C')) return 'C';
  if (artifact.slots.some((s) => s.cls === 'B')) return 'B';
  return 'consensus';
}

const STATUS_TO_CLS = { differ: 'A', overlap: 'B', evidence: 'consensus' };

function beliefFrom(assertions) {
  const present = assertions.filter((a) => a.values.length);
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
  const contested = raw.caus.filter((c) => STATUS_TO_CLS[c.status]);
  const consensusSlots = raw.caus.filter((c) => c.status === 'consensus');
  const entities = [];
  ['form', 'dating'].forEach((slotId) => {
    const cau = raw.caus.find((c) => c.slot === slotId);
    const firstPresent = cau?.assertions.find((a) => a.values.length);
    if (firstPresent) entities.push(firstPresent.values[0]);
  });
  return {
    id: raw.artifact_id,
    name: raw.name,
    aligned: raw.aligned,
    alignmentStatus: raw.aligned && raw.books?.length > 1
      ? 'confirmed'
      : raw.books?.length > 1
        ? 'candidate'
        : raw.books?.length === 1
          ? 'source-local'
          : 'unresolved',
    sources: raw.books,
    records: raw.records,
    imagesByBook: raw.images || {},
    entities: raw.entities?.length ? raw.entities : entities,
    consensusCount: consensusSlots.length,
    slots: contested.map((c) => ({
      id: c.slot,
      label: c.label,
      status: c.status,
      cls: STATUS_TO_CLS[c.status],
      assertions: c.assertions.map((a) => ({
        source: a.book,
        recordId: a.record_id,
        values: a.values,
        raw: a.values.length ? a.values.join('、') : null,
        imagePath: a.image_path || null,
      })),
      belief: beliefFrom(c.assertions),
      note:
        c.status === 'differ'
          ? '自动检测:不同标本来源的名称存在差异,进入冲突候选。'
          : c.status === 'evidence'
            ? '对象证据:该植物已关联多个标本来源,可逐一查看图像和馆藏元数据。'
            : '自动检测:取值部分重叠,疑为详略差异,可考虑合并。',
    })),
  };
}

function resetStore() {
  store.loaded = false;
  store.error = null;
  store.title = '';
  store.caseNote = '';
  Object.keys(store.sources).forEach((key) => delete store.sources[key]);
  store.artifacts.splice(0, store.artifacts.length);
  store.stats = {};
}

export async function loadStore(caseId = 'guqin') {
  resetStore();
  try {
    const res = await fetch(`/api/case-data/${caseId}`);
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
    store.title = data.case?.title || (caseId === 'quercus' ? 'Quercus Historical Flora Corpus' : 'Guqin Heritage Knowledge Revision');
    store.caseNote = data.case?.note || (caseId === 'quercus' ? 'Scanned plant books with indexed OCR and page evidence' : 'Multisource guqin books with scanned-part evidence');
    store.caseId = caseId;
    store.unalignedCount = adapted.filter((artifact) => artifact.alignmentStatus !== 'confirmed').length;
    store.stats = data.stats;
    store.loaded = true;
  } catch (err) {
    store.error = String(err);
  }
}
