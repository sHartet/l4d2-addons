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
// 直接从 scan_addons.mjs 抽出 normalizePath + RULES 做功能测试
import fs from 'node:fs';

const SRC = _L4D2_path.join(L4D2_WORK, "scan_addons.mjs");
const src = fs.readFileSync(SRC, 'utf8');

const s = src.indexOf('const GAME_ROOTS = [');
const e = src.indexOf('\n];', src.indexOf('const RULES = ['));
if (s < 0 || e < 0) { console.log('EXTRACT_FAIL'); process.exit(1); }
const block = src.slice(s, e + 3);

// eslint-disable-next-line no-new-func
const { RULES, normalizePath } = new Function(block + '\nreturn { RULES, normalizePath };')();

// 与 scan_addons.mjs 完全一致的分类入口：先归一化再匹配
const classify = (p) => {
  const n = normalizePath(p);
  for (const [re, lab] of RULES) if (re.test(n)) return lab;
  return '未归类';
};

const CASES = [
  // ---- 问题 1：场景类锚定放宽为 ^(models|materials)/ ----
  ['models/props_buildables/ladder.mdl', '场景物件·梯子'],
  ['materials/models/props_c17/metalladder001.vmt', '场景物件·梯子'],
  ['materials/models/props_c17/metalladder001.vtf', '场景物件·梯子'],
  ['materials/models/props_doors/checkpoint_door_01.vmt', '场景物件·门'],
  ['models/props_doors/checkpoint_door_01.mdl', '场景物件·门'],
  ['materials/models/props_crates/supply_crate01.vmt', '场景物件·补给箱'],
  ['materials/models/props_junk/gascan001a.vmt', '道具·汽油桶'],
  ['models/props_junk/gascan001a.mdl', '道具·汽油桶'],
  // 回归护栏：50cal 那条 bug 不许回来
  ['sound/weapons/50cal/50cal_fire1.wav', '音效·.50 重机枪'],
  ['models/w_models/weapons/50cal.mdl', '固定武器·重机枪'],
  ['sound/weapons/minigun/minigun_fire1.wav', '音效·米尼岗机枪'],
  // 道具规则改锚定后，模型与贴图都仍要认出
  ['models/w_models/weapons/w_eq_molotov.mdl', '道具·燃烧瓶'],
  ['materials/models/w_models/weapons/w_eq_molotov.vmt', '道具·燃烧瓶'],
  ['models/v_models/v_medkit.mdl', '道具·急救包'],

  // ---- 问题 2：.bik ----
  ['left 4 dead 2/left4dead2/media/valve.bik', '界面·启动动画'],
  ['left 4 dead 2/left4dead2/media/l4d2_intro.bik', '界面·启动动画'],
  [' /l4d2_background01.bik', '界面·主菜单背景'],
  [' /l4d2_background05.bik', '界面·主菜单背景'],
  ['media/l4d2_background03.bik', '界面·主菜单背景'],

  // ---- 问题 3：打包元文件 & 包装前缀归一化 ----
  [' /addoninfo.txt', '打包元文件'],
  [' /addonimage.jpg', '打包元文件'],
  ['addonimage.png', '打包元文件'],
  ['readme.txt', '打包元文件'],
  ['for_modders/_ignore_readme_pcf_description.xlsx', '打包元文件'],
  ['for_modders/thirdpersonfx_scripts_pcf_debug_demo.vpk', '打包元文件（嵌套 VPK）'],
  ['for_users/error_fix/left 4 dead 2/left4dead2/particles/urik/urik_survivors.pcf', '特效·其它粒子'],
  ['for_users/error_fix/left 4 dead 2/left4dead2/particles/tracers_50cal.pcf', '特效·其它粒子'],
  ['for_modders/particles/3p/weapon_smg.pcf', '特效·其它粒子'],
  ['for_modders/thirdpersonfx_scripts_pcf_debug_demo/scripts/foo.nuc', '脚本·其他'],
  ['for_modders/thirdpersonfx_scripts_pcf_debug_demo/scripts/vscripts/foo.nuc', '脚本·VScript'],
  ['particles/particles_manifest_original.backup', '特效·粒子清单'],

  // ---- 上一轮修的缺陷不许回归 ----
  ['models/survivors/survivor_teenangst_light.mdl', '佐伊（轻量版）'],
  ['models/survivors/survivor_biker_light.mdl', '弗朗西斯（轻量版）'],
  ['models/survivors/survivor_teenangst.mdl', '佐伊 Zoey'],
  ['models/weapons/melee/w_didgeridoo.mdl', '武器·迪吉里杜管'],
  ['models/infected/common_male01.mdl', '普通感染者·男性基础 01'],
  ['models/infected/common_male02.mdl', '普通感染者·男性基础 02'],
  ['models/w_models/weapons/w_knife_t.mdl', '武器·战斗刀'],
  ['models/v_models/v_knife_t.mdl', '武器·战斗刀'],
  ['models/infected/limbs/exploded_boomer.mdl', '感染者残肢·爆炸残肢'],
  ['models/infected/gibs/gibs.mdl', '感染者残肢·血块与碎尸'],
  ['models/w_models/weapons/w_rifle_b.mdl', '模型·其他'],
  ['sound/weapons/axe/axe_swing1.wav', '音效·消防斧'],
  ['sound/weapons/katana/katana_swing1.wav', '音效·武士刀'],
  ['materials/vgui/healthbar_red.vmt', '界面·HUD-生命条'],
  ['materials/vgui/hud/ammo.vmt', '界面·HUD-通用贴图'],
  ['resource/closecaption_schinese.txt', '界面·文本与字幕'],
  ['maps/c1m1_hotel.bsp', '地图·战役'],
  ['maps/c1m1_hotel.nav', '地图·附属文件（导航与光照）'],

  // ---- 2026-10-03 新增两类：手电筒- / 管理员插件- ----
  // 手电筒正例：**只认手电筒本体**（effects/flashlight 光斑贴图 + 含 flashlight 的模型）
  ['materials/effects/flashlight001.vtf', '手电筒'],
  ['models/weapons/w_models/w_flashlight.mdl', '手电筒'],
  // 回归护栏：粒子包/菜单里的共享光束与光晕**不算**手电筒 mod。
  //（实测 材质-ESC菜单 Kokomi自用版 4 条路径里 2 条是 beam_flashlight，曾被误判成手电筒）
  ['materials/particle/beam_flashlight.vmt', '材质·环境贴图'],
  ['materials/particle/beam_flashlight.vtf', '材质·环境贴图'],
  ['materials/particle/flashlight_glow_noz.vmt', '材质·环境贴图'],
  // 回归护栏：枪口焰 / 相机闪光 / 闪光弹 / 引信 **都不含** flashlight 子串，不许被手电筒规则吞掉
  //（这就是为什么规则不用 /flash/）
  ['materials/effects/muzzleflashx.vtf', '材质·环境贴图'],
  ['materials/particles/ins_muzzle_flash_spread.vtf', '材质·环境贴图'],
  ['sound/glub5/camera_flash.mp3', '音效·未列入表格'],
  ['materials/models/re8_flash_grenade', '材质·模型贴图'],
  ['particles/pipe_fuseflash.pcf', '特效·其它粒子'],
  // 管理员插件正例：VScript 管理入口 + SourceMod / MetaMod 交付物
  ['scripts/vscripts/admin_system.nut', '管理员插件'],
  ['scripts/vscripts/admin_system', '管理员插件'],
  ['scripts/vscripts/adminmenu.nut', '管理员插件'],
  ['addons/sourcemod/plugins/basecomm.smx', '管理员插件'],
  ['addons/metamod/metaplugins.ini', '管理员插件'],
  ['cfg/sourcemod/sm_basecommands.cfg', '管理员插件'],
  // clientmenu.txt = 脚本类管理菜单的注册文件（Admin Menu 2.0 CN 内部只有这一个文件）
  ['scripts/clientmenu.txt', '管理员插件'],
  // ---- 2026-10-03 新增：非标准布局与构建产物（本批 5 件实测补的）----
  ['vscripts/director_base_addon.nut', '脚本·VScript'],          // 顶层 vscripts/（正常在 scripts/ 下）
  ['cubemap_screenshots/dc3m6_stationup.tga', '打包元文件（cubemap 构建产物）'],
  ['cubemap_screenshots/dc3m5_plantup.pfm', '打包元文件（cubemap 构建产物）'],
  // 回归护栏：通用 VScript 工具库不许被当管理插件（规则只认文件名里的 admin，不认 sm_*）
  ['scripts/vscripts/director_base_addon.nut', '脚本·VScript'],
  ['scripts/vscripts/sm_utilities.nut', '脚本·VScript'],
];

const fails = [];
for (const [p, want] of CASES) {
  const got = classify(p);
  if (got !== want) fails.push({ path: p, normalized: normalizePath(p), want, got });
}

// 归一化本身也单独断言（防止规则“碰巧”通过但归一化坏了）
const NORM = [
  ['left 4 dead 2/left4dead2/media/valve.bik', 'media/valve.bik'],
  ['for_users/error_fix/left 4 dead 2/left4dead2/particles/x.pcf', 'particles/x.pcf'],
  ['for_modders/particles/3p/x.pcf', 'particles/3p/x.pcf'],
  [' /l4d2_background01.bik', 'l4d2_background01.bik'],
  ['materials/models/props_c17/metalladder001.vmt', 'materials/models/props_c17/metalladder001.vmt'],
  ['models/w_models/weapons/w_rifle_m16a2.mdl', 'models/w_models/weapons/w_rifle_m16a2.mdl'],
];
const normFails = [];
for (const [raw, want] of NORM) {
  const got = normalizePath(raw);
  if (got !== want) normFails.push({ raw, want, got });
}

// 标签唯一性（RULES 层面：同一标签出现在多条规则里是允许的，但必须是有意为之）
const byLabel = {};
for (const [re, lab] of RULES) (byLabel[lab] = byLabel[lab] || []).push(String(re));
const multi = Object.entries(byLabel).filter(([, v]) => v.length > 1);

console.log(JSON.stringify({
  rules: RULES.length,
  cases: CASES.length,
  passed: CASES.length - fails.length,
  failed: fails,
  normalizeCases: NORM.length,
  normalizePassed: NORM.length - normFails.length,
  normalizeFailed: normFails,
  multiRuleLabels: multi.map(([k, v]) => k + ' × ' + v.length),
}, null, 1));
