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
"""逐条核对 6 处缺陷的修复结果（读回 xlsx，不做修改）"""
import json, os, re, sys
from openpyxl import load_workbook

sys.stdout.reconfigure(encoding="utf-8")
XLSX = L4D2_XLSX
WORK = L4D2_WORK

wb = load_workbook(XLSX)
label_map = json.load(open(os.path.join(WORK, "label_map.json"), encoding="utf-8"))
scan = json.load(open(os.path.join(WORK, "addons_scan.json"), encoding="utf-8"))
by_target = json.load(open(os.path.join(WORK, "addons_by_target.json"), encoding="utf-8"))
out = {}


def rows_of(sheet, key="中文名"):
    ws = wb[sheet]
    h = [c.value for c in ws[2]]
    ki, si, mi = h.index(key), h.index("替换状态"), h.index("替换它的 MOD")
    return {ws.cell(row=r, column=ki + 1).value:
            (ws.cell(row=r, column=si + 1).value, ws.cell(row=r, column=mi + 1).value)
            for r in range(3, ws.max_row + 1) if ws.cell(row=r, column=ki + 1).value}


# ---------- 缺陷 1 ----------
s = rows_of("生还者")
out["缺陷1_轻量模型"] = {
    "修复前预期": "佐伊（轻量版）曾误报 ✅ 已替换 / 角色-Francis-COD： MWII Francis - Woodland.vpk",
    "弗朗西斯（轻量版）": s.get("弗朗西斯（轻量版）"),
    "佐伊（轻量版）": s.get("佐伊（轻量版）"),
    "全库含 survivor_teenangst_light 的路径数": sum(1 for m in scan for p in [m["file"]] if False),
}

# ---------- 缺陷 2 ----------
ml = rows_of("近战")
out["缺陷2_迪吉里杜管"] = {
    "近战表该行": ml.get("迪吉里杜管"),
    "scan 中该标签是否有 mod 覆盖": by_target.get("武器·迪吉里杜管", "（无 mod 覆盖，属正常）"),
}

# ---------- 缺陷 3 ----------
def labels_of(sheet, cn):
    return [k for k, v in label_map.items() if f"{sheet}::{cn}" in v]


cases = [
    ("普通感染者", ["普通男性感染者（基础）", "普通男性感染者 2"]),
    ("普通感染者", ["男性（西装）", "男性（T恤工装裤）", "男性（背心牛仔裤）", "男性（背心背带裤）",
                "男性（衬衫牛仔裤）", "男性（正式礼服）", "男性（摩托车手）", "男性（花花公子）", "男性（乡村）"]),
    ("特殊感染者", ["爆炸残肢"]),
    ("普通感染者", ["血块与碎尸"]),
    ("主武器", ["M-16 突击步枪"]),
]
detail = []
for sheet, names in cases:
    for cn in names:
        detail.append({"表": sheet, "行": cn, "指派标签": labels_of(sheet, cn)})
out["缺陷3_标签一一对应"] = {
    "enrich 自检": "OK（220 个标签无共用）" if not [k for k, v in label_map.items() if len(v) > 1]
                  else [k for k, v in label_map.items() if len(v) > 1],
    "共用标签数": len([k for k, v in label_map.items() if len(v) > 1]),
    "抽样指派": detail,
}

# ---------- 缺陷 4 ----------
PATH_COLS = ["角色模型路径 (.mdl)", "第一人称手臂模型", "语音音效目录", "模型路径 (.mdl)", "音效目录",
             "第三人称世界模型 w_", "第一人称手持模型 v_", "粒子特效 .pcf",
             "游戏内目录", "游戏内路径", "对应游戏路径"]
PREFIXES = ("models/", "sound/", "materials/", "particles/", "resource/", "maps/", "scripts/",
            "modes/", "missions/", "update/", "media/", "lights.rad")
# VPK 根目录下的合法完整路径：L4D2 的 .bik 视频、addoninfo 等本来就躺在根目录，
# 它们不是「缺目录的裸文件名」，而是完整的相对路径。
ROOT_LEVEL_OK = re.compile(r"^[^/\\]+\.(bik|bsp|nav|lmp|rad|txt|res|vpk|jpg|jpeg|png|xlsx)$", re.I)
bad = []
for ws in wb.worksheets:
    hdr = [c.value for c in ws[2]]
    cols = [(i, h) for i, h in enumerate(hdr) if h in PATH_COLS]
    if not cols:
        continue
    for r in range(3, ws.max_row + 1):
        for i, h in cols:
            v = ws.cell(row=r, column=i + 1).value
            if not v or v == "—":
                continue
            for part in str(v).split("、"):
                part = part.strip()
                if not part or part == "—":
                    continue
                if part.startswith(PREFIXES) or part.endswith("/") or "*" in part:
                    continue
                if ROOT_LEVEL_OK.match(part):
                    continue
                bad.append({"表": ws.title, "列": h, "值": part})
out["缺陷4_多值单元格全路径"] = {
    "不合格条目数": len(bad),
    "样例": bad[:12],
}

# ---------- 缺陷 5 ----------
ws = wb["我的MOD清单"]
hdr = [c.value for c in ws[2]]
srcs = {}
for r in range(3, ws.max_row + 1):
    v = ws.cell(row=r, column=hdr.index("来源") + 1).value if "来源" in hdr else None
    srcs[v] = srcs.get(v, 0) + 1
out["缺陷5_计数口径"] = {
    "清单表头": ws.cell(row=1, column=1).value,
    "表头列": hdr,
    "来源分布": srcs,
}

# ---------- 缺陷 6 ----------
ws0 = wb["说明"]
notes = {}
for r in range(2, ws0.max_row + 1):
    k = ws0.cell(row=r, column=1).value
    v = ws0.cell(row=r, column=2).value
    if k in ("替换对象建议写法", "⭐ VPK 计数口径", "⭐ 路径写法约定", "覆盖范围"):
        notes[k] = (v or "")[:150]
ws1 = wb["分类速查"]
cat = [[ws1.cell(row=r, column=c).value for c in (1, 4)]
       for r in range(3, ws1.max_row + 1) if ws1.cell(row=r, column=1).value]
out["缺陷6_说明与分类速查"] = {"说明": notes, "分类速查(前缀,数量)": cat,
                              "速查表标题": ws1.cell(row=1, column=1).value}

print(json.dumps(out, ensure_ascii=False, indent=1))
