# -*- coding: utf-8 -*-
"""L4D2 addons skill —— 首次调用引导 / 环境生成器。

它做四件事：
  1. 校验并落盘 config.json（addons 路径、workshop 路径、工作目录 ⋯）
  2. 把 skill 自带的脚本铺进 <workDir>\\<scriptsSubdir>\\（覆盖旧版本）
  3. 渲染 <workDir>\\刷新表格.bat（把本机 python / node 绝对路径写进去，纯 ASCII）
  4. 跑一次刷新，产出《求生之路2_可MOD替换物品总表.xlsx》

用法（非交互；问答由 AI 在调用前完成）：
  python bootstrap.py --addons "<addonsDir>" [--workshop "<dir>"] [--workdir "<dir>"]
                      [--mirror "<dir>"] [--steam-userdata "<dir>"] [--node "<node.exe>"]
                      [--python "<python.exe>"] [--force] [--no-run] [--no-pointer]

只给 --show 时不写任何东西，只打印「当前已有什么配置」，供 AI 判断是否要问用户。
"""
import argparse, io, json, os, shutil, subprocess, sys

sys.stdout.reconfigure(encoding='utf-8')

SKILL_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts')
POINTER = os.path.join(os.path.expanduser('~'), '.l4d2-addons.home')
XLSX_DEFAULT = '求生之路2_可MOD替换物品总表.xlsx'

BAT = '''@echo off
chcp 65001 >nul 2>&1
setlocal
set "L4D2_HOME={home}"
set "PY={py}"
set "NODE={node}"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "SCRIPTS={home}\\{sub}"

rem ---- silent mode for automation: pass "nopause" ----
if /i "%~1"=="nopause" set "NOPAUSE=1"

echo ============================================================
echo   L4D2  MOD Reference Table  -  REFRESH
echo ============================================================
echo   Work dir : %L4D2_HOME%
echo   Scripts  : %SCRIPTS%
echo   Python   : %PY%
echo   Node     : %NODE%
echo ------------------------------------------------------------
echo.

rem ---- 0. pre-flight: is the output xlsx still open in WPS / Excel? ----
"%NODE%" "%SCRIPTS%\\check_lock.mjs" "%L4D2_HOME%."
if errorlevel 1 goto stop
echo.

echo [1/3] Rebuilding base workbook ...
"%PY%" "%SCRIPTS%\\build_ref_xlsx.py"
if errorlevel 1 goto fail
echo.

echo [2/3] Scanning addons folder ...
"%NODE%" "%SCRIPTS%\\scan_addons.mjs"
if errorlevel 1 goto fail
echo.

echo [3/3] Merging replacement status ...
"%PY%" "%SCRIPTS%\\enrich_ref_xlsx.py"
if errorlevel 1 goto fail
echo.

echo ------------------------------------------------------------
echo  DONE. Output file:
for %%F in ("%L4D2_HOME%\\*.xlsx") do echo    %%~nxF   %%~tF   %%~zF bytes
echo ------------------------------------------------------------
if not defined NOPAUSE pause
exit /b 0

:stop
if not defined NOPAUSE pause
exit /b 2

:fail
echo.
echo ------------------------------------------------------------
echo  [FAILED]  Something went wrong above. Table NOT refreshed.
echo  Send the messages above and the maintainer will fix it.
echo ------------------------------------------------------------
if not defined NOPAUSE pause
exit /b 1
'''


def find_node(argv_node=None):
    if argv_node and os.path.exists(argv_node):
        return argv_node
    c = shutil.which('node')
    if c:
        return c
    d = os.path.dirname(sys.executable)
    for rel in (('..', '..', 'node', 'bin', 'node.exe'),
                ('..', '..', '..', 'node', 'bin', 'node.exe'),
                ('..', 'node', 'node.exe')):
        p = os.path.normpath(os.path.join(d, *rel))
        if os.path.exists(p):
            return p
    for p in (r'C:\Program Files\nodejs\node.exe', r'C:\Program Files (x86)\nodejs\node.exe'):
        if os.path.exists(p):
            return p
    return None


def load_pointer():
    try:
        with open(POINTER, encoding='utf-8') as f:
            return f.read().strip() or None
    except Exception:
        return None


def cfg_path(home):
    return os.path.join(home, 'config.json')


def read_cfg(home):
    try:
        with open(cfg_path(home), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--workdir')
    ap.add_argument('--addons')
    ap.add_argument('--workshop')
    ap.add_argument('--mirror')
    ap.add_argument('--backup')
    ap.add_argument('--steam-userdata')
    ap.add_argument('--python')
    ap.add_argument('--node')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--no-run', action='store_true')
    ap.add_argument('--no-pointer', action='store_true')
    a = ap.parse_args()

    ptr = load_pointer()
    cwd_cfg = read_cfg(os.getcwd())
    home = os.path.abspath(a.workdir or os.getcwd())
    known = {"pointer": ptr, "cwdConfig": cfg_path(os.getcwd()) if cwd_cfg else None,
             "pointerConfig": cfg_path(ptr) if ptr and read_cfg(ptr) else None}

    if a.show or not a.addons:
        out = {"mode": "show", "cwd": os.getcwd(), "known": known,
               "pointerPath": POINTER,
               "needAsk": [] if (ptr and read_cfg(ptr)) else ["addonsDir", "workshopDir"]}
        if ptr and read_cfg(ptr):
            out["config"] = read_cfg(ptr)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0 if (a.show or not a.addons) else 1

    addons = os.path.abspath(a.addons)
    if not os.path.isdir(addons):
        print(json.dumps({"ok": False, "error": "addonsDir 不存在: " + addons,
                          "hint": "请确认《求生之路2》的 left4dead2\\addons 目录"}), )
        return 1

    workshop = os.path.abspath(a.workshop) if a.workshop else os.path.join(addons, 'workshop')
    py = os.path.abspath(a.python) if a.python else sys.executable
    node = find_node(a.node)
    if not node:
        print(json.dumps({"ok": False, "error": "找不到 node.exe",
                          "hint": "请用 --node 指定，或安装 Node.js"}, ensure_ascii=False, indent=1))
        return 1

    old = read_cfg(home) or {}
    cfg = {
        "version": 1,
        "skill": "l4d2-addons",
        "workDir": home,
        "scriptsDir": old.get("scriptsDir", "_work"),
        "xlsxName": old.get("xlsxName", XLSX_DEFAULT),
        "addonsDir": addons,
        "workshopDir": workshop,
        "backupDir": os.path.abspath(a.backup) if a.backup else os.path.join(addons, 'mod备份'),
        "whitelistFile": os.path.join(addons, 'mod白名单.txt'),
        "stagingDir": os.path.join(addons, 'mod暂存'),
        "mirrorDir": a.mirror or (home + '-backup'),
        "steamAppId": 550,
        "steamUserdataDir": os.path.abspath(a.steam_userdata) if a.steam_userdata else "",
        "pythonPath": py,
        "nodePath": node,
    }
    if old and not a.force:
        cfg["scriptsDir"] = old.get("scriptsDir", cfg["scriptsDir"])
        cfg["xlsxName"] = old.get("xlsxName", cfg["xlsxName"])
        if old.get("steamUserdataDir") and not a.steam_userdata:
            cfg["steamUserdataDir"] = old["steamUserdataDir"]

    scripts_dir = os.path.join(home, cfg["scriptsDir"])
    os.makedirs(scripts_dir, exist_ok=True)

    # 冲突备份目录：不存在就建（以前只写进 config.json，从不创建，
    # 导致第一次需要移走冲突败方时无处可放）
    made_dirs = []
    for _d in (cfg['backupDir'],):
        if _d and not os.path.isdir(_d):
            try:
                os.makedirs(_d, exist_ok=True)
                made_dirs.append(_d)
            except Exception:
                pass
    with open(cfg_path(home), 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    # 只铺「工具脚本」。绝不能无条件复制整个目录 ——
    # skill 里一旦混进用户数据（白名单 / 例外表 / 批次 / 扫描结果），
    # 就会被复制进 workDir 并**覆盖用户自己那份**。
    TOOL_EXT = {'.py', '.mjs', '.js', '.ps1'}
    DATA_NAMES = {'config.json', 'name_exempt.json', 'set_exempt.json', 'rename_plan.md',
                  'addons_scan.json', 'addons_by_target.json', 'label_map.json', 'rv_paths.json',
                  'target_conflicts.txt', 'overlap_report.json', 'addons_sha1.csv'}
    copied, skipped_data = [], []
    src = os.path.normpath(SKILL_SCRIPTS)
    for n in sorted(os.listdir(src)):
        s = os.path.join(src, n)
        if not os.path.isfile(s):
            continue
        if (os.path.splitext(n)[1].lower() not in TOOL_EXT
                or n in DATA_NAMES
                or n.startswith('ws_batch')
                or n.endswith('_log.txt')
                or n.startswith('mod白名单')):
            skipped_data.append(n)
            continue
        shutil.copyfile(s, os.path.join(scripts_dir, n))
        copied.append(n)

    def cp(name):
        s = os.path.join(scripts_dir, name)
        if not os.path.exists(s):
            s2 = os.path.join(src, name)
            if os.path.exists(s2):
                shutil.copyfile(s2, s)
                return s
        return s if os.path.exists(s) else None
    cp('workspace_backup.ps1')

    # 用户数据文件：不存在就建空壳，方便 AI / 用户往里追加
    seeded = []
    for n in ('name_exempt.json', 'set_exempt.json'):
        p = os.path.join(scripts_dir, n)
        if not os.path.exists(p):
            with open(p, 'w', encoding='utf-8') as f:
                f.write('[]\n')
            seeded.append(n)
    wl = cfg['whitelistFile']
    if not os.path.exists(wl):
        with open(wl, 'w', encoding='utf-8') as f:
            f.write('mod 白名单 —— 以下条目在做「替换冲突检查 / 归纳整理」时一律跳过，不做任何处理。\n'
                    '（此文件仅供记录，游戏会忽略未知扩展名，可以安全保留在 addons 里）\n\n'
                    '⚠️ 解析规则：只有「行首就是 <前缀>-」的行才算条目；写说明时别让续行以 <前缀>- 开头，\n'
                    '   否则会被当成条目收进去。\n')
        seeded.append(wl)

    bat = os.path.join(home, '刷新表格.bat')
    with open(bat, 'w', encoding='ascii', newline='\r\n') as f:
        f.write(BAT.format(home=home, sub=cfg["scriptsDir"], py=py, node=node.replace('/', '\\')))

    if not a.no_pointer:
        try:
            with open(POINTER, 'w', encoding='utf-8') as f:
                f.write(home)
        except Exception:
            pass

    result = {"ok": True, "workDir": home, "config": cfg_path(home), "bat": bat,
              "scriptsDir": scripts_dir, "scriptsCopied": len(copied), "skippedData": skipped_data, "seeded": seeded,
              "createdDirs": made_dirs,
              "python": py, "node": node, "pointer": None if a.no_pointer else POINTER}

    if a.no_run:
        result["ran"] = False
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0

    proc = subprocess.run(['cmd', '/c', bat, 'nopause'], cwd=home,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    tail = proc.stdout.decode('utf-8', 'replace').strip().splitlines()
    result["ran"] = True
    result["refreshExitCode"] = proc.returncode
    result["refreshTail"] = tail[-16:]
    xlsx = os.path.join(home, cfg["xlsxName"])
    result["xlsx"] = xlsx if os.path.exists(xlsx) else None
    result["xlsxBytes"] = os.path.getsize(xlsx) if os.path.exists(xlsx) else 0
    result["ok"] = proc.returncode == 0 and result["xlsx"] is not None
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["ok"] else 1


if __name__ == '__main__':
    sys.exit(main())
