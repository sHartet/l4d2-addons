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
import io, json, sys
sys.stdout.reconfigure(encoding='utf-8')
W = L4D2_WORK

# 暂缓：这两条是待你定夺的取舍，先不动
HOLD = {
    '材质-BLOODIER GUTS AND GIBS!',
    '角色-SpecialInfected-xdReanimsBase (L4D2) Anim Mods base',
}

rows = []
for line in io.open(W + r'\rename_plan.md', encoding='utf-8').read().splitlines():
    if not line.startswith('| ') or not line.endswith(' |'):
        continue
    c = [x.strip() for x in line.strip('|').split(' | ')]
    if len(c) != 4 or not c[0].isdigit():
        continue
    old, new = c[1].strip('`'), c[2].strip('`')
    if old == new:
        continue
    ok = old not in HOLD
    rows.append({'old': old, 'new': new, 'len': len(new), 'held': not ok})

json.dump(rows, io.open(W + r'\rename_batch.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

todo = [r for r in rows if not r['held']]
print('总需改名 %d 条；本批执行 %d 条，暂缓 %d 条' % (len(rows), len(todo), len(rows) - len(todo)))
print()
over = [r for r in todo if r['len'] > 120]
print('超过 120 字符上限的：%d 条' % len(over))
for r in over:
    print('   %3d  %s' % (r['len'], r['new']))
print()
print('最长 5 条新名：')
for r in sorted(todo, key=lambda x: -x['len'])[:5]:
    print('   %3d  %s' % (r['len'], r['new']))
print()
print('暂缓的两条：')
for r in rows:
    if r['held']:
        print('   %s  →  （计划：%s）' % (r['old'], r['new']))
