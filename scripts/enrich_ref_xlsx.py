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
"""把 addons 扫描结果并入《求生之路2 可MOD替换物品总表》"""
import json, os, re, sys
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from official_names import OFFICIAL

XLSX = L4D2_XLSX
WORK = L4D2_WORK


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


mods = json.load(open(os.path.join(WORK, "addons_scan.json"), encoding="utf-8"))
by_target = json.load(open(os.path.join(WORK, "addons_by_target.json"), encoding="utf-8"))

# ---------------------------------------------------------------- 人工标签覆盖
# 有些 mod 的「身份」由用户裁定（改名成 手电筒- / 管理员插件- 之类），但内部路径里没有对应特征
# → 路径推导的标签认不出它，表格会把该行显示成「未替换」，与名字自相矛盾。用户可手动补标签：
#   <WORK>/label_override.json
#   [ { "mod": "<addons_scan.json 里的 file>", "add_labels": ["手电筒"], "reason": "..." } ]
# 安全：① 已有该标签则跳过（幂等）② 标签不在任何表格行里会 WARN（不造孤立标签）
#      ③ 只并入派生数据并回写，让 verify_overlaps / plan_v4 / 表格看到同一份
OVERRIDE = os.path.join(WORK, "label_override.json")
OV_APPLIED = 0
OV_MISSING = []
if os.path.exists(OVERRIDE):
    _ov = json.load(open(OVERRIDE, encoding="utf-8"))
    _byfile = {m.get("file"): m for m in mods}
    for _it in _ov:
        _f = (_it.get("mod") or "").strip()
        _m = _byfile.get(_f) or _byfile.get(_f + ".vpk")
        if not _m:
            OV_MISSING.append(_f)
            continue
        for _lab in (_it.get("add_labels") or []):
            if (_m.get("targets") or {}).get(_lab):
                continue
            _m.setdefault("targets", {})[_lab] = 1
            _lst = by_target.setdefault(_lab, [])
            if _m["file"] not in _lst:
                _lst.append(_m["file"])
            OV_APPLIED += 1
    for _f in OV_MISSING:
        print("[WARN] label_override: 扫描数据里找不到 mod「%s」（文件名写对了吗？）" % _f)
    if OV_APPLIED:
        json.dump(mods, open(os.path.join(WORK, "addons_scan.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        json.dump(by_target, open(os.path.join(WORK, "addons_by_target.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("[OK] 人工标签覆盖: 并入 %d 条标签（已回写 addons_scan / addons_by_target，"
              "保证各工具与表格一致）" % OV_APPLIED)

OK_FILL = PatternFill("solid", fgColor="D6F0DC")
NO_FILL = PatternFill("solid", fgColor="F7E2E2")
NA_FILL = PatternFill("solid", fgColor="EEEEEE")
WARN_FILL = PatternFill("solid", fgColor="FDF3D0")
HEAD_FILL = PatternFill("solid", fgColor="2E6B4F")
THIN = Side(style="thin", color="BFCFC6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


# 附带覆盖：地图/战役包顺手带的资源，不算「你专门替换的」
def is_incidental(m):
    """含 .bsp 地图文件，或文件名以「地图-」开头（地图补丁包可能不含 bsp）"""
    rt = m.get("rawTop") or {}
    if rt.get("maps", 0) > 0:
        return True
    return m["file"].startswith("地图-")


def mods_for(labels):
    """labels -> (状态, 说明文本)"""
    if not labels:
        return None
    hits, inc = [], []
    seen = set()
    for lab in labels:
        if lab.startswith("__VOICE__"):
            names = [k for k in by_target if k.startswith("语音·")]
        else:
            names = [lab] if lab in by_target else []
        for n in names:
            for f in by_target[n]:
                key = f
                if key in seen:
                    continue
                seen.add(key)
                mm = next((x for x in mods if x["file"] == f), None)
                if mm and is_incidental(mm):
                    inc.append(f)
                else:
                    hits.append(f)
    if not hits and not inc:
        return None
    parts = []
    if hits:
        head = hits[:4]
        parts.append("、".join(head) + (f" 等 {len(hits)} 个" if len(hits) > 4 else ""))
    if inc:
        parts.append(f"（另有 {len(inc)} 个地图/脚本包附带该资源）")
    status = "✅ 已替换" if hits else "⚠ 仅附带覆盖"
    return (status, "　".join(parts))


# ---------------------------------------------------------------- 逐行映射
M_SURV = {
    "教练": ["教练 Coach"], "埃利斯": ["埃利斯 Ellis"], "尼克": ["尼克 Nick"],
    "罗谢尔": ["罗谢尔 Rochelle"], "比尔": ["比尔 Bill"], "弗朗西斯": ["弗朗西斯 Francis"],
    "路易斯": ["路易斯 Louis"], "佐伊": ["佐伊 Zoey"],
    "弗朗西斯（轻量版）": ["弗朗西斯（轻量版）"], "佐伊（轻量版）": ["佐伊（轻量版）"],
    "生还者骨架动画": ["生还者骨架动画"], "生还者手势": ["生还者手势"],
    "生还者通用音效": ["音效·生还者技能音效"], "生还者语音": ["__VOICE__"],
}
M_SI = {
    "呕吐者": ["呕吐者 Boomer"], "女呕吐者": ["女呕吐者 Boomette"], "烟鬼": ["烟鬼 Smoker"],
    "猎人": ["猎人 Hunter"], "坦克（巨兽）": ["坦克 Tank"], "坦克（Cold Stream 版）": ["坦克（Cold Stream 版）"],
    "女巫": ["女巫 Witch"], "新娘女巫": ["新娘女巫 Witch Bride"], "冲撞者": ["冲撞者 Charger"],
    "骑师": ["骑师 Jockey"], "喷酸者": ["喷酸者 Spitter"], "L4D1 版感染者模型": ["L4D1 版感染者模型"],
    "感染者第一人称爪（第三人称视角模式）": ["感染者第一人称爪"], "感染者手臂": ["感染者手臂"],
    "爆炸残肢": ["感染者残肢·爆炸残肢"],
}
M_CI = {
    "普通男性感染者（基础）": ["普通感染者·男性基础 01"],
    "普通男性感染者 2": ["普通感染者·男性基础 02"],
    "普通女性感染者（基础）": ["普通感染者·女性基础"],
    "女性感染者（套装）": ["普通感染者·女性套装"],
    "女性感染者（农村）": ["普通感染者·女性农村"],
    "女性感染者（护士）": ["普通感染者·女性护士"],
    "女性感染者（行李员）": ["普通感染者·女性行李员"],
    "女性感染者（背心牛仔裤）": ["普通感染者·女性背心牛仔裤"],
    "女性感染者（T恤短裙）": ["普通感染者·女性T恤短裙"],
    "女性感染者（正式礼服）": ["普通感染者·女性正式礼服"],
    "男性（西装）": ["普通感染者·男性西装"],
    "男性（T恤工装裤）": ["普通感染者·男性T恤工装裤"],
    "男性（背心牛仔裤）": ["普通感染者·男性背心牛仔裤"],
    "男性（背心背带裤）": ["普通感染者·男性背心背带裤"],
    "男性（衬衫牛仔裤）": ["普通感染者·男性衬衫牛仔裤"],
    "男性（正式礼服）": ["普通感染者·男性正式礼服"],
    "男性（摩托车手）": ["普通感染者·男性摩托车手"],
    "男性（花花公子）": ["普通感染者·男性花花公子"],
    "男性（乡村）": ["普通感染者·男性乡村"],
    "男性（行李搬运工）": ["普通感染者·男性行李搬运工"],
    "CEDA 工作人员": ["普通感染者·CEDA 工作人员"],
    "小丑": ["普通感染者·小丑"],
    "泥人": ["普通感染者·泥人"],
    "防暴警察": ["普通感染者·防暴警察"],
    "筑路工": ["普通感染者·筑路工"],
    "堕落生还者": ["普通感染者·堕落生还者"],
    "吉米·吉布斯二世": ["普通感染者·吉米·吉布斯二世"],
    "伞兵": ["普通感染者·伞兵"],
    "飞行员": ["普通感染者·飞行员"],
    "警察": ["普通感染者·警察"],
    "军人": ["普通感染者·军人"],
    "外科医生": ["普通感染者·外科医生"],
    "病人": ["普通感染者·病人"],
    "工人": ["普通感染者·工人"],
    "TSA 安检员": ["普通感染者·TSA 安检员"],
    "女性感染者残肢模型": ["普通感染者·女性残肢模型"],
    "普通感染者残肢模型": ["普通感染者·普通感染者残肢模型"],
    "血块与碎尸": ["感染者残肢·血块与碎尸"],
}
M_PRIMARY = {
    "泵动式霰弹枪": ["武器·泵动式霰弹枪"], "镀铬霰弹枪": ["武器·镀铬霰弹枪"],
    "冲锋枪（乌兹）": ["武器·冲锋枪（乌兹）"], "消音冲锋枪": ["武器·消音冲锋枪"],
    "战术霰弹枪": ["武器·战术霰弹枪"], "战斗霰弹枪": ["武器·战斗霰弹枪"],
    "猎枪": ["武器·猎枪"], "狙击步枪": ["武器·狙击步枪"],
    "M-16 突击步枪": ["武器·M-16 突击步枪"], "战斗步枪": ["武器·战斗步枪"],
    "AK-47 突击步枪": ["武器·AK-47 突击步枪"], "榴弹发射器": ["武器·榴弹发射器"],
    "M60 机枪": ["武器·M60 机枪"], "MP5 冲锋枪": ["武器·MP5 冲锋枪"],
    "SG552 突击步枪": ["武器·SG552 突击步枪"], "Scout 狙击枪": ["武器·Scout 狙击枪"],
    "AWP 狙击枪": ["武器·AWP 狙击枪"],
}
M_SIDEARMS = {
    "手枪（P220）": ["武器·手枪（P220）"], "格洛克手枪": ["武器·格洛克手枪"],
    "双持手枪": ["武器·双持手枪"], "马格南手枪": ["武器·马格南手枪"],
}
M_MELEE = {
    "消防斧": ["武器·消防斧"], "棒球棍": ["武器·棒球棍"], "板球棒": ["武器·板球棒"],
    "撬棍": ["武器·撬棍"], "平底锅": ["武器·平底锅"], "高尔夫球杆": ["武器·高尔夫球杆"],
    "电吉他": ["武器·电吉他"], "武士刀": ["武器·武士刀"], "砍刀": ["武器·砍刀"],
    "警棍": ["武器·警棍"], "干草叉": ["武器·干草叉"], "铁铲": ["武器·铁铲"],
    "战斗刀": ["武器·战斗刀"], "电锯": ["武器·电锯"], "花园地精": ["武器·花园地精"],
    "迪吉里杜管": ["武器·迪吉里杜管"], "防暴盾": ["武器·防暴盾"],
}
M_THROWABLE = {
    "燃烧瓶": ["道具·燃烧瓶"], "管状炸弹": ["道具·管状炸弹"], "胆汁炸弹": ["道具·胆汁炸弹"],
}
M_CONSUM = {
    "急救包": ["道具·急救包"], "止痛药": ["道具·止痛药"], "肾上腺素": ["道具·肾上腺素"],
    "除颤器": ["道具·除颤器"],
}
M_UPG = {
    "高爆弹药": ["道具·高爆弹药"], "燃烧弹药": ["道具·燃烧弹药"], "激光瞄准器": ["道具·激光瞄准器"],
    "可乐（可乐瓶）": ["道具·可乐"], "花园地精": ["道具·花园地精"], "汽油桶": ["道具·汽油桶"],
    "丙烷罐": ["道具·丙烷罐"], "氧气罐": ["道具·氧气罐"], "烟花盒": ["道具·烟花盒"],
    "爆炸油桶": ["道具·爆炸油桶"],
}
M_FIXED = {
    "米尼岗机枪": ["固定武器·米尼岗机枪"], "重机枪（.50 口径）": ["固定武器·重机枪"],
    "损坏的重机枪": ["固定武器·损坏的重机枪"], "榴弹（榴弹发射器弹体）": ["场景道具·榴弹弹体"],
    "火箭弹弹体": ["场景道具·火箭弹弹体"], "梯子": ["场景物件·梯子"],
    "门（检查站/地堡等）": ["场景物件·门"], "补给箱": ["场景物件·补给箱"],
    "木箱": ["场景物件·木箱"],
}
M_SND = {
    "sound/weapons/pistol/": ["音效·手枪"], "sound/weapons/pistol_silver/": ["音效·格洛克 银手枪"],
    "sound/weapons/dual_pistol/": ["音效·双持手枪"], "sound/weapons/magnum/": ["音效·马格南"],
    "sound/weapons/smg/": ["音效·冲锋枪"], "sound/weapons/smg_silenced/": ["音效·消音冲锋枪"],
    "sound/weapons/mp5navy/": ["音效·MP5"], "sound/weapons/shotgun/": ["音效·泵动霰弹枪"],
    "sound/weapons/shotgun_chrome/": ["音效·镀铬霰弹枪"], "sound/weapons/auto_shotgun/": ["音效·战术霰弹枪"],
    "sound/weapons/auto_shotgun_spas/": ["音效·战斗霰弹枪"], "sound/weapons/rifle/": ["音效·M16 突击步枪"],
    "sound/weapons/rifle_desert/": ["音效·战斗步枪"], "sound/weapons/rifle_ak47/": ["音效·AK-47"],
    "sound/weapons/sg552/": ["音效·SG552"], "sound/weapons/hunting_rifle/": ["音效·猎枪"],
    "sound/weapons/sniper_military/": ["音效·军用狙击枪"], "sound/weapons/scout/": ["音效·Scout"],
    "sound/weapons/awp/": ["音效·AWP"], "sound/weapons/grenade_launcher/": ["音效·榴弹发射器"],
    "sound/weapons/hegrenade/": ["音效·手雷弹体"], "sound/weapons/molotov/": ["音效·燃烧瓶"],
    "sound/weapons/ceda_jar/": ["音效·胆汁炸弹"], "sound/weapons/defibrillator/": ["音效·除颤器"],
    "sound/weapons/adrenaline/": ["音效·肾上腺素"], "sound/weapons/chainsaw/": ["音效·电锯"],
    "sound/weapons/axe/": ["音效·消防斧"], "sound/weapons/bat/": ["音效·棒球棍与板球棒"],
    "sound/weapons/crowbar/": ["音效·撬棍"], "sound/weapons/pan/": ["音效·平底锅"],
    "sound/weapons/guitar/": ["音效·电吉他"], "sound/weapons/katana/": ["音效·武士刀"],
    "sound/weapons/machete/": ["音效·砍刀"], "sound/weapons/tonfa/": ["音效·警棍"],
    "sound/weapons/knife/": ["音效·战斗刀"], "sound/weapons/pitchfork/": ["音效·干草叉"],
    "sound/weapons/shovel/": ["音效·铁铲"], "sound/weapons/minigun/": ["音效·米尼岗机枪"],
    "sound/weapons/50cal/": ["音效·.50 重机枪"], "sound/weapons/fx/": ["音效·通用开枪与撞击"],
    "sound/player/survivor/": ["音效·生还者其它"], "sound/player/boomer/": ["音效·呕吐者"],
    "sound/player/smoker/": ["音效·烟鬼"], "sound/player/hunter/": ["音效·猎人"],
    "sound/player/tank/": ["音效·坦克"], "sound/player/charger/": ["音效·冲撞者"],
    "sound/player/jockey/": ["音效·骑师"], "sound/player/spitter/": ["音效·喷酸者"],
    "sound/npc/witch/": ["音效·女巫"], "sound/npc/": ["音效·NPC 对白"],
    "sound/music/": ["音效·游戏音乐"], "sound/ui/": ["音效·UI 音效"],
    "sound/items/": ["音效·物品拾取"], "sound/ambient/": ["音效·环境氛围"],
    "sound/level/": ["音效·关卡音效"], "sound/physics/": ["音效·物理撞击"],
    "sound/vehicles/": ["音效·载具"],
}
M_OTHER = {
    "HUD 贴图（含角色头像）": ["界面·HUD-通用贴图"], "生命条": ["界面·HUD-生命条"],
    "准星": ["界面·准星与精灵"], "感染者图标": ["界面·HUD-感染者图标"],
    "主菜单背景": ["界面·主菜单背景"], "启动动画": ["界面·启动动画"],
    "载入画面": ["界面·载入画面"], "成就图标": ["界面·成就图标"], "战役/地图选择": ["界面·地图选择"],
    "喷漆图案": ["界面·喷漆图案"], "字体与界面脚本": ["界面·字体与布局"], "文本与字幕": ["界面·文本与字幕"],
    "血液与血浆": ["特效·血液与血浆"], "火焰": ["特效·火焰"], "弹着点与火花": ["特效·弹着点与火花"],
    "枪口焰": ["特效·枪口焰"], "感染体液": ["特效·感染体液"], "雨天/天气": ["特效·雨天与天气"],
    "屏幕效果": ["特效·屏幕效果"], "爆炸与碎屑": ["特效·爆炸与碎屑"], "粒子清单": ["特效·粒子清单"],
    "环境材质": ["材质·环境贴图"], "模型材质": ["材质·模型贴图"], "天空盒": ["材质·天空盒"],
    "贴花": ["材质·贴花"], "涂鸦标语": ["材质·涂鸦"],
    "地图附属文件（导航/光照）": ["地图·附属文件（导航与光照）"],
    "地图/战役": ["地图·战役"], "游戏模式定义": ["脚本·游戏模式"], "任务与战役脚本": ["脚本·战役任务"],
    "VScript 脚本": ["脚本·VScript"], "武器数值脚本": ["脚本·武器数值"],
    "近战数值脚本": ["脚本·近战数值"], "感染者骨架动画": ["动画·感染者骨骼"],
    "手电筒": ["手电筒"], "管理员插件": ["管理员插件"],
    "语音": ["__VOICE__"], "喷漆与本地资源": None,
}
# 注：`打包元文件` / `打包元文件（嵌套 VPK）` 由 scan 产出（把 addoninfo.txt 等从「未归类」里捞出来），
# 但它们不是游戏内物件，**故意不给表格行** —— 因此不会出现在「替换覆盖总览」里。

SHEET_MAP = {
    "生还者": ("中文名", M_SURV),
    "特殊感染者": ("中文名", M_SI),
    "普通感染者": ("中文名", M_CI),
    "主武器": ("中文名", M_PRIMARY),
    "副武器": ("中文名", M_SIDEARMS),
    "近战": ("中文名", M_MELEE),
    "投掷物": ("中文名", M_THROWABLE),
    "消耗品": ("中文名", M_CONSUM),
    "场景道具": ("中文名", M_UPG),
    "固定武器·场景": ("中文名", M_FIXED),
    "音效路径": ("游戏内目录", M_SND),
    "界面·特效·材质·其他": ("可替换内容", M_OTHER),
}

wb = load_workbook(XLSX)
overview = []

# 防御：本脚本可能被单独重跑（不经 build），先清掉上一轮的派生表，避免出现「我的MOD清单1」
for _derived in ("我的MOD清单", "替换覆盖总览"):
    if _derived in wb.sheetnames:
        del wb[_derived]

# ---- 自检不变量：一个标签只能对应一行表格 ----
# （缺陷 1/3 的根因就是多行共用一个标签，这里机器校验，防止再犯）
label_rows = {}
for _sname, (_keycol, _mapping) in SHEET_MAP.items():
    for _cn, _labels in _mapping.items():
        for _lab in (_labels or []):
            if _lab == "__VOICE__":
                continue
            label_rows.setdefault(_lab, []).append(f"{_sname}::{_cn}")
DUP_LABELS = {k: v for k, v in label_rows.items() if len(v) > 1}
if DUP_LABELS:
    print("[WARN] 以下标签被多行共用（违反 1 行 1 标签）：")
    for k, v in sorted(DUP_LABELS.items()):
        print("   ", k, "←", "、".join(v))
else:
    print(f"[OK] 标签与表格行一一对应：{len(label_rows)} 个标签，无共用")
# 落盘标签映射，便于事后核对与排错
json.dump(label_rows, open(os.path.join(WORK, "label_map.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, sort_keys=True)
# label_override 若写了表格里不存在的标签，它不会显示在任何行 —— 明确报警，别静默失效
if os.path.exists(OVERRIDE):
    _ovl = [l for _it in json.load(open(OVERRIDE, encoding="utf-8"))
            for l in (_it.get("add_labels") or [])]
    _badl = sorted({l for l in _ovl if l not in label_rows})
    if _badl:
        print("[WARN] label_override 用了表格里不存在的标签（不会出现在任何行）：%s" % "、".join(_badl))

for sname, (keycol, mapping) in SHEET_MAP.items():
    ws = wb[sname]
    headers = [c.value for c in ws[2]]
    ki = headers.index(keycol)
    ei = headers.index("英文名") if "英文名" in headers else None
    col0 = len(headers) + 1
    h1, h2 = ws.cell(row=2, column=col0, value="替换状态"), ws.cell(row=2, column=col0 + 1, value="替换它的 MOD")
    for h in (h1, h2):
        h.font = Font(bold=True, color="FFFFFF", size=10)
        h.fill = HEAD_FILL
        h.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        h.border = BORDER
    for r in range(3, ws.max_row + 1):
        key = ws.cell(row=r, column=ki + 1).value
        if key is None:
            continue
        labels = mapping.get(str(key), "MISS")
        res = None if labels in (None, "MISS") else mods_for(labels)
        if labels == "MISS":
            st, txt, fill = "—", "（本表未逐项映射）", NA_FILL
        elif res is None:
            st, txt, fill = "未替换", "—", NO_FILL
        else:
            st, txt = res
            if st.startswith("⚠"):
                fill = WARN_FILL
            else:
                fill = OK_FILL
        c1 = ws.cell(row=r, column=col0, value=st)
        c2 = ws.cell(row=r, column=col0 + 1, value=txt)
        for c in (c1, c2):
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.font = Font(size=10)
            c.border = BORDER
            c.fill = fill
        c1.font = Font(size=10, bold=True)

        # 用游戏本体字符串覆盖我自己写的英文名
        off = OFFICIAL.get(sname, {}).get(str(key))
        if off:
            en, src = off
        else:
            en, src = ("—（游戏内不显示名称）", "—")
        if ei is not None:
            cell = ws.cell(row=r, column=ei + 1, value=en)
            cell.font = Font(size=10, italic=True, color="1F4E79")
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = BORDER
        overview.append([sname, str(key), en, src, st, txt])
    ws.column_dimensions[get_column_letter(col0)].width = 12
    ws.column_dimensions[get_column_letter(col0 + 1)].width = 56
    ws.auto_filter.ref = f"A2:{get_column_letter(col0 + 1)}{ws.max_row}"

# ---------------------------------------------------------------- 我的 MOD 清单
GENERIC = {"材质·环境贴图", "材质·模型贴图", "材质·武器贴图", "材质·感染者贴图", "材质·生还者贴图",
           "脚本·VScript", "脚本·其他", "界面·其他 UI", "特效·粒子", "音效·其他", "模型·其他",
           "材质·天空盒", "界面·HUD", "材质·贴花"}
rows = []
for i, m in enumerate(sorted(mods, key=lambda x: -(x.get("paths") or 0)), 1):
    t = m.get("targets") or {}
    main = [k for k in sorted(t, key=lambda k: -t[k]) if k not in GENERIC][:4]
    inc = "是（地图/战役包，含 .bsp）" if is_incidental(m) else "否"
    prefix = m["file"].split("-")[0] + "-" if re.match(r"^(地图|脚本|角色|武器|其它|界面|音效|特效|材质|效果)-", m["file"]) else "（无前缀）"
    rows.append([i, m["file"], m.get("src") or "?", m.get("sizeMB", 0), prefix, m.get("paths", 0),
                 "、".join(main) if main else "仅通用资源", inc])
ws = wb.create_sheet("我的MOD清单")
TOTAL_PATHS = sum(m.get("paths") or 0 for m in mods)
TOP_COUNT = sum(1 for m in mods if str(m.get("src") or "").startswith("addons 顶层"))
EXTRA_COUNT = len(mods) - TOP_COUNT
ws.cell(row=1, column=1,
        value=f"你的 addons 扫描结果　·　addons 顶层 VPK {TOP_COUNT} 个 ＋ 额外纳入 cfhd\\pak01_dir.vpk {EXTRA_COUNT} 个 "
              f"＝ 本清单 {len(mods)} 行 / {TOTAL_PATHS:,} 条资源路径")
ws.cell(row=1, column=1).font = Font(bold=True, size=13, color="FFFFFF")
ws.cell(row=1, column=1).fill = PatternFill("solid", fgColor="1F3B57")
ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)
ws.row_dimensions[1].height = 26
hdrs = ["#", "MOD 文件", "来源", "大小(MB)", "已分类前缀", "覆盖路径数", "主要替换对象", "属于附带覆盖"]
for c, h in enumerate(hdrs, 1):
    cell = ws.cell(row=2, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=10)
    cell.fill = HEAD_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BORDER
for i, row in enumerate(rows):
    for c, v in enumerate(row, 1):
        cell = ws.cell(row=3 + i, column=c, value=v)
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.font = Font(size=10)
        cell.border = BORDER
        if i % 2:
            cell.fill = PatternFill("solid", fgColor="F2F7F4")
for c, w in enumerate([5, 72, 34, 10, 12, 12, 50, 24], 1):
    ws.column_dimensions[get_column_letter(c)].width = w
ws.freeze_panes = "A3"
ws.auto_filter.ref = f"A2:H{2 + len(rows)}"
ws.sheet_properties.tabColor = "1F3B57"

# ---------------------------------------------------------------- 替换覆盖总览
ws2 = wb.create_sheet("替换覆盖总览")
ws2.cell(row=1, column=1, value="逐个物件的替换状态总览　·　按工作表分组")
ws2.cell(row=1, column=1).font = Font(bold=True, size=13, color="FFFFFF")
ws2.cell(row=1, column=1).fill = PatternFill("solid", fgColor="7A3030")
ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
ws2.row_dimensions[1].height = 26
for c, h in enumerate(["所属工作表", "物件", "原版英文名", "英文名字符串来源（本地化 Token）", "替换状态", "替换它的 MOD"], 1):
    cell = ws2.cell(row=2, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=10)
    cell.fill = HEAD_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BORDER
ws2.row_dimensions[2].height = 28
for i, row in enumerate(overview):
    st = row[4]
    fill = (OK_FILL if st == "✅ 已替换" else
            NO_FILL if st == "未替换" else
            WARN_FILL if str(st).startswith("⚠") else NA_FILL)
    for c, v in enumerate(row, 1):
        cell = ws2.cell(row=3 + i, column=c, value=v)
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.font = Font(size=10, bold=(c == 5))
        cell.border = BORDER
        cell.fill = fill
    ws2.cell(row=3 + i, column=3).font = Font(size=10, italic=True, color="1F4E79")
    ws2.cell(row=3 + i, column=4).font = Font(size=9, color="7A7A7A")
for c, w in enumerate([16, 32, 30, 44, 12, 56], 1):
    ws2.column_dimensions[get_column_letter(c)].width = w
ws2.freeze_panes = "A3"
ws2.auto_filter.ref = f"A2:F{2 + len(overview)}"
ws2.sheet_properties.tabColor = "7A3030"

# ---------------------------------------------------------------- 说明补一行
ws0 = wb["说明"]
r = ws0.max_row + 1
ws0.cell(row=r, column=1, value="替换状态怎么看")
ws0.cell(row=r, column=2, value=f"扫描时间点：addons 顶层 VPK {TOP_COUNT} 个，另额外纳入 cfhd\\pak01_dir.vpk {EXTRA_COUNT} 个，共解析 {len(mods)} 个 VPK / {TOTAL_PATHS:,} 条资源路径。"
                                 "「✅ 已替换」= 有 MOD 真的覆盖了这个物件的文件；「⚠ 仅附带覆盖」= 只有地图/战役包顺手带了该资源，你没有专门装替换 MOD；"
                                 "「未替换」= 目前没有任何 MOD 碰它；「—」= 该项不适用逐项映射。"
                                 "注意：addons 目录是活的——你增删或改名 MOD 后，重跑扫描脚本本表数字才会更新。"
                                 "每个 VPK 的归属见「我的MOD清单」的「来源」列；详细对应关系见「替换覆盖总览」。")
for c in (1, 2):
    ws0.cell(row=r, column=c).alignment = Alignment(vertical="top", wrap_text=True)
    ws0.cell(row=r, column=c).font = Font(size=10)
    if c == 1:
        ws0.cell(row=r, column=c).font = Font(size=10, bold=True)

safe_save(wb, XLSX)

done = sum(1 for o in overview if o[4] == "✅ 已替换")
warn = sum(1 for o in overview if str(o[4]).startswith("⚠"))
no = sum(1 for o in overview if o[4] == "未替换")
named = sum(1 for o in overview if o[2] and not str(o[2]).startswith("—"))
print(json.dumps({"sheets": wb.sheetnames, "overviewRows": len(overview),
                  "officialEnglishNames": named,
                  "replaced": done, "incidentalOnly": warn, "notReplaced": no,
                  "mods": len(rows), "labels": len(label_rows),
                  "duplicateLabels": {k: v for k, v in DUP_LABELS.items()}}, ensure_ascii=False))
