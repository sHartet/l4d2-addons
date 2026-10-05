# -*- coding: utf-8 -*-
"""verify_all.py —— 一条命令跑完全部验收，只打印一行摘要。

以前每轮收尾要 6-8 次工具调用：plan_v4（需改名）/ scan_targets（冲突）/ verify_rules（断言）/
verify_fixes（表格）/ verify_overlaps（真冲突）/ 63 字节体检 / unclassifiedPaths / 标签唯一性。
现在一次调用，成功时输出形如：
    ALL OK  rename=0 conflicts=0 rules=75/75 fixes=0 overlaps=0 unclassified=0 name63=ok labels=223
任何一项不过，就打印 FAIL 行 + 该项关键输出（截断），便于直接定位。

子进程输出用「重定向到临时文件」而不是管道 —— 受限沙箱下管道会 EPERM。
"""
import json, os, re, subprocess, sys, tempfile

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.environ.get('L4D2_HOME') or os.path.dirname(HERE)
CFG = {}
try:
    CFG = json.load(open(os.path.join(HOME, 'config.json'), encoding='utf-8'))
except Exception:
    pass
WORK = os.path.join(HOME, CFG.get('scriptsDir', '_work'))
ADDONS = os.environ.get('L4D2_ADDONS') or CFG.get('addonsDir') or \
    r'D:\Steam\steamapps\common\Left 4 Dead 2\left4dead2\addons'
PY = sys.executable
NODE = CFG.get('nodePath') or 'node'


def run(args):
    fd, tmp = tempfile.mkstemp(suffix='.out')
    os.close(fd)
    with open(tmp, 'w', encoding='utf-8', errors='replace') as fh:
        try:
            subprocess.run(args, stdout=fh, stderr=subprocess.STDOUT, cwd=WORK, timeout=1200)
        except Exception as e:
            fh.write('SPAWN_FAIL %s %s' % (type(e).__name__, e))
    t = open(tmp, encoding='utf-8', errors='replace').read()
    os.remove(tmp)
    return t


def last_json(t):
    i = t.rfind('{')
    if i < 0:
        return None
    try:
        return json.loads(t[i:])
    except Exception:
        return None


def stem_bytes(s):
    """ANSI(GBK) 字节数 —— 与 plan_v4._stem_bytes / CapName / mk_rename_json 口径一致。
    GBK 是双字节编码：ASCII 1 字节，其余一律 2 字节。"""
    return len(s.encode('gbk', errors='replace'))


vals, fails = {}, []

# 1) 命名幂等
if '--quick' not in sys.argv:
    t = run([PY, os.path.join(WORK, 'plan_v4.py')])
    m = re.search(r'需改名\s*(\d+)\s*个', t)
    vals['rename'] = m.group(1) if m else '?'
    if vals['rename'] != '0':
        fails.append(('rename', '需改名 %s' % vals['rename']))

# 2) 冲突扫描
t = run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(WORK, 'scan_targets.ps1')])
m = re.search(r'conflicts=(\d+)', t)
vals['conflicts'] = m.group(1) if m else '?'
if vals['conflicts'] != '0':
    fails.append(('conflicts', (t.strip().splitlines() or [''])[-1][:200]))

# 3) 分类断言
t = run([NODE, os.path.join(WORK, 'verify_rules.mjs')])
j = last_json(t)
if j and 'passed' in j:
    vals['rules'] = '%d/%d' % (j['passed'], j['cases'])
    if j.get('failed'):
        fails.append(('rules', json.dumps(j['failed'], ensure_ascii=False)[:300]))
else:
    vals['rules'] = '?'
    fails.append(('rules', t.strip()[-200:]))

# 4) 表格完整性
if '--quick' not in sys.argv:
    t = run([PY, os.path.join(WORK, 'verify_fixes.py')])
    m = re.search(r'"不合格条目数"\s*:\s*(\d+)', t)   # 嵌套 JSON，直接用正则取那个键
    bad = m.group(1) if m else '?'
    vals['fixes'] = bad
    if bad != '0':
        fails.append(('fixes', t.strip()[-200:]))

# 5) 真冲突（标签链路）
t = run([PY, os.path.join(WORK, 'verify_overlaps.py')])
m = re.search(r'"([^"]*真冲突[^"]*)"\s*:\s*\[(.*?)\]\s*[,}]', t, re.S)   # 键名带 emoji，用正则最稳
body = (m.group(2) if m else '').strip()
n = 0 if body == '' else body.count('{')
vals['overlaps'] = str(n)
if n:
    fails.append(('overlaps', '真冲突 %d 组：%s' % (n, body[:200])))

# 6) 未归类路径 + 标签唯一性（直接读派生数据，不再起进程）
try:
    scan = json.load(open(os.path.join(WORK, 'addons_scan.json'), encoding='utf-8'))
    unc = sum((m.get('targets') or {}).get('未归类', 0) for m in scan)
    vals['unclassified'] = str(unc)
    if unc:
        who = [m['file'] for m in scan if (m.get('targets') or {}).get('未归类')][:3]
        fails.append(('unclassified', '%d 条未归类，例：%s' % (unc, '、'.join(who))))
except Exception as e:
    vals['unclassified'] = '?'
    fails.append(('unclassified', '读不到 addons_scan.json: %s' % e))

try:
    lm = json.load(open(os.path.join(WORK, 'label_map.json'), encoding='utf-8'))
    dup = {k: v for k, v in lm.items() if len(v) > 1}
    vals['labels'] = str(len(lm))
    if dup:
        fails.append(('labels', '被多行共用：%s' % json.dumps(dup, ensure_ascii=False)[:200]))
except Exception:
    vals['labels'] = '?'
    fails.append(('labels', '读不到 label_map.json'))

# 6b) 扫描数据是否过期 —— 磁盘上的 vpk 与 scan 记录必须一致（刷新被占用挡住时就会不一致）
try:
    disk = {f[:-4] for f in os.listdir(ADDONS) if f.lower().endswith('.vpk')}
    # 排除 scan 里刻意记录的「目录内件」伪条目（如 cfhd\\pak01_dir），它们不是顶层 vpk
    scanned = {m['file'][:-4] for m in scan if os.sep not in m['file'] and '/' not in m['file']}
    missing = sorted(disk - scanned)      # 磁盘有、扫描没有 → 刚搬进来还没刷
    extra = sorted(scanned - disk)        # 扫描有、磁盘没有 → 刚被移走/改名
    if missing or extra:
        vals['stale'] = 'YES(%d+%d)' % (len(missing), len(extra))
        fails.append(('stale', 'addons_scan.json 已过期：磁盘多出 %s / 扫描残留 %s —— 先跑刷新表格.bat'
                      % (missing[:3], extra[:3])))
    else:
        vals['stale'] = 'no'
except Exception as e:
    vals['stale'] = '?'
    fails.append(('stale', '无法比对磁盘与扫描：%s' % e))

# 6c) 盲点扫描（信息性）：路径有交集且内容真的不同 —— 需人工裁决，故不判失败，只报数字
t = run([NODE, os.path.join(WORK, 'overlap_scan.mjs'), '--top', '1'])
m = re.search(r'真抢位=(\d+)', t)
vals['blind'] = m.group(1) if m else '?'
if vals['blind'] not in ('0', '?'):
    print('  [blind] %s 对真抢位（路径相同、内容不同）—— 明细见 _work\\blind_overlaps.md' % vals['blind'])

# 7) 63 字节硬约束
long_names = []
try:
    for f in os.listdir(ADDONS):
        if f.lower().endswith('.vpk'):
            stem = f[:-4]
            if stem_bytes(stem) > 63:
                long_names.append('%s(%d)' % (stem, stem_bytes(stem)))
except Exception as e:
    long_names = ['读不到 addons: %s' % e]
vals['name63'] = 'ok' if not long_names else 'OVER(%d)' % len(long_names)
if long_names:
    fails.append(('name63', '、'.join(long_names[:3])))

order = ['stale', 'rename', 'conflicts', 'rules', 'fixes', 'overlaps', 'unclassified', 'name63', 'blind', 'labels']
summary = ' '.join('%s=%s' % (k, vals.get(k, '-')) for k in order if k in vals)
if fails:
    print('FAIL %d 项  %s' % (len(fails), summary))
    for k, d in fails:
        print('  [%s] %s' % (k, d))
    sys.exit(1)
print('ALL OK  ' + summary)
