# -*- coding: utf-8 -*-
# ==== L4D2 skill: 统一路径解析（构建时注入，勿手改）====
import os as _os, json as _json
def _l4d2_home():
    h = _os.environ.get("L4D2_HOME")
    if h:
        return h
    return _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
L4D2_HOME = _l4d2_home()
def _l4d2_cfg():
    try:
        with open(_os.path.join(L4D2_HOME, "config.json"), encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}
L4D2_CFG = _l4d2_cfg()
L4D2_WORK = _os.path.join(L4D2_HOME, L4D2_CFG.get("scriptsDir", "_work"))
L4D2_XLSX = (_os.environ.get("L4D2_XLSX_OUT")
             or _os.path.join(L4D2_HOME, L4D2_CFG.get("xlsxName", "求生之路2_可MOD替换物品总表.xlsx")))
L4D2_ADDONS = (_os.environ.get("L4D2_ADDONS")
               or L4D2_CFG.get("addonsDir")
               or r"D:\Steam\steamapps\common\Left 4 Dead 2\left4dead2\addons")
# ==== 注入结束 ====
# -*- coding: utf-8 -*-
"""生成《求生之路2 可MOD替换物品总表》xlsx（基础数据表）

路径写法约定（缺陷 4 修正后统一执行）：
  * 单个模型 = 完整 VPK 路径，如 models/w_models/weapons/w_rifle_m16a2.mdl
  * 多个值用「、」分隔，且**每个值都写全路径**，不允许只给第一个带前缀
  * 通配/整目录用 `*` 或结尾 `/` 明确标出，说明性文字一律放「备注/说明」列
"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = L4D2_XLSX

# ---------------- addons 现状快照（动态统计，防止说明书/速查表里的数字过期）----------------
# 现行分类前缀（2026-10-03 定稿；旧 角色- / 武器- / 效果- 已废弃）
PREFIXES = ["生还者", "特感", "普感", "主武器", "副武器", "近战", "投掷物", "消耗品",
            "场景道具", "场景", "模型", "地图", "材质", "界面", "特效", "脚本", "音效",
            "手电筒", "管理员插件", "其它"]


def _scan_addons():
    """数一遍 addons 顶层 VPK 及其分类前缀，供说明/速查表引用（每次刷新都重算）"""
    try:
        names = [f for f in os.listdir(L4D2_ADDONS) if f.lower().endswith(".vpk")]
    except OSError:
        return 0, {}
    by = {}
    for n in names:
        hit = next((p for p in PREFIXES if n.startswith(p + "-")), "（无前缀）")
        by[hit] = by.get(hit, 0) + 1
    return len(names), by


ADDON_TOP, ADDON_BY_PREFIX = _scan_addons()

WM = "models/w_models/weapons/"      # 第三人称世界模型
VM = "models/v_models/"              # 第一人称手持模型
MM = "models/weapons/melee/"         # 近战武器模型


def safe_save(workbook, path, tries=3, wait=1.5):
    """xlsx 被 WPS / Excel 打开时会 EBUSY，重试几次再给出可读提示"""
    import time
    for i in range(tries):
        try:
            workbook.save(path)
            return
        except PermissionError:
            if i < tries - 1:
                time.sleep(wait)
    print("\n[错误] 无法写入：%s" % path)
    print("       该文件正被 WPS / Excel 占用。请关闭表格后重新运行。")
    raise SystemExit(2)


TITLE_FILL = PatternFill("solid", fgColor="1F3B57")
HEAD_FILL = PatternFill("solid", fgColor="2E6B4F")
ALT_FILL = PatternFill("solid", fgColor="F2F7F4")
THIN = Side(style="thin", color="BFCFC6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def add_sheet(wb, name, headers, rows, widths, tab_color=None, title=None):
    ws = wb.create_sheet(name)
    r = 1
    if title:
        ws.cell(row=1, column=1, value=title)
        ws.cell(row=1, column=1).font = Font(bold=True, size=13, color="FFFFFF")
        ws.cell(row=1, column=1).fill = TITLE_FILL
        ws.cell(row=1, column=1).alignment = Alignment(vertical="center", horizontal="left", indent=1)
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        ws.row_dimensions[1].height = 26
        r = 2
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[r].height = 28
    head_row = r
    for i, row in enumerate(rows):
        rr = head_row + 1 + i
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=rr, column=c, value=v)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.font = Font(size=10)
            cell.border = BORDER
            if i % 2 == 1:
                cell.fill = ALT_FILL
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = ws.cell(row=head_row + 1, column=1)
    ws.auto_filter.ref = f"A{head_row}:{get_column_letter(len(headers))}{head_row + len(rows)}"
    if tab_color:
        ws.sheet_properties.tabColor = tab_color
    return ws


wb = Workbook()
wb.remove(wb.active)

SL = "sound/player/survivor/voice/"
ARMS = "models/weapons/arms/"

# ---------------------------------------------------------------- 说明
add_sheet(
    wb, "说明", ["项目", "内容"], [
        ["表格用途", "求生之路2（Left 4 Dead 2）全部可被 MOD 替换的游戏内物件速查表。用于给 MOD 归类、填写「替换对象」、判断一个 VPK 到底覆盖了哪个游戏资源。"],
        ["覆盖范围", "生还者 8 人 / 特殊感染者 8 种 / 普通感染者 38 行变体 / 主武器 17 把 / 副武器 4 把 / 近战 17 种 / 投掷物 3 种 / 消耗品 4 种 / 场景道具 10 种 / 场景物件与固定武器 / 音效 / 界面·特效·材质·其他资源 / 手电筒 / 管理员插件。"],
        ["数据来源", "① 游戏本体 VPK 目录树（left4dead2/pak01_dir.vpk、left4dead2_dlc1~3、update/pak01_dir.vpk）共 38,004 条资源路径；② scripts/weapon_*.txt、scripts/melee/*.txt 脚本清单；③ resource/left4dead2_english.txt 官方字符串表；④ addons 下每个 VPK 的真实内部资源树（用于「替换状态」列）。"],
        ["⭐ 路径写法约定", "所有模型/音效单元格：单个值 = 完整 VPK 路径；多个值用「、」分隔且**每个值都是完整路径**（不允许只有第一条带目录）；通配写成 `models/.../xxx_*.mdl`，整目录写成 `models/.../xxx/`（以 / 结尾）；"
                          "**VPK 根目录下的文件直接写文件名**（如 `l4d2_background01.bik`、`addoninfo.txt`），这也是完整路径；说明性文字一律放「备注/说明」列，不混进路径列。"],
        ["⭐ VPK 计数口径", "addons 顶层目录下 VPK **%d 个**（本表生成时动态统计，不是写死的）；另外**额外纳入 `cfhd\\pak01_dir.vpk` 1 个**（拆分式 VPK 的目录文件，仅含索引树）。所以「我的MOD清单」共 %d 行 = %d + 1，明细见该表「来源」列。" % (ADDON_TOP, ADDON_TOP + 1, ADDON_TOP)],
        ["重要结论", "「update/」是 The Last Stand（2020）更新包，干草叉、铁铲、L4D1 版感染者皮肤、v_arms 手臂等只在 update/ 里，老版本游戏或旧整合包可能缺失。"],
        ["MOD 安装位置", "① VPK 形式：丢进 left4dead2\\addons\\，游戏自动挂载（推荐）；② 散件形式：按同名目录结构放到 left4dead2\\ 下（models/ materials/ sound/ 等），会覆盖原文件；③ 本地服务器插件（SourceMod）：left4dead2\\addons\\sourcemod\\。"],
        ["addoninfo.txt", "自制 VPK 时打包根目录需含 addoninfo.txt，至少要写 addonTitle。缺了它游戏里能加载但不显示名称。"],
        ["同一物件多个 MOD", "多个 MOD 改同一个文件时，按 addons 文件夹加载顺序后者覆盖前者；散件（left4dead2 根目录）优先级高于所有 VPK。"],
        ["模型三件套", "任何 .mdl 都必须同时提供同名 .vvd / .dx90.vtx（有的还要 .phy / .ani），只换 .mdl 不换贴图会出现白模或模型错乱。.vmt 是指向 .vtf 的材质脚本。"],
        ["命名规律", "w_ 前缀 = 第三人称世界里看到的模型；v_ 前缀 = 第一人称手持模型；models/weapons/arms/v_arms_*.mdl = 第一人称手臂（分角色，可单独换）。"],
        ["替换对象建议写法", "现行 **19 个前缀**（2026-10-03 定稿，含当日新增的 手电筒- / 管理员插件-）：物件域 生还者- / 特感- / 普感- / 主武器- / 副武器- / 近战- / 投掷物- / 消耗品- / 场景道具- / 场景-；"
                          "资源类型 模型- / 地图- / 材质- / 界面- / 特效- / 脚本- / 音效- / 手电筒- / 管理员插件-；兜底 其它-。"
                          "写法 `<分类>-<替换对象>-<原标题>`；生还者 / 特感 用官方**英文名**（Coach / Boomer），其余物件域用官方**中文名**（AK-47 突击步枪 / 武士刀 / 马格南手枪）；"
                          "资源类型前缀与低置信项**省略中段**。中段取值细则见 _work\\工作流规范_分类命名.md。"
                          "旧 角色- / 武器- / 效果- 已废弃（角色- 拆成 生还者/特感/普感，武器- 拆成 主武器/副武器/近战/投掷物/消耗品，效果- 并入 特效-/材质-）。"],
        ["版本说明", "本表以 2026 年最新版本（含 The Last Stand 更新）为准。标注「TLS」的条目为 2020 年更新后新增。"],
    ],
    [22, 158], "1F3B57", "求生之路2 可 MOD 替换物品总表 · 使用说明")

# ---------------------------------------------------------------- 生还者
SURV = [
    ["1", "教练", "Coach", "coach", "models/survivors/survivor_coach.mdl", ARMS + "v_arms_coach_new.mdl", SL + "coach/", "模型 / 贴图 / 语音 / 头像 / 手臂", "L4D2 主角，近战范围略大"],
    ["2", "埃利斯", "Ellis", "mechanic", "models/survivors/survivor_mechanic.mdl", ARMS + "v_arms_mechanic_new.mdl", SL + "mechanic/", "模型 / 贴图 / 语音 / 头像 / 手臂", "L4D2 主角，修车工"],
    ["3", "尼克", "Nick", "gambler", "models/survivors/survivor_gambler.mdl", ARMS + "v_arms_gambler_new.mdl", SL + "gambler/", "模型 / 贴图 / 语音 / 头像 / 手臂", "L4D2 主角，骗子"],
    ["4", "罗谢尔", "Rochelle", "producer", "models/survivors/survivor_producer.mdl", ARMS + "v_arms_producer_new.mdl", SL + "producer/", "模型 / 贴图 / 语音 / 头像 / 手臂", "L4D2 主角，制片助理"],
    ["5", "比尔", "Bill", "namvet", "models/survivors/survivor_namvet.mdl", ARMS + "v_arms_bill.mdl", SL + "namvet/", "模型 / 贴图 / 语音 / 头像 / 手臂", "L4D1 老兵；DLC「The Passing」起可用"],
    ["6", "弗朗西斯", "Francis", "biker", "models/survivors/survivor_biker.mdl", ARMS + "v_arms_francis.mdl", SL + "biker/", "模型 / 贴图 / 语音 / 头像 / 手臂", "L4D1 飞车党"],
    ["7", "路易斯", "Louis", "manager", "models/survivors/survivor_manager.mdl", ARMS + "v_arms_louis.mdl", SL + "manager/", "模型 / 贴图 / 语音 / 头像 / 手臂", "L4D1 系统分析员"],
    ["8", "佐伊", "Zoey", "teenangst", "models/survivors/survivor_teenangst.mdl", ARMS + "v_arms_zoey.mdl", SL + "teenangst/", "模型 / 贴图 / 语音 / 头像 / 手臂", "L4D1 大学生"],
    ["9", "弗朗西斯（轻量版）", "Francis (Light)", "biker_light", "models/survivors/survivor_biker_light.mdl", "—", SL + "biker/", "模型 / 贴图", "低配模型，部分模式/远景使用"],
    ["10", "佐伊（轻量版）", "Zoey (Light)", "teenangst_light", "models/survivors/survivor_teenangst_light.mdl", "—", SL + "teenangst/", "模型 / 贴图", "低配模型，部分模式/远景使用"],
    ["11", "生还者骨架动画", "Survivor Skeletons (anim)", "anim_*", "models/survivors/anim_coach.mdl、models/survivors/anim_mechanic.mdl、models/survivors/anim_gambler.mdl、models/survivors/anim_producer.mdl、models/survivors/anim_biker.mdl、models/survivors/anim_namvet.mdl、models/survivors/anim_manager.mdl、models/survivors/anim_teenangst.mdl、models/survivors/anim_gestures.mdl", "—", "—", "动画骨架", "换动作/姿势类 MOD 改这里；与主体模型必须配套"],
    ["12", "生还者手势", "Survivor Gestures", "gestures_*", "models/survivors/gestures_coach.mdl、models/survivors/gestures_mechanic.mdl、models/survivors/gestures_gambler.mdl、models/survivors/gestures_producer.mdl、models/survivors/gestures_biker.mdl、models/survivors/gestures_namvet.mdl、models/survivors/gestures_teenangst.mdl", "—", "—", "动作", "招手、指路等互动动作"],
    ["13", "生还者通用音效", "Survivor Common SFX", "—", "—", "—", "sound/player/survivor/heal/、sound/player/survivor/hit/、sound/player/survivor/splat/、sound/player/survivor/swing/", "音效", "治疗、受击、血溅、挥击音效，四人共用"],
    ["14", "生还者语音", "Survivor Voice", "—", "—", "—", SL + "coach/、sound/player/survivor/voice/gambler/、sound/player/survivor/voice/mechanic/、sound/player/survivor/voice/producer/、sound/player/survivor/voice/biker/、sound/player/survivor/voice/namvet/、sound/player/survivor/voice/manager/、sound/player/survivor/voice/teenangst/", "语音（大量 .wav）", "中文语音包/日语语音包改这里"],
]
add_sheet(wb, "生还者", ["#", "中文名", "英文名", "内部代号", "角色模型路径 (.mdl)", "第一人称手臂模型", "语音音效目录", "可替换内容", "备注"],
          SURV, [5, 20, 22, 16, 60, 44, 60, 26, 30], "2E6B4F", "生还者（Survivors）· 共 8 名可用角色")

# ---------------------------------------------------------------- 特殊感染者
SI = [
    ["1", "呕吐者", "Boomer", "boomer", "models/infected/boomer.mdl", "sound/player/boomer/", "模型 / 贴图 / 音效", "呕吐胆汁吸引尸潮"],
    ["2", "女呕吐者", "Boomette", "boomette", "models/infected/boomette.mdl", "sound/player/boomer/", "模型 / 贴图", "罕见女性变体"],
    ["3", "烟鬼", "Smoker", "smoker", "models/infected/smoker.mdl", "sound/player/smoker/", "模型 / 贴图 / 音效", "长舌拖拽"],
    ["4", "猎人", "Hunter", "hunter", "models/infected/hunter.mdl", "sound/player/hunter/", "模型 / 贴图 / 音效", "扑倒"],
    ["5", "坦克（巨兽）", "Tank", "hulk", "models/infected/hulk.mdl", "sound/player/tank/", "模型 / 贴图 / 音效", "Boss，血量极高"],
    ["6", "坦克（Cold Stream 版）", "Tank (Cold Stream)", "hulk_dlc3", "models/infected/hulk_dlc3.mdl", "sound/player/tank/", "模型 / 贴图", "DLC3 专用皮肤"],
    ["7", "女巫", "Witch", "witch", "models/infected/witch.mdl", "sound/npc/witch/", "模型 / 贴图 / 音效", "被动 Boss，被惊动后追杀"],
    ["8", "新娘女巫", "Witch Bride", "witch_bride", "models/infected/witch_bride.mdl", "sound/npc/witch/", "模型 / 贴图", "DLC1「The Passing」专属"],
    ["9", "冲撞者", "Charger", "charger", "models/infected/charger.mdl", "sound/player/charger/", "模型 / 贴图 / 音效", "冲撞抓取"],
    ["10", "骑师", "Jockey", "jockey", "models/infected/jockey.mdl", "sound/player/jockey/", "模型 / 贴图 / 音效", "骑乘控制"],
    ["11", "喷酸者", "Spitter", "spitter", "models/infected/spitter.mdl", "sound/player/spitter/", "模型 / 贴图 / 音效", "喷酸池"],
    ["12", "L4D1 版感染者模型", "L4D1 Variant Models", "*_l4d1", "models/infected/boomer_l4d1.mdl、models/infected/hunter_l4d1.mdl、models/infected/smoker_l4d1.mdl、models/infected/hulk_l4d1.mdl", "sound/player/boomer/、sound/player/smoker/、sound/player/hunter/、sound/player/tank/", "模型 / 贴图", "玩 L4D1 战役时替换用"],
    ["13", "感染者第一人称爪（第三人称视角模式）", "Infected View Claws", "v_claw_*", "models/v_models/weapons/v_claw_boomer.mdl、models/v_models/weapons/v_claw_hulk.mdl、models/v_models/weapons/v_claw_hunter.mdl、models/v_models/weapons/v_claw_smoker.mdl、models/v_models/weapons/v_claw_boomer_l4d1.mdl、models/v_models/weapons/v_claw_hulk_l4d1.mdl、models/v_models/weapons/v_claw_hunter_l4d1.mdl、models/v_models/weapons/v_claw_smoker_l4d1.mdl、models/v_models/weapons/v_claw_hulk_dlc3.mdl", "sound/player/<角色>/", "模型 / 贴图", "对抗模式扮演感染者时的手部模型"],
    ["14", "感染者手臂", "Infected Arms", "v_*_arms", "models/weapons/arms/v_charger_arms.mdl、models/weapons/arms/v_jockey_arms.mdl、models/weapons/arms/v_spitter_arms.mdl", "—", "模型 / 贴图", "三个新感染者的手臂"],
    ["15", "爆炸残肢", "Boomer Explosion Gibs", "limbs/exploded_boomer*", "models/infected/limbs/exploded_boomer.mdl、models/infected/limbs/exploded_boomer_head.mdl、models/infected/limbs/exploded_boomer_rarm.mdl、models/infected/limbs/exploded_boomer_steak1.mdl、models/infected/limbs/exploded_boomer_steak2.mdl、models/infected/limbs/exploded_boomer_steak3.mdl、models/infected/limbs/exploded_boomette.mdl", "—", "模型 / 贴图", "Boomer 被击杀后的爆开残骸；与普通感染者的「血块与碎尸」是两套资源"],
]
add_sheet(wb, "特殊感染者", ["#", "中文名", "英文名", "内部代号", "模型路径 (.mdl)", "音效目录", "可替换内容", "备注"],
          SI, [5, 24, 26, 20, 96, 24, 22, 40], "7A3030", "特殊感染者（Special Infected）· 共 8 种")

# ---------------------------------------------------------------- 普通感染者
COMMON = [
    ["1", "普通男性感染者（基础）", "Common Male 01", "common_male01", "models/infected/common_male01.mdl", "普通"],
    ["2", "普通男性感染者 2", "Common Male 02", "common_male02", "models/infected/common_male02.mdl", "普通"],
    ["3", "普通女性感染者（基础）", "Common Female 01", "common_female01", "models/infected/common_female01.mdl", "普通"],
    ["4", "女性感染者（套装）", "Common Female Suit", "common_female01_suit", "models/infected/common_female01_suit.mdl", "普通"],
    ["5", "女性感染者（农村）", "Common Female Rural", "common_female_rural01", "models/infected/common_female_rural01.mdl", "普通"],
    ["6", "女性感染者（护士）", "Common Female Nurse", "common_female_nurse01", "models/infected/common_female_nurse01.mdl", "非普通（医院）"],
    ["7", "女性感染者（行李员）", "Common Female Baggage", "common_female_baggagehandler_01", "models/infected/common_female_baggagehandler_01.mdl", "普通"],
    ["8", "女性感染者（背心牛仔裤）", "Common Female Tanktop Jeans", "common_female_tanktop_jeans", "models/infected/common_female_tanktop_jeans.mdl、models/infected/common_female_tanktop_jeans_rain.mdl、models/infected/common_female_tanktop_jeans_swamp.mdl", "普通"],
    ["9", "女性感染者（T恤短裙）", "Common Female Tshirt Skirt", "common_female_tshirt_skirt", "models/infected/common_female_tshirt_skirt.mdl、models/infected/common_female_tshirt_skirt_swamp.mdl", "普通"],
    ["10", "女性感染者（正式礼服）", "Common Female Formal", "common_female_formal", "models/infected/common_female_formal.mdl", "普通"],
    ["11", "男性（西装）", "Common Male Suit", "common_male_suit", "models/infected/common_male_suit.mdl", "普通"],
    ["12", "男性（T恤工装裤）", "Common Male Tshirt Cargos", "common_male_tshirt_cargos", "models/infected/common_male_tshirt_cargos.mdl、models/infected/common_male_tshirt_cargos_swamp.mdl", "普通"],
    ["13", "男性（背心牛仔裤）", "Common Male Tanktop Jeans", "common_male_tanktop_jeans", "models/infected/common_male_tanktop_jeans.mdl、models/infected/common_male_tanktop_jeans_rain.mdl、models/infected/common_male_tanktop_jeans_swamp.mdl", "普通"],
    ["14", "男性（背心背带裤）", "Common Male Tanktop Overalls", "common_male_tanktop_overalls", "models/infected/common_male_tanktop_overalls.mdl、models/infected/common_male_tanktop_overalls_rain.mdl、models/infected/common_male_tanktop_overalls_swamp.mdl", "普通"],
    ["15", "男性（衬衫牛仔裤）", "Common Male Dressshirt Jeans", "common_male_dressshirt_jeans", "models/infected/common_male_dressshirt_jeans.mdl", "普通"],
    ["16", "男性（正式礼服）", "Common Male Formal", "common_male_formal", "models/infected/common_male_formal.mdl", "普通"],
    ["17", "男性（摩托车手）", "Common Male Biker", "common_male_biker", "models/infected/common_male_biker.mdl", "普通"],
    ["18", "男性（花花公子）", "Common Male Polo Jeans", "common_male_polo_jeans", "models/infected/common_male_polo_jeans.mdl", "普通"],
    ["19", "男性（乡村）", "Common Male Rural", "common_male_rural01", "models/infected/common_male_rural01.mdl", "普通"],
    ["20", "男性（行李搬运工）", "Common Male Baggage Handler", "common_male_baggagehandler_01/02", "models/infected/common_male_baggagehandler_01.mdl、models/infected/common_male_baggagehandler_02.mdl", "普通（机场）"],
    ["21", "CEDA 工作人员", "CEDA Worker", "common_male_ceda", "models/infected/common_male_ceda.mdl", "非普通（防化服，抗爆）"],
    ["22", "小丑", "Clown", "common_male_clown", "models/infected/common_male_clown.mdl", "非普通（Dark Carnival，会尖叫引怪）"],
    ["23", "泥人", "Mudman", "common_male_mud", "models/infected/common_male_mud.mdl", "非普通（Swamp Fever，泥土护甲）"],
    ["24", "防暴警察", "Riot Infected", "common_male_riot", "models/infected/common_male_riot.mdl", "非普通（正面防弹衣 + 防暴盾）"],
    ["25", "筑路工", "Road Crew", "common_male_roadcrew", "models/infected/common_male_roadcrew.mdl、models/infected/common_male_roadcrew_rain.mdl", "非普通（Hard Rain，戴耳罩+雨衣）"],
    ["26", "堕落生还者", "Fallen Survivor", "common_male_fallen_survivor", "models/infected/common_male_fallen_survivor.mdl", "非普通（携带补给，击杀掉落）"],
    ["27", "吉米·吉布斯二世", "Jimmy Gibbs Jr.", "common_male_jimmy", "models/infected/common_male_jimmy.mdl", "非普通（Dead Center 终点专属彩蛋）"],
    ["28", "伞兵", "Parachutist", "common_male_parachutist", "models/infected/common_male_parachutist.mdl", "普通（挂在建筑上的尸袋/尸体）"],
    ["29", "飞行员", "Pilot", "common_male_pilot", "models/infected/common_male_pilot.mdl", "普通"],
    ["30", "警察", "Police Officer", "common_police_male01", "models/infected/common_police_male01.mdl", "非普通（防弹衣）"],
    ["31", "军人", "Soldier", "common_military_male01", "models/infected/common_military_male01.mdl", "非普通（防弹衣）"],
    ["32", "外科医生", "Surgeon", "common_surgeon_male01", "models/infected/common_surgeon_male01.mdl", "普通"],
    ["33", "病人", "Patient", "common_patient_male01", "models/infected/common_patient_male01.mdl、models/infected/common_patient_male01_l4d2.mdl", "普通（病号服）"],
    ["34", "工人", "Worker", "common_worker_male01", "models/infected/common_worker_male01.mdl", "普通"],
    ["35", "TSA 安检员", "TSA Agent", "common_tsaagent_male01", "models/infected/common_tsaagent_male01.mdl", "普通"],
    ["36", "女性感染者残肢模型", "Female Common Body Parts", "common_fem_infected_w_*", "models/infected/common_fem_infected_w_*.mdl", "部件（破坏效果，全部普通感染者共用）"],
    ["37", "普通感染者残肢模型", "Common Body Parts", "common_infected_w_*", "models/infected/common_infected_w_*.mdl", "部件（破坏效果，全部普通感染者共用）"],
    ["38", "血块与碎尸", "Common Infected Gibs", "gibs + limbs", "models/infected/gibs/gibs.mdl、models/infected/limbs/common_infected_w_*.mdl、models/infected/limbs/limb_male_*.mdl", "通用碎尸与断肢（不含 Boomer 爆开残骸）"],
]
add_sheet(wb, "普通感染者", ["#", "中文名", "英文名", "内部代号", "模型路径 (.mdl)", "类型"],
          COMMON, [5, 30, 32, 34, 96, 44], "6B5B2E", "普通感染者（Common Infected）· 含非普通感染者，共 38 行")

# ---------------------------------------------------------------- 主武器
PRIMARY = [
    ["1", "T1", "泵动式霰弹枪", "Pump Shotgun", "weapon_pumpshotgun", WM + "w_pumpshotgun_a.mdl", VM + "v_pumpshotgun.mdl", "sound/weapons/shotgun/", "初始武器，8 发"],
    ["2", "T1", "镀铬霰弹枪", "Chrome Shotgun", "weapon_shotgun_chrome", WM + "w_shotgun.mdl", VM + "v_shotgun_chrome.mdl", "sound/weapons/shotgun_chrome/", "射程略远于泵动"],
    ["3", "T1", "冲锋枪（乌兹）", "Submachine Gun", "weapon_smg", WM + "w_smg_uzi.mdl", VM + "v_smg.mdl", "sound/weapons/smg/", "初始武器，50 发"],
    ["4", "T1", "消音冲锋枪", "Silenced SMG", "weapon_smg_silenced", WM + "w_smg_a.mdl", VM + "v_silenced_smg.mdl", "sound/weapons/smg_silenced/", "MAC-10，弹道更稳"],
    ["5", "T2", "战术霰弹枪", "Tactical Shotgun", "weapon_autoshotgun", WM + "w_autoshot_m4super.mdl", VM + "v_autoshotgun.mdl", "sound/weapons/auto_shotgun/", "半自动霰弹枪"],
    ["6", "T2", "战斗霰弹枪", "Combat Shotgun", "weapon_shotgun_spas", WM + "w_shotgun_spas.mdl", VM + "v_shotgun_spas.mdl", "sound/weapons/auto_shotgun_spas/", "SPAS，弹匣供弹"],
    ["7", "T2", "猎枪", "Hunting Rifle", "weapon_hunting_rifle", WM + "w_sniper_mini14.mdl", VM + "v_huntingrifle.mdl", "sound/weapons/hunting_rifle/", "Mini-14，无限穿透"],
    ["8", "T2", "狙击步枪", "Sniper Rifle", "weapon_sniper_military", WM + "w_sniper_military.mdl", VM + "v_sniper_military.mdl", "sound/weapons/sniper_military/", "军用狙击，带瞄准镜"],
    ["9", "T2", "M-16 突击步枪", "M-16 Assault Rifle", "weapon_rifle", WM + "w_rifle_m16a2.mdl", VM + "v_rifle.mdl", "sound/weapons/rifle/", "通用性最好的步枪"],
    ["10", "T2", "战斗步枪", "Combat Rifle", "weapon_rifle_desert", WM + "w_desert_rifle.mdl", VM + "v_desert_rifle.mdl", "sound/weapons/rifle_desert/", "SCAR，三连发，精度高"],
    ["11", "T2", "AK-47 突击步枪", "AK-47", "weapon_rifle_ak47", WM + "w_rifle_ak47.mdl", VM + "v_rifle_ak47.mdl", "sound/weapons/rifle_ak47/", "单发伤害最高"],
    ["12", "T3", "榴弹发射器", "Grenade Launcher", "weapon_grenade_launcher", WM + "w_grenade_launcher.mdl", VM + "v_grenade_launcher.mdl", "sound/weapons/grenade_launcher/", "弹药箱不可补给；对 Tank 3 倍伤害"],
    ["13", "T3", "M60 机枪", "M60 Machine Gun", "weapon_rifle_m60", WM + "w_m60.mdl", VM + "v_m60.mdl", "—", "弹药箱不可补给，打完即弃"],
    ["14", "TLS", "MP5 冲锋枪", "MP5", "weapon_smg_mp5", WM + "w_smg_mp5.mdl", VM + "v_smg_mp5.mdl", "sound/weapons/mp5navy/", "原德版独占，TLS 后全版本可拾取"],
    ["15", "TLS", "SG552 突击步枪", "SG 552", "weapon_rifle_sg552", WM + "w_rifle_sg552.mdl", VM + "v_rif_sg552.mdl", "sound/weapons/sg552/", "带瞄准镜的步枪"],
    ["16", "TLS", "Scout 狙击枪", "Scout", "weapon_sniper_scout", WM + "w_sniper_scout.mdl", VM + "v_snip_scout.mdl", "sound/weapons/scout/", "轻量狙击枪"],
    ["17", "TLS", "AWP 狙击枪", "AWP", "weapon_sniper_awp", WM + "w_sniper_awp.mdl", VM + "v_snip_awp.mdl", "sound/weapons/awp/", "重狙击枪"],
]
add_sheet(wb, "主武器", ["#", "等级", "中文名", "英文名", "实体名（生成码）", "第三人称世界模型 w_", "第一人称手持模型 v_", "音效目录", "备注"],
          PRIMARY, [5, 7, 24, 24, 26, 48, 40, 34, 40], "8A5A20",
          "主武器（Primary Weapons）· 17 把　·　模型均位于 models/w_models/weapons/ 与 models/v_models/")

# ---------------------------------------------------------------- 副武器（手枪）
SIDEARMS = [
    ["1", "手枪", "手枪（P220）", "Pistol", "weapon_pistol", WM + "w_pistol_a.mdl", VM + "v_pistol.mdl", "sound/weapons/pistol/", "无限弹药，倒地可用"],
    ["2", "手枪", "格洛克手枪", "Glock", "weapon_pistol", WM + "w_pistol_b.mdl", VM + "v_pistola.mdl", "sound/weapons/pistol_silver/", "双持时出现在左手，无手电"],
    ["3", "手枪", "双持手枪", "Dual Pistols", "weapon_pistol（双持）", WM + "w_pistol_a_dual.mdl", VM + "v_dual_pistola.mdl", "sound/weapons/dual_pistol/", "两把 P220"],
    ["4", "手枪", "马格南手枪", "Magnum Pistol", "weapon_pistol_magnum", WM + "w_desert_eagle.mdl", VM + "v_desert_eagle.mdl", "sound/weapons/magnum/", "沙漠之鹰，可一枪爆头"],
]
add_sheet(wb, "副武器", ["#", "类型", "中文名", "英文名", "实体名（生成码）", "第三人称世界模型 w_", "第一人称手持模型 v_", "音效目录", "备注"],
          SIDEARMS, [5, 12, 20, 22, 34, 44, 36, 36, 46], "46527A",
          "副武器 / 手枪（Sidearms）· 共 4 把　·　模型位于 models/w_models/weapons/ 与 models/v_models/")

# ---------------------------------------------------------------- 近战武器
MELEE = [
    ["1", "近战", "消防斧", "Fire Axe", "weapon_melee (fireaxe)", MM + "w_fireaxe.mdl", MM + "v_fireaxe.mdl", "sound/weapons/axe/", "伤害 90，可断肢"],
    ["2", "近战", "棒球棍", "Baseball Bat", "weapon_melee (baseball_bat)", MM + "w_bat.mdl", MM + "v_bat.mdl", "sound/weapons/bat/", "击退强"],
    ["3", "近战", "板球棒", "Cricket Bat", "weapon_melee (cricket_bat)", MM + "w_cricket_bat.mdl", MM + "v_cricket_bat.mdl", "sound/weapons/bat/", "同棒球棍"],
    ["4", "近战", "撬棍", "Crowbar", "weapon_melee (crowbar)", MM + "w_crowbar.mdl", MM + "v_crowbar.mdl", "sound/weapons/crowbar/", "经典武器"],
    ["5", "近战", "平底锅", "Frying Pan", "weapon_melee (frying_pan)", MM + "w_frying_pan.mdl", MM + "v_frying_pan.mdl", "sound/weapons/pan/", "击中音效独特"],
    ["6", "近战", "高尔夫球杆", "Golf Club", "weapon_melee (golfclub)", MM + "w_golfclub.mdl", MM + "v_golfclub.mdl", "—", "DLC1 加入；无声效目录，复用通用挥击音"],
    ["7", "近战", "电吉他", "Electric Guitar", "weapon_melee (electric_guitar)", MM + "w_electric_guitar.mdl", MM + "v_electric_guitar.mdl", "sound/weapons/guitar/", "有音效彩蛋"],
    ["8", "近战", "武士刀", "Katana", "weapon_melee (katana)", MM + "w_katana.mdl", MM + "v_katana.mdl", "sound/weapons/katana/", "伤害 70，速度最快之一"],
    ["9", "近战", "砍刀", "Machete", "weapon_melee (machete)", MM + "w_machete.mdl", MM + "v_machete.mdl", "sound/weapons/machete/", "断肢利器"],
    ["10", "近战", "警棍", "Nightstick", "weapon_melee (tonfa)", MM + "w_tonfa.mdl", MM + "v_tonfa.mdl", "sound/weapons/tonfa/", "内部脚本名是 tonfa"],
    ["11", "近战", "干草叉", "Pitchfork", "weapon_melee (pitchfork)", MM + "w_pitchfork.mdl", MM + "v_pitchfork.mdl", "update/sound/weapons/pitchfork/", "TLS 新增，PC 版限定"],
    ["12", "近战", "铁铲", "Shovel", "weapon_melee (shovel)", MM + "w_shovel.mdl", MM + "v_shovel.mdl", "update/sound/weapons/shovel/", "TLS 新增，PC 版限定"],
    ["13", "近战", "战斗刀", "Knife", "weapon_melee (knife)", WM + "w_knife_t.mdl", VM + "v_knife_t.mdl", "sound/weapons/knife/", "原德版/TLS 解锁；模型在 w_models/v_models，不在 melee/ 下"],
    ["14", "特殊近战", "电锯", "Chainsaw", "weapon_chainsaw", MM + "w_chainsaw.mdl", MM + "v_chainsaw.mdl", "sound/weapons/chainsaw/", "伤害 100×10/秒，燃油有限不可补"],
    ["15", "特殊近战", "花园地精", "Gnome Chompski", "weapon_gnome", "models/props_junk/gnome.mdl", MM + "v_gnome.mdl", "sound/level/gnomeftw.wav", "搞笑彩蛋武器"],
    ["16", "特殊近战", "迪吉里杜管", "Didgeridoo", "—", MM + "w_didgeridoo.mdl", "—", "—", "澳版电吉他替代模型，正式版未启用"],
    ["17", "未启用", "防暴盾", "Riot Shield", "—", MM + "w_riotshield.mdl", MM + "v_riotshield.mdl", "—", "被删除的武器，文件仍在，防暴感染者有同款"],
]
add_sheet(wb, "近战", ["#", "类型", "中文名", "英文名", "实体名（生成码）", "第三人称世界模型 w_", "第一人称手持模型 v_", "音效目录", "备注"],
          MELEE, [5, 12, 20, 22, 34, 44, 40, 36, 48], "6A3A6A",
          "近战武器（Melee）· 共 17 种　·　模型位于 models/weapons/melee/（战斗刀例外，见备注）")

# ---------------------------------------------------------------- 投掷物
THROWABLES = [
    ["1", "投掷物", "燃烧瓶", "Molotov Cocktail", "weapon_molotov", WM + "w_eq_molotov.mdl", VM + "v_molotov.mdl", "sound/weapons/molotov/", "particles/fire_01l4d.pcf", "燃烧地面，封锁路线"],
    ["2", "投掷物", "管状炸弹", "Pipe Bomb", "weapon_pipe_bomb", WM + "w_eq_pipebomb.mdl", VM + "v_pipebomb.mdl", "sound/weapons/fx/", "particles/gen_dest_fx.pcf", "爆炸吸引尸潮"],
    ["3", "投掷物", "胆汁炸弹", "Bile Bomb", "weapon_vomitjar", WM + "w_eq_bile_flask.mdl", VM + "v_bile_flask.mdl", "sound/weapons/ceda_jar/", "particles/boomer_fx.pcf", "L4D2 新增，吸引尸潮更久"],
]
add_sheet(wb, "投掷物", ["#", "类型", "中文名", "英文名", "实体名（生成码）", "第三人称世界模型 w_", "第一人称手持模型 v_", "音效目录", "粒子特效 .pcf", "备注"],
          THROWABLES, [5, 10, 18, 22, 28, 42, 34, 32, 30, 44], "7A5A1F",
          "投掷物 / 手雷（Grenades）· 共 3 种，每次只能携带一个　·　模型位于 models/w_models/weapons/（w_eq_ 前缀）与 models/v_models/")

# ---------------------------------------------------------------- 消耗品
CONSUMABLES = [
    ["1", "消耗品", "急救包", "First Aid Kit", "weapon_first_aid_kit", WM + "w_eq_medkit.mdl", VM + "v_medkit.mdl", "sound/player/survivor/heal/", "—", "回满血，可治疗队友"],
    ["2", "消耗品", "止痛药", "Pain Pills", "weapon_pain_pills", WM + "w_eq_painpills.mdl", VM + "v_painpills.mdl", "sound/player/survivor/heal/", "—", "临时血量，会衰减"],
    ["3", "消耗品", "肾上腺素", "Adrenaline Shot", "weapon_adrenaline", WM + "w_eq_adrenaline.mdl", VM + "v_adrenaline.mdl", "sound/weapons/adrenaline/", "—", "L4D2 新增，提速+免减速"],
    ["4", "消耗品", "除颤器", "Defibrillator", "weapon_defibrillator", WM + "w_eq_defibrillator.mdl", VM + "v_defibrillator.mdl", "sound/weapons/defibrillator/", "—", "L4D2 新增，复活死亡队友"],
]
add_sheet(wb, "消耗品", ["#", "类型", "中文名", "英文名", "实体名（生成码）", "第三人称世界模型 w_", "第一人称手持模型 v_", "音效目录", "粒子特效 .pcf", "备注"],
          CONSUMABLES, [5, 10, 18, 22, 28, 42, 34, 32, 30, 44], "2F6B6B",
          "消耗品 / 医疗补给（Usable Items）· 共 4 种　·　这些不是投掷物，按左键使用　·　模型位于 models/w_models/weapons/（w_eq_ 前缀）与 models/v_models/")

# ---------------------------------------------------------------- 场景道具
UPG = [
    ["1", "武器升级", "高爆弹药", "Explosive Ammo", "weapon_upgradepack_explosive", WM + "w_eq_explosive_ammopack.mdl", VM + "v_explosive_ammopack.mdl", "弹药附带爆炸伤害，可穿透尸群"],
    ["2", "武器升级", "燃烧弹药", "Incendiary Ammo", "weapon_upgradepack_incendiary", WM + "w_eq_incendiary_ammopack.mdl", VM + "v_incendiary_ammopack.mdl", "弹药点燃目标"],
    ["3", "武器升级", "激光瞄准器", "Laser Sight", "upgrade_laser_sight", WM + "w_laser_sights.mdl", "—", "提升精度，绿色激光；挂在枪上，无独立手持模型"],
    ["4", "特殊道具", "可乐（可乐瓶）", "Cola Bottles", "weapon_cola_bottles", WM + "w_cola.mdl", VM + "v_cola.mdl", "Dead Center 收集任务用"],
    ["5", "特殊道具", "花园地精", "Gnome Chompski", "weapon_gnome", "models/props_junk/gnome.mdl", MM + "v_gnome.mdl", "Hard Rain 成就任务/近战武器"],
    ["6", "场景物件", "汽油桶", "Gas Can", "weapon_gascan", "models/props_junk/gascan001a.mdl", "models/props_junk/gascan001a.mdl", "可搬动，燃烧/灌油任务；手持=世界模型"],
    ["7", "场景物件", "丙烷罐", "Propane Tank", "weapon_propanetank", "models/props_junk/propanecanister001a.mdl", "models/props_junk/propanecanister001a.mdl", "可搬动，射击引爆；手持=世界模型"],
    ["8", "场景物件", "氧气罐", "Oxygen Tank", "weapon_oxygentank", "models/props_equipment/oxygentank01.mdl", "models/props_equipment/oxygentank01.mdl", "可搬动，射击引爆且飞得远；手持=世界模型"],
    ["9", "场景物件", "烟花盒", "Fireworks Crate", "weapon_fireworkcrate", "models/props_junk/explosive_box001.mdl", "models/props_junk/explosive_box001.mdl", "L4D2 新增，可搬动；粒子 firework_crate_fx.pcf；手持=世界模型"],
    ["10", "场景物件", "爆炸油桶", "Explosive Barrel", "prop_physics（地图摆放并带爆炸属性）", "models/props_urban/oil_drum001.mdl、models/props_c17/oildrum001.mdl", "—", "红色油桶，被击中或受爆炸波及即引爆"],
]
add_sheet(wb, "场景道具", ["#", "类型", "中文名", "英文名", "实体名（生成码）", "第三人称世界模型 w_", "第一人称手持模型 v_", "说明"],
          UPG, [5, 12, 22, 24, 34, 62, 46, 52], "5C3A70",
          "场景道具（Upgrades / Special / Placeable Items）· 含武器升级 3 种、特殊道具 2 种、可搬动场景物件 5 种")

# ---------------------------------------------------------------- 固定武器·场景
FIXED = [
    ["1", "固定武器", "米尼岗机枪", "Minigun", "地图实体（地图内摆放的固定机枪）", WM + "w_minigun.mdl", "sound/weapons/minigun/", "L4D1 终章固定机枪，弹幕压制"],
    ["2", "固定武器", "重机枪（.50 口径）", "Heavy Machine Gun (.50 cal)", "地图实体（地图内摆放的固定机枪）", WM + "50cal.mdl", "sound/weapons/50cal/", "L4D2 终章固定机枪，连射会过热"],
    ["3", "固定武器", "损坏的重机枪", "Broken HMG", "—", WM + "50_cal_broken.mdl", "—", "被摧毁状态的模型"],
    ["4", "场景道具", "榴弹（榴弹发射器弹体）", "HE Grenade", "—", WM + "w_he_grenade.mdl", "sound/weapons/hegrenade/", "榴弹发射器打出的弹体"],
    ["5", "场景道具", "火箭弹弹体", "Grenade Round", "—", "models/w_models/weapons/w_rd_grenade_scale_x1.mdl、models/w_models/weapons/w_rd_grenade_scale_x4.mdl、models/w_models/weapons/w_rd_grenade_scale_x4_burn.mdl", "—", "地图上的火箭弹（终章、The Passing）"],
    ["6", "场景物件", "梯子", "Ladder", "func_useableladder", "models/props_buildables/ladder.mdl、models/props_buildables/ladder_guide.mdl、models/props_buildables/ladder_rung.mdl、models/props_buildables/ladder_w_guides.mdl", "—", "常用替换对象（发光梯子、HD 梯子）；其余装饰性梯子散在 models/props/、models/props_c17/ 等目录"],
    ["7", "场景物件", "门（检查站/地堡等）", "Doors", "prop_door_rotating", "models/props_doors/", "—", "整目录，共 257 个 .mdl；常用替换对象（多角色门等）"],
    ["8", "场景物件", "补给箱", "Supply Crate", "prop_physics", "models/props_crates/supply_crate01.mdl、models/props_crates/supply_crate02.mdl", "—", "弹药堆/补给箱外观"],
    ["9", "场景物件", "木箱", "Wooden Crate", "prop_physics", "models/props_junk/wood_crate001a.mdl", "—", "最常出现的可破坏箱子"],
]
add_sheet(wb, "固定武器·场景", ["#", "类型", "中文名", "英文名", "实体名", "模型路径 (.mdl)", "音效目录", "说明"],
          FIXED, [5, 12, 22, 26, 26, 92, 30, 56], "35566B",
          "固定武器与常见场景物件（Fixed Weapons & Props）")

# ---------------------------------------------------------------- 音效
SND = [
    ["1", "武器音效", "手枪", "sound/weapons/pistol/", "换弹、开火、空仓"],
    ["2", "武器音效", "格洛克 / 银手枪", "sound/weapons/pistol_silver/", "双持左手枪"],
    ["3", "武器音效", "双持手枪", "sound/weapons/dual_pistol/", "双枪合击音"],
    ["4", "武器音效", "马格南", "sound/weapons/magnum/", "沙漠之鹰"],
    ["5", "武器音效", "冲锋枪", "sound/weapons/smg/", "乌兹"],
    ["6", "武器音效", "消音冲锋枪", "sound/weapons/smg_silenced/", "MAC-10"],
    ["7", "武器音效", "MP5", "sound/weapons/mp5navy/", "TLS"],
    ["8", "武器音效", "泵动霰弹枪", "sound/weapons/shotgun/", ""],
    ["9", "武器音效", "镀铬霰弹枪", "sound/weapons/shotgun_chrome/", ""],
    ["10", "武器音效", "战术霰弹枪", "sound/weapons/auto_shotgun/", "M4 Super"],
    ["11", "武器音效", "战斗霰弹枪", "sound/weapons/auto_shotgun_spas/", "SPAS"],
    ["12", "武器音效", "M16 突击步枪", "sound/weapons/rifle/", ""],
    ["13", "武器音效", "战斗步枪", "sound/weapons/rifle_desert/", "SCAR"],
    ["14", "武器音效", "AK-47", "sound/weapons/rifle_ak47/", ""],
    ["15", "武器音效", "SG552", "sound/weapons/sg552/", "TLS"],
    ["16", "武器音效", "猎枪", "sound/weapons/hunting_rifle/", "Mini-14"],
    ["17", "武器音效", "军用狙击枪", "sound/weapons/sniper_military/", ""],
    ["18", "武器音效", "Scout", "sound/weapons/scout/", "TLS"],
    ["19", "武器音效", "AWP", "sound/weapons/awp/", "TLS"],
    ["20", "武器音效", "榴弹发射器", "sound/weapons/grenade_launcher/", ""],
    ["21", "武器音效", "手雷弹体", "sound/weapons/hegrenade/", ""],
    ["22", "武器音效", "燃烧瓶", "sound/weapons/molotov/", ""],
    ["23", "武器音效", "胆汁炸弹", "sound/weapons/ceda_jar/", ""],
    ["24", "武器音效", "除颤器", "sound/weapons/defibrillator/", ""],
    ["25", "武器音效", "肾上腺素", "sound/weapons/adrenaline/", ""],
    ["26", "武器音效", "电锯", "sound/weapons/chainsaw/", ""],
    ["27", "武器音效", "消防斧", "sound/weapons/axe/", ""],
    ["28", "武器音效", "棒球棍 / 板球棒", "sound/weapons/bat/", ""],
    ["29", "武器音效", "撬棍", "sound/weapons/crowbar/", ""],
    ["30", "武器音效", "平底锅", "sound/weapons/pan/", ""],
    ["31", "武器音效", "电吉他", "sound/weapons/guitar/", ""],
    ["32", "武器音效", "武士刀", "sound/weapons/katana/", ""],
    ["33", "武器音效", "砍刀", "sound/weapons/machete/", ""],
    ["34", "武器音效", "警棍", "sound/weapons/tonfa/", ""],
    ["35", "武器音效", "战斗刀", "sound/weapons/knife/", ""],
    ["36", "武器音效", "干草叉", "update/sound/weapons/pitchfork/", "TLS"],
    ["37", "武器音效", "铁铲", "update/sound/weapons/shovel/", "TLS"],
    ["38", "武器音效", "米尼岗机枪", "sound/weapons/minigun/", ""],
    ["39", "武器音效", ".50 重机枪", "sound/weapons/50cal/", ""],
    ["40", "武器音效", "通用开枪/撞击", "sound/weapons/fx/", "通用音效库"],
    ["41", "角色音效", "生还者通用", "sound/player/survivor/", "heal / hit / splat / swing / voice"],
    ["42", "角色音效", "呕吐者", "sound/player/boomer/", "voice / vomit / explode / hit / fall"],
    ["43", "角色音效", "烟鬼", "sound/player/smoker/", "voice / attack / death / hit / miss"],
    ["44", "角色音效", "猎人", "sound/player/hunter/", "voice / attack / hit"],
    ["45", "角色音效", "坦克", "sound/player/tank/", "voice / attack / hit / fall"],
    ["46", "角色音效", "冲撞者", "sound/player/charger/", "voice / hit"],
    ["47", "角色音效", "骑师", "sound/player/jockey/", "voice"],
    ["48", "角色音效", "喷酸者", "sound/player/spitter/", "voice / swarm"],
    ["49", "角色音效", "女巫", "sound/npc/witch/", "哭泣、攻击"],
    ["50", "角色音效", "NPC 对白", "sound/npc/", "virgil / whitaker / pilot / churchguy 等"],
    ["51", "音乐", "游戏音乐", "sound/music/", "l4d2 / tank / witch / safe / scavenge / the_end 等"],
    ["52", "界面音效", "UI 音效", "sound/ui/", "菜单点击、奖励音"],
    ["53", "界面音效", "物品拾取", "sound/items/", "itempickup.wav、手电筒"],
    ["54", "环境音", "环境氛围", "sound/ambient/", "天气、警报、火、水、机器"],
    ["55", "音效", "物理撞击", "sound/physics/", "含 TLS 的 shovel_impact / pitchfork_impact"],
    ["56", "音效", "关卡音效", "sound/level/", "倒计时、铃、发电机、游戏厅"],
    ["57", "音效", "载具", "sound/vehicles/", ""],
]
SND_EN = ["Pistol", "Glock / Silver Pistol", "Dual Pistols", "Magnum", "Submachine Gun",
          "Silenced SMG", "MP5", "Pump Shotgun", "Chrome Shotgun", "Tactical Shotgun",
          "Combat Shotgun", "M-16 Assault Rifle", "Combat Rifle (Desert Rifle)", "AK-47", "SG 552",
          "Hunting Rifle", "Military Sniper", "Scout", "AWP", "Grenade Launcher",
          "HE Grenade", "Molotov", "Bile Bomb", "Defibrillator", "Adrenaline",
          "Chainsaw", "Fire Axe", "Baseball Bat / Cricket Bat", "Crowbar", "Frying Pan",
          "Electric Guitar", "Katana", "Machete", "Nightstick", "Knife",
          "Pitchfork", "Shovel", "Minigun", "Heavy Machine Gun (.50 cal)", "Weapon generic SFX",
          "Survivor common SFX", "Boomer", "Smoker", "Hunter", "Tank",
          "Charger", "Jockey", "Spitter", "Witch", "NPC dialogue",
          "Music", "UI sounds", "Item pickup", "Ambience", "Physics impacts",
          "Level sounds", "Vehicles"]
assert len(SND_EN) == len(SND), (len(SND_EN), len(SND))
SND2 = [[r[0], r[1], r[2], en, r[3], r[4]] for r, en in zip(SND, SND_EN)]
add_sheet(wb, "音效路径", ["#", "分类", "对应物件", "英文描述", "游戏内目录", "备注"],
          SND2, [5, 14, 26, 30, 50, 46], "7A4A20", "音效替换路径（Sound）· 音效文件为 .wav / .mp3，直接放同名目录即可覆盖")

# ---------------------------------------------------------------- 界面·特效·材质·其他
OTHER = [
    ["1", "界面 HUD", "HUD 贴图（含角色头像）", "materials/vgui/hud/", "生命条图标、弹药显示、控制器图标、角色头像等", "界面-"],
    ["2", "界面 HUD", "生命条", "materials/vgui/healthbar_green.vmt、materials/vgui/healthbar_orange.vmt、materials/vgui/healthbar_red.vmt、materials/vgui/healthbar_grey.vmt、materials/vgui/healthbar_white.vmt", "队伍成员血量条颜色", "界面-"],
    ["3", "界面 HUD", "准星", "materials/sprites/crosshairs.vmt、materials/vgui/crosshair_bg.vmt、materials/vgui/gfx/vgui/crosshair.vmt", "准星样式/颜色", "界面-"],
    ["4", "界面", "感染者图标", "materials/vgui/boomer.vmt、materials/vgui/hunter.vmt、materials/vgui/smoker.vmt、materials/vgui/charger.vmt、materials/vgui/jockey.vmt、materials/vgui/spitter.vmt、materials/vgui/hulk.vmt、materials/vgui/witch.vmt", "HUD 提示图标", "界面-"],
    ["5", "界面", "主菜单背景", "materials/vgui/background_survivor.vmt、materials/vgui/background_infected.vmt、l4d2_background01.bik、l4d2_background02.bik、l4d2_background03.bik、l4d2_background04.bik、l4d2_background05.bik", "主菜单左右两侧背景，以及动态背景视频（.bik 躺在 VPK 根目录）", "界面-"],
    ["6", "界面", "启动动画", "media/valve.bik、media/l4d2_intro.bik", "开场 Valve Logo 与游戏片头动画；部分包会带 left4dead2/ 外层目录", "界面-"],
    ["7", "界面", "载入画面", "materials/vgui/loadingscreen_*.vmt、materials/vgui/loadingscreen_*_widescreen.vmt", "地图加载时的剧照；通配模式，每张图另有 _widescreen 版", "界面-"],
    ["8", "界面", "成就图标", "materials/vgui/achievements/", "成就与奖杯图标", "界面-"],
    ["9", "界面", "战役/地图选择", "materials/vgui/maps/、materials/vgui/missions/、missions/", "战役菜单条目", "界面-"],
    ["10", "界面", "喷漆图案", "materials/vgui/logos/", "内置喷漆；玩家自定义喷漆存在别处", "界面-"],
    ["11", "界面", "字体与界面脚本", "resource/*.res、materials/vgui/fonts/", "界面布局与字体", "界面-"],
    ["12", "界面", "文本与字幕", "resource/closecaption_schinese.txt、resource/*_schinese.txt", "字幕、物品名、提示文本", "界面-"],
    ["13", "特效", "血液与血浆", "particles/blood_fx.pcf、materials/decals/blood*.vmt", "溅血、血迹贴花", "特效-"],
    ["14", "特效", "火焰", "particles/fire_fx.pcf、particles/fire_01l4d.pcf、particles/fire_infected_fx.pcf", "燃烧瓶、着火感染者", "特效-"],
    ["15", "特效", "弹着点与火花", "particles/impact_fx.pcf", "子弹打在墙面/血肉的效果", "特效-"],
    ["16", "特效", "枪口焰", "particles/weapon_fx.pcf", "开枪火光是脚本指定", "特效-"],
    ["17", "特效", "感染体液", "particles/boomer_fx.pcf、particles/smoker_fx.pcf、particles/spitter_fx.pcf、particles/charger_fx.pcf、particles/hunter_fx.pcf、particles/tank_fx.pcf、particles/witch_fx.pcf", "各特殊感染者技能特效", "特效-"],
    ["18", "特效", "雨天/天气", "particles/rain_fx.pcf、particles/rain_storm_fx.pcf、particles/environmental_fx.pcf", "Hard Rain 等关卡天气", "特效-"],
    ["19", "特效", "屏幕效果", "particles/screen_fx.pcf", "屏幕血迹、全屏滤镜", "特效-"],
    ["20", "特效", "爆炸与碎屑", "particles/gen_dest_fx.pcf、particles/impact_fx.pcf", "爆炸、道具碎裂", "特效-"],
    ["21", "特效", "粒子清单", "particles/particles_manifest.txt", "新增自定义粒子需在此登记", "特效-"],
    ["22", "材质", "环境材质", "materials/concrete/、materials/wood/、materials/metal/、materials/brick/、materials/glass/、materials/ground/、materials/nature/", "墙面、地面、木材等", "材质-"],
    ["23", "材质", "模型材质", "materials/models/", "所有模型贴图（角色/武器/感染者都在这里）", "材质-"],
    ["24", "材质", "天空盒", "materials/skybox/*.vmt、materials/skybox/*.vtf", "每张地图 6 面天空贴图（docks / river / highrise / moonfull 等）", "材质-"],
    ["25", "材质", "贴花", "materials/decals/", "血迹、路标、划痕（不含 blood 前缀，那属于「血液与血浆」行）", "材质-"],
    ["26", "材质", "涂鸦标语", "materials/graffiti/", "安全屋与墙上的文字涂鸦", "材质-"],
    ["27", "其他", "地图附属文件（导航/光照）", "maps/*.nav、maps/*.lmp、lights.rad、update/texture_shadow_fix.rad", "AI 导航与光照编译产物；重打光需要编译地图", "地图-"],
    ["28", "其他", "地图/战役", "maps/*.bsp", "整张地图替换，最常见 MOD 类型；覆盖 c1~c14 各章节", "地图-"],
    ["29", "其他", "游戏模式定义", "modes/*.txt", "突变模式、生存、清道夫等规则", "脚本-"],
    ["30", "其他", "任务与战役脚本", "missions/*.txt", "战役菜单与章节配置", "脚本-"],
    ["31", "其他", "VScript 脚本", "scripts/vscripts/*.nuc", "地图逻辑、刷怪控制", "脚本-"],
    ["32", "其他", "武器数值脚本", "scripts/weapon_*.txt", "伤害、弹道、射速、模型指向（改模型路径也在这里）", "脚本-"],
    ["33", "其他", "近战数值脚本", "scripts/melee/*.txt", "近战伤害、视角模型/世界模型路径（fireaxe / katana / shovel…）", "脚本-"],
    ["34", "其他", "感染者骨架动画", "models/infected/anim_*.mdl", "感染者（含特殊感染者）的骨骼动画模型", "特感-"],
    ["35", "其他", "语音", "sound/player/survivor/voice/、sound/npc/", "语音包（中文语音/日语语音/梗语音）", "音效-"],
    ["36", "其他", "喷漆与本地资源", "materials/vgui/logos/", "玩家自定义喷漆走本地文件夹或自定义 VPK", "界面-"],
    ["37", "其他", "手电筒", "materials/effects/flashlight001.vtf、materials/particle/beam_flashlight.vmt、materials/particle/flashlight_glow_noz.vmt",
     "只认手电筒**本体**：materials/effects/flashlight*（光斑贴图）与含 flashlight 的模型。粒子包/菜单里的 particle/beam_flashlight* 与 flashlight_glow* 是共享资源，不算手电筒 mod", "手电筒-"],
    ["38", "其他", "管理员插件", "scripts/vscripts/*admin*.nut、scripts/clientmenu.txt、addons/sourcemod/、*.smx、addons/metamod/",
     "服务器 / 房间管理工具（VScript 管理菜单、SourceMod 插件）。含任一入口文件即定身份，不靠路径占比", "管理员插件-"],
]
OTHER_EN = ["HUD Textures", "Health Bar", "Crosshair", "Infected Icons",
            "Main Menu Background", "Startup Movies", "Loading Screens", "Achievement Icons",
            "Campaign / Map Menu", "Spray Logos", "Fonts & UI Layout", "Text & Subtitles",
            "Blood & Gore", "Fire", "Impact & Sparks", "Muzzle Flash", "Infected Ability FX",
            "Rain & Weather", "Screen Effects", "Explosions & Debris", "Particle Manifest",
            "Environment Textures", "Model Textures", "Skybox", "Decals", "Graffiti",
            "Map Support Files (nav/lightmaps)", "Maps / Campaigns", "Game Mode Definitions",
            "Mission & Campaign Scripts", "VScript", "Weapon Scripts", "Melee Scripts",
            "Infected Skeletons", "Voice", "Local Sprays",
            "Flashlight", "Admin Plugins"]
assert len(OTHER_EN) == len(OTHER), (len(OTHER_EN), len(OTHER))
OTHER2 = [[r[0], r[1], r[2], en, r[3], r[4], r[5]] for r, en in zip(OTHER, OTHER_EN)]
add_sheet(wb, "界面·特效·材质·其他", ["#", "大类", "可替换内容", "英文描述", "游戏内路径", "说明", "建议分类前缀"],
          OTHER2, [5, 14, 26, 28, 78, 46, 16], "4A4A4A",
          "界面 / 特效 / 材质 / 其他可替换资源　·　「建议分类前缀」对齐现有分类命名")

# ---------------------------------------------------------------- 分类速查
CAT_META = [
    ("生还者", "生还者模型 / 贴图 / 语音 / 手臂", "models/survivors/、models/weapons/arms/v_arms_*.mdl、sound/player/survivor/", "8 名生还者；中段用官方英文名（Coach / Ellis / Francis…）"),
    ("特感", "特殊感染者模型 / 贴图 / 骨骼 / 残肢", "models/infected/、materials/models/infected/", "8 种特感；中段用官方英文名（Boomer / Hunter / Tank…）。骨架动画、手臂、爆炸残肢等横切行也归这里"),
    ("普感", "普通感染者模型 / 贴图 / 残肢", "models/infected/common/", "含女性感染者、血块与碎尸；纯贴图的「血块与碎尸」经用户裁定仍用 材质-"),
    ("主武器", "主武器模型 / 贴图 / 枪声", "models/w_models/weapons/、models/v_models/、sound/weapons/", "17 把主武器；中段用官方中文名（AK-47 突击步枪…），同域多行取上位名（霰弹枪）"),
    ("副武器", "手枪类模型 / 贴图", "models/w_models/weapons/w_pistol*.mdl", "上位名「手枪」合并 P220 / 格洛克 / 双持"),
    ("近战", "近战武器模型 / 贴图 / 拖尾", "models/weapons/melee/、scripts/melee/*.txt", "17 种近战（武士刀 / 撬棍 / 棒球棍…）"),
    ("投掷物", "投掷物模型 / 贴图", "models/w_models/weapons/w_eq_*.mdl", "燃烧瓶 / 管状炸弹 / 土制炸弹"),
    ("消耗品", "消耗品模型 / 贴图", "models/w_models/weapons/w_eq_*.mdl", "止痛药 / 肾上腺素 / 急救包 / 除颤器"),
    ("场景道具", "升级道具与特殊道具", "models/、materials/", "激光瞄准器、高爆 / 燃烧弹药包等"),
    ("场景", "固定武器与场景物件", "models/、materials/", "固定机枪、梯子、门、木箱；规则锚定 ^(models|materials)/"),
    ("模型", "模型资源（无更具体的物件域归属）", "models/", "物件域判不出来时的资源类型落点"),
    ("地图", "整张战役地图 / 地图资源包", "maps/*.bsp、maps/*.nav", "体量最大；一个战役常拆成多个 VPK（如 Cold Front 三件套）"),
    ("材质", "贴图与材质脚本", "materials/", "环境贴图、天空盒、贴花、涂鸦、纯贴图类 mod"),
    ("界面", "HUD / 菜单 / 加载画面 / 大厅", "materials/vgui/、resource/、media/*.bik", "准星、生命条、载入图、启动动画、大厅背景"),
    ("特效", "粒子与屏幕效果", "particles/*.pcf、materials/decals/blood*.vmt", "2026-10-03 起吸收旧「效果-」，该前缀不再使用"),
    ("脚本", "数值 / 规则 / 逻辑脚本", "scripts/*.txt、scripts/melee/*.txt、scripts/vscripts/*.nuc、modes/*.txt", "改伤害、无限弹药、免控、第三人称、血量显示"),
    ("音效", "音效 / 语音 / 音乐", "sound/", "吸收旧「语音·」；枪声、角色语音、BGM、环境音"),
    ("手电筒", "手电筒光斑 / 光晕贴图", "materials/effects/flashlight*.vtf、materials/particle/(beam_)?flashlight*.vmt",
     "2026-10-03 新增。只认 flashlight；枪口焰 muzzleflash 不含该子串，天然不误伤"),
    ("管理员插件", "服务器 / 房间管理工具", "scripts/vscripts/*admin*.nut、addons/sourcemod/**、*.smx",
     "2026-10-03 新增。含任一入口文件即定身份（不靠路径占比），与 S1「含 bsp 即地图」同理"),
    ("其它", "无法归入以上分类", "—", "兜底前缀"),
]
CAT = [[p + "-", desc, path, str(ADDON_BY_PREFIX.get(p, 0)), note] for p, desc, path, note in CAT_META]
CAT.append(["（无前缀）", "尚未按规范命名的 VPK", "—", str(ADDON_BY_PREFIX.get("（无前缀）", 0)),
            "应恒为 0；非 0 说明还有 VPK 没跑完整理流程（_work\\plan_v4.py）"])
add_sheet(wb, "分类速查", ["分类前缀", "覆盖内容", "对应游戏路径", "现有 MOD 数量", "说明"],
          CAT, [14, 30, 66, 16, 56], "2E4F6B",
          "分类 × 现有 MOD 数量（生成时动态统计：addons 顶层 %d 个 VPK）"
          "　·　现行方案 = 2026-10-03 定稿的 19 个前缀（当日新增 手电筒- / 管理员插件-）；旧 角色- / 武器- / 效果- 已废弃" % ADDON_TOP)

safe_save(wb, OUT)
print("OK", OUT, os.path.getsize(OUT), "bytes")
print("sheets:", wb.sheetnames)
