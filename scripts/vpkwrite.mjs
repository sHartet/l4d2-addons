// 造一个合法的 VPK v1（目录树 + 数据段），够 scan_addons / rv_dump_paths / vpkdump 解析
// 用法: node vpkwrite.mjs <out.vpk> <spec.json>
//   spec.json = [ { "path": "models/w_models/weapons/w_rifle_ak47.mdl", "text": "MDL..." }, ... ]
//   路径自动拆成 VPK 的 ext / dir / name 三层；根目录文件（addoninfo.txt）的 dir 写作单个空格 " "。
import fs from 'node:fs';
import path from 'node:path';

const [, , outFile, specFile] = process.argv;
if (!outFile || !specFile) { console.error('usage: node vpkwrite.mjs <out.vpk> <spec.json>'); process.exit(2); }
const raw = JSON.parse(fs.readFileSync(specFile, 'utf8'));

const files = raw.map((f) => {
  const p = String(f.path).replace(/\\/g, '/');
  const slash = p.lastIndexOf('/');
  const dir = slash < 0 ? ' ' : p.slice(0, slash);
  const base = slash < 0 ? p : p.slice(slash + 1);
  const dot = base.lastIndexOf('.');
  const name = dot < 0 ? base : base.slice(0, dot);
  const ext = dot < 0 ? '' : base.slice(dot + 1);
  const text = f.text == null ? '' : String(f.text);
  return { ext, dir, name, text, len: Buffer.byteLength(text, 'latin1'),
           key: (dir === ' ' ? '' : dir + '/') + name + (ext ? '.' + ext : '') };
});

const cstr = (s) => Buffer.concat([Buffer.from(s, 'latin1'), Buffer.from([0])]);

function buildTree() {
  const chunks = [];
  const byExt = new Map();
  for (const e of files) {
    if (!byExt.has(e.ext)) byExt.set(e.ext, new Map());
    const dirs = byExt.get(e.ext);
    if (!dirs.has(e.dir)) dirs.set(e.dir, []);
    dirs.get(e.dir).push(e);
  }
  for (const [ext, dirs] of byExt) {
    chunks.push(cstr(ext));
    for (const [dir, list] of dirs) {
      chunks.push(cstr(dir));
      for (const e of list) {
        chunks.push(cstr(e.name));
        const buf = Buffer.alloc(18);
        buf.writeUInt32LE(0, 0);              // crc
        buf.writeUInt16LE(0, 4);              // preloadBytes
        buf.writeUInt16LE(0x7fff, 6);         // archiveIndex 0x7FFF = 数据在本文件
        buf.writeUInt32LE(e.off ?? 0, 8);     // entryOffset（相对数据段起点，规范写法）
        buf.writeUInt32LE(e.len, 12);         // entryLength
        buf.writeUInt16LE(0xffff, 16);        // terminator
        chunks.push(buf);
      }
      chunks.push(cstr(''));
    }
    chunks.push(cstr(''));
  }
  chunks.push(cstr(''));
  return Buffer.concat(chunks);
}

// 第一趟只为量出 treeSize（offset 先填 0）
let tree = buildTree();
const dataStart = 12 + tree.length;
let off = 0;
for (const e of files) { e.off = off; off += e.len; }
tree = buildTree();                        // 第二趟写真实 offset

const header = Buffer.alloc(12);
header.writeUInt32LE(0x55aa1234, 0);
header.writeUInt32LE(1, 4);                // v1：注意 v1 也有 treeSize（必踩的坑）
header.writeUInt32LE(tree.length, 8);

fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, Buffer.concat([header, tree, ...files.map((e) => Buffer.from(e.text, 'latin1'))]));
console.log(JSON.stringify({ out: outFile, entries: files.length, treeSize: tree.length, dataStart }));
