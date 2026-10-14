// flow.mjs —— 「干活」的固定 10 步里，可自动化的部分合成一条命令
//
// 为什么要它：一次「干活」过去要手打 12-15 条命令（scan_workshop → digest → 读工坊 API →
// 写 batch json → consolidate 干跑 → apply → scan_targets → overlap_scan → 刷新 → verify_all），
// 每条一次调用 + 一段输出。中间还有大量手打路径的失误空间（实测出现过把 addons 路径打错、
// 连查 4 次才定位）。本脚本把「只读探查」与「只读校验」全部收进来，一条命令给一屏结论。
//
// ⚠️ 它**不改库**：搬迁/移旧仍必须走 consolidate5.ps1 / resolve_conflicts.ps1（默认干跑）。
//    这样「先看计划再动手」的用户偏好与脚本的 SKIP 保护都不会被绕过。
//
// 用法:
//   node flow.mjs                 # 只读巡检：暂存件证据 + 名字体检 + 冲突两条腿 + 收尾验收
//   node flow.mjs --plan          # 追加：按已有 ws_batch*.json 出干跑结果（仍不改库）
//   node flow.mjs --names <json>  # 指定候选名做 63 字节体检（默认自动从最新 batch 推）
//   node flow.mjs --quiet         # 只印结论行（给「已确认无变化」的轮次省 token）
//
// 输出纪律：默认只印「需要模型决策的东西」+ 一行总结；明细写 _work\flow_report.md。

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import {
  HOME, WORK, ADDONS, STAGING, BACKUP, CFG,
  arg, flag, treeEntries, classify, stemBytes, STEM_MAX,
  stem, isWorkshopId, listVpk, stemSet, humanMB,
} from './lib.mjs';

const QUIET = flag('quiet');
const OUT_MD = path.join(WORK, 'flow_report.md');
const rep = [];                       // 报告行（写文件）
const say = (s) => { console.log(s); rep.push(s); };
const sec = (t) => { rep.push('', '## ' + t, ''); if (!QUIET) console.log('\n--- ' + t + ' ---'); };

// 定位 python（自测/校验脚本必须用 config.json 的 pythonPath，PATH 上的可能缺 openpyxl）
const PY = CFG.pythonPath || 'python';
const run = (cmd, args, opts = {}) => {
  try { return execFileSync(cmd, args, { encoding: 'utf8', timeout: opts.timeout || 600000, cwd: opts.cwd || HOME }); }
  catch (e) { return ((e.stdout || '') + (e.stderr || '')).toString(); }
};

// ============ 1. 暂存件证据 ============
sec('暂存件（' + STAGING + '）');
const wsFiles = listVpk(STAGING);
const manual = wsFiles.filter((f) => !isWorkshopId(f));
const shop = wsFiles.filter(isWorkshopId);
say(`件数=${wsFiles.length}  工坊件=${shop.length}  手工件=${manual.length}`);
if (!wsFiles.length) say('（workshop\\ 为空 —— 本轮无新件，跳到校验）');

// 名字体检用到的 addons 现存名
const existing = stemSet(ADDONS);

const rows = [];
const uncAll = {};
for (const f of wsFiles) {
  const full = path.join(STAGING, f);
  const id = isWorkshopId(f) ? stem(f) : '(手工件)';
  const sizeMB = humanMB(fs.statSync(full).size);
  const t = treeEntries(full);
  if (!t.size) { rows.push({ id, sizeMB, bad: 'PARSE_FAIL' }); continue; }
  const by = {}; const unc = [];
  for (const p of t) { const l = classify(p); by[l] = (by[l] || 0) + 1; if (l === '未归类') unc.push(p); }
  const cnt = (exts) => [...t].filter((p) => exts.some((x) => p.toLowerCase().endsWith(x))).length;
  const top = Object.entries(by).sort((a, b) => b[1] - a[1]).filter(([l]) => l !== '打包元文件').slice(0, 3);
  const bsp = [...t].find((p) => p.toLowerCase().endsWith('.bsp'));
  const mdl = [...t].find((p) => p.toLowerCase().endsWith('.mdl'));
  const nut = [...t].find((p) => p.toLowerCase().endsWith('.nut'));
  rows.push({
    id, sizeMB, paths: t.size,
    bsp: cnt(['.bsp']), nav: cnt(['.nav']), mdl: cnt(['.mdl']), nut: cnt(['.nut']), snd: cnt(['.wav', '.mp3']),
    top: top.map(([l, n]) => `${l}(${n})`).join(' ') || '-',
    unc: unc.length, sample: bsp || nut || mdl || [...t][0] || '',
  });
  if (unc.length) uncAll[f] = unc.slice(0, 6);
}
if (!QUIET && rows.length) {
  console.log('  id             MB      路径  bsp nav mdl nut snd  命中标签(前3)                                      未归类');
  for (const r of rows) {
    if (r.bad) { console.log(`  ${r.id.padEnd(13)} ${r.sizeMB.padStart(7)}  ${r.bad}`); continue; }
    console.log(`  ${r.id.padEnd(13)} ${r.sizeMB.padStart(7)} ${String(r.paths).padStart(5)} ${String(r.bsp).padStart(3)} ${String(r.nav).padStart(3)} ${String(r.mdl).padStart(3)} ${String(r.nut).padStart(3)} ${String(r.snd).padStart(3)}  ${r.top.slice(0, 48).padEnd(48)} ${String(r.unc).padStart(5)}`);
  }
}
for (const r of rows) rep.push(`- \`${r.id}\` ${r.sizeMB} MB · ${r.paths || 0} 路径 · bsp${r.bsp || 0} nav${r.nav || 0} mdl${r.mdl || 0} nut${r.nut || 0} snd${r.snd || 0} · ${r.top || '-'} · 未归类 ${r.unc || 0} · 抽样 \`${r.sample || ''}\``);
const badTree = rows.filter((r) => r.bad);
if (badTree.length) say('⚠️ 解析失败: ' + badTree.map((r) => r.id).join(', '));
if (Object.keys(uncAll).length) {
  say('⚠️ 未归类（必须为 0，否则补规则）:');
  for (const [f, us] of Object.entries(uncAll)) say(`   ${f}: ${us.join(' | ')}`);
  rep.push('', '### 未归类明细', '');
  for (const [f, us] of Object.entries(uncAll)) rep.push(`- ${f}: ${us.join(' | ')}`);
}

// ============ 2. 候选名体检 ============
// 优先用 --names 指定；否则从最新 ws_batch*.json 推；再否则用工坊原标题不可知 → 跳过
let cands = [];
const namesArg = arg('names', '');
if (namesArg && fs.existsSync(namesArg)) {
  cands = JSON.parse(fs.readFileSync(namesArg, 'utf8'))
    .map((x) => (typeof x === 'string' ? x : [x.base, x.cat && x.title ? `${x.cat}-${x.title}` : ''].filter(Boolean)[0] || ''))
    .filter(Boolean);
} else {
  // 自动推：只在「batch 里的 src 文件此刻仍躺在 workshop\」时才用它 —— 否则那是**上一轮已处理完**
  // 的批次，拿它做体检会把已入库的名字报成「占用」，纯误导（实测踩过：ws_batch19 报 5 个假占用）。
  const stagingNow = new Set(fs.readdirSync(STAGING).filter((f) => f.toLowerCase().endsWith('.vpk')));
  const batches = fs.readdirSync(WORK).filter((f) => /^ws_batch\d+\.json$/.test(f))
    .map((f) => ({ f, n: parseInt(f.match(/(\d+)/)[1], 10) })).sort((a, b) => b.n - a.n);
  for (const { f } of batches) {
    const b = JSON.parse(fs.readFileSync(path.join(WORK, f), 'utf8'));
    const live = b.filter((x) => x.src && stagingNow.has(x.src));
    if (live.length) {
      cands = live.map((x) => x.base || [x.cat, x.target, x.title].filter(Boolean).join('-')).filter(Boolean);
      say(`（名字体检取 ${f} 中仍在暂存区的 ${live.length} 件；其余批次已处理完，不参与）`);
      break;
    }
  }
}
if (cands.length) {
  sec('名字体检（主干 ≤ ' + STEM_MAX + ' ANSI 字节；占用=addons 顶层已有同名）');
  let over = 0; let occ = 0;
  for (const n of cands) {
    const b = stemBytes(n); const isOver = b > STEM_MAX; const isOcc = existing.has(n);
    if (isOver) over++; if (isOcc) occ++;
    if (!QUIET || isOver || isOcc) {
      console.log(`  ${String(b).padStart(3)} 字节  ${isOver ? '✗超限' : '✓    '}  ${isOcc ? '⚠占用' : 'free  '}  ${n}`);
    }
    rep.push(`- ${b} 字节 ${isOver ? '✗超限' : '✓'} ${isOcc ? '⚠占用' : 'free'} \`${n}\``);
  }
  say(over || occ ? `名字体检：超限 ${over} / 占用 ${occ}` : `名字体检：全部合规（${cands.length} 条）`);
}

// ============ 3. 冲突两条腿 ============
sec('冲突检查');
// 3a 名字级：调 scan_targets.ps1（真源，别重写）
const stOut = run('powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.join(WORK, 'scan_targets.ps1')]);
const stM = stOut.match(/conflicts=(\d+)/);
const stN = stM ? stM[1] : '?';
say(`名字级 scan_targets.ps1：conflicts=${stN}`);
if (stN !== '0' && stN !== '?') {
  const cf = path.join(WORK, 'target_conflicts.txt');
  if (fs.existsSync(cf)) {
    const txt = fs.readFileSync(cf, 'utf8').split(/\r?\n/);
    const i = txt.findIndex((l) => l.includes('CONFLICT'));
    if (i >= 0) { console.log(txt.slice(i, i + 12).join('\n')); rep.push('', '```', ...txt.slice(i, i + 12), '```'); }
  }
}

// 3b 文件级：调 overlap_scan.mjs（它自己会写 blind_overlaps.md）
const ovOut = run('node', [path.join(WORK, 'overlap_scan.mjs'), '--top', QUIET ? '0' : '3']);
const ovM = ovOut.match(/真抢位=(\d+)/);
const ovN = ovM ? ovM[1] : '?';
say(`文件级 overlap_scan.mjs：真抢位=${ovN}（明细 _work\\blind_overlaps.md）`);

// ============ 4. 干跑（可选）============
if (flag('plan')) {
  const batches = fs.readdirSync(WORK).filter((f) => /^ws_batch\d+\.json$/.test(f))
    .map((f) => ({ f, n: parseInt(f.match(/(\d+)/)[1], 10) })).sort((a, b) => b.n - a.n);
  if (batches.length) {
    sec('搬迁干跑（不改库）');
    const bp = path.join(WORK, batches[0].f);
    const dr = run('powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.join(WORK, 'consolidate5.ps1'), '-Batch', bp]);
    say(`${batches[0].f}  ${dr.trim().split(/\r?\n/).pop()}`);
    const log = path.join(WORK, path.basename(bp, '.json') + '_log.txt');
    if (fs.existsSync(log)) {
      const ls = fs.readFileSync(log, 'utf8').split(/\r?\n/).filter((l) => /new    =/.test(l));
      for (const l of ls) console.log('   ' + l.trim());
      rep.push('', '```', ...ls.map((l) => l.trim()), '```');
    }
  }
}

// ============ 5. 收尾验收（一条命令）============
sec('收尾验收');
const vaOut = run(PY, [path.join(WORK, 'verify_all.py')], { timeout: 900000 });
const vaLine = vaOut.split(/\r?\n/).filter((l) => /^ALL OK|^FAIL/.test(l)).pop() || vaOut.trim().split(/\r?\n/).pop();
say(vaLine);
if (!/^ALL OK/.test(vaLine || '')) { console.log(vaOut.split(/\r?\n/).slice(-25).join('\n')); }

// ============ 落盘 ============
const head = `# 干活巡检报告（${new Date().toISOString().replace('T', ' ').slice(0, 19)}）\n\n> 由 \`flow.mjs\` 生成，每次运行覆盖。**本脚本不改库** —— 搬迁/移旧仍走 consolidate5.ps1 / resolve_conflicts.ps1。`;
fs.writeFileSync(OUT_MD, head + '\n' + rep.join('\n') + '\n', 'utf8');

// 总结行（给模型看的唯一必须读的一行）
console.log('\nFLOW SUMMARY  ' + [
  `staging=${wsFiles.length}(工坊${shop.length}/手工${manual.length})`,
  `conflicts=${stN}`, `overlaps=${ovN}`,
  /^ALL OK/.test(vaLine || '') ? 'verify=OK' : 'verify=FAIL',
].join('  '));
console.log('报告: ' + OUT_MD);
