---
name: l4d2-addons
description: Left 4 Dead 2（求生之路2）mod 库整理工作流：把创意工坊订阅的 VPK 归纳进 left4dead2\addons 并按「分类-替换对象-原标题」重命名、按替换对象做冲突留新移旧、生成并刷新《求生之路2_可MOD替换物品总表.xlsx》与「刷新表格.bat」。当用户提到 求生之路2 / L4D2 / left4dead2 的 addons、workshop、mod 整理、mod 重命名、mod 冲突、mod 总表、替换物品表、取消工坊订阅时使用。
---

# L4D2 mod 库整理

把「一个 mod 文件 → 一个可读的名字 + 一个工坊快捷方式」做成**可重复、可复核、幂等**的流程。

**核心思路**：不靠文件名猜，而是**解出每个 VPK 的真实资源路径**，用它反推这个 mod 替换了什么；
再按 `S1 地图 → S2 物件域 → S3 物件域·贴图类 → S4 资源类型 → S5 低置信保留原前缀` 五步定分类前缀。
低置信时**保留人工前缀并列入待复核，绝不静默猜**。

> **📖 读文档的顺序**（省 token 的关键）：本文件 = **流程骨架**；判据细节在 `reference\`，**用到哪份读哪份**，
> 不要一次性全读。`reference\toolbox.md` 是工具箱全表（按需查）。

---

## 0. 首次调用必做：定位 / 生成工作目录

```powershell
python <skill>\scripts\bootstrap.py --show
```

⚠️ **无论记忆里是否已有「这台机器配置过」的信息，每次调用都必须真的跑一次** —— 配置可能已过期
（换硬盘、重装 Steam、改目录）。**以 `--show` 的返回字段为准，不要自己猜**：

| 字段 | 含义 |
|---|---|
| `needAsk` | **要问用户的清单，以它为准。** 全新安装 = `workDir` + `addonsDir` + `workshopDir`；已配置过 = 空数组 |
| `workDir` | **照当前参数跑下去、产物会落在哪** |
| `pointerWorkDir` | 本机**已配置过**的工作目录 |
| `pointerDiffersFromCwd` | 上面那个目录**是否与当前会话目录不同**；`true` → **必须问一句** |

**判定**：`known.cwdConfig` 有值 → 直接用；`pointerConfig` 有值且 `pointerDiffersFromCwd=false` → 直接用；
`pointerDiffersFromCwd=true` → **必须问**（默认 workDir = 用户正在对话的目录，用户期待产物出现在那里）；
两者都空 → 按 `needAsk` 问，然后 bootstrap。

`pointerDiffersFromCwd=true` 时的问法与分支：

```
检测到本机已有一份配置：
  workDir   = D:\work\L4D2      ← 不是你现在这个目录
  addonsDir = D:\Steam\…\left4dead2\addons
本次整理用哪个目录？产物（xlsx / 刷新表格.bat / _work\）会放在那里。
  A) 当前会话目录 （推荐）→ 新建一份配置，addons 路径沿用上面那个，不用你重填
  B) 用上面那个 workDir → 产物继续落在 D:\work\L4D2
```

- 选 **A** → `bootstrap.py --workdir "<当前目录>" --addons "<上面那个 addonsDir>"`（**不要重问 addons 路径**）
- 选 **B** → 按指针那个 workDir 干，别再问
- 用户说过「以后都放某个固定目录」→ 记下来，之后不再问

**无论走哪条分支，最后都要把解析结果回报给用户**（`workDir` / `addonsDir` / `workshopDir` 三行），
让他一眼能发现「指到别的盘 / 旧安装」；**指错了就重跑 bootstrap（加 `--force`）或改 `config.json`**。
不要只说一句「已找到配置」就往下干。

首次调用要问的三项（一次问完）：① **addons 目录**（提示：Steam 库右键游戏 → 管理 → 浏览本地文件 → `left4dead2\addons`）
② **workshop 暂存目录**（默认 `<addons>\workshop`，多数人不用改）③ **工作目录**（默认当前 AI 工作目录，问一句要不要换）。

```powershell
python <skill>\scripts\bootstrap.py --workdir "<workDir>" --addons "<addonsDir>" [--workshop "<dir>"]
```

bootstrap 自动做完：写 `config.json` → 铺脚本进 `<workDir>\_work\` → 渲染 `刷新表格.bat` → **跑一次刷新产出 xlsx**
→ 记全局指针 `%USERPROFILE%\.l4d2-addons.home`。跑完提醒用户：以后**双击 `刷新表格.bat` 就能重扫刷新**。
已有 `config.json` 时不会覆盖用户数据（`name_exempt.json` / `set_exempt.json` / `mod白名单.txt` 缺了才建）。

---

## 1. 配置与路径约定

全在 `<workDir>\config.json`：`workDir` / `scriptsDir`(默认 `_work`) / `xlsxName` / `addonsDir`（**mod 库最终落点**）/
`workshopDir` / `backupDir`(默认 `mod备份`) / `stagingDir`(`mod暂存` —— **用户自留区，绝不动**) / `whitelistFile` /
`mirrorDir` / `pythonPath` / `nodePath`。

所有脚本按 **环境变量 → `config.json` → 内置默认** 三级解析，可用
`L4D2_HOME` / `L4D2_ADDONS` / `L4D2_XLSX_OUT` / `L4D2_MIRROR` 临时覆盖。

---

## 2. 标准流程（用户说「干活」时执行）

> ⭐ **第 1-3 步与第 6/9 步已合并进一条命令**：`node <scriptsDir>\flow.mjs`
> —— 它给出暂存件证据 + 名字体检 + 冲突两条腿 + 收尾验收，**且不改库**。先跑它，再按下面的判断补做人工环节。

1. **扫描 `workshopDir`**，列出 `<id>.vpk` / `<id>.jpg`
   - ⚠️ **不是每个文件都来自工坊**：只有**纯数字 ID** 的是订阅件；中文名/别的名字是**手工件**
   - 手工件**没有工坊 ID → 不建 `.url`**，不参与「取工坊信息」与「取消订阅」
2. **取工坊信息**：批量 POST `ISteamRemoteStorage/GetPublishedFileDetails`（≤100 ID 一次，避免风控）。
   `result=9` = 已删除/不可见 → 跳过并写明原因。详见 `reference/steam-api.md`
3. **取「命名证据」+ 查重与冲突预判**
   - ⚠️ **新订阅件还没进 addons，`scan_addons.mjs` 看不到它们** → 命名证据必须来自
     `scan_workshop.ps1`（用**同一套分类规则**扫 `workshop\`，输出 `workshop_scan.json`，告出每件命中的标签）。
     `flow.mjs` 已内含这一步。
   - 再按 `.url` 里的 ID 建映射 → 对 vpk 算 SHA1 与 addons 现存比对（同内容 = 重复）→ 检查目标名是否被占用
4. **命名**：`<分类>-<替换对象>-<原标题>`；无替换对象时省略中段。
   **完整判据见 `reference/naming-rules.md`**（S1–S5、邻接标签、横切行、上位名、规则例外），别凭印象写
5. **搬迁**：用 `consolidate5.ps1 -Batch <json>`（**默认干跑**，核对 `OK/SKIP` 再 `-Apply`）—— **别手写搬移**
   - 批次 JSON（UTF-8，中文的唯一来源）字段：`id`（**手工件写 `""` → 不建 `.url`**）/ `src`（源文件名）/
     `base`（直接指定成品名主体，多件套附加件用它共用主件前缀）/ `cat`+`target`+`title`
   - 它自带：非法字符全角化、**主干 >63 字节自动截断**、**目标名被占用则整条 SKIP**、vpk+jpg+url 三件同步
6. **冲突检查（两条腿，都要看）**
   - a) **名字级** `scan_targets.ps1`；b) **文件级** `overlap_scan.mjs`（见 §3）
   - ⚠️ **核心标准（用户明确指定，别记错）：未整理的 —— 即还在 `workshopDir` 内的 —— 永远按新算**，
     **即使它的工坊日期更旧**。`time_updated` **只在两件都来自 `workshopDir` 时**才用于分胜负
   - 执行用 `resolve_conflicts.ps1 -Batch <json>`（**默认干跑**）；它只负责「搬 + 记账」，
     **判谁赢是调用方的决定**。**安全不变式**：`keep` 在 addons 里没有 `.vpk` 时**整条拒绝**，绝不搬空
   - 豁免：`mod白名单.txt` 条目跳过；多件套只按 `set_exempt.json` **声明过的成员**判定，**不按组键**
7. **清理**：`workshopDir` 清空后**保留空目录**（删了会影响 Steam 下载）
8. **取消订阅** —— ⚠️ **每次执行前都必须停下来问用户一次，不要自作主张**
   - **为什么必须做**：L4D2 工坊投递是把 `<id>.vpk` 直接放进 `workshop\`；只要订阅还在，下次启动游戏
     Steam 就会把同样的 VPK 再下一遍，整理白做
   - **但它是账号级、不可逆操作**（Steam 原文「此操作无法撤销！」）→ 问时必须说清三件事：
     ① **退哪些**（列 ID + 标题 + 总数，别只说「3 个」）② **为什么必须做** ③ **不可逆 + 回退方式**
     （回退 = 重新订阅；但 `result=9` 的已删除条目与**手工件**没有 `.url`，退订后无处可回）
   - **授权不跨会话**：只有用户**在当前这次会话**里明确说「以后不用问 / 直接退」才可跳过。详见 `reference/steam-api.md`
9. **刷新表格 + 验收** —— ✅ **流程的固定最后一步**：`<workDir>\刷新表格.bat`（或 `cmd /c "刷新表格.bat" nopause`）
   → `python <scriptsDir>\verify_all.py`（**一行总验**）
   - **为什么必须在最后**：`plan_v4` / `verify_*` 全读 `addons_scan.json`。**改名或搬迁后不重跑刷新，那份数据里
     还是旧文件名** → 再推演会对着旧名重复提同样的改名（看着像「幂等失效」，其实只是数据旧了）。
     `verify_all.py` 会报 `stale=YES` 帮你抓这个
10. **写进记忆（收尾，不改库）** —— 把结论压成**一条精简记忆**，省掉下次重新探索的 token
    - **写什么**：① 本次**结论级数字**（入库几件、计数变化、新增前缀/例外）② **稳定环境事实**（workDir、skill 路径、新工具）
    - **不写什么**：逐条文件清单（xlsx 里就有）、过程叙事、临时进度、能一条命令查到的东西
    - **先去重**：已有同义条目用 `replace` 而不是 `add`
    - 工具：DSH 用 `mnemon_runtime_memory`（`target=memory`）

---

## 3. 冲突判定：为什么有两条腿

| 腿 | 工具 | 能看出什么 |
|---|---|---|
| 名字级 | `scan_targets.ps1` | 同「前缀 + 第二段」分组里的多份。⚠️ **剥掉前缀后不含短横的条目永远不进判定**（已知盲点，见 `reference/naming-rules.md` §C3） |
| 文件级 | ⭐ `overlap_scan.mjs` | **装了同一文件且内容不同**的 mod 对 —— 这类**第二段名可能不同，扫描器与 `verify_overlaps` 都看不出** |

`overlap_scan.mjs` 的判据：解析全库 VPK 目录树取**路径 + CRC**，反向索引求交集，**逐对比 CRC** ——
内容相同（原版素材 / 同作者共用贴图 / VScript 公共库）→ 良性；内容不同 → **真抢位**。
完整结果写 `_work\blind_overlaps.md`；`--strict` 有真抢位时退出码 1（可当门禁）。

⚠️ **它报出来的不一定都是冲突**：同系列分卷（Cold Front / Poolcore / 地心引力 / 切尔诺贝利 / Glubtastic）
各代共用素材目录且内容逐代迭代，会被报成真抢位，但那是**作者自己的打包习惯**，判据见 `reference/naming-rules.md` §G/§C3。

---

## 4. 工具箱

**全表见 `reference/toolbox.md`**（按需查）。日常只需记住三个：

| 脚本 | 作用 |
|---|---|
| ⭐ `flow.mjs [--plan] [--quiet]` | **巡检总入口**：暂存件证据 + 名字体检 + 冲突两条腿 + 验收；明细写 `flow_report.md`；**不改库** |
| ⭐ `verify_all.py` | **一条命令收尾验收**，成功只印一行 `ALL OK stale=… rename=… conflicts=… rules=… fixes=… overlaps=… unclassified=… name63=… blind=… labels=…` |
| `lib.mjs` | **共用底座**（配置 / VPK 树 / 分类规则 / 名字字节）—— **写新工具一律从这里取，别再抄一份** |

---

## 5. 省 token 的纪律（用户明确要求过，2026-10-04 立）

每轮真正烧掉上下文的不是干活本身，而是**被反复注入的长文本**与**一次性探测命令**：

1. **长文档只留承重内容**：`AGENTS.md` 与 `SKILL.md` **每轮都被注入**。历史叙事一律进 `_work\执行记录.md`；
   判据细节一律进 `reference\`；文档里只留「怎么做 + 坑 + 指针」。⚠️ **别把历史/细节粘回去**
2. **别写一次性探针**：看一批 mod → `flow.mjs` 或 `batch_digest.mjs`；收尾 → `verify_all.py` 一行
3. **报告只给结论**：清单化表格 + 验收数字，**不要贴工具原始输出**（那是给模型看的，不是给人的）
4. 按固定 10 步走，**不要重新推导规则**（读 `reference\` 比重新试快得多）

---

## 6. 硬约束（踩过的坑，务必守住）

1. **一个标签 ↔ 一行表格**（可用 `label_override.json` 人工补；补的标签必须是已有表格行，否则 WARN）
2. **物件域规则必须锚定 `^(models|materials)/`** —— 只锚 `^models/` 会误伤「只改贴图」的物件 mod；
   完全不锚会误吞同名 sound 目录（实测 `sound/weapons/50cal/` 抢走 `.50 重机枪`）
3. **多值单元格每个值都写全路径**（分隔符「、」，通配 `*`，整目录以 `/` 结尾）；`verify_fixes.py` 必须 0
4. **路径必须先归一化再分类**（`normalizePath()`）。**验收标准：`unclassifiedPaths` 必须为 0**
5. **`rv_paths.json` 按文件名索引，改名后必须重跑**（`plan_v4.py` 已自动做）
6. **改名必须幂等**：用「前缀匹配」判断是否已合规，**不能按短横切分**（替换对象自己可能带短横：`AK-47 突击步枪`）
7. **多件套**：共用同一前缀、附加件末尾加 `-附加名`，改名**跟随主体**；豁免**按成员**声明（**不是按组键**）
8. **用户拍板过的取舍写进 `name_exempt.json`**，否则重跑规则会把名字推回去
9. `mod白名单.txt` 里**只有「行首就是 `<前缀>-`」的行才算条目**；写说明时别让续行以 `<前缀>-` 开头
10. **绝不动 `stagingDir`（`mod暂存`）**
11. ⚠️ **文件名主干 ≤ 63 ANSI 字节** —— 超限的包引擎**根本不挂载**且**日志零报错**（极易误判成 mod 做得烂）
12. 中文/编码/PowerShell 5.1 的坑见 `reference/pitfalls.md`（26 条）

---

## 7. 用户偏好（沿用）

- 回复与产物一律用**用户的语言**（默认中文）
- 结果**清单化**：原文件名 / 新文件名 / 快捷方式链接 / 处理状态
- **先看计划再动手**（干跑转正在执行）
- 用户会自己动手改库；**文件数变少不等于出错**，不要把手动删除当异常去"修复"
- **不生成 HTML 汇总页**，只要每个 mod 一个独立 `.url` 快捷方式
- 遇到不确定的取舍（哪份算新、是否算冲突、跨域归属）**先问，不要自行决定**
- ⚠️ **取消订阅每次都要问**（授权不跨会话）

---

## 8. 参考文档

| 文件 | 内容 |
|---|---|
| `reference/naming-rules.md` | 分类命名规范全文（S1–S5、邻接标签、横切行、上位名、**规则例外三类**、白名单可撤销、扫描盲点、同系列分卷） |
| `reference/toolbox.md` | **工具箱全表**（按链路分组，含每个脚本的参数与坑） |
| `reference/xlsx-pipeline.md` | 表格生成链路、4 条硬不变量、各脚本输出字段 |
| `reference/vpk-format.md` | VPK 二进制格式要点与两个必踩的坑 |
| `reference/steam-api.md` | 工坊批量查询 API、`.url` 格式、取消全部订阅（含确认话术） |
| `reference/pitfalls.md` | Windows / PowerShell 5.1 / 中文编码 / 沙箱 环境坑清单（26 条） |
| `CONTRIBUTING.md` | 贡献指南 + 11 条硬不变量 |
