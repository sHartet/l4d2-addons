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
// 扫描 addons 目录，解析每个 VPK 实际覆盖的游戏资源，并归类到「替换对象」
import fs from 'node:fs';
import path from 'node:path';

// L4D2_SCAN_DIR 可指向别的目录（例如 workshop 暂存）；默认扫 addons 顶层
const A = process.env.L4D2_SCAN_DIR || L4D2_ADDONS;
const OUT = process.env.L4D2_SCAN_OUT || _L4D2_path.join(L4D2_WORK, "addons_scan.json");

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
      r = cstr(buf, p); p = r.next; const dir = r.s; if (!dir) break;
      while (true) {
        r = cstr(buf, p); p = r.next; const name = r.s; if (!name) break;
        const preload = buf.readUInt16LE(p + 4);
        const t = p + 16; p = t + 2;
        if (preload > 0) p += preload;
        list.push((dir ? dir + '/' : '') + name + '.' + ext);
      }
    }
  }
  return list;
};

// ---- 路径归一化 ----
// 部分打包者把外层目录也打进了 VPK，例如：
//   left 4 dead 2/left4dead2/media/valve.bik
//   for_users/error_fix/left 4 dead 2/left4dead2/particles/urik/x.pcf
//   for_modders/particles/3p/weapon_smg.pcf
// 这些路径用 `^` 锚定的规则一条都匹配不到，会整体掉进「未归类」。
// 统一剥到「游戏内真实相对路径」再分类。
const GAME_ROOTS = ['models', 'materials', 'sound', 'particles', 'scripts',
  'resource', 'maps', 'missions', 'modes', 'media', 'scenes', 'expressions', 'cfg'];
const WRAPPER_DIRS = /^(for_users|for_modders|error_fix|extras?|optional)\//i;

const normalizePath = (raw) => {
  let s = String(raw).replace(/^\s+/, '').replace(/^\/+/, '');
  // 先剥掉打包者的分类外层目录（可能叠多层）
  let guard = 0;
  while (WRAPPER_DIRS.test(s) && guard++ < 8) s = s.replace(WRAPPER_DIRS, '');
  // 再定位最早的「游戏根目录」并从这里截断
  let best = -1;
  for (const r of GAME_ROOTS) {
    if (s.startsWith(r + '/')) { best = 0; break; }
    const i = s.indexOf('/' + r + '/');
    if (i >= 0 && (best < 0 || i + 1 < best)) best = i + 1;
  }
  return best > 0 ? s.slice(best) : s;
};

// ---- 路径 -> 替换对象 标签 ----
const RULES = [
  // 骨架 / 手势 / 轻量模型（必须先于角色主模型匹配）
  [/models\/survivors\/anim_gestures/, '生还者手势'],
  [/models\/survivors\/anim_/, '生还者骨架动画'],
  [/models\/survivors\/gestures_/, '生还者手势'],
  // 轻量模型：弗朗西斯与佐伊是**两个不同物件**，必须各给一个标签（缺陷 1）
  // 位置必须在 survivor_biker / survivor_teenangst 主模型规则之前
  [/models\/survivors\/survivor_biker_light/, '弗朗西斯（轻量版）'],
  [/models\/survivors\/survivor_teenangst_light/, '佐伊（轻量版）'],
  // 生还者
  [/models\/survivors\/(survivor_coach|anim_coach|gestures_coach)/, '教练 Coach'],
  [/models\/survivors\/(survivor_mechanic|anim_mechanic|gestures_mechanic)/, '埃利斯 Ellis'],
  [/models\/survivors\/(survivor_gambler|anim_gambler|gestures_gambler)/, '尼克 Nick'],
  [/models\/survivors\/(survivor_producer|anim_producer|gestures_producer)/, '罗谢尔 Rochelle'],
  [/models\/survivors\/(survivor_namvet|anim_namvet|gestures_namvet)/, '比尔 Bill'],
  [/models\/survivors\/(survivor_biker|anim_biker|gestures_biker)/, '弗朗西斯 Francis'],
  [/models\/survivors\/(survivor_manager|anim_manager)/, '路易斯 Louis'],
  [/models\/survivors\/(survivor_teenangst|anim_teenangst|gestures_teenangst)/, '佐伊 Zoey'],
  [/models\/weapons\/arms\/v_arms_coach/, '教练·手臂'],
  [/models\/weapons\/arms\/v_arms_mechanic/, '埃利斯·手臂'],
  [/models\/weapons\/arms\/v_arms_gambler/, '尼克·手臂'],
  [/models\/weapons\/arms\/v_arms_producer/, '罗谢尔·手臂'],
  [/models\/weapons\/arms\/v_arms_bill/, '比尔·手臂'],
  [/models\/weapons\/arms\/v_arms_francis/, '弗朗西斯·手臂'],
  [/models\/weapons\/arms\/v_arms_louis/, '路易斯·手臂'],
  [/models\/weapons\/arms\/v_arms_zoey/, '佐伊·手臂'],
  [/models\/infected\/.*_l4d1/, 'L4D1 版感染者模型'],
  [/models\/v_models\/weapons\/v_claw_/, '感染者第一人称爪'],
  [/models\/weapons\/arms\/v_(charger|jockey|spitter)_arms/, '感染者手臂'],
  // 感染者（含特殊感染者）的骨骼动画模型，对应「界面·特效·材质·其他」表的「感染者骨架动画」行
  [/models\/infected\/anim_/, '动画·感染者骨骼'],
  // 残肢：Boomer 爆开残骸 与 通用血块碎尸 是**两套资源**，分开标签（缺陷 3）
  // 必须排在下面的 呕吐者 / limbs 兜底 之前
  [/models\/infected\/limbs\/exploded_boomer/, '感染者残肢·爆炸残肢'],
  [/models\/infected\/limbs\/exploded_boomette/, '感染者残肢·爆炸残肢'],
  // 特殊感染者
  [/models\/infected\/boomette/, '女呕吐者 Boomette'],
  [/models\/infected\/hulk_dlc3/, '坦克（Cold Stream 版）'],
  [/models\/infected\/boomer/, '呕吐者 Boomer'],
  [/models\/infected\/smoker/, '烟鬼 Smoker'],
  [/models\/infected\/hunter/, '猎人 Hunter'],
  [/models\/infected\/hulk/, '坦克 Tank'],
  [/models\/infected\/witch_bride/, '新娘女巫 Witch Bride'],
  [/models\/infected\/witch/, '女巫 Witch'],
  [/models\/infected\/charger/, '冲撞者 Charger'],
  [/models\/infected\/jockey/, '骑师 Jockey'],
  [/models\/infected\/spitter/, '喷酸者 Spitter'],
  [/models\/infected\/gibs\/gibs/, '感染者残肢·血块与碎尸'],
  [/models\/infected\/limbs\//, '感染者残肢·血块与碎尸'],
  // 普通感染者 —— 一行表格 = 一个标签，一一对应（缺陷 3）
  // 顺序要求：更具体的在前；female01_suit 必须在 female01 之前
  [/models\/infected\/common_male_ceda/, '普通感染者·CEDA 工作人员'],
  [/models\/infected\/common_male_clown/, '普通感染者·小丑'],
  [/models\/infected\/common_male_mud/, '普通感染者·泥人'],
  [/models\/infected\/common_male_riot/, '普通感染者·防暴警察'],
  [/models\/infected\/common_male_roadcrew/, '普通感染者·筑路工'],
  [/models\/infected\/common_male_fallen_survivor/, '普通感染者·堕落生还者'],
  [/models\/infected\/common_male_jimmy/, '普通感染者·吉米·吉布斯二世'],
  [/models\/infected\/common_male_baggagehandler/, '普通感染者·男性行李搬运工'],
  [/models\/infected\/common_male_pilot/, '普通感染者·飞行员'],
  [/models\/infected\/common_male_parachutist/, '普通感染者·伞兵'],
  [/models\/infected\/common_male_suit/, '普通感染者·男性西装'],
  [/models\/infected\/common_male_formal/, '普通感染者·男性正式礼服'],
  [/models\/infected\/common_male_biker/, '普通感染者·男性摩托车手'],
  [/models\/infected\/common_male_polo_jeans/, '普通感染者·男性花花公子'],
  [/models\/infected\/common_male_rural01/, '普通感染者·男性乡村'],
  [/models\/infected\/common_male_dressshirt_jeans/, '普通感染者·男性衬衫牛仔裤'],
  [/models\/infected\/common_male_tshirt_cargos/, '普通感染者·男性T恤工装裤'],
  [/models\/infected\/common_male_tanktop_jeans/, '普通感染者·男性背心牛仔裤'],
  [/models\/infected\/common_male_tanktop_overalls/, '普通感染者·男性背心背带裤'],
  [/models\/infected\/common_male01/, '普通感染者·男性基础 01'],
  [/models\/infected\/common_male02/, '普通感染者·男性基础 02'],
  [/models\/infected\/common_female01_suit/, '普通感染者·女性套装'],
  [/models\/infected\/common_female_baggagehandler/, '普通感染者·女性行李员'],
  [/models\/infected\/common_female_nurse/, '普通感染者·女性护士'],
  [/models\/infected\/common_female_rural/, '普通感染者·女性农村'],
  [/models\/infected\/common_female_formal/, '普通感染者·女性正式礼服'],
  [/models\/infected\/common_female_tanktop_jeans/, '普通感染者·女性背心牛仔裤'],
  [/models\/infected\/common_female_tshirt_skirt/, '普通感染者·女性T恤短裙'],
  [/models\/infected\/common_female01/, '普通感染者·女性基础'],
  [/models\/infected\/common_police/, '普通感染者·警察'],
  [/models\/infected\/common_military/, '普通感染者·军人'],
  [/models\/infected\/common_surgeon/, '普通感染者·外科医生'],
  [/models\/infected\/common_patient/, '普通感染者·病人'],
  [/models\/infected\/common_worker/, '普通感染者·工人'],
  [/models\/infected\/common_tsaagent/, '普通感染者·TSA 安检员'],
  [/models\/infected\/common_fem_infected_w_/, '普通感染者·女性残肢模型'],
  [/models\/infected\/common_infected_w_/, '普通感染者·普通感染者残肢模型'],
  [/models\/infected\/common_(morph_test|shadertest|test)/, '普通感染者·开发测试模型'],
  // 残留兜底：标签名自带「需补行」，一旦命中就会出现在 MOD 清单里提醒补表格行
  [/models\/infected\/common_/, '普通感染者·⚠未归类模型（需补表格行）'],
  // 主武器（长名优先）
  [/w_pumpshotgun_a|v_pumpshotgun/, '武器·泵动式霰弹枪'],
  [/w_shotgun\.|v_shotgun_chrome/, '武器·镀铬霰弹枪'],
  [/w_smg_uzi|v_smg\.mdl/, '武器·冲锋枪（乌兹）'],
  [/w_smg_a\.|v_silenced_smg/, '武器·消音冲锋枪'],
  [/w_autoshot_m4super|v_autoshotgun/, '武器·战术霰弹枪'],
  [/w_shotgun_spas|v_shotgun_spas/, '武器·战斗霰弹枪'],
  [/w_sniper_mini14|v_huntingrifle/, '武器·猎枪'],
  [/w_sniper_military|v_sniper_military/, '武器·狙击步枪'],
  [/w_rifle_m16a2|v_rifle\.mdl/, '武器·M-16 突击步枪'],
  [/w_desert_rifle|v_desert_rifle/, '武器·战斗步枪'],
  [/w_rifle_ak47|v_rifle_ak47/, '武器·AK-47 突击步枪'],
  [/w_grenade_launcher|v_grenade_launcher/, '武器·榴弹发射器'],
  [/w_m60|v_m60/, '武器·M60 机枪'],
  [/w_smg_mp5|v_smg_mp5/, '武器·MP5 冲锋枪'],
  [/w_rifle_sg552|v_rif_sg552/, '武器·SG552 突击步枪'],
  [/w_sniper_scout|v_snip_scout/, '武器·Scout 狙击枪'],
  [/w_sniper_awp|v_snip_awp/, '武器·AWP 狙击枪'],
  // 注：models/w_models/weapons/w_rifle_b.mdl 是游戏内的**孤立模型**——
  // 全部 scripts/weapon_*.txt 都没有引用它，换它不会改变任何一把枪的外观。
  // 因此这里**故意不建规则**，避免把它误算到 M-16 名下（同类误判见缺陷 1）。
  // 副武器
  [/w_pistol_a_dual|v_dual_pistola/, '武器·双持手枪'],
  [/w_pistol_b|v_pistola\.mdl/, '武器·格洛克手枪'],
  [/w_pistol_a|v_pistol\.mdl/, '武器·手枪（P220）'],
  [/w_desert_eagle|v_desert_eagle/, '武器·马格南手枪'],
  // 近战
  [/melee\/[vw]_fireaxe/, '武器·消防斧'],
  [/melee\/[vw]_bat\./, '武器·棒球棍'],
  [/melee\/[vw]_cricket_bat/, '武器·板球棒'],
  [/melee\/[vw]_crowbar/, '武器·撬棍'],
  [/melee\/[vw]_frying_pan/, '武器·平底锅'],
  [/melee\/[vw]_golfclub/, '武器·高尔夫球杆'],
  [/melee\/[vw]_electric_guitar/, '武器·电吉他'],
  [/melee\/[vw]_katana/, '武器·武士刀'],
  [/melee\/[vw]_machete/, '武器·砍刀'],
  [/melee\/[vw]_tonfa/, '武器·警棍'],
  [/melee\/[vw]_pitchfork/, '武器·干草叉'],
  [/melee\/[vw]_shovel/, '武器·铁铲'],
  [/melee\/[vw]_chainsaw/, '武器·电锯'],
  [/melee\/[vw]_gnome/, '武器·花园地精'],
  [/melee\/[vw]_riotshield/, '武器·防暴盾'],
  [/melee\/[vw]_didgeridoo/, '武器·迪吉里杜管'],
  // 战斗刀的模型**不在 melee/ 下**（实际在 models/w_models/weapons/ 与 models/v_models/）。
  // 原写法 `melee\/v_knife_t|w_knife_t` 只是因为 `|` 把整条模式切成两半、右半边碰巧命中才有效，
  // 这里按真实路径写全。
  [/w_knife_t\.|v_knife_t\./, '武器·战斗刀'],
  // 投掷物 / 消耗品 / 升级 / 场景道具 —— 物件域规则**统一锚定 `^(models|materials)/`**
  //   ① 只锚 `^models/` 会误伤「只改贴图」的物件 mod（实测：材质-全部梯子 36 条全是 materials/ 贴图）
  //   ② 完全不锚会误吞 sound/ 下的同名目录（实测：/weapons\/50cal/ 抢走了 sound/weapons/50cal/）
  //   ③ `^(models|materials)/` 两头都挡住
  [/^(models|materials)\/.*(w_eq_molotov|v_molotov)/, '道具·燃烧瓶'],
  [/^(models|materials)\/.*(w_eq_pipebomb|v_pipebomb)/, '道具·管状炸弹'],
  [/^(models|materials)\/.*(w_eq_bile_flask|v_bile_flask)/, '道具·胆汁炸弹'],
  [/^(models|materials)\/.*(w_eq_medkit|v_medkit)/, '道具·急救包'],
  [/^(models|materials)\/.*(w_eq_painpills|v_painpills)/, '道具·止痛药'],
  [/^(models|materials)\/.*(w_eq_adrenaline|v_adrenaline)/, '道具·肾上腺素'],
  [/^(models|materials)\/.*(w_eq_defibrillator|v_defibrillator)/, '道具·除颤器'],
  [/^(models|materials)\/.*(w_eq_explosive_ammopack|v_explosive_ammopack)/, '道具·高爆弹药'],
  [/^(models|materials)\/.*(w_eq_incendiary_ammopack|v_incendiary_ammopack)/, '道具·燃烧弹药'],
  [/^(models|materials)\/.*w_laser_sights/, '道具·激光瞄准器'],
  [/^(models|materials)\/.*(w_cola|v_cola)/, '道具·可乐'],
  [/^(models|materials)\/.*props_junk\/gnome/, '道具·花园地精'],
  [/^(models|materials)\/.*props_junk\/gascan/, '道具·汽油桶'],
  [/^(models|materials)\/.*props_junk\/propanecanister/, '道具·丙烷罐'],
  [/^(models|materials)\/.*props_equipment\/oxygentank/, '道具·氧气罐'],
  [/^(models|materials)\/.*props_junk\/explosive_box/, '道具·烟花盒'],
  [/^(models|materials)\/.*oil_?drum/, '道具·爆炸油桶'],
  [/^(models|materials)\/.*w_minigun/, '固定武器·米尼岗机枪'],
  [/^(models|materials)\/.*\/50cal\./, '固定武器·重机枪'],
  [/^(models|materials)\/.*50_cal_broken/, '固定武器·损坏的重机枪'],
  [/^(models|materials)\/.*w_he_grenade/, '场景道具·榴弹弹体'],
  [/^(models|materials)\/.*w_rd_grenade/, '场景道具·火箭弹弹体'],
  [/^(models|materials)\/.*ladder/, '场景物件·梯子'],
  [/^(models|materials)\/.*props_doors\//, '场景物件·门'],
  [/^(models|materials)\/.*props_crates\//, '场景物件·补给箱'],
  [/^(models|materials)\/.*wood_crate/, '场景物件·木箱'],
  // 音效 —— 一条规则 = 「音效路径」表的一行，标签全局唯一（缺陷 3）
  // 顺序：更长/更具体的目录必须排在它的前缀目录之前
  [/^sound\/weapons\/pistol_silver\//, '音效·格洛克 银手枪'],
  [/^sound\/weapons\/dual_pistol\//, '音效·双持手枪'],
  [/^sound\/weapons\/pistol\//, '音效·手枪'],
  [/^sound\/weapons\/magnum\//, '音效·马格南'],
  [/^sound\/weapons\/smg_silenced\//, '音效·消音冲锋枪'],
  [/^sound\/weapons\/smg\//, '音效·冲锋枪'],
  [/^sound\/weapons\/mp5navy\//, '音效·MP5'],
  [/^sound\/weapons\/shotgun_chrome\//, '音效·镀铬霰弹枪'],
  [/^sound\/weapons\/shotgun\//, '音效·泵动霰弹枪'],
  [/^sound\/weapons\/auto_shotgun_spas\//, '音效·战斗霰弹枪'],
  [/^sound\/weapons\/auto_shotgun\//, '音效·战术霰弹枪'],
  [/^sound\/weapons\/rifle_desert\//, '音效·战斗步枪'],
  [/^sound\/weapons\/rifle_ak47\//, '音效·AK-47'],
  [/^sound\/weapons\/rifle\//, '音效·M16 突击步枪'],
  [/^sound\/weapons\/sg552\//, '音效·SG552'],
  [/^sound\/weapons\/hunting_rifle\//, '音效·猎枪'],
  [/^sound\/weapons\/sniper_military\//, '音效·军用狙击枪'],
  [/^sound\/weapons\/scout\//, '音效·Scout'],
  [/^sound\/weapons\/awp\//, '音效·AWP'],
  [/^sound\/weapons\/grenade_launcher\//, '音效·榴弹发射器'],
  [/^sound\/weapons\/hegrenade\//, '音效·手雷弹体'],
  [/^sound\/weapons\/molotov\//, '音效·燃烧瓶'],
  [/^sound\/weapons\/ceda_jar\//, '音效·胆汁炸弹'],
  [/^sound\/weapons\/defibrillator\//, '音效·除颤器'],
  [/^sound\/weapons\/adrenaline\//, '音效·肾上腺素'],
  [/^sound\/weapons\/chainsaw\//, '音效·电锯'],
  [/^sound\/weapons\/axe\//, '音效·消防斧'],
  [/^sound\/weapons\/bat\//, '音效·棒球棍与板球棒'],
  [/^sound\/weapons\/crowbar\//, '音效·撬棍'],
  [/^sound\/weapons\/pan\//, '音效·平底锅'],
  [/^sound\/weapons\/guitar\//, '音效·电吉他'],
  [/^sound\/weapons\/katana\//, '音效·武士刀'],
  [/^sound\/weapons\/machete\//, '音效·砍刀'],
  [/^sound\/weapons\/tonfa\//, '音效·警棍'],
  [/^sound\/weapons\/knife\//, '音效·战斗刀'],
  [/^sound\/weapons\/pitchfork\//, '音效·干草叉'],
  [/^sound\/weapons\/shovel\//, '音效·铁铲'],
  [/^sound\/weapons\/minigun\//, '音效·米尼岗机枪'],
  [/^sound\/weapons\/50cal\//, '音效·.50 重机枪'],
  [/^sound\/weapons\/fx\//, '音效·通用开枪与撞击'],
  [/^sound\/weapons\//, '音效·武器（未列入音效路径表）'],
  [/^sound\/player\/survivor\/voice\/coach\//, '语音·教练'],
  [/^sound\/player\/survivor\/voice\/mechanic\//, '语音·埃利斯'],
  [/^sound\/player\/survivor\/voice\/gambler\//, '语音·尼克'],
  [/^sound\/player\/survivor\/voice\/producer\//, '语音·罗谢尔'],
  [/^sound\/player\/survivor\/voice\/biker\//, '语音·弗朗西斯'],
  [/^sound\/player\/survivor\/voice\/namvet\//, '语音·比尔'],
  [/^sound\/player\/survivor\/voice\/manager\//, '语音·路易斯'],
  [/^sound\/player\/survivor\/voice\/teenangst\//, '语音·佐伊'],
  [/^sound\/player\/survivor\/(heal|hit|splat|swing)\//, '音效·生还者技能音效'],
  [/^sound\/player\/survivor\//, '音效·生还者其它'],
  [/^sound\/player\/boomer\//, '音效·呕吐者'],
  [/^sound\/player\/smoker\//, '音效·烟鬼'],
  [/^sound\/player\/hunter\//, '音效·猎人'],
  [/^sound\/player\/tank\//, '音效·坦克'],
  [/^sound\/player\/charger\//, '音效·冲撞者'],
  [/^sound\/player\/jockey\//, '音效·骑师'],
  [/^sound\/player\/spitter\//, '音效·喷酸者'],
  [/^sound\/player\//, '音效·其它角色音效'],
  [/^sound\/npc\/witch\//, '音效·女巫'],
  [/^sound\/npc\//, '音效·NPC 对白'],
  [/^sound\/music\//, '音效·游戏音乐'],
  [/^sound\/ui\//, '音效·UI 音效'],
  [/^sound\/items\//, '音效·物品拾取'],
  [/^sound\/ambient\//, '音效·环境氛围'],
  [/^sound\/level\//, '音效·关卡音效'],
  [/^sound\/physics\//, '音效·物理撞击'],
  [/^sound\/vehicles\//, '音效·载具'],
  [/^sound\//, '音效·未列入表格'],
  // 主菜单背景 / 启动动画（.bik 视频）
  // 注意：这两类原来一条规则都没有，100% 掉「未归类」。
  // 大厅背景的 .bik 在 VPK 根目录（路径形如 " /l4d2_background01.bik"），
  // 启动动画在 media/ 下（可能带 left4dead2/ 外层，已由 normalizePath 剥掉）。
  [/l4d2_background\d*\.bik$/i, '界面·主菜单背景'],
  [/^media\/.*\.bik$/i, '界面·启动动画'],
  [/\.bik$/i, '界面·其他视频'],
  // 打包元文件：addoninfo / 预览图 / 说明文档 / 作者留的原版参考副本。
  // 不是游戏资源，但也不该算「未归类」。
  [/(^|\/)addoninfo\.txt$/i, '打包元文件'],
  [/(^|\/)addonimage\d*\.(jpg|jpeg|png|bmp|vtf|vmt)$/i, '打包元文件'],
  // 作者自己建的「参考/备份」目录，形如 `scripts (original)`、`scripts (for 3rd person fx)`
  [/^[^\/]*\([^)]*\)/, '打包元文件（作者参考/备份）'],
  [/^[^\/]*readme[^\/]*\.(txt|md|pdf|docx)$/i, '打包元文件'],
  [/^[^\/]*\.(txt|md)$/i, '打包元文件'],            // 根目录下的说明文本（含 [ksep]readme.txt 这类作者前缀）
  [/^[^\/]*\.(jpg|jpeg|png|bmp|gif)$/i, '打包元文件'],  // 根目录下的预览图
  [/\.(xlsx|xls|docx|pdf)$/i, '打包元文件'],
  [/\.vpk$/i, '打包元文件（嵌套 VPK）'],
  // 地图编译时引擎写出的立方体贴图构建产物（.tga 截图 / .pfm 烘焙数据），在 VPK 根目录。
  // 实测来源：The Arrival 带了 42 条，全库其它 mod 都没有。不是游戏资源，但也不该算「未归类」。
  [/^cubemap_screenshots\//, '打包元文件（cubemap 构建产物）'],
  // 界面 / 特效 / 材质 / 其他 —— 同样一行一个唯一标签（缺陷 3）
  [/^materials\/vgui\/healthbar_/, '界面·HUD-生命条'],
  [/^materials\/vgui\/(boomer|hunter|smoker|charger|jockey|spitter|hulk|witch)\./, '界面·HUD-感染者图标'],
  [/^materials\/vgui\/hud\//, '界面·HUD-通用贴图'],
  [/^materials\/vgui\/loadingscreen/, '界面·载入画面'],
  [/^materials\/vgui\/achievements\//, '界面·成就图标'],
  [/^materials\/vgui\/logos\//, '界面·喷漆图案'],
  [/^materials\/vgui\/maps\//, '界面·地图选择'],
  [/^materials\/vgui\/missions\//, '界面·战役选择'],
  [/^materials\/vgui\//, '界面·其他 UI'],
  [/^resource\/.*\.txt$/, '界面·文本与字幕'],
  [/^resource\//, '界面·字体与布局'],
  [/^particles\/blood_fx|^materials\/decals\/blood/, '特效·血液与血浆'],
  [/^particles\/(fire_fx|fire_01l4d|fire_infected_fx|fire_01)/, '特效·火焰'],
  [/^particles\/impact_fx/, '特效·弹着点与火花'],
  [/^particles\/weapon_fx/, '特效·枪口焰'],
  [/^particles\/(boomer|smoker|spitter|charger|hunter|tank|witch)_fx/, '特效·感染体液'],
  [/^particles\/(rain_fx|rain_storm_fx|environmental_fx)/, '特效·雨天与天气'],
  [/^particles\/screen_fx/, '特效·屏幕效果'],
  [/^particles\/(gen_dest_fx|tanker_explosion)/, '特效·爆炸与碎屑'],
  [/^particles\/particles_manifest/, '特效·粒子清单'],
  [/^particles\//, '特效·其它粒子'],
  [/^materials\/decals\//, '材质·贴花'],
  // ---- 手电筒（2026-10-03 新增）----
  // 只认「手电筒本体」：materials/effects/flashlight*（光斑贴图）与含 flashlight 的模型。
  // **故意不认** materials/particle/(beam_)?flashlight* 与 flashlight_glow* ——
  // 那是粒子包/菜单的共享光束与光晕资源，实测有 3 个菜单/粒子 mod 顺带带了它们，
  // 认了就会把那些 mod 误判成手电筒（附带覆盖陷阱）。
  // 顺带：muzzleflash（枪口焰）不含 flashlight 子串，天然不会被这条吞掉。
  [/^materials\/effects\/flashlight/, '手电筒'],
  [/^models\/.*flashlight/, '手电筒'],
  // ---- 管理员插件（2026-10-03 新增）----
  // VScript 管理类入口文件 + SourceMod / MetaMod 交付物。
  // 只认文件名里的 admin，**不认 sm_***（那是通用 VScript 工具库，如 Turret Mod 的 sm_utilities.nut）。
  [/^(addons\/)?(sourcemod|metamod)\//, '管理员插件'],
  [/^cfg\/sourcemod\//, '管理员插件'],
  [/\.smx$/, '管理员插件'],
  [/^scripts\/vscripts\/[^/]*admin/, '管理员插件'],
  // scripts/clientmenu.txt = 客户端菜单定义；脚本类管理菜单靠它注册条目，
  // 文件名里根本没有 admin，只能靠这个路径认（实测全库仅 1 个 mod 带它）。
  // ⚠️ 不能用更宽的 /menu/ —— 那会命中 materials/vgui/ 下的界面贴图。
  [/^scripts\/clientmenu\.txt$/, '管理员插件'],
  [/^materials\/skybox\//, '材质·天空盒'],
  [/^materials\/graffiti\//, '材质·涂鸦'],
  [/^materials\/models\/infected\//, '材质·感染者贴图'],
  [/^materials\/models\/survivors\//, '材质·生还者贴图'],
  [/^materials\/models\/weapons\//, '材质·武器贴图'],
  [/^materials\/models\//, '材质·模型贴图'],
  [/^materials\/sprites\//, '界面·准星与精灵'],
  [/^materials\//, '材质·环境贴图'],
  [/^maps\/.*\.bsp$/, '地图·战役'],
  [/^maps\//, '地图·附属文件（导航与光照）'],
  [/^missions\//, '脚本·战役任务'],
  [/^modes\//, '脚本·游戏模式'],
  [/^scripts\/vscripts\//, '脚本·VScript'],
  // 顶层 vscripts/ —— 非标准布局（正常在 scripts/vscripts/ 下），本体仍是 VScript。
  // 实测来源：Stronger Flashlight [REUPLOAD] 把 nut 放在了 VPK 根目录的 vscripts/ 里。
  [/^vscripts\//, '脚本·VScript'],
  [/^scripts\/melee\//, '脚本·近战数值'],
  [/^scripts\/weapon/, '脚本·武器数值'],
  [/^scripts\//, '脚本·其他'],
  [/^cfg\//, '脚本·配置文件（cfg）'],
  [/^ems\//, '脚本·武器配置（ems）'],
  [/^models\//, '模型·其他'],
];

const classify = (p) => { for (const [re, label] of RULES) if (re.test(p)) return label; return '未归类'; };

// ---- 收集 VPK ----
const files = [];
for (const e of fs.readdirSync(A, { withFileTypes: true })) {
  if (e.isFile() && /\.vpk$/i.test(e.name)) files.push({ name: e.name, full: path.join(A, e.name), src: 'addons 顶层' });
  if (e.isDirectory() && e.name === 'cfhd') {
    const f = path.join(A, e.name, 'pak01_dir.vpk');
    if (fs.existsSync(f)) files.push({ name: e.name + '\\pak01_dir.vpk', full: f, src: 'cfhd 目录包（拆分式 VPK 的索引文件）' });
  }
}
const topLevelVpkCount = files.filter((f) => f.src === 'addons 顶层').length;

const mods = [];
let totalPaths = 0;
let normalizedPaths = 0;
for (const f of files) {
  let sizeMB = 0;
  try { sizeMB = +(fs.statSync(f.full).size / 1048576).toFixed(2); } catch (e) { }
  let list = null;
  try { list = readVpkTree(f.full); } catch (e) { list = null; }
  if (!list) { mods.push({ file: f.name, src: f.src, sizeMB, error: '非标准 VPK 或解析失败', paths: 0, targets: {} }); continue; }
  totalPaths += list.length;
  const targets = {};
  const rawTop = {};
  const prefixes = new Set();
  for (const raw of list) {
    const p = normalizePath(raw);
    if (p !== raw) normalizedPaths++;
    const lab = classify(p);
    targets[lab] = (targets[lab] || 0) + 1;
    const seg = p.split('/');
    const top = seg[0] || '(根)';
    rawTop[top] = (rawTop[top] || 0) + 1;
    if (seg.length >= 3) prefixes.add(seg.slice(0, 3).join('/'));
    if (seg.length >= 2) prefixes.add(seg.slice(0, 2).join('/'));
  }
  mods.push({ file: f.name, src: f.src, sizeMB, paths: list.length, targets, rawTop, prefixes: [...prefixes] });
}

fs.writeFileSync(OUT, JSON.stringify(mods, null, 1), 'utf8');

// 汇总每个替换对象被哪些 mod 覆盖
const byTarget = {};
for (const m of mods) {
  for (const t of Object.keys(m.targets || {})) {
    if (t === '未归类') continue;
    (byTarget[t] = byTarget[t] || []).push(m.file);
  }
}
fs.writeFileSync(process.env.L4D2_SCAN_TARGETS_OUT || _L4D2_path.join(L4D2_WORK, "addons_by_target.json"), JSON.stringify(byTarget, null, 1), 'utf8');

const unclassifiedPaths = mods.reduce((s, m) => s + ((m.targets || {})['未归类'] || 0), 0);
const over50 = mods
  .map((m) => ({ file: m.file, u: (m.targets || {})['未归类'] || 0, p: m.paths || 0 }))
  .filter((x) => x.p > 0 && x.u / x.p > 0.5)
  .sort((a, b) => b.u / b.p - a.u / a.p);

console.log(JSON.stringify({
  addonsTopLevelVpk: topLevelVpkCount,
  extraDirVpk: files.length - topLevelVpkCount,
  scannedTotal: files.length,
  parsed: mods.filter(m => !m.error).length,
  failed: mods.filter(m => m.error).map(m => m.file),
  totalPaths,
  targetCount: Object.keys(byTarget).length,
  normalizedPaths,
  unclassifiedPaths,
  unclassifiedPct: +(unclassifiedPaths / totalPaths * 100).toFixed(2),
  modsOver50pctUnclassified: over50.map(x => `${x.file}  ${x.u}/${x.p} = ${Math.round(x.u / x.p * 100)}%`),
}, null, 1));
