# l4d2-addons

把《求生之路2》(Left 4 Dead 2) 的创意工坊 mod 库整理成**可读、可查、不重复**的样子。

一个 **Agent Skill**：装进 DSH / Claude Code 之类的 agent 后，
你跟它说「整理我的 L4D2 mod」，它会自己把整套工具链铺好，然后按规则干活。

[English README](README.en.md) · [贡献指南](CONTRIBUTING.md)

---

## 它解决什么问题

从创意工坊订阅的 mod 落到硬盘上，文件名是一串数字：`3778253592.vpk`。
装了几百个之后，你既不知道哪个文件是什么，也不知道**哪些 mod 在抢同一个位置**（装了两个 Hunter 替换件，只有一个会生效）。

这个 skill 做四件事：

1. **摸清每个 mod 到底替换了什么** —— 自己解析 VPK 二进制，取出内部全部资源路径，而不是靠文件名猜
2. **按 `分类-替换对象-原标题` 重命名**，17 个分类前缀（`生还者-` `特感-` `主武器-` `近战-` `材质-` `脚本-` …）
3. **找出真冲突并留新移旧** —— 同一替换对象下多个 mod，按工坊 `time_updated` 保留较新的，旧的移进 `mod备份\`
4. **生成《可MOD替换物品总表》xlsx** —— 16 张表，逐个物件标注「已替换 / 未替换 / 仅地图包附带」，以及替换它的具体 mod

## 快速开始

首次调用时 skill 会问你三件事（**只需一次**）：

- 《求生之路2》的 `left4dead2\addons` 目录
- `workshop` 暂存目录（默认就在 addons 下面，多数人不用改）
- 工作目录（默认当前目录）

然后它会自动生成 `config.json`、把脚本铺好、渲染一个 `刷新表格.bat`、并跑出第一版 xlsx。
之后**双击 `刷新表格.bat` 就能重扫刷新**，不必再找 AI。

```
<workDir>\
  config.json
  刷新表格.bat                      ← 双击即可重扫刷新
  求生之路2_可MOD替换物品总表.xlsx     ← 16 张表
  _work\                            ← 全部脚本 + 中间产物
```

## 设计要点

- **置信度分层**：判定分 `S1 地图 → S2 物件域 → S3 物件域·贴图类 → S4 资源类型 → S5 保留原前缀` 五步。
  低置信时**保留人工前缀并列入待复核，绝不静默猜**。
- **幂等**：在已整理好的库上重跑，提出 **0 条改动**。
- **规则例外可持久化**：你拍板过的取舍写进 `name_exempt.json`，重跑不会推回去。
- **不靠文件名猜冲突**：冲突判定走「VPK 真实路径 → 标签 → 表格行」这条链路；
  文件名扫描器只作辅助（落到资源类型前缀的 mod 中段为空，文件名扫描器判不了）。
- **不含任何用户数据**：白名单、例外表、批次、扫描结果、xlsx 全在 `.gitignore` 里，
  仓库只有工具与文档。

## 目录结构

```
l4d2-addons/
  SKILL.md                    agent 读的入口：首次引导 + 标准流程 + 工具箱
  README.md / README.en.md    中英文说明
  CONTRIBUTING.md             贡献指南 —— 含 10 条硬不变量（踩过坑才写下的）
  LICENSE                     MIT
  install.ps1                 安装到 DSH 的 skill 目录
  .gitignore / .gitattributes / .editorconfig
  reference/
    naming-rules.md           分类命名规范全文（判据、邻接标签、横切行、上位名、规则例外）
    xlsx-pipeline.md          表格生成链路 + 4 条硬不变量
    vpk-format.md             VPK 二进制格式要点
    steam-api.md              工坊 API、.url 格式、取消全部订阅
    pitfalls.md               Windows / PowerShell 5.1 / 中文编码 环境坑
  scripts/                    全部可执行工具（路径全部由 config.json 驱动）
```

## 手动安装

```powershell
powershell -File install.ps1
```

默认装到 `$env:DSH_HOME\skills\l4d2-addons`（缺省 `~\.dsh\skills\l4d2-addons`），
也可用 `-Dest "<目录>"` 指定。装完在 agent 里说一句「整理我的 L4D2 mod」即可。

## 自测

```powershell
python scripts\self_test.py
```

在一个**临时目录**里模拟「全新用户 + 空库」，走完 9 个阶段：bootstrap 生成工作区 →
造 3 个假 VPK → 空库刷新 → 扫 workshop 暂存件 → 搬迁（干跑+执行）→ 三件校验 →
再刷新 → 命名幂等（需改名 0）→ 冲突扫描与全部校验脚本。

**完全不碰你的真实 mod 库**；某一阶段失败时会保留临时目录供排查。改任何脚本前先跑它。

## 环境要求

- Windows（脚本用到 robocopy / 批处理 / PowerShell）
- Python 3.10+，**需要 `openpyxl`**
- Node.js 18+
- `config.json` 里的路径按 **环境变量 → config.json → 内置默认** 三级解析，
  也可用 `L4D2_HOME` / `L4D2_ADDONS` / `L4D2_XLSX_OUT` / `L4D2_MIRROR` 临时覆盖

## 许可

MIT —— 见 [LICENSE](LICENSE)。
