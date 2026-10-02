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
// 独立解出 addons 下每个 VPK 的完整资源路径，落盘给 rv_check.py 用
import fs from 'node:fs';
import path from 'node:path';

const A = L4D2_ADDONS;
const OUT = _L4D2_path.join(L4D2_WORK, "rv_paths.json");

const cstr = (buf, st) => { const e = buf.indexOf(0, st); return { s: buf.toString('latin1', st, e), next: e + 1 }; };

const readVpkTree = (file) => {
  const buf = fs.readFileSync(file);
  if (buf.length < 12 || buf.readUInt32LE(0) !== 0x55AA1234) return null;
  const ver = buf.readUInt32LE(4);
  let p = ver === 2 ? 28 : 12;
  const end = p + buf.readUInt32LE(8);
  const list = [];
  while (p < end) {
    let r = cstr(buf, p); p = r.next; const ext = r.s; if (!ext) break;
    while (true) {
      r = cstr(buf, p); p = r.next; let dir = r.s; if (!dir) break;
      if (dir === ' ') dir = '';
      while (true) {
        r = cstr(buf, p); p = r.next; const name = r.s; if (!name) break;
        const preload = buf.readUInt16LE(p + 4);
        p += 18 + preload;
        list.push((dir ? dir + '/' : '') + name + '.' + ext);
      }
    }
  }
  return { list, treeSize: buf.readUInt32LE(8), consumed: end - (ver === 2 ? 28 : 12) };
};

const files = [];
for (const e of fs.readdirSync(A, { withFileTypes: true })) {
  if (e.isFile() && /\.vpk$/i.test(e.name)) files.push({ name: e.name, full: path.join(A, e.name) });
}
const cf = path.join(A, 'cfhd', 'pak01_dir.vpk');
if (fs.existsSync(cf)) files.push({ name: 'cfhd\\pak01_dir.vpk', full: cf });

const out = {};
let total = 0, bad = [];
for (const f of files) {
  let r = null;
  try { r = readVpkTree(f.full); } catch (e) { r = null; }
  if (!r) { bad.push([f.name, 'parse failed']); continue; }
  if (r.consumed !== r.treeSize) bad.push([f.name, `tree desync ${r.consumed}/${r.treeSize}`]);
  out[f.name] = r.list;
  total += r.list.length;
}
fs.writeFileSync(OUT, JSON.stringify(out), 'utf8');
console.log(JSON.stringify({ vpk: files.length, totalPaths: total, treeSelfCheckFailed: bad }, null, 1));
