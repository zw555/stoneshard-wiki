# Stoneshard 中文资料库

一个为《Stoneshard（紫色晶石）》自建的中文资料库：**全部文本直接从游戏本体逆向提取**，配以游戏内图标，构建成纯静态站点。

- **在线站点**：<https://stoneshard-wiki-cn.app.workbuddy.host/>
- **游戏版本**：Steam 正式版（v0.9.4.24）

## 页面一览

| 页面 | 内容 |
|---|---|
| `index.html` | 全文双语搜索（16,363 条词条，客户端即时搜索） |
| `items.html` | 物品图鉴：2,074 条（1,767 物品 + 301 技能 + 6 法术），687 条带伤害/属性/耐久/价格数值 |
| `skills.html` | 技能树：29 个技能系 / 238 个技能节点 / 70 本解锁文献 |
| `enemies.html` | 敌人图鉴：236 个敌人的 HP、三维、抗性等 |
| `trade.html` | 交易行情：697 件装备的收购商人排行与价格 |
| `icons.html` | 图标库：可搜索 |

属性数值配色**完全依据游戏自己的标记**（`~lg~` 增益绿 / `~r~` 减益红），而非正负号——因此「失手几率 -12%」显示为绿色、「冷却时间 -3%」也是绿色，与游戏内一致。

## 快速开始

不需要安装任何东西，仓库里的 `site_deploy/` 就是完整成品（约 15 MB，含 2,074 个图标）：

```bash
cd site_deploy
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

直接双击 `index.html` 也能用（全部数据内嵌在页面里），但部分浏览器对 `file://` 下的功能有限制，推荐起个本地服务。

## 从零重建

若想自己跑一遍提取管线（例如游戏更新后刷新数据，或想得到全量 17,247 个图标）：

**依赖**：Python 3.8+，`pip install Pillow`（仅 `extract_sprites.py` 需要）。Node.js 仅用于运行冒烟测试，非必需。

**指定游戏目录**：脚本会自动探测常见 Steam 库路径，找不到时用环境变量显式指定：

```bash
# Windows (PowerShell)
$env:STONESHARD_DIR = "D:\SteamLibrary\steamapps\common\Stoneshard"
# Linux
export STONESHARD_DIR="$HOME/.steam/steam/steamapps/common/Stoneshard"
```

在 Steam 里：右键游戏 → 管理 → 浏览本地文件，即可看到该目录（需含 `data.win` 与 `StoneShard.exe`）。

**执行管线**（顺序执行，`tools/` 目录下）：

```bash
python tools/dump_strg.py              # data.win 的 STRG 块 -> data/strings.json (42,825 条资源名)
python tools/extract_exe_text.py       # StoneShard.exe 多语言文本段 -> data/exe_text_segments.jsonl
python tools/build_localization.py     # 结构化 -> data/localization.jsonl (16,363 条)
python tools/extract_sprites.py        # 解码 QOIZ 纹理 -> data/sprites.json + site/icons/ (17,247 个)
python tools/build_stat_polarity.py    # 属性极性表 -> data/stat_polarity.json
python tools/build_linkage.py          # 文本 x 图标关联 -> data/items.json + site/items.html
python tools/build_skills.py           # -> site/skills.html
python tools/build_icons_gallery.py    # -> site/icons.html
python tools/build_site.py             # 注入共享导航（含 enemies）
python tools/build_deploy.py           # 生成精简发布版 site_deploy/
```

**两个已知限制**：

1. `trade.html` 与 `parse_community_equipment.py` 依赖社区 wiki 的 697 个装备详情页（`data/ssw_pages/`，体积原因未入库，也没有收录抓取脚本）。不过成品页已在 `site_deploy/` 里，对应数据在 `data/community_trade_category_matrix.json`。
2. 游戏是 **YYC 编译**，GML 逻辑以原生机器码存在，无法反编译。物品数值来自 [stoneshardwiki.com](https://www.stoneshardwiki.com) 社区数据（版本与正式版一致）。

## 数据说明

| 文件 | 内容 |
|---|---|
| `data/strings.json` | data.win STRG 块全部字符串（资源名为主） |
| `data/localization.jsonl` | 游戏全部本地化文本（含官方简中），16363 条双语 |
| `data/sprites.json` / `sprites_frames.json` | 17,247 个精灵的元数据与全部 155,081 帧坐标 |
| `data/items.json` | 文本与图标关联后的物品条目（含数值） |
| `data/stat_polarity.json` | 属性极性表：某属性 +N/-N 是增益还是减益（依据游戏原文标记） |
| `data/community_*.json` | 来自 stoneshardwiki.com 的社区数据（敌人/技能树/交易/外观等） |

## 技术要点

游戏文本**不在** `data.win` 里，而在 `StoneShard.exe` 内（YYC 编译），以分号分隔的 12 语言链存储；图标则在 `data.win` 的自定义 **QOIZ** 纹理容器里（魔数 `2zoq` + bzip2 + GameMaker 变体 QOI，操作码与标准 QOI 不同）。相关实现见 `tools/extract_exe_text.py` 与 `tools/extract_sprites.py`，注释里记录了全部格式细节。

`tools/_smoke_dialog.mjs` 是一个不依赖测试框架的冒烟测试（Node 直连 Chromium 调试协议），覆盖弹窗交互、滚动保持与数值配色共 18 项断言。

## 版权与使用范围

- 本项目为**个人兴趣的非官方资料整理**，与 [Ink Stains Games](https://store.steampowered.com/app/625960/Stoneshard/) 无任何关联，也不是替代品。请支持正版。
- 页面与 `site_deploy/` 中包含的**游戏文本与美术素材**（图标等）版权归 **Ink Stains Games** 所有；本仓库**不含任何发行商发布的原始资源文件**，`tools/` 仅提供从用户自己已购买的游戏本体中提取数据的能力。
- 数值、价格、配方等事实性数据不受著作权保护；技能树结构整理与代码为本项目自有成果。
- 第三方数据（`data/community_*.json`、`data/ssw_pages/`）来自 [stoneshardwiki.com](https://www.stoneshardwiki.com)，感谢其整理工作。
- 本项目**禁止用于商业用途**（不收费、无广告、无赞助）。若权利人认为有任何内容侵犯其权益，请提出，我会立即处理。

## 目录结构

```
stoneshard-wiki/
├── tools/          # 提取与构建管线（本项目核心）
├── data/           # 提取产物与数据集（JSON/JSONL）
├── site/           # 完整构建产物（全量图标，未入库）
├── site_deploy/    # 精简发布版（已入库，即线上站点）
└── ssw_meta/       # 验证截图、探针输出
```

大体积、可由 `tools/` 重新生成的中间产物（原始纹理图集、抓取缓存、全量图标）见 `.gitignore`。
