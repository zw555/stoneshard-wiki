# -*- coding: utf-8 -*-
"""在 exe 文本段里搜索"装备修饰词"渲染模板，确认游戏如何给装备词条上色。"""
import json, io, re, os, collections

DATA = r'E:\GameProject\stoneshard-wiki\data'
OUT = r'E:\GameProject\stoneshard-wiki\ssw_meta\probe_modifier_templates.txt'

buf = []
def w(*a):
    buf.append(' '.join(str(x) for x in a))

segs = []
with io.open(os.path.join(DATA, 'exe_text_segments.jsonl'), encoding='utf-8') as f:
    for l in f:
        l = l.strip()
        if not l:
            continue
        try:
            segs.append(json.loads(l))
        except Exception:
            pass
w('exe_text_segments:', len(segs))
if segs:
    w('sample keys:', list(segs[0].keys()))
    w('sample:', json.dumps(segs[0], ensure_ascii=False)[:500])

# 找一个可搜索的文本字段
def texts(seg):
    out = []
    for k, v in seg.items():
        if isinstance(v, str):
            out.append((k, v))
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, str):
                    out.append((k, x))
    return out

# A. 搜索含修饰词占位符 + 颜色标记的模板
PAT_TPL = re.compile(r'~[a-zA-Z]{1,4}~[^~]*?[+/\-][^~]*?~/~')
# B. 搜索形如 "N% #标签" 或 "标签 +N%" 且带标记的短模板
hits = collections.Counter()
found = []
for i, s in enumerate(segs):
    for k, t in texts(s):
        if '~' not in t:
            continue
        # 只要短模板（可能含占位符）
        if len(t) < 200 and re.search(r'~(r|lg|g|gr|w)~', t):
            found.append((i, k, t))

w('\n=== 含近色标记的短文本段 (最多150条) ===')
seen = set()
c = 0
for i, k, t in found:
    if t in seen:
        continue
    seen.add(t)
    if not re.search(r'\*|\$|#|/', t):
        continue
    w('  [%d/%s] %s' % (i, k, t))
    c += 1
    if c >= 150:
        break

w('\n=== 直接搜含 技/咒/精 力消耗 或 冷却时间 且带标记的段 ===')
KW = ['技能精力消耗', '咒法精力消耗', '冷却时间', '失手几率', '准度', '所受伤害']
n = 0
for i, s in enumerate(segs):
    for k, t in texts(s):
        if '~' in t and any(x in t for x in KW) and len(t) < 300:
            w('  [%d/%s] %s' % (i, k, t))
            n += 1
    if n > 200:
        break
w('  total:', n)

io.open(OUT, 'w', encoding='utf-8').write('\n'.join(buf))
print('OK ->', OUT, len(buf), 'lines')
