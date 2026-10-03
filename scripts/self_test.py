# -*- coding: utf-8 -*-
"""l4d2-addons 全链路自测 —— 在一个临时目录里模拟「全新用户 + 空库」，跑完 12 个阶段。

    python self_test.py [--keep]

它**不碰你的真实 addons 库**：所有产物都在临时目录里，跑完自动删除（--keep 可保留以便排查）。

阶段：
  S0 准备空目录
  S1 bootstrap 生成工作区（config / 刷新表格.bat / xlsx / 脚本 / mod备份 / 空白白名单）
  S2 造 3 个假 VPK 进 workshop（2 个工坊件 + 1 个手工件）+ 1 张 jpg
  S3 刷新表格（空库也要能跑通）
  S3b 扫 workshop 暂存件（新订阅件的命名证据）
  S4 搬迁：consolidate5 干跑 -> 执行
  S5 校验搬迁结果（三件同步 / 手工件不建 .url / workshop 清空但保留目录）
  S6 再刷新（新 mod 进清单）
  S6b 人工标签覆盖（label_override.json 并入 + 回写 + 幂等）
  S7 命名推演幂等（应 0 条需改名）
  S7b 冲突留新移旧（resolve_conflicts：负向拒绝搬空 + 正向搬移 + 清单记账）
  S8 冲突扫描 + 校验脚本 + .ps1 ASCII 护栏
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))       # <skill>\scripts
PYEXE = sys.executable
VPKWRITE = os.path.join(HERE, 'vpkwrite.mjs')

A = ('3332997614', '[AK47] CrossFire AK47-A')
B = ('3057798941', 'Lime replace Coach\n')               # 标题带尾随换行，顺便测净化
C = ('', '手工件_武士刀测试')                            # 手工件：非数字名、无工坊 ID


def node_exe():
    for c in (os.environ.get('L4D2_NODE'),):
        if c and os.path.exists(c):
            return c
    p = shutil.which('node')
    if p:
        return p
    for rel in (('..', '..', 'node', 'bin', 'node.exe'),):
        q = os.path.normpath(os.path.join(os.path.dirname(PYEXE), *rel))
        if os.path.exists(q):
            return q
    return 'node'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep', action='store_true')
    a = ap.parse_args()

    node = node_exe()
    root = tempfile.mkdtemp(prefix='l4d2-selftest-')
    AD, WORK = os.path.join(root, 'addons'), os.path.join(root, 'work')
    WS, WD = os.path.join(AD, 'workshop'), os.path.join(WORK, '_work')
    os.makedirs(WS, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    res = []

    def stage(name, fn):
        try:
            res.append((name, 'PASS', fn() or ''))
        except Exception as e:
            res.append((name, 'FAIL', str(e)[:200]))

    def sh(args, **kw):
        return subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                              errors='replace', **kw)

    def need(cond, msg):
        if not cond:
            raise AssertionError(msg)

    def bat():
        return sh(['cmd', '/c', os.path.join(WORK, '刷新表格.bat'), 'nopause'], cwd=WORK)

    def rj(p):
        with open(p, encoding='utf-8') as f:
            return json.load(f)

    def s1():
        r = sh([PYEXE, os.path.join(HERE, 'bootstrap.py'), '--workdir', WORK,
                '--addons', AD, '--no-pointer'])
        need(r.returncode == 0, 'bootstrap 退出码 %s: %s' % (r.returncode, r.stdout[-400:]))
        j = json.loads(r.stdout)
        need(j['ok'], 'bootstrap ok=False')
        need(os.path.exists(os.path.join(WORK, 'config.json')), '缺 config.json')
        need(os.path.exists(os.path.join(WORK, '刷新表格.bat')), '缺 刷新表格.bat')
        x = os.path.join(WORK, j.get('xlsxName', '求生之路2_可MOD替换物品总表.xlsx'))
        need(os.path.exists(x) and os.path.getsize(x) > 5000, 'xlsx 没生成或过小')
        need(os.path.isdir(os.path.join(AD, 'mod备份')), 'mod备份 没建')
        wl = os.path.join(AD, 'mod白名单.txt')
        need(os.path.exists(wl), 'mod白名单.txt 没种')
        ent = [l for l in open(wl, encoding='utf-8').read().splitlines()
               if re.match(r'^\s*\S+-\S', l) and not l.startswith('⚠')]
        need(not ent, '白名单模板里不该有条目: %s' % ent)
        n = len([f for f in os.listdir(WD) if os.path.isfile(os.path.join(WD, f))])
        need(n >= 19, '脚本只铺了 %d 个' % n)
        return '脚本 %d 个 / xlsx %d B / mod备份已建 / 白名单 0 条目' % (n, os.path.getsize(x))

    def s2():
        specs = {
            A[0]: [
                {'path': 'addoninfo.txt', 'text': '"AddonInfo"\n{\n\taddonSteamAppID\t550\n\taddontitle\t"[AK47] CrossFire AK47-A"\n}\n'},
                {'path': 'models/w_models/weapons/w_rifle_ak47.mdl', 'text': 'IDST AK47-MDL'},
                {'path': 'models/w_models/weapons/w_rifle_ak47.vvd', 'text': 'IDSV AK47-VVD'},
                {'path': 'materials/models/weapons/ak47/ak47.vmt', 'text': '"VertexLitGeneric"\n{}\n'},
                {'path': 'sound/weapons/rifle_ak47/fire.wav', 'text': 'RIFF AK47-WAV'},
            ],
            B[0]: [
                {'path': 'addoninfo.txt', 'text': '"AddonInfo"\n{\n\taddonSteamAppID\t550\n\taddontitle\t"Lime replace Coach"\n}\n'},
                {'path': 'models/survivors/survivor_coach.mdl', 'text': 'IDST COACH-MDL'},
                {'path': 'models/survivors/survivor_coach.vvd', 'text': 'IDSV COACH-VVD'},
                {'path': 'materials/models/survivors/coach/coach.vmt', 'text': '"VertexLitGeneric"\n{}\n'},
                {'path': 'materials/vgui/hud/coach.vtf', 'text': 'VTF COACH-HUD'},
            ],
            '__manual__': [
                {'path': 'models/weapons/melee/w_katana.mdl', 'text': 'IDST KATANA-MDL'},
                {'path': 'materials/models/weapons/melee/katana.vmt', 'text': '"VertexLitGeneric"\n{}\n'},
            ],
        }
        for key, spec in specs.items():
            sp = os.path.join(root, 'spec_%s.json' % key)
            with open(sp, 'w', encoding='utf-8') as f:
                json.dump(spec, f, ensure_ascii=False)
            name = {'3332997614': A[0], '3057798941': B[0]}.get(key, C[1]) + '.vpk'
            r = sh([node, VPKWRITE, os.path.join(WS, name), sp])
            need(r.returncode == 0, 'vpkwrite 失败: %s' % r.stderr[-300:])
        with open(os.path.join(WS, B[0] + '.jpg'), 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0' + b'FAKE-JPEG' * 40)
        need(len(os.listdir(WS)) == 4, 'workshop 应有 4 个文件')
        return '2 个工坊件(5+5 entries) + 1 个手工件(2 entries) + 1 jpg'

    def s3():
        r = bat()
        need(r.returncode == 0, '刷新失败: %s' % r.stdout[-500:])
        m = re.search(r'"unclassifiedPaths":\s*(\d+)', r.stdout)
        need(m and m.group(1) == '0', 'unclassifiedPaths 不为 0')
        need(len(rj(os.path.join(WD, 'addons_scan.json'))) == 0, '空库阶段不该扫到 VPK')
        return 'unclassified=0 / 空库扫到 0 个（正确）'

    def s3b():
        r = sh(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', os.path.join(WD, 'scan_workshop.ps1')], cwd=WORK)
        need(r.returncode == 0, 'scan_workshop 失败: %s' % (r.stdout + r.stderr)[-400:])
        scan = rj(os.path.join(WD, 'workshop_scan.json'))
        need(len(scan) == 3, 'workshop 扫到 %d 个（应 3）' % len(scan))
        by = {e['file']: set((e.get('targets') or {}).keys()) for e in scan}
        for f, want in ((A[0] + '.vpk', '武器·AK-47 突击步枪'),
                        (B[0] + '.vpk', '教练 Coach'),
                        (C[1] + '.vpk', '武器·武士刀')):
            need(want in by.get(f, set()), '%s 缺标签 %s，实际 %s' % (f, want, sorted(by.get(f, []))))
        return '3 件标签命中：武器·AK-47 突击步枪 / 教练 Coach / 武器·武士刀'

    def s4():
        batch = [
            {'id': A[0], 'src': A[0] + '.vpk', 'cat': '主武器', 'target': 'AK-47 突击步枪', 'title': A[1]},
            {'id': B[0], 'src': B[0] + '.vpk', 'cat': '生还者', 'target': 'Coach', 'title': B[1]},
            {'id': '', 'src': C[1] + '.vpk', 'cat': '近战', 'target': '武士刀', 'title': C[1]},
        ]
        bp = os.path.join(WD, 'ws_batch_selftest.json')
        with open(bp, 'w', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False, indent=1)
        con = os.path.join(WD, 'consolidate5.ps1')
        base = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', con, '-Batch', bp]
        dry = sh(base, cwd=WORK)
        need('apply=False ok=3 skip=0' in dry.stdout, '干跑异常: %s' % dry.stdout.strip())
        ap = sh(base + ['-Apply'], cwd=WORK)
        need('apply=True ok=3 skip=0' in ap.stdout, '执行异常: %s' % ap.stdout.strip())
        return 'dry ok=3 skip=0 -> apply ok=3 skip=0'

    def s5():
        exp = {'主武器-AK-47 突击步枪-[AK47] CrossFire AK47-A': ['.vpk', '.url'],
               '生还者-Coach-Lime replace Coach': ['.vpk', '.jpg', '.url'],
               '近战-武士刀-手工件_武士刀测试': ['.vpk']}
        for b, exts in exp.items():
            for e in exts:
                need(os.path.exists(os.path.join(AD, b + e)), '缺 %s%s' % (b, e))
        need(not os.path.exists(os.path.join(AD, '近战-武士刀-手工件_武士刀测试.url')), '手工件不该建 .url')
        need(os.listdir(WS) == [], 'workshop 没清空')
        need(os.path.isdir(WS), 'workshop 目录被删了')
        return '3 件入库 / 手工件无 .url / workshop 空且保留'

    def s6():
        r = bat()
        need(r.returncode == 0 and '"unclassifiedPaths": 0' in r.stdout, '再刷新失败')
        need(len(rj(os.path.join(WD, 'addons_scan.json'))) == 3, '刷新后应扫到 3 个')
        return '3 个 mod 进入清单'

    def s6b():
        # 人工标签覆盖：给一个 mod 手动补表格行标签，应计入并回写两份派生数据；再跑一次应幂等
        ov = os.path.join(WD, 'label_override.json')
        coach = '生还者-Coach-Lime replace Coach.vpk'
        with open(ov, 'w', encoding='utf-8') as f:
            json.dump([{'mod': coach, 'add_labels': ['手电筒'], 'reason': 'selftest'}], f, ensure_ascii=False)
        r = bat()
        need(r.returncode == 0 and '"unclassifiedPaths": 0' in r.stdout, '覆盖后刷新失败')
        need('人工标签覆盖: 并入 1 条标签' in r.stdout, '覆盖未生效: %s' % r.stdout[-300:])
        bt = rj(os.path.join(WD, 'addons_by_target.json'))
        need(coach in bt.get('手电筒', []), 'by_target 没并入')
        sc = {m['file']: m for m in rj(os.path.join(WD, 'addons_scan.json'))}
        need('手电筒' in (sc[coach].get('targets') or {}), 'addons_scan 没并入')
        # 刷新会重跑 scan（addons_scan.json 每次重生成），所以覆盖**每次都重新并入**；
        # 正确的不变量是「计数不累加」，不是「第二次不再打印」。
        r2 = bat()
        need(r2.returncode == 0, '第二次刷新失败')
        bt2 = rj(os.path.join(WD, 'addons_by_target.json'))
        need(bt2.get('手电筒', []).count(coach) == 1, '重复应用导致 by_target 重复计数')
        sc2 = {m['file']: m for m in rj(os.path.join(WD, 'addons_scan.json'))}
        need((sc2[coach].get('targets') or {}).get('手电筒') == 1, '重复应用导致 targets 计数不幂等')
        os.remove(ov)
        bat()
        return '并入 1 条 + 回写两文件 + 幂等 + 已清理'

    def s7():
        r = sh([PYEXE, os.path.join(WD, 'plan_v4.py')], cwd=WORK)
        m = re.search(r'需改名\s*(\d+)\s*个', r.stdout)
        need(m and m.group(1) == '0', '幂等性被破坏：还要改 %s 条' % (m.group(1) if m else '?'))
        return '需改名 0（幂等）'

    def s7b():
        # 冲突留新移旧：造一个「常驻旧件」与已入库的 AK-47 抢同一替换对象
        old = '主武器-AK-47 突击步枪-旧版AK47（自测冲突）'
        keep = '主武器-AK-47 突击步枪-' + A[1]
        sp = os.path.join(root, 'spec_old.json')
        with open(sp, 'w', encoding='utf-8') as f:
            json.dump([{'path': 'models/w_models/weapons/w_rifle_ak47.mdl', 'text': 'IDST OLD-AK47'}],
                      f, ensure_ascii=False)
        r = sh([node, VPKWRITE, os.path.join(AD, old + '.vpk'), sp])
        need(r.returncode == 0, '造常驻旧件失败: %s' % r.stderr[-200:])
        rc = os.path.join(WD, 'resolve_conflicts.ps1')
        need(os.path.exists(rc), 'resolve_conflicts.ps1 没铺下来')
        ps = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', rc, '-Batch']
        bad = os.path.join(WD, 'conflict_bad.json')
        with open(bad, 'w', encoding='utf-8') as f:
            json.dump([{'target': 'AK-47 突击步枪', 'keep': 'no-such-mod',
                        'move': [old], 'reason': 'selftest safety'}], f, ensure_ascii=False)
        # 负向（关键安全不变式）：keep 不存在 -> 整条拒绝，绝不把替换对象搬空
        r = sh(ps + [bad, '-Apply'], cwd=WORK)
        need('files=0' in r.stdout and 'KEEP-MISSING' in r.stdout,
             '负向安全测试没拦住: %s' % r.stdout.strip()[-200:])
        need(os.path.exists(os.path.join(AD, old + '.vpk')), '负向测试居然把文件搬走了')
        # 正向：工坊来的那件胜出 -> 旧件进 mod备份 + 清单加行
        good = os.path.join(WD, 'conflict_good.json')
        with open(good, 'w', encoding='utf-8') as f:
            json.dump([{'target': 'AK-47 突击步枪', 'keep': keep, 'move': [old],
                        'reason': 'selftest: workshop item always wins'}], f, ensure_ascii=False)
        dry = sh(ps + [good], cwd=WORK)
        need('DRY RUN' in dry.stdout and 'files=1' in dry.stdout, '干跑异常: %s' % dry.stdout.strip()[-200:])
        ap = sh(ps + [good, '-Apply'], cwd=WORK)
        need('APPLY' in ap.stdout and 'files=1' in ap.stdout, '执行异常: %s' % ap.stdout.strip()[-200:])
        bk = os.path.join(AD, 'mod备份')
        need(os.path.exists(os.path.join(bk, old + '.vpk')), '旧件没进 mod备份')
        need(not os.path.exists(os.path.join(AD, old + '.vpk')), '旧件还在 addons')
        need(os.path.exists(os.path.join(AD, keep + '.vpk')), '胜方不见了（不该动它）')
        mf = os.path.join(bk, 'backup_manifest.md')
        need(os.path.exists(mf) and old in open(mf, encoding='utf-8').read(), '清单没记这行')
        return '负向拦截OK / 干跑files=1 / 旧件进 mod备份 + 清单加行 / 胜方未动'

    def s8():
        out = []
        r = sh(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', os.path.join(WD, 'scan_targets.ps1')], cwd=WORK)
        m = re.search(r'conflicts=(\d+)', r.stdout)
        need(m and m.group(1) == '0', '冲突扫描: %s' % r.stdout.strip()[-150:])
        out.append('conflicts=0')
        r = sh([node, os.path.join(WD, 'verify_rules.mjs')], cwd=WORK)
        j = json.loads(r.stdout[r.stdout.index('{'):])
        need(j['failed'] == [], 'verify_rules 失败 %s' % j['failed'])
        out.append('verify_rules %d/%d' % (j['passed'], j['cases']))
        r = sh([PYEXE, os.path.join(WD, 'verify_fixes.py')], cwd=WORK)
        j = json.loads(r.stdout[r.stdout.index('{'):])
        need(j['缺陷4_多值单元格全路径']['不合格条目数'] == 0, 'verify_fixes 不合格')
        out.append('verify_fixes 0')
        r = sh([PYEXE, os.path.join(HERE, 'verify_ps1_ascii.py'), WD], cwd=WORK)
        need('"ok": true' in r.stdout, '.ps1 非 ASCII 护栏未通过: %s' % r.stdout.strip())
        out.append('ps1 ASCII 护栏 OK')
        return ' / '.join(out)

    for nm, fn in (('S1 bootstrap 生成工作区', s1), ('S2 造 3 个假 VPK 进 workshop', s2),
                   ('S3 刷新表格（空库也能跑）', s3), ('S3b 扫 workshop 暂存件（命名证据）', s3b),
                   ('S4 搬迁（consolidate5 干跑+执行）', s4), ('S5 校验搬迁结果', s5),
                   ('S6 再刷新（新 mod 进清单）', s6),
                   ('S6b 人工标签覆盖（label_override）', s6b),
                   ('S7 命名推演幂等', s7),
                   ('S7b 冲突留新移旧（resolve_conflicts）', s7b),
                   ('S8 冲突扫描 + 校验 + ASCII 护栏', s8)):
        stage(nm, fn)

    print('=' * 92)
    print('l4d2-addons 全链路自测   (node=%s)' % node)
    print('=' * 92)
    for nm, st, ex in res:
        print('  [%s] %-34s %s' % (st, nm, ex))
    bad = [r for r in res if r[1] == 'FAIL']
    print()
    print('结果: %d/%d 通过' % (len(res) - len(bad), len(res)))
    if a.keep or bad:
        print('临时目录保留在: %s' % root)
    else:
        shutil.rmtree(root, ignore_errors=True)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
