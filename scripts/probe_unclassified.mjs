// ==== L4D2 skill: 统一路径解析（构建时注入，勿手改）====
import _L4D2_fs from 'node:fs';
import _L4D2_path from 'node:path';
import { fileURLToPath as _L4D2_fu } from 'node:url';
const _L4D2_dir = _L4D2_path.dirname(_L4D2_fu(import.meta.url));
const L4D2_HOME = process.env.L4D2_HOME || _L4D2_path.dirname(_L4D2_dir);
let L4D2_CFG = {};
try { L4D2_CFG = JSON.parse(_L4D2_fs.readFileSync(_L4D2_path.join(L4D2_HOME, 'config.json'), 'utf8')); } catch (e) {}
const L4D2_WORK = _L4D2_path.join(L4D2_HOME, L4D2_CFG.scriptsDir || '_work');
const L4D2_ADDONS = process.env.L4D2_ADDONS || L4D2_CFG.addonsDir
  || 'D:\\Steam\\steamapps\\common\\Left 4 Dead 2\\left4dead2\\addons';
const L4D2_XLSX = process.env.L4D2_XLSX_OUT
  || _L4D2_path.join(L4D2_HOME, L4D2_CFG.xlsxName || '求生之路2_可MOD替换物品总表.xlsx');
// ==== 注入结束 ====
// 探针：用 scan_addons.mjs 当前 RULES 分类指定 mod 的内部路径，列出未归类项
import fs from 'node:fs';
import path from 'node:path';

const W = L4D2_WORK;
const A = L4D2_ADDONS;

const src = fs.readFileSync(W + 'scan_addons.mjs', 'utf8');
const s0 = src.indexOf('const GAME_ROOTS = [');
const e0 = src.indexOf('\n];', src.indexOf('const RULES = ['));
const { RULES, normalizePath } = new Function(src.slice(s0, e0 + 3) + '\nreturn { RULES, normalizePath };')();
// 必须和 scan_addons.mjs 一致：先归一化再匹配
const classify = (p) => {
  const n = normalizePath(p);
  for (const [re, lab] of RULES) if (re.test(n)) return lab;
  return '未归类';
};

const cstr = (b, st) => { const i = b.indexOf(0, st); return { s: b.toString('latin1', st, i), next: i + 1 }; };
const tree = (file) => {
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
        r = cstr(buf, p); p = r.next; const name = r.s; if (!name) break;
        const preload = buf.readUInt16LE(p + 4); const t = p + 16; p = t + 2; if (preload > 0) p += preload;
        list.push((dir ? dir + '/' : '') + name + '.' + ext);
      }
    }
  }
  return { list, consumed: p, treeSize };
};

const TARGETS = process.argv.slice(2);
const report = {};
for (const t of TARGETS) {
  const files = fs.readdirSync(A).filter((f) => f.includes(t) && f.endsWith('.vpk'));
  for (const f of files) {
    const r = tree(path.join(A, f));
    if (!r) { report[f] = 'PARSE_FAIL'; continue; }
    const by = {};
    const unc = [];
    for (const p of r.list) {
      const lab = classify(p);
      by[lab] = (by[lab] || 0) + 1;
      if (lab === '未归类') unc.push(p);
    }
    report[f] = {
      selfCheck: r.consumed === r.treeSize ? 'ok' : `MISMATCH ${r.consumed}/${r.treeSize}`,
      paths: r.list.length,
      byLabel: by,
      unclassified: unc.slice(0, 40),
      unclassifiedCount: unc.length,
    };
  }
}
console.log(JSON.stringify(report, null, 1).slice(0, 6000));
