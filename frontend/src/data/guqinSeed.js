export const SOURCES = {
  gq: { id: 'gq', title: '古琴', color: '#6e5335' },
  yjzq: { id: 'yjzq', title: '一见钟琴', color: '#9a7b4f' },
  qnqy: { id: 'qnqy', title: '千年清音', color: '#b89a6a' },
  cql: { id: 'cql', title: '藏琴录', color: '#8c6d43' },
  gqjt: { id: 'gqjt', title: '古琴纪事图录', color: '#a58e63' },
};

export const CLASS_COLORS = {
  A: '#d85a30',
  B: '#ef9f27',
  C: '#7a8699',
  consensus: '#1d9e75',
  missing: '#c9cdd4',
};

export const CLASS_LABELS = {
  A: 'A · 实质分歧',
  B: 'B · 表述差异',
  C: 'C · 文献讹误',
  consensus: '一致',
  missing: '缺失',
};

export const ARTIFACTS = [
  {
    id: 'zhenyuan',
    name: '"贞元二年"款琴',
    sources: ['gq', 'yjzq', 'qnqy'],
    entities: ['仲尼式', '北宋', '三峡博物馆'],
    slots: [
      {
        id: 'dating', label: '断代', cls: 'A',
        assertions: [
          { source: 'gq', raw: '经鉴定组鉴定,此琴不晚于北宋,很可能更早。' },
          { source: 'yjzq', raw: '北宋仲尼式"贞元二年"七弦琴。' },
          { source: 'qnqy', raw: '北宋仲尼式"贞元二年"七弦琴。' },
        ],
        belief: [{ value: '北宋', p: 0.62 }, { value: '早于北宋(唐?)', p: 0.38 }],
        note: '腹款"贞元二年"为唐德宗年号(786),与两书"北宋"定断存在张力。',
      },
      {
        id: 'lacquer', label: '漆色', cls: 'B',
        assertions: [
          { source: 'gq', raw: '通体糙黑漆,漆皮炭化严重。' },
          { source: 'yjzq', raw: '通体黑紫色漆,流水断。' },
          { source: 'qnqy', raw: null },
        ],
        belief: [{ value: '黑漆系(疑同义)', p: 0.85 }, { value: '实质不同', p: 0.15 }],
        note: '糙黑漆与黑紫色漆疑为同一漆面在不同观察下的表述,建议归一。',
      },
    ],
  },
  {
    id: 'fengming',
    name: '"凤鸣"琴',
    sources: ['gq', 'yjzq', 'qnqy'],
    entities: ['伶官式', '北宋', '三峡博物馆'],
    slots: [
      {
        id: 'inscription_lines', label: '铭刻行数', cls: 'B',
        assertions: [
          { source: 'gq', raw: '其下阴刻行草四言诗两行。' },
          { source: 'yjzq', raw: '其下阴刻行草四言诗两行:"凤皇来仪,鸣于高冈…"' },
          { source: 'qnqy', raw: '其下阴刻行草五行:"凤皇来仪,鸣于高冈。文章璨黉,其道大光。景祐元年春日,清跸堂主人题。"款文为"王元颖印"。' },
        ],
        belief: [{ value: '同一铭刻,计行口径不同', p: 0.9 }, { value: '记载矛盾', p: 0.1 }],
        note: '《千年清音》把落款计入行数(五行);其余按诗文计(两行)。口径差异,非事实分歧。',
      },
    ],
  },
  {
    id: 'weizhongzheng',
    name: '"卫中正制"琴',
    sources: ['gq', 'yjzq', 'qnqy'],
    entities: ['仲尼式', '北宋', '三峡博物馆'],
    slots: [
      {
        id: 'inscription_body', label: '腹款记载', cls: 'B',
        assertions: [
          { source: 'gq', raw: '龙池内纳音左侧阴刻楷书"宋庆历道士卫中正制"。' },
          { source: 'yjzq', raw: '其腹题云:"庆历五年臣道士卫中正奉圣旨研,崇宁四年臣马熙先奉圣旨重修"。' },
          { source: 'qnqy', raw: '龙池内纳音左侧阴刻楷书"宋庆历道士卫中正制"。' },
        ],
        belief: [{ value: '两处铭刻并存', p: 0.7 }, { value: '同一铭刻异录', p: 0.3 }],
        note: '《一见钟琴》所引腹题内容更长且含重修记录,疑引自文献而非琴身;待考。',
      },
    ],
  },
  {
    id: 'songshijianyi',
    name: '"松石间意"琴',
    sources: ['gq', 'yjzq', 'qnqy'],
    entities: ['仲尼式', '北宋', '三峡博物馆'],
    slots: [
      {
        id: 'shoulder_width', label: '肩宽', cls: 'C',
        assertions: [
          { source: 'gq', raw: '肩宽19.2厘米。' },
          { source: 'yjzq', raw: '肩宽20.7厘米。' },
          { source: 'qnqy', raw: '肩宽19.2厘米。' },
        ],
        belief: [{ value: '19.2 cm', p: 0.91 }, { value: '20.7 cm', p: 0.09 }],
        note: '两源独立记载19.2;20.7疑为《一见钟琴》排印讹误。',
      },
      {
        id: 'inscriber', label: '题刻人名', cls: 'C',
        assertions: [
          { source: 'gq', raw: '落款者……陈庭鹭等。' },
          { source: 'yjzq', raw: '落款者……程庭鹭等。' },
          { source: 'qnqy', raw: '落款者……陈庭鹭等。' },
        ],
        belief: [{ value: '程庭鹭(清代画家,有据可查)', p: 0.66 }, { value: '陈庭鹭', p: 0.34 }],
        note: '程庭鹭为清代著名画家;多数记载反而作"陈"。多数印证与外部知识冲突,典型待考例。',
      },
    ],
  },
  {
    id: 'laihuang',
    name: '"来凰"琴',
    sources: ['qnqy', 'cql'],
    entities: ['仲尼式', '唐', '浙江省博物馆'],
    slots: [
      {
        id: 'forehead_width', label: '额宽', cls: 'C',
        assertions: [
          { source: 'qnqy', raw: '额宽5.8厘米。' },
          { source: 'cql', raw: '额宽15.8厘米。' },
        ],
        belief: [{ value: '15.8 cm', p: 0.8 }, { value: '5.8 cm', p: 0.2 }],
        note: '琴额宽度5.8cm与通长120.4cm比例失衡,疑脱"1";领域规则触发。',
      },
      {
        id: 'inscription_punct', label: '铭文断句', cls: 'B',
        assertions: [
          { source: 'qnqy', raw: '庚戌春予得鸣凤,为怡府二十四琴斋物,后得廿余琴…' },
          { source: 'cql', raw: '庚戌春,予得鸣凤为怡府二十四琴斋物,后得廿余琴…' },
        ],
        belief: [{ value: '断句差异,文本同源', p: 0.95 }, { value: '实质差异', p: 0.05 }],
        note: '同一铭文的不同标点转写。',
      },
    ],
  },
  {
    id: 'caifeng',
    name: '"彩凤鸣岐"琴',
    sources: ['qnqy', 'cql'],
    entities: ['落霞式', '唐', '浙江省博物馆'],
    slots: [
      {
        id: 'duanwen', label: '断纹描述', cls: 'B',
        assertions: [
          { source: 'qnqy', raw: '琴背冰裂纹断兼小流水断,三、四、五徽部位隐见类似梅花断的小圆圈。' },
          { source: 'cql', raw: '琴背以栗壳色原漆为主,有冰裂断兼小流水断。三、四、五徽部位隐见类似梅花断的小圆圈。' },
        ],
        belief: [{ value: '描述同源,详略不同', p: 0.92 }, { value: '实质差异', p: 0.08 }],
        note: '两书描述高度相似,《藏琴录》多漆色细节;疑存在承袭关系。',
      },
    ],
  },
  {
    id: 'jiuxiao',
    name: '"九霄环佩"琴',
    sources: ['qnqy', 'gqjt'],
    entities: ['伏羲式', '唐', '故宫博物院'],
    slots: [],
  },
];

export function worstClass(artifact) {
  if (!artifact.slots.length) return 'consensus';
  if (artifact.slots.some((s) => s.cls === 'A')) return 'A';
  if (artifact.slots.some((s) => s.cls === 'C')) return 'C';
  if (artifact.slots.some((s) => s.cls === 'B')) return 'B';
  return 'consensus';
}
