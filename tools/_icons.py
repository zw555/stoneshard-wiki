# -*- coding: utf-8 -*-
"""site/icons 文件名解析：大小写敏感环境下的正确性保障。

Windows 的 os.path.exists / 文件写入对大小写不敏感，会把「引用名与磁盘实际文件名
大小写不一致」这类问题完全掩盖住（文件看起来存在、复制也不报错）；而线上站点运行在
Linux（大小写敏感），引用名对不上就是 404、图标空白。

历史案例：trade 页 79 个、enemies 页 3 个图标的引用名是全小写，磁盘上是驼峰命名
（s_inv_bagel.png vs s_inv_Bagel.png）。

用法：
    from _icons import icon_index, real_name
    idx = icon_index(SITE)
    ic = real_name("s_inv_bagel.png", idx)      # -> "s_inv_Bagel.png"
"""
import os


def icon_index(site):
    """小写文件名 -> 磁盘上的真实文件名。"""
    idx = {}
    d = os.path.join(site, "icons")
    if not os.path.isdir(d):
        return idx
    for n in os.listdir(d):
        idx.setdefault(n.lower(), n)
    return idx


def real_name(name, idx):
    """把引用名纠正为磁盘真实文件名；查不到就原样返回（交给调用方处理缺失）。"""
    if not name:
        return name
    return idx.get(name.lower(), name)


def mismatches(names, idx):
    """返回 names 里大小写写错的那些引用名（审计/守卫用）。"""
    out = []
    for n in names:
        real = idx.get((n or "").lower())
        if real and real != n:
            out.append(n)
    return out
