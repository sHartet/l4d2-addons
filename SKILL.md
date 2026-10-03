---
name: l4d2-addons
description: Left 4 Dead 2（求生之路2）mod 库整理工作流：把创意工坊订阅的 VPK 归纳进 left4dead2\addons 并按「分类-替换对象-原标题」重命名、按替换对象做冲突留新移旧、生成并刷新《求生之路2_可MOD替换物品总表.xlsx》与「刷新表格.bat」。当用户提到 求生之路2 / L4D2 / left4dead2 的 addons、workshop、mod 整理、mod 重命名、mod 冲突、mod 总表、替换物品表、取消工坊订阅时使用。
---

# L4D2 mod 库整理

把「一个 mod 文件 → 一个可读的名字 + 一个工坊快捷方式」这件事做成**可重复、可复核、幂等**的流程。

**核心思路**：不靠文件名猜，而是**解出每个 VPK 的真实资源路径**，用它反推这个 mod 到底替换了什么；
再按 `S1 地图 → S2 物件域 → S3 物件域·贴图类 → S4 资源类型 → S5 低置信保留原前缀` 五步定分类前缀。
低置信时**保留人工前缀并列入待复核，绝不静默猜**。

---

## 0. 首次调用必做：定位 / 生成工作目录

工作目录（下称 `workDir`）里放：`config.json`、生成的脚本 `<workDir>\_work\`、`求生之路2_可MOD替换物品总表.xlsx`、`刷新表格.bat`。

**默认 `workDir` = 用户自己的 AI 工作目录（当前会话 cwd）。**

⚠️ **无论记忆/上下文里是否已经有「这台机器配置过」的信息，每次调用都必须真的跑一次这条命令。**
记忆只能当提示，不能替代这次实际探测 —— 配置可能已过期（换了硬盘、重装 Steam、改了目录）。

```powershell
python <skill>\scripts\bootstrap.py --show
```

它返回三样东西，据此判断：

| 情况 | 怎么做 |
|---|---|
| `known.cwdConfig` 有值 | 当前目录就是 workDir → 直接用 |
| `known.pointerConfig` 有值 **且** 指针指向的 workDir **等于**当前会话 cwd | 直接用，不用问 |
| `known.pointerConfig` 有值 **但** 与当前会话 cwd **不同** | ⚠️ **必须问一句**，见下 |
| 两者都空 | **首次调用**：按 `needAsk` 问（应为 `workDir` / `addonsDir` / `workshopDir` 三项），然后跑 bootstrap |

**以 `--show` 的返回字段为准，不要自己猜：**

| 字段 | 含义 |
|---|---|
| `needAsk` | **要问用户的清单，以它为准。** 全新安装 = `workDir` + `addonsDir` + `workshopDir`；已配置过 = 空数组 |
| `workDir` | **照当前参数跑下去、产物会落在哪** —— 解析规则与 install 完全一致（`--workdir` > 当前目录） |
| `workDirSource` | 上一行是怎么定出来的（`explicit (--workdir)` / `current directory (default)`） |
| `pointerWorkDir` | 本机**已配置过**的工作目录（没配置则是空） |
| `pointerDiffersFromCwd` | 上一行那个目录**是否与当前会话目录不同**；`true` → 按上表那行「必须问一句」 |

> ⚠️ 别把 `workDir` 和 `pointerWorkDir` 混为一谈：前者是「**这次**会写哪」，后者是「**以前**配过哪」。
> 只有当 `pointerDiffersFromCwd` 为 `true`、且用户选了沿用旧目录时，才把 `--workdir "<pointerWorkDir>"` 显式传给 bootstrap。
>
> ⚠️ **全新安装时 `workDir` 也在询问清单里**：agent 自己的 cwd 常常不是用户选的地方，
> 不打招呼就往那里丢 `config.json` / `xlsx` / `_work\` 会让人意外（已有用户就此反馈过）。

#### ⚠️ 指针的 workDir ≠ 当前会话 cwd 时，必须先问

**默认 `workDir` = 用户自己的 AI 工作目录（当前会话 cwd）** —— 用户期待**产物出现在自己正在对话的那个目录**，
所以「已配置过」不能成为静默沿用别的目录的理由。问法：

```
检测到本机已有一份配置：
  workDir     = D:\work\L4D2      ← 不是你现在这个目录
  addonsDir   = D:\Steam\…\left4dead2\addons
本次整理用哪个目录？产物（xlsx / 刷新表格.bat / _work\）会放在那里。
  A) 当前会话目录 （推荐）→ 新建一份配置，addons 路径沿用上面那个，不用你重填
  B) 用上面那个 workDir → 产物继续落在 D:\work\L4D2
```

- 选 **A** → 跑 `bootstrap.py --workdir "<当前目录>" --addons "<上面那个 addonsDir>"`（`--workshop` 等一并沿用），
  这条会把当前目录变成新的 workDir（并更新全局指针）。**不要重新问 addons 路径**，已经知道了。
- 选 **B** → 就按指针那个 workDir 干，别再问。
- 用户明确说过「以后都放某个固定目录」→ 记下来，之后不再问（属于用户显式指令，可以覆盖默认）。

**无论走哪条分支，最后都要把解析结果回报给用户**，格式类似：

```
配置来源：全局指针（C:\Users\<你>\.l4d2-addons.home）
  workDir     = D:\work\L4D2
  addonsDir   = D:\Steam\steamapps\common\Left 4 Dead 2\left4dead2\addons
  workshopDir = …\left4dead2\addons\workshop
```

这三行让用户能一眼发现「指到别的盘 / 旧安装」这类问题；**发现指错了就重跑 bootstrap**（加 `--force`）或直接改 `config.json`，然后重新探测。
不要只说一句「已找到配置」就往下干。

首次调用要问的（一次问完，别挤牙膏）：

1. **《求生之路2》的 addons 目录** —— 例如 `D:\Steam\steamapps\common\Left 4 Dead 2\left4dead2\addons`
   （提示用户：Steam 库里右键游戏 → 管理 → 浏览本地文件 → `left4dead2\addons`）
2. **workshop 暂存目录** —— 默认就是 `<addons>\workshop`，多数人不用改
3. **工作目录** —— 默认用当前 AI 工作目录，问一句「要不要换个地方」

拿到答案后：

```powershell
python <skill>\scripts\bootstrap.py --workdir "<workDir>" --addons "<addonsDir>" [--workshop "<dir>"]
```

bootstrap 会自动做完：写 `config.json` → 把脚本铺进 `<workDir>\_work\` → 渲染 `刷新表格.bat`（写入本机 python/node 绝对路径）→ **跑一次刷新，产出 xlsx** → 记一个全局指针 `%USERPROFILE%\.l4d2-addons.home`（下次任何目录都能找到 workDir）。

跑完把结果告诉用户，并提醒：以后**双击 `刷新表格.bat` 就能重扫刷新**，不用再找 AI。

> 已有 `config.json` 时 bootstrap 不会覆盖用户数据（`name_exempt.json` / `set_exempt.json` / `mod白名单.txt` 缺了才建）。
> 想改路径就再跑一次 bootstrap，或直接编辑 `<workDir>\config.json`。

---

## 1. 配置与路径约定

全在 `<workDir>\config.json`：

| 键 | 含义 |
|---|---|
| `workDir` | 工作目录 |
| `scriptsDir` | 脚本子目录，默认 `_work` |
| `xlsxName` | 表格文件名，默认 `求生之路2_可MOD替换物品总表.xlsx` |
| `addonsDir` | **游戏 mod 库（最终落点）** |
| `workshopDir` | Steam 下载暂存，默认 `<addonsDir>\workshop` |
| `backupDir` | 冲突备份，默认 `<addonsDir>\mod备份` |
| `stagingDir` | `<addonsDir>\mod暂存` —— **用户自留区，绝不动** |
| `whitelistFile` | `<addonsDir>\mod白名单.txt` |
| `mirrorDir` | 工作区镜像备份，默认 `<workDir>-backup` |
| `pythonPath` / `nodePath` | 渲染 `刷新表格.bat` 用的解释器 |

所有脚本按 **环境变量 → `config.json` → 内置默认** 三级解析路径，可用
`L4D2_HOME` / `L4D2_ADDONS` / `L4D2_XLSX_OUT` / `L4D2_MIRROR` 临时覆盖。

---

## 2. 标准流程（用户说「干活」时执行）

1. **扫描 `<workshopDir>`**，列出 `<id>.vpk` / `<id>.jpg`
   - ⚠️ **不是里面每个文件都来自工坊**：只有**纯数字 ID** 文件名的是订阅件；中文名/别的名字是用户手工丢进来的**手工件**
   - 手工件**没有工坊 ID → 不建 `.url`**，不参与「取工坊信息」与「取消订阅」
2. **取工坊信息**：批量 POST `ISteamRemoteStorage/GetPublishedFileDetails`（≤100 个 ID 一次，避免风控）。
   `result=9` = 条目已删除/不可见 → 跳过并在报告里写明原因。详见 `reference/steam-api.md`
3. **取「命名证据」+ 查重与冲突预判**

   ⚠️ **新订阅件还没进 addons，扫库的 `scan_addons.mjs` 看不到它们** —— 直接看路径瞎猜很容易分错类。先跑：

   ```powershell
   & "<workDir>\<scriptsDir>\scan_workshop.ps1"
   ```

   它用**同一套分类规则**扫 `workshop\`，输出 `workshop_scan.json`，直接告出每件命中了哪些标签
   （`武器·AK-47 突击步枪` / `教练 Coach` / `武器·武士刀` …）—— 分类前缀与替换对象就有据可依。

   然后：按 `.url` 里的 ID 建映射（判断该 ID 是否已在 addons 中）→ 对 vpk 算 SHA1 与 addons 现存比对
   （同内容 = 重复，删旧留新）→ 检查目标名是否已被占用。
4. **命名**：`<分类>-<替换对象>-<原标题>`；无替换对象时省略中段。规则见第 3 节 + `reference/naming-rules.md`
5. **搬迁**：vpk + jpg 移入 addons 并改名，**同时新建 `.url`** —— 用 `consolidate5.ps1`，**别手写搬移**：

   ```powershell
   & "<workDir>\<scriptsDir>\consolidate5.ps1" -Batch "<workDir>\<scriptsDir>\ws_batch<N>.json"          # 干跑
   & "<workDir>\<scriptsDir>\consolidate5.ps1" -Batch "<workDir>\<scriptsDir>\ws_batch<N>.json" -Apply   # 执行
   ```

   批次 JSON（UTF-8，中文的唯一来源）字段：`id`（**手工件写 `""` → 不建 `.url`**）/ `src`（手工件的源文件名）/
   `base`（直接指定成品名主体，多件套共用前缀时用它）/ `cat`+`target`+`title`（未给 base 时按 `<cat>[-<target>]-<title>` 拼）。

   它自带：Windows 非法字符全角化、120 字符截断、**目标名被占用则整条 SKIP**（不覆盖）、vpk+jpg+url 三件同步、
   日志写 `<批次名>_log.txt`。干跑输出的 `OK / SKIP` 数必须核对过再 `-Apply`。
6. **冲突检查**：同一替换对象下有多个 mod → 保留最新、其余连同 jpg/url 移入 `backupDir`，
   并在 `<backupDir>\backup_manifest.md` 追加一行（写明理由 + 保留了哪份）
7. **清理**：`workshopDir` 清空后**保留空目录**（删了会影响 Steam 下载）
8. **取消订阅** —— ⚠️ **每次执行前都必须停下来问用户一次，不要自作主张。**
   - **为什么必须做**：L4D2 的工坊投递是把 `<id>.vpk` 直接放进 `workshop\`。你把 VPK 搬走后，
     只要订阅还在，下次启动游戏 Steam 就会把同样的 VPK 再下一遍，整理白做。
   - **但它是账号级、不可逆操作**（Steam 原文「此操作无法撤销！」）→ 所以问的时候要说清三件事：
     1. **退哪些** —— 列出 ID + 标题 + 总数（别只说「3 个」）
     2. **为什么必须做** —— 不退的话下次进游戏会把刚整理走的 VPK 重新下回来
     3. **不可逆 + 回退方式** —— 回退 = 重新订阅；addons 里每个 mod 都留了 `.url` 可直达工坊页，
        但 `result=9` 的已删除条目与**手工件**没有 `.url`，退订后无处可回
   - **授权不跨会话**：只有用户在**当前这次会话**里明确说了「以后不用问 / 直接退」之类的话，本次才可以跳过；
     不要因为记忆或上次会话授权过就默认免确认。详见 `reference/steam-api.md`
9. **刷新表格** —— ✅ **这是流程的固定最后一步**：跑 `<workDir>\刷新表格.bat`（双击，或 `cmd /c "刷新表格.bat" nopause`）。
   - **为什么必须在最后**：`plan_v4` / `verify_*` / `扫描` 全都读 `addons_scan.json`。**改名或搬迁之后不重跑刷新，那份扫描数据里还是旧文件名** —— 再跑推演会对着旧名重复提出同样的改名，看起来像「幂等失效」，其实只是数据旧了（`plan_v4` 现在会打 `[WARN] addons_scan.json 已过期` 提醒）。
   - 刷新会重建 xlsx → 重扫 addons → 并入替换状态，正常应看到 `unclassifiedPaths: 0`、
     `[OK] 标签与表格行一一对应：N 个标签，无共用`。
   - **刷新完再复验一次**：`plan_v4` 需改名 0 / `scan_targets.ps1` conflicts=0。

---

## 3. 分类与命名（摘要）

**19 个前缀**：物件域 10 个 —— `生还者-` `特感-` `普感-` `主武器-` `副武器-` `近战-` `投掷物-` `消耗品-` `场景道具-` `场景-`；
资源类型 7 个 —— `模型-` `地图-` `材质-` `界面-` `特效-` `脚本-` `音效-`；兜底 `其它-`。

**中段（替换对象）**：`生还者-`/`特感-` 用官方**英文名**（Coach / Boomer / Hunter）；
其余物件域用官方**中文名**（AK-47 突击步枪 / 武士刀 / 马格南手枪）；资源类型前缀与低置信项**省略中段**。
同域多行时用**上位名**（手枪 / 霰弹枪 / Francis / Witch / Boomer / Tank）。

**原标题原样保留**（尊重发布者），只把 Windows 非法字符换成全角
`\ / : * ? " < > |` → `＼ ／ ： ＊ ？ ＂ ＜ ＞ ｜`，清理换行/制表符/结尾句点，超长截断至 120 字符。

⚠️ 完整判据（S1–S5、邻接标签映射、横切行表、上位名表、规则例外）见 **`reference/naming-rules.md`**，别凭印象写。

---

## 4. 工具箱

全部在 `<workDir>\<scriptsDir>\`。

### 表格链路

| 脚本 | 作用 |
|---|---|
| `刷新表格.bat` | 一键：占用检测 → 重建基础表 → 扫 addons → 写回替换状态。**日常只需要它** |
| `build_ref_xlsx.py` | 生成 14 张基础表（说明/生还者/特殊感染者/普通感染者/主武器/副武器/近战/投掷物/消耗品/场景道具/固定武器·场景/音效路径/界面·特效·材质·其他/分类速查） |
| `scan_addons.mjs` | 解出每个 VPK 的完整资源树并归类 → `addons_scan.json` / `addons_by_target.json` |
| `enrich_ref_xlsx.py` | 并入「替换状态 / 替换它的 MOD / 原版英文名 / Token 来源」四列，追加「我的MOD清单」「替换覆盖总览」→ `label_map.json` |
| `check_lock.mjs` | 刷新前检测 xlsx 是否被 WPS/Excel 占用 |

### 命名链路

| 脚本 | 作用 |
|---|---|
| `rv_dump_paths.mjs` | 自写解析器解出**全部完整路径** → `rv_paths.json`（文件名索引；**改名后必须重跑**，`plan_v4.py` 已能自愈） |
| `plan_v4.py` | 按 S1–S5 推演 → `rename_plan.md`（含规则例外、多件套归并、幂等保护） |
| `mk_rename_json.py` | 出改名批次 `rename_batch.json` |
| `rename_batch.ps1 -Batch <json>` | **干跑**；加 `-Apply` 执行。vpk+jpg+url 三件同步，目标占用则整条 SKIP，日志 `*_log.txt` |

### 搬迁链路

| 脚本 | 作用 |
|---|---|
| `scan_workshop.ps1` | **扫 `workshopDir` 暂存件**，用与扫库完全相同的分类规则 → `workshop_scan.json`。**新订阅件的命名证据靠它**（`scan_addons.mjs` 只扫 addons 顶层，看不到暂存件） |
| `consolidate5.ps1 -Batch <json> [-Apply]` | **`workshop\` → `addons\`**：搬 vpk+jpg、按 `<分类>-<替换对象>-<原标题>` 改名、`id` 非空才建 `.url`。默认干跑，目标占用整条 SKIP。**不要手写搬移** |
| `vpklist.ps1 -Path @($f1,$f2) -OutName x -TopN 20` | 解 VPK 内部文件树（判断手工件替换了哪把枪/哪个角色）。**必须用 `&` 调用**，`powershell -File -Path $数组` 会把数组摊平 |
| `vpkdump.ps1 -Path <vpk> -Match '^addoninfo\.txt$' -OutName x -MaxChars 3000` | 提取 VPK 内某个文件的内容 —— **识别未知 mod / 工坊页已失效（`result=9`）时唯一权威依据**。自动判 `entryOffset` 的两种 base；末尾附全部条目路径 |
| `vpkwrite.mjs <out.vpk> <spec.json>` | 造一个合法 VPK（自测/造样本用）。spec = `[{"path": "...", "text": "..."}]` |

### 冲突与校验

| 脚本 | 作用 |
|---|---|
| `scan_targets.ps1` | 按「前缀 + 第 2 段」分组的**文件名**冲突扫描（辅助，见下方注意） |
| `verify_rules.mjs` | 分类规则断言（改规则后必跑） |
| `verify_fixes.py` | 读回 xlsx 逐条核对已知缺陷类别 |
| `verify_overlaps.py` | 列出被 ≥2 个 mod 覆盖的标签，分「多件套 / 分类级 / 多目标聚合 / 仅地图附带 / ⚠真冲突」 |
| `probe_unclassified.mjs` | 打印某 mod 的路径分类明细与未归类项 |
| `verify_ps1_ascii.py` | **护栏**：检查所有 `.ps1` 是否 100% ASCII。PS 5.1 会把无 BOM 的 UTF-8 `.ps1` 按 GBK 解析，**哪怕中文只出现在注释里**也会打乱解析、吃掉后一行（真实事故：一句中文注释让 `$WS = ...` 整行消失） |
| `self_test.py` | **全链路自测**：在临时目录里模拟「全新用户 + 空库」，跑 9 个阶段（bootstrap → 造 VPK → 刷新 → 扫 workshop 暂存件 → 搬迁 → 三件校验 → 再刷新 → 命名幂等 → 冲突/校验/ASCII 护栏）。**改任何脚本前后都跑它** —— 不碰真实库，失败会保留临时目录供排查 |
| `workspace_backup.ps1 -Mode save\|restore` | 工作区镜像备份（robocopy /MIR），防意外清空 |

**冲突判定以「表格标签链路」为准**（`addons_scan.json` + `label_map.json` + `verify_overlaps.py`），
`scan_targets.ps1` 只作辅助 —— 落到资源类型前缀的 mod 中段为空，文件名扫描器判不了它们。

---

## 5. 硬约束（踩过的坑，务必守住）

1. **一个标签 ↔ 一行表格**。标签被多行共用 → 那几行会同时显示同一份 mod 列表。`enrich_ref_xlsx.py` 启动即自检
2. **物件域规则必须锚定 `^(models|materials)/`**。
   - 只锚 `^models/` → 误伤「只改贴图」的物件 mod（实测梯子行从「已替换」退化成「仅附带覆盖」）
   - 完全不锚 → 误吞同名 sound 目录（实测 `sound/weapons/50cal/` 抢走 `.50 重机枪`）
3. **多值单元格每个值都写全路径**，分隔符统一「、」，通配写 `*`，整目录以 `/` 结尾；
   VPK 根目录下的文件直接写文件名也算完整路径；说明文字挪到备注列。`verify_fixes.py` 核对「不合格条目数」必须为 0
4. **路径必须先归一化再分类**（`scan_addons.mjs` 的 `normalizePath()`）。部分打包者把外层目录也打进 VPK
   （`left 4 dead 2/left4dead2/…`、`for_users/…`、`for_modders/…`），这些用 `^` 锚定的规则一条都匹配不到。
   **验收标准：`unclassifiedPaths` 必须为 0**
5. **`rv_paths.json` 按文件名索引，改名后必须重跑**（`plan_v4.py` 已自动做）
6. **改名必须幂等**：`newname()` 用「前缀匹配」判断当前名是否已合规，**不能按短横切分** ——
   替换对象自己就可能带短横（`AK-47 突击步枪`、`M-16 突击步枪`）
7. **多件套（主体 + 附加）**：共用同一前缀、附加件末尾加 `-附加名`，**改名时必须跟随主体**。
   豁免**按成员**声明在 `set_exempt.json`，**不是按组键**（按组键会放过真冲突）
8. **用户拍板过的取舍写进 `name_exempt.json`**，否则重跑规则会把名字推回去
9. `mod白名单.txt` 里**只有「行首就是 `<前缀>-`」的行才算条目**；写中文说明时别让续行以 `<前缀>-` 开头
10. **绝不动 `stagingDir`（`mod暂存`）**：不整理、不算冲突、不移动、不删除
11. 中文文档/脚本的编码坑、PowerShell 5.1 的各种陷阱见 `reference/pitfalls.md`

---

## 6. 用户偏好（沿用）

- 回复与产物一律用**用户的语言**（默认中文）
- 结果**清单化**：原文件名 / 新文件名 / 快捷方式链接 / 处理状态
- **先看计划再动手**（干跑转正在执行）
- 用户会自己动手改库；**文件数变少不等于出错**，不要把手动删除当异常去"修复"
- **不生成 HTML 汇总页**，只要每个 mod 一个独立 `.url` 快捷方式
- 遇到不确定的取舍（哪份算新、是否算冲突、跨域归属）**先问，不要自行决定**

---

## 7. 参考文档

| 文件 | 内容 |
|---|---|
| `reference/naming-rules.md` | 分类命名规范全文（S1–S5、邻接标签、横切行、上位名、规则例外、实测数据） |
| `reference/xlsx-pipeline.md` | 表格生成链路、4 条硬不变量、各脚本输出字段 |
| `reference/vpk-format.md` | VPK 二进制格式要点与两个必踩的坑 |
| `reference/steam-api.md` | 工坊批量查询 API、`.url` 格式、取消全部订阅 |
| `reference/pitfalls.md` | Windows / PowerShell 5.1 / 中文编码 / 沙箱 环境坑清单 |
