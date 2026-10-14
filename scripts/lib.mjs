// lib.mjs —— 全流程共用的底座（配置解析 / VPK 目录树 / 分类规则 / 名字体检）
//
// 为什么要它：batch_digest.mjs 与 overlap_scan.mjs 各自抄了一份 config 解析、arg 解析、
// VPK 目录树解析（后者还多读 CRC）。三份代码意味着「改一处漏两处」——VPK 根条目归一化
// 那个坑（`" /addoninfo.txt"` 绕过忽略规则，真抢位一度爆到 6774 对）就是因为各写各的。
// 现在只有这一份实现，两个工具都从这里取。
//
// 用法（ESM）：
//   import { HOME, WORK, ADDONS, STAGING, arg, treeEntries, classify, stemBytes, isWorkshopId } from './lib.mjs';
//
// 约定：本文件不做任何 console 输出、不读命令行以外的输入、不写任何文件 —— 纯函数 + 常量。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const _dir = path.dirname(fileURLToPath(import.meta.url));

// ---------- 配置解析（环境变量 → config.json → 内置默认，与各 .ps1 同口径）----------
export const HOME = process.env.L4D2_HOME || path.dirname(_dir);
let _cfg = {};
try { _cfg = JSON.parse(fs.readFileSync(path.join(HOME, 'config.json'), 'utf8')); } catch (e) {}
export const CFG = _cfg;
export const WORK = path.join(HOME, _cfg.scriptsDir || '_work');
export const ADDONS = process.env.L4D2_ADDONS || _cfg.addonsDir || '';
export const STAGING = process.env.L4D2_STAGING || path.join(ADDONS, 'workshop');
export const BACKUP = process.env.L4D2_BACKUP || _cfg.backupDir || path.join(ADDONS, 'mod备份');

// ---------- 命令行 ----------
export function arg(name, dflt) {
  const i = process.argv.indexOf('--' + name);
  const v = i >= 0 ? process.argv[i + 1] : undefined;
  return v && !v.startsWith('--') ? v : dflt;
}
export const flag = (name) => process.argv.includes('--' + name);

// ---------- 分类规则：复用 scan_addons.mjs 的 RULES（同一套分类，避免口径不一致）----------
function loadRules() {
  const src = fs.readFileSync(path.join(WORK, 'scan_addons.mjs'), 'utf8');
  const s = src.indexOf('const GAME_ROOTS = [');
  const e = src.indexOf('\n];', src.indexOf('const RULES = ['));
  return new Function(src.slice(s, e + 3) + '\nreturn { RULES, normalizePath };')();
}
const _r = loadRules();
export const RULES = _r.RULES;
export const normalizePath = _r.normalizePath;
export function classify(p) {
  const n = normalizePath(p);
  for (const [re, lab] of RULES) if (re.test(n)) return lab;
  return '未归类';
}

// ---------- VPK 目录树 ----------
const cstr = (b, st) => { const i = b.indexOf(0, st); return { s: b.toString('latin1', st, i), next: i + 1 }; };

// 归一化：根条目在树里可能是 " "(空格) 或空串 → 必须清掉前导空白/斜杠并压缩 //
// ⚠️ 不做这一步，`" /addoninfo.txt"` 会绕过忽略规则，让每个 mod 两两全配（实测真抢位爆到 6774）。
const normEntry = (dir, nm, ext) =>
  ((dir ? dir.replace(/^[\s/]+/, '') + '/' : '') + nm + '.' + ext)
    .replace(/^[\s/]+/, '').replace(/\/{2,}/g, '/').toLowerCase();

// 读 VPK 目录树。withCrc=false → Set<path>（快）；true → Map<path, "crc:len">（可判内容异同）
export function treeEntries(file, withCrc = false) {
  const out = withCrc ? new Map() : new Set();
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
          const full = normEntry(dir, nm, ext);
          if (withCrc) {
            // VPK entry: crc(4) preload(2) arch(2) off(4) len(4) term(2)
            out.set(full, buf.readUInt32LE(p) + ':' + buf.readUInt32LE(p + 12));
          } else out.add(full);
          const preload = buf.readUInt16LE(p + 4);
          p += 16 + 2; if (preload > 0) p += preload;
        }
      }
    }
  } catch (e) { /* 截断的包：返回已读到的部分 */ } finally { try { fs.closeSync(fd); } catch (e) {} }
  return out;
}

// ---------- 名字与分类小工具 ----------
// ANSI(GBK) 字节数：非 ASCII 一律 2 字节（与 plan_v4._stem_bytes / consolidate5 CapName 同口径）
export const stemBytes = (s) => { let n = 0; for (const ch of s) n += ch.codePointAt(0) > 0x7f ? 2 : 1; return n; };
export const STEM_MAX = 63;                       // 引擎硬约束：主干 ≤63 ANSI 字节，超了根本不挂载
export const stem = (s) => s.replace(/\.vpk$/i, '');
export const isWorkshopId = (s) => /^\d+$/.test(stem(s));
// 与 scan_targets.ps1 相同的分组键：前缀 + 第二段（到下一个短横）
export const cat2 = (s) => { const i = s.indexOf('-'); if (i < 0) return s; const j = s.indexOf('-', i + 1); return j < 0 ? s : s.slice(0, j); };

// ---------- 目录小工具 ----------
export function listVpk(dir) {
  try { return fs.readdirSync(dir).filter((f) => f.toLowerCase().endsWith('.vpk')).sort(); } catch (e) { return []; }
}
export function stemSet(dir) {
  return new Set(listVpk(dir).map((f) => path.basename(f, '.vpk')));
}
export function humanMB(bytes) { return (bytes / 1048576).toFixed(1); }
