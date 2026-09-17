# -*- coding: utf-8 -*-
"""探测游戏原文里颜色标记 (~r~ / ~lg~) 的语义规则，输出到文件供分析。"""
import json, io, re, collections, os, sys

BASE = r'E:\GameProject\stoneshard-wiki\data'
OUT = r'E:\GameProject\stoneshard-wiki\ssw_meta\probe_colors.txt'

rows = [json.loads(l) for l in io.open(os.path.join(BASE, 'localization.jsonl'), encoding='utf-8')]

buf = []
def w(*a):
    buf.append(' '.join(str(x) for x in a))

w('total rows:', len(rows))

# 1) 颜色标记包裹"可选数值"的模式：~X~...~/~  中间的文本
PAT = re.compile(r'~(r|lg|g|gr|w|y|bl|o|ly|p|ur|sy|cg|pr|ly)~([^~]{1,40})~/~')
colcnt = collections.Counter()
pairs = collections.Counter()   # (marker, 是否含正负号)
for r in rows:
    for lang in ('zh', 'en'):
        t = r.get(lang) or ''
        for m in PAT.finditer(t):
            mk, body = m.group(1), m.group(2)
            colcnt[(lang, mk)] += 1
            if mk in ('r', 'lg'):
                b = body.strip()
                if b.startswith('+'):
                    pairs[(mk, '+')] += 1
                elif b.startswith('-'):
                    pairs[(mk, '-')] += 1
                else:
                    pairs[(mk, 'none')] += 1

w('\n=== 标记使用次数 (按语言) ===')
for k, v in sorted(colcnt.items(), key=lambda x: -x[1]):
    w('  ', k, v)

w('\n=== r/lg 标记体内是否带正负号 ===')
for k, v in sorted(pairs.items(), key=lambda x: -x[1]):
    w('  ', k, v)

# 2) 关键反例：同一属性词在不同符号下的标记
w('\n=== 关键反例：~lg~ 配负号 / ~r~ 配正号 ===')
lg_minus, r_plus = [], []
for r in rows:
    z = r.get('zh') or ''
    for m in PAT.finditer(z):
        mk, body = m.group(1), m.group(2).strip()
        if mk == 'lg' and body.startswith('-'):
            lg_minus.append((r['key'], z[:200]))
        if mk == 'r' and body.startswith('+'):
            r_plus.append((r['key'], z[:200]))
w('\n-- ~lg~ 配负号 (绿的负数，说明"减号=好事") :', len(lg_minus))
for k, z in lg_minus[:40]:
    w('   ', k, '|', z)
w('\n-- ~r~ 配正号 (红的正数，说明"加号=坏事") :', len(r_plus))
for k, z in r_plus[:40]:
    w('   ', k, '|', z)

# 3) 收集"属性名 -> (绿/红) 出现"的映射，用于生成语义表
w('\n=== 属性词 x 标记 共现统计 (zh) ===')
LABEL = re.compile(r'([\u4e00-\u9fa5]{2,10})\s*~(r|lg|g|gr)~([^~]{1,30})~/~')
co = collections.Counter()
for r in rows:
    z = r.get('zh') or ''
    for m in LABEL.finditer(z):
        co[(m.group(1), m.group(2))] += 1
by_label = collections.defaultdict(dict)
for (lab, mk), c in co.items():
    by_label[lab][mk] = c
for lab in sorted(by_label, key=lambda x: -sum(by_label[x].values())):
    w('  ', lab, by_label[lab])

io.open(OUT, 'w', encoding='utf-8').write('\n'.join(buf))
print('OK ->', OUT, len(buf), 'lines')
