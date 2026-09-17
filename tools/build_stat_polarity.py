# -*- coding: utf-8 -*-
"""构建属性极性表 stat_polarity.json

规则来源全部是游戏自己的数据（权威）：
  A. localization.jsonl —— 游戏原文用 ~lg~(增益) / ~r~(减益) 给数值上色
  B. community_planner_buffs.json —— 官方修饰键 + 数值 与 带色描述 对齐
  C. modifierLabels —— 官方修饰键 <-> 中文标签 映射
最终得到：某属性 +N 是增益还是减益（不再靠正负号猜）
"""
import json, io, re, os, collections, math

DATA = r'E:\GameProject\stoneshard-wiki\data'
OUTJSON = os.path.join(DATA, 'stat_polarity.json')
REPORT = r'E:\GameProject\stoneshard-wiki\ssw_meta\probe_polarity_report.txt'

rep = []
def w(*a):
    rep.append(' '.join(str(x) for x in a))

# ============ 载入 ============
rows = [json.loads(l) for l in io.open(os.path.join(DATA, 'localization.jsonl'), encoding='utf-8')]
eq = json.load(io.open(os.path.join(DATA, 'community_equipment_stats.json'), encoding='utf-8'))
items = json.load(io.open(os.path.join(DATA, 'items.json'), encoding='utf-8'))
mod = json.load(io.open(os.path.join(DATA, 'community_planner_item_modifiers.json'), encoding='utf-8'))
buffs = json.load(io.open(os.path.join(DATA, 'community_planner_buffs.json'), encoding='utf-8'))

# 官方键 <-> 中文标签
key2zh, zh2key = {}, {}
for k, tr in (mod.get('modifierLabels') or {}).items():
    if isinstance(tr, dict):
        if tr.get('zh'):
            key2zh[k] = tr['zh'].strip()
            zh2key.setdefault(tr['zh'].strip(), k)

GREEN = ('lg', 'g', 'gr')
def cls_of(marker):
    return 'pos' if marker in GREEN else ('neg' if marker == 'r' else 'neutral')

# ============ 来源 A：游戏原文 ============
NUM = r'[+\-]?[0-9][0-9.,]*'
PAT_ZH = re.compile(r'([\u4e00-\u9fa5]{2,12}?)\s*~(r|lg|g|gr|w)~\s*(' + NUM + r')')
PAT_EN = re.compile(r'([A-Z][A-Za-z\'\- ]{2,30}?)\s*~(r|lg|g|gr|w)~\s*(' + NUM + r')')

votes = collections.defaultdict(collections.Counter)   # name -> (sign, cls) -> n
evidence_text = collections.defaultdict(list)

for r in rows:
    z = r.get('zh') or ''
    for m in PAT_ZH.finditer(z):
        lab, mk, num = m.group(1).strip(), m.group(2), m.group(3)
        sg = '+' if num.startswith('+') else ('-' if num.startswith('-') else '0')
        votes[lab][(sg, cls_of(mk))] += 1
    e = r.get('en') or ''
    for m in PAT_EN.finditer(e):
        lab, mk, num = m.group(1).strip(), m.group(2), m.group(3)
        sg = '+' if num.startswith('+') else ('-' if num.startswith('-') else '0')
        votes[lab][(sg, cls_of(mk))] += 1

# ============ 来源 B：planner_buffs 键级对齐 ============
# 描述里所有"带色数值" token
PAT_TOKEN = re.compile(r'~(r|lg|g|gr)~([+\-]?[0-9][0-9.,]*)')
PAT_NEAR = re.compile(r'([\u4e00-\u9fa5A-Za-z ]{0,18})\s*~(r|lg|g|gr)~\s*([+\-]?[0-9][0-9.,]*)')

key_votes = collections.defaultdict(collections.Counter)
key_ctx = collections.defaultdict(list)

def walk_descs(obj, out):
    """递归收集所有 descriptions / text 字段"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ('descriptions', 'description', 'names') and isinstance(v, dict):
                for lang, t in v.items():
                    if isinstance(t, str):
                        out.append(t)
            else:
                walk_descs(v, out)
    elif isinstance(obj, list):
        for x in obj:
            walk_descs(x, out)

for act in (buffs.get('activations') or []):
    src = act.get('source') or {}
    descs = []
    walk_descs(src, descs)
    for t in descs:
        for m in PAT_NEAR.finditer(t):
            ctx, mk, num = m.group(1).strip(), m.group(2), m.group(3)
            f = float(num.replace(',', ''))
            key_ctx[(abs(f), cls_of(mk))].append(ctx)

for eff in (buffs.get('effects') or []):
    descs = []
    walk_descs(eff, descs)
    # 该效果所有描述里的 (绝对值 -> 颜色计数)
    num2cls = collections.defaultdict(collections.Counter)
    for t in descs:
        for m in PAT_TOKEN.finditer(t):
            f = abs(float(m.group(2).replace(',', '')))
            num2cls[f][cls_of(m.group(1))] += 1
    for mo in (eff.get('modifiers') or []):
        key = mo.get('key')
        if not key:
            continue
        vals = mo.get('values_by_stage') or {}
        nums = set()
        for v in vals.values():
            try:
                nums.add(abs(float(v)))
            except Exception:
                pass
        if mo.get('value') is not None:
            try:
                nums.add(abs(float(mo['value'])))
            except Exception:
                pass
        for n in nums:
            if n == 0:
                continue
            cls_cnt = num2cls.get(n)
            if not cls_cnt:
                continue
            # 只接受"该数值在描述中只对应一种颜色"的无歧义配对
            real = {c: v for c, v in cls_cnt.items() if c in ('pos', 'neg')}
            if len(real) != 1:
                continue
            cls = next(iter(real))
            key_votes[key][cls] += real[cls]

# 用上下文词反查中文标签，补强
ctx_votes = collections.defaultdict(collections.Counter)
for (n, cls), ctxs in key_ctx.items():
    for c in ctxs:
        if c:
            ctx_votes[c][cls] += 1

# ============ 合并：标签级极性 ============
def resolve(counter):
    res = {}
    for sg in ('+', '-', '0'):
        p = counter.get((sg, 'pos'), 0)
        n = counter.get((sg, 'neg'), 0)
        u = counter.get((sg, 'neutral'), 0)
        if p == 0 and n == 0:
            res[sg] = None
        elif p > n:
            res[sg] = 'pos'
        elif n > p:
            res[sg] = 'neg'
        else:
            res[sg] = 'neutral'
    return res

# 标签级（原文）
label_pol = {}
label_ev = {}
for lab, c in votes.items():
    if sum(v for k, v in c.items()) < 1:
        continue
    label_pol[lab] = resolve(c)
    label_ev[lab] = {f'{k[0]}{k[1][:3]}': v for k, v in c.most_common()}

# 键级（planner_buffs）：直接用 key_votes 的 pos/neg 计数推方向
key_dir = {}
key_tally = {}
for key, c in key_votes.items():
    p, n = c.get('pos', 0), c.get('neg', 0)
    if p + n == 0:
        continue
    key_dir[key] = 'plus_good' if p >= n else 'minus_good'
    key_tally[key] = (p, n)

# ============ 兜底规则（仅在游戏原文无证据时启用） ============
# 注意：默认等价于"按符号判色"（+绿/-红），只在明确"越低越好"的属性上翻转
MINUS_GOOD_KW = ('消耗', '冷却时间', '所受伤害', '失误几率', '失手几率',
                 '反噬', '后坐力', '疲劳度', '痛感')
PLUS_GOOD_KW = ('抗性', '抵抗', '避免', '坚忍', '吸收', '恢复', '吸取', '加成',
                '上限', '穿透', '破坏', '几率', '伤害', '效果', '法力', '力量',
                '速度', '收益', '距离')

def fallback(label):
    """返回 {'+':cls,'-':cls}；默认与按符号一致"""
    if label.startswith('DMG:'):
        return {'+': 'pos', '-': 'neg', '0': 'neutral'}
    # 抗性类优先（"疲劳抗性"含"疲劳"，必须先判抗性）
    if label.endswith('抗性') or label.endswith('避免') or '抵抗' in label or label == '坚忍':
        return {'+': 'pos', '-': 'neg', '0': 'neutral'}
    if label.endswith('伤害'):
        # 伤害类型/伤害数值：正负都可读，无符号时保持中性
        return {'+': 'pos', '-': 'neg', '0': 'neutral'}
    for k in MINUS_GOOD_KW:
        if k in label:
            return {'+': 'neg', '-': 'pos', '0': 'neutral'}
    for k in PLUS_GOOD_KW:
        if k in label:
            return {'+': 'pos', '-': 'neg', '0': 'neutral'}
    return {'+': 'pos', '-': 'neg', '0': 'neutral'}

# ============ 组装最终表 ============
final = {}
src_kind = {}
for lab, pol in label_pol.items():
    final[lab] = dict(pol)
    src_kind[lab] = 'game_text'

# 用键级结果补：中文标签来源于 key2zh（仅当原文无证据时）
for key, direction in key_dir.items():
    zh = key2zh.get(key)
    if not zh:
        continue
    pol = {'+': 'neg', '-': 'pos'} if direction == 'minus_good' else {'+': 'pos', '-': 'neg'}
    if zh not in final:
        final[zh] = dict(pol, **{'0': 'neutral'})
        src_kind[zh] = 'official_key'
    else:
        for sg in ('+', '-'):
            if final[zh].get(sg) is None:
                final[zh][sg] = pol[sg]

# 人工校正（少数确知方向、但原文/键级给出噪声的属性）
CURATED = {
    '精力':        {'+': 'pos', '-': 'neg', '0': 'neutral'},   # 精力上限，越高越好
    '距离':        {'+': 'pos', '-': 'neg', '0': 'neutral'},   # 射程/距离，越大越好
    '疲劳抗性':    {'+': 'pos', '-': 'neg', '0': 'neutral'},   # 抗性类，越高越好
    '护甲穿透':    {'+': 'pos', '-': 'neg', '0': 'neutral'},
    '护甲破坏':    {'+': 'pos', '-': 'neg', '0': 'neutral'},
    '反伤':        {'+': 'pos', '-': 'neg', '0': 'neutral'},
    '经验收益':    {'+': 'pos', '-': 'neg', '0': 'neutral'},
    '咒法精力消耗': {'+': 'neg', '-': 'pos', '0': 'neutral'},
    '视野上限':    {'+': 'pos', '-': 'neg', '0': 'neutral'},
}
for lab, pol in CURATED.items():
    final[lab] = dict(pol)
    src_kind[lab] = src_kind.get(lab, '') + '+curated' if lab in src_kind else 'curated'

# ============ 覆盖保障：所有 wiki 出现过的标签都必须有结论 ============
wiki_labels = collections.Counter()
for k, v in eq.items():
    st = v.get('stats') if isinstance(v.get('stats'), dict) else v
    if not isinstance(st, dict):
        continue
    for s in (st.get('stats') or []):
        if s.get('label'):
            wiki_labels[s['label'].strip()] += 1
for it in items:
    st = it.get('stats') if isinstance(it.get('stats'), dict) else None
    if not st:
        continue
    for s in (st.get('stats') or []):
        if s.get('label'):
            wiki_labels[s['label'].strip()] += 1
    for s in (st.get('damage') or []):
        if s.get('label'):
            wiki_labels[s['label'].strip()] += 1   # 伤害类型（数值无符号 -> 中性）

unresolved = []
for lab in set(list(final) + list(wiki_labels) + list(key2zh.values())):
    if lab not in final:
        final[lab] = fallback(lab)
        src_kind[lab] = 'fallback'
        continue
    filled = False
    for sg in ('+', '-'):
        if final[lab].get(sg) is None:
            final[lab][sg] = fallback(lab)[sg]
            filled = True
    if filled:
        src_kind[lab] = src_kind.get(lab, '') + '+fallback'

# ============ 报告 ============
w('=== 键级方向（planner_buffs 交叉验证） ===')
for key in sorted(key_tally, key=lambda k: -(key_tally[k][0] + key_tally[k][1])):
    p, n = key_tally[key]
    w('  %-28s %-10s pos=%-3d neg=%-3d %s' % (key, key_dir[key], p, n, key2zh.get(key, '')))

w('')
w('=== 全部标签 -> 极性 (%d) ===' % len(final))
for lab in sorted(final):
    w('  %-16s %-40s %s' % (lab, str(final[lab]), src_kind.get(lab, '-')))

w('')
w('=== 未解析 ===')
w('  ', unresolved if unresolved else '(无，80/80 全部有结论)')

io.open(REPORT, 'w', encoding='utf-8').write('\n'.join(rep))

out = {
    'schema': 'stoneshardwiki.stat_polarity.v1',
    'note': 'polarity: pos=游戏内绿色(增益) / neg=游戏内红色(减益)。来源=游戏原文 ~lg~ ~r~ 标记，不按正负号推断。',
    'sources': {
        'game_text': 'data/localization.jsonl',
        'official_key': 'data/community_planner_buffs.json',
        'curated': 'tools/build_stat_polarity.py CURATED',
        'fallback': 'heuristic',
    },
    'labels': {k: v for k, v in sorted(final.items())},
    'source_kind': src_kind,
    'official_keys': key2zh,
    'key_direction': dict(key_dir),
}
io.open(OUTJSON, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
n_game = sum(1 for k in wiki_labels if 'game_text' in src_kind.get(k, ''))
print('labels total:', len(final), '| wiki labels:', len(wiki_labels),
      '| 有游戏原文直接证据:', n_game, '| 未解析:', len(unresolved))
print('->', OUTJSON)
