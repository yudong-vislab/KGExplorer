# Guqin contested-KG data schema (v0.1)

三层结构:来源记录(不可变) → 规范文物与断言槽位(合并层) → 裁定日志(追加层)。
设计原则:原文永不覆盖;所有合并/判断以标注形式叠加;来源数量开放(≥2)。

## Layer 0 — 书目注册 sources.json

```json
{
  "source_id": "qnqy",
  "title": "千年清音",
  "register": "scholarly | popular",
  "publisher": "…", "year": 2023,
  "holder_institution": "浙江省博物馆",
  "pages_dir": "corpus/qnqy/pages/",
  "ingested_at": "…"
}
```

## Layer 1 — 单书文物记录 records/{source_id}/{record_id}.json

每本书对每张琴的著录 = 一条不可变记录。字段按琴学著录分类组织。

```json
{
  "record_id": "qnqy_053",
  "source_id": "qnqy",
  "artifact_name_in_source": "松石间意",
  "page_images": ["QNQY053.jpg"],
  "md_span": { "file": "qnqy.md", "from": 1042, "to": 1108 },
  "slots": {
    "form_type":   { "raw": "仲尼式", "norm": "仲尼式" },
    "dating":      { "raw": "北宋", "norm": { "kind": "interval", "lo": 960, "hi": 1127, "label": "北宋" } },
    "dim.total_length": { "raw": "通长122.5厘米", "norm": 122.5, "unit": "cm" },
    "dim.shoulder_width": { "raw": "肩宽19.2厘米", "norm": 19.2, "unit": "cm" },
    "material.top": { "raw": "桐面", "norm": "桐" },
    "ash":          { "raw": "鹿角霜灰", "norm": "鹿角灰" },
    "lacquer":      { "raw": "通体黑漆,光亮如新", "norm": "黑漆" },
    "duanwen.top":  { "raw": "发小蛇腹断、流水断和牛毛断", "norm": ["小蛇腹断","流水断","牛毛断"] },
    "duanwen.bottom": null,
    "pools.longchi": { "raw": "长方形,有贴格,21.9×2.4厘米", "norm": { "shape": "长方形", "grid": true, "w": 21.9, "h": 2.4 } },
    "inscriptions": [
      { "loc": "琴项右侧", "script": "行书", "text": "松石间意", "attributed_to": "唐寅" },
      { "loc": "龙池右上", "script": "楷书", "attributed_to": "陈庭鹭" }
    ],
    "provenance_chain": { "raw": "苏州怡园主人顾文彬(1811-1889)所藏…" },
    "acquisition": { "raw": "1964年9月市人民法院拨交" },
    "current_holder": "重庆中国三峡博物馆"
  },
  "images": [
    { "file": "…/qinmian_01.jpg", "part": "琴面", "clip_conf": 0.92 }
  ]
}
```

要点:
- `raw` 永远保留书中原句,`norm` 是归一值;断代等模糊值用区间对象(`不晚于北宋` → `{kind:"interval", hi:1127, open_lo:true}`)。
- 断纹必须分部位(`duanwen.top` / `duanwen.bottom` / `duanwen.side`):卫中正制琴面蛇腹、底流水,混在一起会制造假冲突。
- 铭刻是列表,子结构含位置/书体/文字/归属人:行数之争(四言诗两行 vs 行草五行含落款)源于计数口径,结构上要能表达"同一处铭刻的不同描述"。

## Layer 2 — 规范文物与断言槽位 artifacts/{artifact_id}.json

```json
{
  "artifact_id": "gq_songshijianyi",
  "canonical_name": "松石间意",
  "aliases": { "gq": "松石间意", "yjzq": "松石间意", "qnqy": "松石间意" },
  "match_keys": { "holder": "三峡博物馆", "dims_fingerprint": [122.5, 113.8], "matched_by": "auto|manual" },
  "contested_slots": [
    {
      "slot": "dim.shoulder_width",
      "assertions": [
        { "record": "gq_020",   "norm": 19.2 },
        { "record": "yjzq_019", "norm": 20.7 },
        { "record": "qnqy_053", "norm": 19.2 }
      ],
      "consistency": {
        "status": "error_suspected",
        "class": "C",
        "majority": { "value": 19.2, "count": 2, "of": 3 },
        "detector": "numeric_outlier+majority",
        "belief": { "19.2": 0.91, "20.7": 0.09 }
      },
      "resolution": {
        "status": "resolved",
        "decision": 19.2,
        "decided_by": "expert:zhang",
        "decided_at": "…",
        "rationale": "两书独立记载一致;20.7疑为《一见钟琴》排印讹误",
        "llm_summary_ref": "adjudications/adj_0007.json"
      }
    }
  ],
  "consensus_slots": { "form_type": "仲尼式", "material.top": "桐" }
}
```

要点:
- 断言列表长度开放:两书=双源对峙,三书=出现多数结构(`majority`字段),外环可视化按源数分扇段。
- `class`: A 实质分歧 / B 表述差异 / C 文献讹误;`status` 更细(consensus / compatible区间兼容 / lexical措辞 / conflict / error_suspected / single_source)。
- `resolution` 为空 = 未决,进待办队列;已决则携带完整溯源(题跋)。

## Layer 3 — 裁定日志 adjudications/*.json (append-only)

```json
{
  "adj_id": "adj_0007",
  "slot_ref": "gq_songshijianyi#dim.shoulder_width",
  "action": "adopt_value | mark_compatible | merge_lexical | flag_error | keep_open",
  "evidence_cited": ["gq_020.page:Gq00020.jpg", "qnqy_053.page:QNQY053.jpg"],
  "llm_draft": "…LLM总结的修订文本…",
  "expert_final": "…专家改定的最终表述…",
  "actor": "expert:zhang", "timestamp": "…", "supersedes": null
}
```

LLM的修订建议(`llm_draft`)与专家最终定稿(`expert_final`)分开存,谁改了什么全程可查。

## 属性槽位清单(第一版)

form_type / dating / dim.{total_length, yinjian, shoulder_width, shoulder_thick, tail_width, tail_thick, forehead_width} / material.{top,bottom} / ash / lacquer / duanwen.{top,bottom,side} / pools.{longchi,fengzhao} / nayin / fittings.{hui,zhen,yueshan,yanzu} / inscriptions[] / seals[] / provenance_chain / acquisition / current_holder / sound_quality / naming_origin
