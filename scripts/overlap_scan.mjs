// overlap_scan.mjs —— 找出「互抢同一批文件」的 mod 对（精确到内容是否真的不同）
//
// 为什么要它：冲突扫描（scan_targets.ps1）按「前缀 + 第二段」分组，verify_overlaps 按标签归类 ——
// 两者都看不出「第二段名不同、却改同一个文件」的真冲突。实证 2026-10-05：
//   主武器-镀铬霰弹枪-[国家队02]FARANXX铁喷  ×  主武器-霰弹枪-Chrome Shotgun-COD…
//   两者都换 models/v_models/v_shotgun_chrome.{mdl,vvd,dx90.vtx}，但分组名不同 → 两个工具全静默。
//
// 判据（关键）：
//   1. 两件装了同一个路径 = 交集。但**交集本身不等于冲突** —— 很多 mod 会带上原版素材、
//      同作者的共用贴图、VScript 公共库，字节完全一样，同时启用毫无影响。
//   2. 所以逐条比对 VPK 目录树里的 **CRC + entryLength**（VPK 每条记录自带）：
//        内容相同 → 良性，只计数；内容不同 → 才是真抢位（后加载的赢）。
//   3. 公共库（director_base_addon.nut / scriptedmode_addon.nut 等唯一入口）单独归类 —— 那是
//      引擎级的"脚本池互斥"结构，不是文件级抢位。
//
// 用法:
//   node overlap_scan.mjs               # 全量（含 CRC 比对，默认）
//   node overlap_scan.mjs --strict      # 存在真抢位时退出码 1（可当门禁）
//   node overlap_scan.mjs --paths-only  # 跳过 CRC，只看路径交集（快，但噪声大）
//   node overlap_scan.mjs --min 2       # 只报"内容不同"的交集 ≥ N 条的对（默认 1）

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const _dir = path.dirname(fileURLToPath(import.meta.url));
const HOME = process.env.L4D2_HOME || path.dirname(_dir);
let CFG = {};
try { CFG = JSON.parse(fs.readFileSync(path.join(HOME, 'config.json'), 'utf8')); } catch (e) {}
const WORK = path.join(HOME, CFG.scriptsDir || '_work');
const ADDONS = process.env.L4D2_ADDONS || CFG.addonsDir || '';

function arg(name, dflt) {
  const i = process.argv.indexOf('--' + name);
  const v = i >= 0 ? process.argv[i + 1] : undefined;
  return v && !v.startsWith('--') ? v : dflt;
}
const STRICT = process.argv.includes('--strict');
const PATHS_ONLY = process.argv.includes('--paths-only');
const MIN = parseInt(arg('min', '1'), 10) || 1;
const TOP = parseInt(arg('top', '6'), 10) || 6;      // stdout 只印前 N 条，完整结果写文件
const OUT_MD = path.join(WORK, 'blind_overlaps.md');

// 必然共享、与冲突无关的元文件
const META = /^(addoninfo\.txt|addonimage\.(jpg|jpeg|png|vtf)|sound\/sound\.cache|thumbs\.db)$/i;
// 引擎级公共入口/库：所有 VScript addon 都会带，单独归类
const SHARED_LIB = /^scripts\/vscripts\/(director_base_addon|scriptedmode_addon|dis_base_lib)\.nut$/i;

const stem = (s) => s.replace(/\.vpk$/i, '');
// 与 scan_targets.ps1 相同的分组键：前缀 + 第二段（到下一个短横）
const cat2 = (s) => { const i = s.indexOf('-'); if (i < 0) return s; const j = s.indexOf('-', i + 1); return j < 0 ? s : s.slice(0, j); };

// ---- VPK 目录树：路径 → {crc, len}（只读目录树，不读数据块）----
const cstr = (b, st) => { const i = b.indexOf(0, st); return { s: b.toString('latin1', st, i), next: i + 1 }; };
function treeEntries(file) {
  const out = new Map();
  let fd;
  try { fd = fs.openSync(file, 'r'); } catch (e) { return out; }
  try {
    const head = Buffer.alloc(28); fs.readSync(fd, head, 0, 28, 0);
    if (head.readUInt32LE(0) !== 0x55AA1234) return out;
    const ver = head.readUInt32LE(4), off = ver === 2 ? 28 : 12, treeSize = head.readUInt32LE(8);
    const buf = Buffer.alloc(treeSize); fs.readSync(fd, buf, 0, treeSize, off);
    let p = 0;
    while (p < treeSize) {
      let r = cstr(buf, p); p = r.next; const ext = r.s; if (!ext) break;
      while (true) {
        r = cstr(buf, p); p = r.next; const dir = r.s; if (!dir) break;
        while (true) {
          r = cstr(buf, p); p = r.next; const nm = r.s; if (!nm) break;
          const crc = buf.readUInt32LE(p);            // VPK entry: crc(4) preload(2) arch(2) off(4) len(4) term(2)
          const len = buf.readUInt32LE(p + 12);
          const preload = buf.readUInt16LE(p + 4);
          // 归一化：根条目在树里可能是 " "(空格) 或空串 → 必须清掉前导空白/斜杠并压缩 //
          const full = (( dir ? dir.replace(/^[\s\/]+/, '') + '/' : '') + nm + '.' + ext)
            .replace(/^[\s\/]+/, '').replace(/\/{2,}/g, '/').toLowerCase();
          out.set(full, crc + ':' + len);
          p += 16 + 2; if (preload > 0) p += preload;
        }
      }
    }
    return out;
  } catch (e) { return out; } finally { fs.closeSync(fd); }
}

// ---- 自己枚举 addons 顶层并解析目录树（路径 + CRC 一次拿到）----
// 不依赖 rv_paths.json：那个文件由 rv_dump_paths.mjs 手动生成，刷新链路并不更新它，天生会过期。
let files = [];
try { files = fs.readdirSync(ADDONS).filter((f) => f.toLowerCase().endsWith('.vpk')); }
catch (e) { console.log('OVERLAP FAIL 读不到 addons 目录：' + ADDONS); process.exit(1); }

const crcOf = {};        // stem -> Map(路径 → "crc:len")
const mods = {};         // stem -> [路径]
for (const f of files) {
  const s = stem(f);
  const m = treeEntries(path.join(ADDONS, f));   // 一次读树：路径与 CRC 同时得到
  crcOf[s] = m;
  mods[s] = [...m.keys()];
}
const names = Object.keys(mods).sort();
const missing = [];

// 声明过的多件套 / 白名单
let sets = [];
try { sets = JSON.parse(fs.readFileSync(path.join(WORK, 'set_exempt.json'), 'utf8')); } catch (e) {}
const inSet = {};
for (const s of sets) for (const m of s.members || []) inSet[stem(m)] = s.name;
let wl = [];
try {
  for (const ln of fs.readFileSync(path.join(ADDONS, 'mod白名单.txt'), 'utf8').split(/\r?\n/)) {
    const t = ln.trim();
    if (!t || t.startsWith('【') || t.startsWith('→') || t.startsWith('（') || /^\d{4}-/.test(t)) continue;
    if (ln.startsWith('  ') && t.includes('-') && !t.includes('：') && !t.includes(':')) wl.push(stem(t));
  }
} catch (e) {}
const whitelisted = (s) => wl.some((w) => s === w || s.startsWith(w));

// ---- 反向索引：路径 → 用到它的 mod ----
const byPath = new Map();
const byLib = new Map();
for (const [m, ps] of Object.entries(mods)) {
  for (const p of ps) {
    if (SHARED_LIB.test(p)) { if (!byLib.has(p)) byLib.set(p, []); byLib.get(p).push(m); continue; }
    if (META.test(p)) continue;
    if (!byPath.has(p)) byPath.set(p, []);
    byPath.get(p).push(m);
  }
}

// ---- CRC：从已解析的树里取（无需二次读盘）----
const getCrc = (m) => crcOf[m] || new Map();

// ---- 汇总 ----
const pair = new Map();       // key -> {same:[paths], diff:[paths]}
const bump = (a0, b0, p, same) => {
  const [a, b] = a0 < b0 ? [a0, b0] : [b0, a0];
  const k = a + '\u0000' + b;
  if (!pair.has(k)) pair.set(k, { same: [], diff: [] });
  (same ? pair.get(k).same : pair.get(k).diff).push(p);
};
for (const [p, ms] of byPath) {
  if (ms.length < 2) continue;
  for (let i = 0; i < ms.length; i++) for (let j = i + 1; j < ms.length; j++) {
    let same = false;                                   // 默认按「不同」处理（保守：宁可报出来）
    if (!PATHS_ONLY) {
      const ca = getCrc(ms[i]).get(p), cb = getCrc(ms[j]).get(p);
      same = ca !== undefined && cb !== undefined && ca === cb;   // 内容一致 → 良性
    }
    bump(ms[i], ms[j], p, same);
  }
}

const rows = [];
for (const [k, v] of pair) {
  const [a, b] = k.split('\u0000');
  const sameSet = inSet[a] && inSet[b] && inSet[a] === inSet[b];
  const wlBoth = whitelisted(a) && whitelisted(b);
  rows.push({
    a, b, sameN: v.same.length, diffN: v.diff.length, diff: v.diff,
    sameSet, wlBoth, setInfo: sameSet ? inSet[a] : null, sameGroup: cat2(a) === cat2(b),
  });
}
const real = rows.filter((r) => r.diffN >= MIN && !r.sameSet && !r.wlBoth);          // 需裁决
const benign = rows.filter((r) => r.diffN < MIN || r.sameSet || r.wlBoth);           // 折叠
real.sort((x, y) => y.diffN - x.diffN || y.sameN - x.sameN);
benign.sort((x, y) => (y.diffN + y.sameN) - (x.diffN + x.sameN));

const libPairs = new Set();
for (const [, ms] of byLib) for (let i = 0; i < ms.length; i++) for (let j = i + 1; j < ms.length; j++) {
  const [a, b] = ms[i] < ms[j] ? [ms[i], ms[j]] : [ms[j], ms[i]];
  libPairs.add(a + '\u0000' + b);
}

console.log(`OVERLAP SCAN  件数=${names.length}${PATHS_ONLY ? '  [--paths-only 未比对 CRC，噪声会偏多]' : ''}` +
  `  交集配对=${rows.length}  真抢位=${real.length}`);

if (real.length) {
  console.log('  ⚠️ 真抢位（同一路径、内容不同 → 同时启用时后加载的赢）：');
  for (const r of real.slice(0, TOP)) {
    console.log(`    内容不同 ${String(r.diffN).padStart(3)} 条（另有 ${r.sameN} 条内容相同）  ${r.sameGroup ? '[同组·扫描器也会报]' : '[扫描器看不出：第二组名不同]'}`);
    console.log(`         ${r.a}`);
    console.log(`      ×  ${r.b}`);
    const show = r.diff.slice(0, 4);
    console.log(`         冲突文件: ${show.join(' | ')}${r.diff.length > show.length ? ` … 共 ${r.diff.length} 条` : ''}`);
  }
  if (real.length > TOP) console.log(`    … 其余 ${real.length - TOP} 条见 ${OUT_MD}`);
} else if (rows.length) {
  console.log('  ✓ 有交集但内容都相同（原版素材 / 共用贴图 / 同一作者的公共文件），不算冲突');
} else {
  console.log('  ✓ 没有路径交集');
}
if (benign.length) {
  console.log(`  （折叠 ${benign.length} 对：内容相同 / 多件套 / 白名单）`);
  for (const r of benign.slice(0, 4)) {
    const why = r.sameSet ? `多件套「${r.setInfo}」` : r.wlBoth ? '白名单' : `${r.sameN} 条内容相同`;
    console.log(`     ${why}  ${r.a} × ${r.b}${r.diffN ? `（另有 ${r.diffN} 条不同）` : ''}`);
  }
  if (benign.length > 4) console.log(`     … 其余 ${benign.length - 4} 对同理`);
}
if (libPairs.size) console.log(`  另有 ${libPairs.size} 对只共享 VScript 公共入口/库（director_base_addon / scriptedmode_addon / dis_base_lib）—— 引擎级脚本池互斥，不是文件级抢位`);
console.log(real.length ? 'OVERLAP RESULT: NEEDS REVIEW' : 'OVERLAP RESULT: OK');

// ---- 完整结果写文件（stdout 只给前几条，省 token；细节留给需要时翻文件）----
try {
  const L = [];
  L.push('# 盲点扫描：路径有交集、且内容真的不同（' + new Date().toISOString().slice(0, 19).replace('T', ' ') + '）');
  L.push('');
  L.push('> 由 `overlap_scan.mjs` 生成。判据：两件的 VPK 目录树里有**相同路径**且 **CRC/长度不同** —— ');
  L.push('> 同时启用时后加载的赢，即真抢位。内容相同的交集（原版素材、同作者共用贴图、VScript 公共库）已排除。');
  L.push('> 本文件每次运行都会被覆盖；需要存档请另存。');
  L.push('');
  L.push(`件数 ${names.length} · 交集配对 ${rows.length} · 真抢位 **${real.length}**`);
  L.push('');
  if (real.length) {
    L.push('## 真抢位（需人工裁决）');
    L.push('');
    L.push('| # | 内容不同 | 内容相同 | 同组? | A | B | 冲突文件 |');
    L.push('|---|---|---|---|---|---|---|');
    real.forEach((r, i) => {
      L.push(`| ${i + 1} | ${r.diffN} | ${r.sameN} | ${r.sameGroup ? '是（扫描器也会报）' : '**否**（扫描器看不出）'} | \`${r.a}\` | \`${r.b}\` | ${r.diff.map((p) => '`' + p + '`').join('<br>')} |`);
    });
    L.push('');
  }
  if (benign.length) {
    L.push('## 折叠（内容相同 / 多件套 / 白名单）');
    L.push('');
    for (const r of benign) {
      const why = r.sameSet ? `多件套「${r.setInfo}」` : r.wlBoth ? '白名单' : `${r.sameN} 条内容相同`;
      L.push(`- ${why}：\`${r.a}\` × \`${r.b}\`${r.diffN ? `（另有 ${r.diffN} 条不同）` : ''}`);
    }
    L.push('');
  }
  fs.writeFileSync(OUT_MD, L.join('\n'), 'utf8');
} catch (e) { /* 写报告失败不影响主流程 */ }

if (STRICT && real.length) process.exit(1);
