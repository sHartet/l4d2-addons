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
"""列出被 ≥2 个 mod 覆盖的标签，并区分「同一 mod 的多件套」与「不同 mod 抢同一物件」"""
import json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
WORK = L4D2_WORK

by_target = json.load(open(os.path.join(WORK, "addons_by_target.json"), encoding="utf-8"))
scan = json.load(open(os.path.join(WORK, "addons_scan.json"), encoding="utf-8"))
exempt_path = os.path.join(WORK, "set_exempt.json")
declared = []
if os.path.exists(exempt_path):
    declared = json.load(open(exempt_path, encoding="utf-8"))
declared_members = set()
for d in declared:
    for m in d.get("members", []):
        declared_members.add(m)

# 每个 mod 的归类对象（用于判断是否「地图/战役包附带」）
incidental = set()
for m in scan:
    rt = m.get("rawTop") or {}
    if rt.get("maps", 0) > 0 or m["file"].startswith("地图-"):
        incidental.add(m["file"])

# 派生表里不体现的通用标签，单独标出，避免淹没真实冲突
GENERIC = {"材质·环境贴图", "材质·模型贴图", "材质·武器贴图", "材质·感染者贴图", "材质·生还者贴图",
           "脚本·VScript", "脚本·其他", "界面·其他 UI", "模型·其他", "地图·战役",
           "音效·未列入表格", "特效·其它粒子", "材质·天空盒", "材质·贴花", "材质·涂鸦"}


# 分类级标签所在的表（这些行描述的是「一类资源」，多个 mod 各改一部分是正常的，不构成"抢同一物件"）
CATEGORY_SHEETS = {"音效路径", "界面·特效·材质·其他"}
label_map = json.load(open(os.path.join(WORK, "label_map.json"), encoding="utf-8"))


def owning_sheets(lab):
    return {x.split("::")[0] for x in label_map.get(lab, [])}


def is_set(mods):
    """同一 mod 的多件套判定：去掉 .vpk 后，最短的名字是其余每个名字的前缀
    （附加件命名规则 = 主体名 + '-附加名'）"""
    names = sorted((re.sub(r"\.vpk$", "", m) for m in mods), key=len)
    base = names[0]
    return all(n == base or n.startswith(base + "-") for n in names)


# 2026-10-03 起分类前缀已精细化（旧 角色-/武器-/效果- 已拆开）。这里必须跟上前缀表，
# 否则 target_of() 剥不掉新前缀，返回的就成了「生还者」「特感」这类**域**而不是替换对象，
# 于是两个改不同物件的 mod 会被算成同一个 target → 报出假「真冲突」。
# 实测：修复前 `L4D1 版感染者模型` 把 特感-Boomer-… 与 特感-Hunter-… 判成真冲突。
# 顺序要求：`场景道具` 必须排在 `场景` 前（虽无二义，仍按长前缀优先写）。
CATS = ("生还者", "特感", "普感", "主武器", "副武器", "近战", "投掷物", "消耗品",
        "场景道具", "场景", "模型", "地图", "材质", "界面", "特效", "脚本", "音效", "其它",
        # 旧前缀：精细化之前的名字，仅为兼容历史文件名保留（库里已无此类名字）
        "普通感染者", "特殊感染者", "角色", "武器", "效果")


def target_of(name):
    """取「分类-替换对象-标题」里的替换对象段；没有第二段则返回 None"""
    rest = re.sub(r"\.vpk$", "", name)
    for c in CATS:
        if rest.startswith(c + "-"):
            rest = rest[len(c) + 1:]
            break
    if "-" not in rest:
        return None
    return rest.split("-", 1)[0]


rows = []
for lab, mods in sorted(by_target.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    if len(mods) < 2:
        continue
    real = [m for m in mods if m not in incidental]
    sheets = owning_sheets(lab)
    category_level = bool(sheets) and sheets.issubset(CATEGORY_SHEETS)
    targets = {target_of(m) for m in real}
    same_target = len(real) >= 2 and len(targets) == 1 and None not in targets
    kind = []
    if is_set(mods):
        kind.append("同一 mod 的多件套")
    if any(m in declared_members for m in mods):
        kind.append("已声明豁免（set_exempt.json）")
    if not real:
        kind.append("全部为地图/战役包附带")
    elif len(real) == 1:
        kind.append("1 个专门 mod ＋ 其余为地图/战役包附带（无冲突）")
    elif len(real) >= 2:
        if not sheets:
            kind.append("残留标签（无对应表格行）")
        elif category_level:
            kind.append("分类级重叠（多个 mod 各改该类的一部分）")
        elif not same_target:
            kind.append("多目标聚合（同一行涵盖多个物件，mod 各改各的）")
        elif not is_set(real):
            kind.append("⚠ 不同 mod 抢同一物件（真冲突）")
    rows.append({
        "标签": lab,
        "所属表": "、".join(sorted(sheets)) or "（无对应表格行）",
        "覆盖 mod 数": len(mods),
        "其中非附带": len(real),
        "非附带mod的替换对象": sorted(t or "（无）" for t in targets),
        "性质": "；".join(kind) or "（待判）",
        "mods": mods,
    })

conflicts = [r for r in rows if "真冲突" in r["性质"]]
object_level = [r for r in rows if r["所属表"] != "（无对应表格行）"
                and not set(r["所属表"].split("、")).issubset(CATEGORY_SHEETS)]

# ---- 全库「同一 mod 的多件套」组（按文件名前缀判定，与标签无关）----
allnames = sorted(re.sub(r"\.vpk$", "", m["file"]) for m in scan)
sets_found = []
used = set()
for i, base in enumerate(allnames):
    if base in used:
        continue
    members = [n for n in allnames if n == base or n.startswith(base + "-")]
    if len(members) > 1:
        # 只保留最短的那个作为 base（避免把 base 又当成别人的附加件重复上报）
        if not any(base.startswith(o + "-") for o in allnames if o != base and len(o) < len(base)):
            sets_found.append({"主体": base, "成员": sorted(members)})
            used.update(members)

print(json.dumps({
    "总_被≥2个mod覆盖的标签数": len(rows),
    "①_同一mod的多件套（全库扫描，按文件名前缀）": sets_found,
    "②_物件级标签被≥2个mod覆盖": [
        {"标签": r["标签"], "所属表": r["所属表"], "覆盖mod数": r["覆盖 mod 数"],
         "非附带mod数": r["其中非附带"], "替换对象": r["非附带mod的替换对象"],
         "判定": r["性质"]}
        for r in sorted(object_level, key=lambda x: -x["其中非附带"])
    ],
    "③_⚠真冲突（同替换对象多份，需留新移旧）": [
        {"标签": r["标签"], "所属表": r["所属表"], "mods": r["mods"]} for r in conflicts
    ],
    "④_分类级重叠（多个mod各改该类一部分，不作冲突处理）": [
        {"标签": r["标签"], "mod数": r["覆盖 mod 数"]} for r in rows
        if "分类级重叠" in r["性质"]
    ],
    "⑤_仅地图/战役包附带": [
        {"标签": r["标签"], "mod数": r["覆盖 mod 数"]} for r in rows
        if "全部为地图/战役包附带" in r["性质"]
    ],
}, ensure_ascii=False, indent=1))
