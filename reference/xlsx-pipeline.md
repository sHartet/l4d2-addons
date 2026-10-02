# 表格生成链路

产出：`<workDir>\求生之路2_可MOD替换物品总表.xlsx`（16 张工作表）＋ 用户可双击的 `刷新表格.bat`。

## 工作流

```
刷新表格.bat nopause
  [0/3] check_lock.mjs        xlsx 是否被 WPS/Excel 占用（占用则停，不动任何东西）
  [1/3] build_ref_xlsx.py     从零重建 14 张基础表
  [2/3] scan_addons.mjs       解 addons 下每个 VPK 的资源树 → 归类 → addons_scan.json / addons_by_target.json
  [3/3] enrich_ref_xlsx.py    写回「替换状态 / 替换它的 MOD / 原版英文名 / Token 来源」四列
                              ＋ 追加「我的MOD清单」「替换覆盖总览」两张表 → label_map.json
```

`刷新表格.bat` 由 `bootstrap.py` **渲染生成**（把本机 python/node 绝对路径与 `L2D2_HOME` 写进去），
文件本身保持**纯 ASCII** —— 中文一律由子进程（Node/Python）输出，因为 cmd 会按 GBK 解析批处理里的中文。

## 16 张表

基础表 14：说明 / **生还者** / **特殊感染者** / **普通感染者** / **主武器** / **副武器** / **近战** /
**投掷物** / **消耗品** / **场景道具** / **固定武器·场景** / 音效路径 / 界面·特效·材质·其他 / 分类速查

追加表 2：我的MOD清单 / 替换覆盖总览

加粗的 10 张就是**物件域表**，每行一个可替换物件，是分类前缀判定的依据。

## 4 条硬不变量（改脚本务必守住）

1. **一个标签 ↔ 一行表格**。`scan_addons.mjs` 的 RULES 产出的标签，在 `enrich_ref_xlsx.py` 的映射里**只能对应一行**。
   多行共用一个标签 = 那几行会同时显示同一份 mod 列表（真实误判：佐伊（轻量版）被写成 Francis 的 mod）。
   `enrich_ref_xlsx.py` 启动即自检，正常打印 `[OK] 标签与表格行一一对应：N 个标签，无共用`。
2. **物件域 / 场景 / 固定武器类规则必须锚定 `^(models|materials)/`** —— 两头都不能少：
   - 只锚 `^models/` → 误伤「只改贴图」的物件 mod（实测梯子行从 `✅ 已替换` 退化成 `⚠ 仅附带覆盖`）
   - 完全不锚 → 误吞同名 sound 目录（实测 `/weapons\/50cal/` 抢走 `sound/weapons/50cal/`）
3. **多值单元格每个值都写全路径**，分隔符统一「、」；通配写 `*`，整目录以 `/` 结尾；
   **VPK 根目录下的文件直接写文件名**（如 `l4d2_background01.bik`）也算完整路径；说明性文字挪到备注列。
   `verify_fixes.py` 会核对「不合格条目数」必须为 0。
4. **路径必须先过 `normalizePath()` 再分类**。部分打包者把外层目录也打进 VPK：
   - `left 4 dead 2/left4dead2/media/valve.bik`（带完整外层）
   - `for_users/error_fix/left 4 dead 2/left4dead2/particles/x.pcf`（叠了两层）
   - `for_modders/particles/3p/x.pcf`、`for_modders/scripts (original)/weapon_x.txt`

   归一化 = 先剥 `for_users/`、`for_modders/`、`error_fix/`、`extras/`、`optional/` 等包装目录，
   再截到最早的「游戏根目录」（`models|materials|sound|particles|scripts|resource|maps|missions|modes|media|scenes|…`）。
   **验收标准：`unclassifiedPaths` 必须为 0。**

## 关键数据源

- `official_names.py` —— 游戏内官方英文名 + 本地化 Token 对照（硬编码，无需重解游戏文件）
- `scan_addons.json` —— 每个 VPK 的标签命中统计（含 `src`、`paths`、`targets`、`rawTop`、`prefixes`）
- `addons_by_target.json` —— 标签 → 覆盖它的 mod 列表
- `label_map.json` —— 标签 → `表名::行名`（221 个左右；enrich 自动产出）
- `rv_paths.json` —— 文件名 → 完整路径数组（由 `rv_dump_paths.mjs` 产出，命名链路用）

## 刷新后应看到的健康指标

```
parsed == scannedTotal          # 没有解析失败的 VPK
unclassifiedPaths == 0          # 路径 100% 归类
duplicateLabels == {}           # 标签无共用（不变量 1）
verify_rules: failed == []      # 分类断言全过
verify_fixes: 不合格条目数 == 0  # 不变量 3
```
