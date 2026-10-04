// batch_digest.mjs —— 一屏看全一批暂存件/新件的「命名证据」
//
// 目的：取代每轮临时写的探测脚本。以前为了搞清一批 mod 是什么，我要写好几个临时
//      probe（路径构成 / 标签命中 / 未归类 / 名字占用），每个都是一次 write + 一次 run + 一段输出。
//      现在一条命令给出一屏紧凑证据。
//
// 用法:
//   node batch_digest.mjs                         # 默认扫 workshopDir 里的全部件
//   node batch_digest.mjs --ids 123,456           # 只看这些 id
//   node batch_digest.mjs --dir <目录>            # 换目录（默认 addonsDir\workshop）
//   node batch_digest.mjs --names <names.json>    # 额外做「名字体检」：["地图-XXX", ...] 或批量 JSON 的 base 列表
//
// 输出：每件一行的紧凑摘要 + 未归类明细 + 名字主干字节/占用。只读目录树，很快。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const _dir = path.dirname(fileURLToPath(import.meta.url));
const HOME = process.env.L4D2_HOME || path.dirname(_dir);
let CFG = {};
try { CFG = JSON.parse(fs.readFileSync(path.join(HOME, 'config.json'), 'utf8')); } catch (e) {}
const WORK = path.join(HOME, CFG.scriptsDir || '_work');
const ADDONS = process.env.L4D2_ADDONS || CFG.addonsDir || 'D:\\Steam\\steamapps\\common\\Left 4 Dead 2\\left4dead2\\addons';
const STAGING = process.env.L4D2_STAGING || path.join(ADDONS, 'workshop');

function arg(name, dflt) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : dflt;
}

// ---- 复用 scan_addons.mjs 的规则（同一套分类，避免口径不一致）----
const src = fs.readFileSync(path.join(WORK, 'scan_addons.mjs'), 'utf8');
const s = src.indexOf('const GAME_ROOTS = [');
const e = src.indexOf('\n];', src.indexOf('const RULES = ['));
const { RULES, normalizePath } = new Function(src.slice(s, e + 3) + '\nreturn { RULES, normalizePath };')();
const classify = (p) => { const n = normalizePath(p); for (const [re, lab] of RULES) if (re.test(n)) return lab; return '未归类'; };

// ---- VPK 目录树（只读 tree，不读数据块）----
const cstr = (b, st) => { const i = b.indexOf(0, st); return { s: b.toString('latin1', st, i), next: i + 1 }; };
function tree(file) {
  const fd = fs.openSync(file, 'r');
  const head = Buffer.alloc(28); fs.readSync(fd, head, 0, 28, 0);
  if (head.readUInt32LE(0) !== 0x55AA1234) { fs.closeSync(fd); return null; }
  const ver = head.readUInt32LE(4), off = ver === 2 ? 28 : 12, treeSize = head.readUInt32LE(8);
  const buf = Buffer.alloc(treeSize); fs.readSync(fd, buf, 0, treeSize, off); fs.closeSync(fd);
  let p = 0; const list = [];
  while (p < treeSize) {
    let r = cstr(buf, p); p = r.next; const ext = r.s; if (!ext) break;
    while (true) {
      r = cstr(buf, p); p = r.next; const dir = r.s; if (!dir) break;
      while (true) {
        r = cstr(buf, p); p = r.next; const nm = r.s; if (!nm) break;
        const preload = buf.readUInt16LE(p + 4); const t = p + 16; p = t + 2; if (preload > 0) p += preload;
        list.push((dir ? dir + '/' : '') + nm + '.' + ext);
      }
    }
  }
  return { list, ok: p === treeSize };
}

// ANSI(GBK) 字节数：GBK 是双字节编码，非 ASCII 一律 2 字节（与 plan_v4._stem_bytes 口径一致）
const stemBytes = (s) => { let n = 0; for (const ch of s) n += ch.codePointAt(0) > 0x7f ? 2 : 1; return n; };

// ---- 目标批 ----
const idsFilter = (arg('ids', '') || '').split(',').map((x) => x.trim()).filter(Boolean);
const dir = arg('dir', STAGING);
let files = [];
try {
  files = fs.readdirSync(dir).filter((f) => f.toLowerCase().endsWith('.vpk'));
} catch (e) { console.log('DIGEST FAIL 读不到目录: ' + dir); process.exit(1); }
if (idsFilter.length) files = files.filter((f) => idsFilter.includes(path.basename(f, '.vpk')));
files.sort();

const rows = [];
const unclassifiedAll = {};
for (const f of files) {
  const full = path.join(dir, f);
  const id = /^\d+$/.test(path.basename(f, '.vpk')) ? path.basename(f, '.vpk') : '(手工件)';
  const sizeMB = (fs.statSync(full).size / 1048576).toFixed(1);
  const t = tree(full);
  if (!t) { rows.push({ id, sizeMB, bad: 'PARSE_FAIL' }); continue; }
  const by = {}; const unc = [];
  for (const p of t.list) { const l = classify(p); by[l] = (by[l] || 0) + 1; if (l === '未归类') unc.push(p); }
  const cnt = (exts) => t.list.filter((p) => exts.some((x) => p.toLowerCase().endsWith(x))).length;
  const top = Object.entries(by).sort((a, b) => b[1] - a[1]).filter(([l]) => l !== '打包元文件').slice(0, 3);
  const bsp = t.list.find((p) => p.toLowerCase().endsWith('.bsp'));
  const mdl = t.list.find((p) => p.toLowerCase().endsWith('.mdl'));
  const nut = t.list.find((p) => p.toLowerCase().endsWith('.nut'));
  rows.push({
    id, sizeMB, paths: t.list.length, ok: t.ok,
    bsp: cnt(['.bsp']), nav: cnt(['.nav']), mdl: cnt(['.mdl']), nut: cnt(['.nut']), snd: cnt(['.wav', '.mp3']),
    top: top.map(([l, n]) => `${l}(${n})`).join(' ') || '-',
    unc: unc.length,
    sample: bsp || nut || mdl || t.list[0] || '',
  });
  if (unc.length) unclassifiedAll[f] = unc.slice(0, 6);
}

// ---- 打印 ----
console.log(`DIGEST dir=${dir} 件数=${files.length}`);
console.log('  id             MB      路径  bsp nav mdl nut snd  命中标签(前3)                                          未归类  抽样路径');
for (const r of rows) {
  if (r.bad) { console.log(`  ${r.id.padEnd(13)} ${r.sizeMB.padStart(7)}  ${r.bad}`); continue; }
  console.log(`  ${r.id.padEnd(13)} ${r.sizeMB.padStart(7)} ${String(r.paths).padStart(5)} ${String(r.bsp).padStart(3)} ${String(r.nav).padStart(3)} ${String(r.mdl).padStart(3)} ${String(r.nut).padStart(3)} ${String(r.snd).padStart(3)}  ${r.top.slice(0, 52).padEnd(52)} ${String(r.unc).padStart(5)}  ${String(r.sample).slice(0, 46)}`);
}
const badTree = rows.filter((r) => r.ok === false);
if (badTree.length) console.log('  ⚠️ 树自检失败: ' + badTree.map((r) => r.id).join(','));
if (Object.keys(unclassifiedAll).length) {
  console.log('  --- 未归类明细（需补规则，否则 unclassifiedPaths 不为 0）---');
  for (const [f, us] of Object.entries(unclassifiedAll)) console.log(`    ${f}: ${us.join(' | ')}`);
}

// ---- 可选：名字体检 ----
const namesFile = arg('names', '');
if (namesFile && fs.existsSync(namesFile)) {
  let cands = JSON.parse(fs.readFileSync(namesFile, 'utf8'));
  cands = cands.map((x) => (typeof x === 'string' ? x : (x.base || ''))).filter(Boolean);
  const existing = new Set(fs.readdirSync(ADDONS).filter((f) => f.toLowerCase().endsWith('.vpk')).map((f) => path.basename(f, '.vpk')));
  console.log('  --- 名字体检（主干必须 ≤63 字节；占用=addons 顶层已有同名）---');
  for (const n of cands) {
    const b = stemBytes(n);
    console.log(`    ${String(b).padStart(3)} 字节  ${b > 63 ? '✗超限' : '✓    '}  ${existing.has(n) ? '⚠占用' : 'free  '}  ${n}`);
  }
}
