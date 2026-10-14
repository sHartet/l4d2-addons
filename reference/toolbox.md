# 工具箱全表

全部在 `<workDir>\<scriptsDir>\`（默认 `_work\`）。

> **日常只需要两个**：`flow.mjs`（巡检总入口）与 `verify_all.py`（收尾验收）。
> 其余是改规则 / 排查 / 自测时才用的。本表按链路分组，方便按需查阅。

## ⭐ 两个总入口

| 脚本 | 作用 |
|---|---|
| ⭐ `flow.mjs [--plan] [--quiet] [--names <json>]` | **巡检总入口**：一条命令给全 —— 暂存件构成/标签/未归类 + 名字 63 字节体检 + 冲突两条腿（`scan_targets.ps1` + `overlap_scan.mjs`）+ 收尾验收。明细写 `_work\flow_report.md`，末尾一行 `FLOW SUMMARY`。**它不改库**（搬迁/移旧仍走 consolidate5 / resolve_conflicts）。`--plan` 追加搬迁干跑；`--quiet` 只印结论行 |
| ⭐ `verify_all.py [--quick]` | **一条命令跑完全部验收**，成功只印一行：`ALL OK  stale=no rename=0 conflicts=0 rules=75/75 fixes=0 overlaps=0 unclassified=0 name63=ok blind=N labels=223`；任何一项不过就 `FAIL` + 该项关键输出。**取代过去 6-8 次收尾调用** |

## 表格链路

| 脚本 | 作用 |
|---|---|
| `刷新表格.bat` | 一键：占用检测 → 重建基础表 → 扫 addons → 写回替换状态。**日常只需要它** |
| `build_ref_xlsx.py` | 生成 14 张基础表（说明/生还者/特殊感染者/普通感染者/主武器/副武器/近战/投掷物/消耗品/场景道具/固定武器·场景/音效路径/界面·特效·材质·其他/分类速查） |
| `scan_addons.mjs` | 解出每个 VPK 的完整资源树并归类 → `addons_scan.json` / `addons_by_target.json`。**规则真源**（`lib.mjs` 与 `batch_digest` 都从它取 `RULES`） |
| `enrich_ref_xlsx.py` | 并入「替换状态 / 替换它的 MOD / 原版英文名 / Token 来源」四列，追加「我的MOD清单」「替换覆盖总览」→ `label_map.json`；**并读 `label_override.json` 回写** |
| `check_lock.mjs` | 刷新前检测 xlsx 是否被 WPS/Excel 占用 |

## 命名链路

| 脚本 | 作用 |
|---|---|
| `rv_dump_paths.mjs` | 自写解析器解出**全部完整路径** → `rv_paths.json`（文件名索引；**改名后必须重跑**，`plan_v4.py` 已能自愈） |
| `plan_v4.py` | 按 S1–S5 推演 → `rename_plan.md`（含规则例外、多件套归并、幂等保护） |
| `mk_rename_json.py` | 出改名批次 `rename_batch.json` |
| `rename_batch.ps1 -Batch <json>` | **干跑**；加 `-Apply` 执行。vpk+jpg+url 三件同步，目标占用则整条 SKIP，日志 `*_log.txt` |

## 搬迁链路

| 脚本 | 作用 |
|---|---|
| `scan_workshop.ps1` | **扫 `workshopDir` 暂存件**，用与扫库完全相同的分类规则 → `workshop_scan.json`。**新订阅件的命名证据靠它**（`scan_addons.mjs` 只扫 addons 顶层，看不到暂存件） |
| `consolidate5.ps1 -Batch <json> [-Apply]` | **`workshop\` → `addons\`**：搬 vpk+jpg、按 `<分类>-<替换对象>-<原标题>` 改名、`id` 非空才建 `.url`。默认干跑，目标占用整条 SKIP。**不要手写搬移**。⚠️ 全角化表 `$illegal` 就在这个脚本里（`\|` 必须是 `｜` U+FF5C） |
| `resolve_conflicts.ps1 -Batch <json> [-Apply]` | **冲突留新移旧**：把败方 vpk+jpg+url 移入 `backupDir` 并追加清单行。**默认干跑**；`keep` 不存在则整条拒绝（不搬空）。批次 = `[{target, keep, move:[...], reason}]` |
| `batch_digest.mjs [--ids a,b] [--dir <目录>] [--names <json>]` | 单批证据：每件一行（体积/路径数/bsp·nav·mdl·nut·snd 计数/命中标签前 3/未归类数/抽样路径）+ 未归类明细；`--names` 体检候选名（GBK 字节 + 占用）。**`flow.mjs` 已含，单独用时才调** |
| `vpklist.ps1 -Path <单个 vpk> -OutName x -TopN 20` | 解 VPK 内部文件树（判断手工件替换了哪把枪/哪个角色）。**用 `-ExecutionPolicy Bypass -File` 调用、一次一个路径** |
| `vpkdump.ps1 -Path <vpk> -Match '^addoninfo\.txt$' -OutName x -MaxChars 3000` | 提取 VPK 内某文件内容 —— **识别未知 mod / 工坊页已失效（`result=9`）时唯一权威依据**。自动判 `entryOffset` 两种 base；末尾附全部条目路径 |
| `vpkwrite.mjs <out.vpk> <spec.json>` | 造一个合法 VPK（自测/造样本用）。spec = `[{"path": "...", "text": "..."}]` |

## 冲突与校验

| 脚本 | 作用 |
|---|---|
| ⭐ `overlap_scan.mjs [--strict] [--top N] [--min N] [--paths-only]` | **盲点扫描（文件级）**：解析全库 VPK 目录树取**路径 + CRC**，找出「装了同一文件且内容不同」的 mod 对 —— 这类冲突**第二段名可能不同，扫描器与 `verify_overlaps` 都看不出**。完整结果写 `_work\blind_overlaps.md`；内容相同的交集（原版素材/共用贴图/VScript 公共库）自动折叠。回归用例：自测 S9 |
| `scan_targets.ps1` | 按「前缀 + 第 2 段」分组的**文件名**冲突扫描（辅助）。⚠️ 落到资源类型前缀的 mod 中段为空，它判不了 → **冲突判定以表格标签链路为准**。它读 `mod白名单.txt` 与 `set_exempt.json`（**按成员**），对每个 >1 成员的组按顺序判定：① **所有成员**都在已声明的多件套里 → `[set (all members declared)]` ② 组内**每个**成员都在白名单里 → `[all members whitelisted]` ③ 否则 → `[CONFLICT]`，标注 `<set:…>` / `<whitelisted>` / `<*** OUTSIDER ***>`。支持 `-RootDir <目录> -OutFile <文件>` 做正负回归测试（合成目录，不碰真实库）：负向（三件套 + 一个未声明的新 Scout）期望 `conflicts=1` 且打印 `*** OUTSIDER ***`；正向（只有三件套）期望 `conflicts=0` |
| `verify_rules.mjs` | 分类规则断言（改规则后必跑；现 75 条：69 分类 + 6 归一化） |
| `verify_fixes.py` | 读回 xlsx 逐条核对已知缺陷类别（「不合格条目数」必须 0） |
| `verify_overlaps.py` | 列出被 ≥2 个 mod 覆盖的标签，分「多件套 / 分类级 / 多目标聚合 / 仅地图附带 / ⚠真冲突」 |
| `probe_unclassified.mjs` | 打印某 mod 的路径分类明细与未归类项（`$env:L4D2_ADDONS=<workshop>` 可扫暂存件） |
| `verify_ps1_ascii.py` | **护栏**：检查所有 `.ps1` 是否 100% ASCII（PS 5.1 会把无 BOM 的 UTF-8 `.ps1` 按 GBK 解析） |
| `verify_docs.py` | **护栏**：检查文档瘦身没弄丢关键知识 —— 关键主题必须在 skill 里仍可寻（见下） |
| `self_test.py` | **全链路自测**：临时目录模拟「全新用户 + 空库」，跑 15 阶段。**改任何脚本前后都跑它** —— 不碰真实库，失败会保留临时目录。⚠️ 必须用 `config.json` 的 `pythonPath` 跑 |
| `workspace_backup.ps1 -Mode save\|restore` | 工作区镜像备份（robocopy /MIR），防意外清空 |

## 共用底座

| 文件 | 作用 |
|---|---|
| `lib.mjs` | **全流程共用底座**：配置解析 / 命令行 / VPK 目录树（`treeEntries`，可选带 CRC）/ 分类规则（从 `scan_addons.mjs` 取 `RULES`）/ 名字字节（`stemBytes`）/ 分组键（`cat2`）。**新工具一律从这里取，别再抄一份** |
