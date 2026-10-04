# l4d2-addons

自动化整理《求生之路2》(Left 4 Dead 2) 的创意工坊 mod 

 **Skill**：装进 DSH / Claude Code 之类的 agent 后，
跟它说「整理我的 L4D2 mod」，它会自己把整套工具链铺好，然后按规则干活。

[English README](README.en.md) · [贡献指南](CONTRIBUTING.md)

---

## 它解决什么问题

从创意工坊订阅的 mod 落到硬盘上，文件名是一串数字：`3778253592.vpk`。
装了几百个之后，你既不知道哪个文件是什么，也不知道**哪些 mod 在抢同一个位置**（例如装了两个 Hunter 替换件，只有一个会生效）。

这个 skill 做四件事：

1. **摸清每个 mod 到底替换了什么** —— 自己解析 VPK 二进制，取出内部全部资源路径，不单靠文件名取值
2. **按 `分类-替换对象-原标题` 重命名**，19 个分类前缀（`生还者-` `特感-` `主武器-` `近战-` `材质-` `脚本-` …）
3. **找出真冲突并留新移旧** —— 同一替换对象下多个 mod 时，**还没整理的（还在 `workshop\` 里的）永远算新**，
   旧的移进 `mod备份\` 并记进清单；工坊 `time_updated` 只在**两件都来自 `workshop\`** 时用来分胜负
4. **生成《可MOD替换物品总表》xlsx** —— 16 张表，逐个物件标注「已替换 / 未替换 / 仅地图包附带」，以及替换它的具体 mod

## 快速开始

首次调用时 skill 会问你三件事（**只需一次**）：

- 《求生之路2》的 `left4dead2\addons` 目录
- `workshop` 暂存 / 创意工坊 目录（默认就在 addons 下面，多数人不用改）
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

## 工作流

跟它说「整理我的 L4D2 mod」，它会走完这 5 件事：

1. **搬进 `addons\` 并规范化命名** —— 把 `workshop\` 里的订阅件移进 `addons\`，按 `<分类>-<替换对象>-<原标题>` 改名，
   并为每件生成 `.url` 快捷方式（双击直达工坊页）。例：`3778253592.vpk` → `主武器-AK-47 突击步枪-<作者原标题>.vpk`。
   搬走后**不再依赖 workshop 加载**，启动更干净，也不会被 Steam 重新下发覆盖。
   - 手工丢进来的 vpk（文件名不是纯数字 ID）**没有工坊 ID → 不建 `.url`**，也不参与退订
   - `workshop\` 空目录**保留**（删掉会影响 Steam 下载）
2. **建一张会自己更新的总表** —— 生成《求生之路2_可MOD替换物品总表.xlsx》（16 张表），逐行标注每个可替换物件：
   **已替换 / 未替换 / 仅被地图包附带覆盖**，并写明**是哪个 mod 替换的**；另附「我的MOD清单」与「替换覆盖总览」。
   库有变化时双击 `刷新表格.bat` 就重扫重建，不必找 AI。
3. **自动识别冲突并留新移旧** —— 按「替换对象」分组（武器 / 角色 / 投掷物 / 消耗品 / 场景物件…），
   同一对象下有多个 mod 时保留较新的（比较工坊 `time_updated`，**`workshop\` 里的算新**），
   旧的连同 `.jpg` / `.url` 一起移进同目录的 `mod备份\`，并把理由与 SHA1 记进 `mod备份\backup_manifest.md`。
   - **多件套豁免**：同一 mod 的主体 + 材质 / 瞄准镜 / 音效等附加件本就该共存，不算冲突；改名时附加件跟随主体
   - 豁免只按 `_work\set_exempt.json` 里**声明过的成员**判定，**不是按组** —— 组里出现未声明的新 mod 就是真冲突
   - 你的判断优先：写进 `mod白名单.txt` 的条目一律跳过，你改口时也能撤销（并记进 backup_manifest）
4. **主动问你要不要退订**（双保险）—— 流程走完后它会**停下来问一次**，并说清三件事：
   ① 退哪些（列 ID + 标题 + 总数）② 为什么必须做 ③ 不可逆与怎么回退。
   你同意后它自动退订，**不用你再去创意工坊手动点**。
   - 为什么必须做：L4D2 的工坊投递是把 VPK 直接放进 `workshop\`；不退订的话，下次启动游戏 Steam 会把刚搬走的 VPK 重新下回来，整理白做
   - 作用范围安全：只清 `appid=550`，其它游戏的订阅实测字节数不变
   - **授权不跨会话**：只有你在当次会话里说「不用问」，那一次才跳过
5. **最后刷新总表并把流程写进记忆** —— 跑一次 `刷新表格.bat`，让扫描数据与磁盘一致
   （改名后不刷新，`plan_v4` 会对着旧数据重复提出同样的改名 —— 它会打 `[WARN] addons_scan.json 已过期` 提醒）；
   然后把本次结论压成**一条精简记忆**，下次开会话直接复用，**省掉重新探索的 token**。


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

在一个**临时目录**里模拟「全新用户 + 空库」，走完 12 个阶段：bootstrap 生成工作区 →
造 3 个假 VPK → 空库刷新 → 扫 workshop 暂存件 → 搬迁（干跑+执行）→ 三件校验 →
再刷新 → 命名幂等（需改名 0）→ 冲突扫描与全部校验脚本 → **超长名按 63 字节截断**。

**完全不碰你的真实 mod 库**；某一阶段失败时会保留临时目录供排查。改任何脚本前先跑它。

## 环境要求

- Windows（脚本用到 robocopy / 批处理 / PowerShell）
- Python 3.10+，**需要 `openpyxl`**
- Node.js 18+
- `config.json` 里的路径按 **环境变量 → config.json → 内置默认** 三级解析，
  也可用 `L4D2_HOME` / `L4D2_ADDONS` / `L4D2_XLSX_OUT` / `L4D2_MIRROR` 临时覆盖

## 许可

MIT —— 见 [LICENSE](LICENSE)。
