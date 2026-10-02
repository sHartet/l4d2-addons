// 检测输出 xlsx 是否被 WPS/Excel 占用。参数可以是文件或目录。
// 关键点：Windows 上 fs.accessSync(W_OK) 对 Office 锁无效，必须真正尝试 r+ 打开。
// 中文提示放在这里输出（Node 走 UTF-8，批处理里不写中文，否则 cmd 会按 GBK 解析出错）。
import fs from 'node:fs';
import path from 'node:path';

const arg = process.argv[2] || '.';
let target = arg;
let name = arg;

try {
  if (fs.statSync(arg).isDirectory()) {
    const cands = fs.readdirSync(arg).filter((f) => f.toLowerCase().endsWith('.xlsx'));
    if (!cands.length) { console.log('[0/3] 还没生成过表格，跳过占用检查。'); process.exit(0); }
    name = cands[0];
    target = path.join(arg, cands[0]);
  }
} catch (e) {
  console.log('[0/3] 还没生成过表格，跳过占用检查。');
  process.exit(0);
}

let locked = false;
try {
  const fd = fs.openSync(target, 'r+');
  fs.closeSync(fd);
} catch (e) {
  if (e.code === 'ENOENT') {
    console.log('[0/3] 还没生成过表格，跳过占用检查。');
    process.exit(0);
  }
  locked = true;
}

if (!locked) {
  console.log('[0/3] 输出文件未被占用，可以刷新。');
  process.exit(0);
}

console.log('[0/3] 输出文件被占用，已停止。');
console.log('');
console.log('============================================================');
console.log('  [停止]  表格正被 WPS / Excel 打开，无法写入。');
console.log('');
console.log('  被占用的文件：');
console.log('    ' + name);
console.log('');
console.log('  怎么解决：');
console.log('    1. 切到 WPS，把这张表关掉（或直接关掉 WPS 表格 et.exe）');
console.log('    2. 回到这个文件夹，重新双击「刷新表格.bat」');
console.log('');
console.log('  本次没有做任何修改，表格内容仍是上一次的版本。');
console.log('============================================================');
process.exit(1);
