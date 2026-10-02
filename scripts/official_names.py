# -*- coding: utf-8 -*-
"""L4D2 游戏内官方英文名字符串
取自本机 resource/left4dead2_english.txt 与 left4dead2_schinese.txt 的 [english] 段。
键 = 表内中文名；值 = (游戏内英文名, 本地化 Token)
"""

NA = ("—（游戏内不显示名称）", "—")

# L4D_Instructor_explain_* ：游戏内拾取提示用的名字
INSTR = "L4D_Instructor_explain_"
INSTR2 = "L4D2_Instructor_explain_"
MELEE = "L4D_Melee_"
CLS = "L4D_class_"

SURVIVORS = {
    "教练": ("Coach", "角色专有名词（全语言一致）"),
    "埃利斯": ("Ellis", "角色专有名词（全语言一致）"),
    "尼克": ("Nick", "角色专有名词（全语言一致）"),
    "罗谢尔": ("Rochelle", "角色专有名词（全语言一致）"),
    "比尔": ("Bill", "角色专有名词（全语言一致）"),
    "弗朗西斯": ("Francis", "角色专有名词（全语言一致）"),
    "路易斯": ("Louis", "角色专有名词（全语言一致）"),
    "佐伊": ("Zoey", "角色专有名词（全语言一致）"),
    "弗朗西斯（轻量版）": ("Francis", "角色专有名词（全语言一致）"),
    "佐伊（轻量版）": ("Zoey", "角色专有名词（全语言一致）"),
    "生还者骨架动画": NA, "生还者手势": NA, "生还者通用音效": NA,
    "生还者语音": NA, "HUD 头像": NA,
}

SPECIAL = {
    "呕吐者": ("Boomer", CLS + "boomer_name"),
    "女呕吐者": ("Boomer", CLS + "boomer_name" + "（女性变体，名称相同）"),
    "烟鬼": ("Smoker", CLS + "smoker_name"),
    "猎人": ("Hunter", CLS + "hunter_name"),
    "坦克（巨兽）": ("Tank", CLS + "tank_name"),
    "坦克（Cold Stream 版）": ("Tank", CLS + "tank_name"),
    "女巫": ("Witch", CLS + "witch_name"),
    "新娘女巫": ("Witch", CLS + "witch_name" + "（The Passing 皮肤，名称相同）"),
    "冲撞者": ("Charger", CLS + "charger_name"),
    "骑师": ("Jockey", CLS + "jockey_name"),
    "喷酸者": ("Spitter", CLS + "spitter_name"),
    "L4D1 版感染者模型": NA,
    "感染者第一人称爪（第三人称视角模式）": NA,
    "感染者手臂": NA,
    "爆炸残肢": NA,
}

_COMMON = ("Common Infected", "L4D_SurvivalScoreboard_Common")
COMMON = {k: _COMMON for k in [
    "普通男性感染者（基础）", "普通男性感染者 2", "普通女性感染者（基础）",
    "女性感染者（套装）", "女性感染者（农村）", "女性感染者（护士）", "女性感染者（行李员）",
    "女性感染者（背心牛仔裤）", "女性感染者（T恤短裙）", "女性感染者（正式礼服）",
    "男性（西装）", "男性（T恤工装裤）", "男性（背心牛仔裤）", "男性（背心背带裤）",
    "男性（衬衫牛仔裤）", "男性（正式礼服）", "男性（摩托车手）", "男性（花花公子）",
    "男性（乡村）", "男性（行李搬运工）", "伞兵", "飞行员", "警察", "军人",
    "外科医生", "病人", "工人", "TSA 安检员", "筑路工",
]}
COMMON.update({
    "CEDA 工作人员": ("CEDA Agent", "L4D_Gender_CEDA"),
    "小丑": ("Clown", "L4D_Gender_Clown"),
    "泥人": ("Mudmen", "ACH_KILL_SUBMERGED_MUDMEN_DESC"),
    "防暴警察": ("Riot Officer", "L4D_Gender_Riot_Control"),
    "堕落生还者": ("Fallen Survivor", "L4D_Gender_Fallen"),
    "吉米·吉布斯二世": ("Jimmy Gibbs Jr.", "角色专有名词（成就/字幕中使用）"),
    "女性感染者残肢模型": NA, "普通感染者残肢模型": NA, "血块与碎尸": NA,
})

PRIMARY = {
    "泵动式霰弹枪": ("Pump Shotgun", INSTR + "pumpshotgun / L4D_Weapon_PumpShotgun"),
    "镀铬霰弹枪": ("Chrome Shotgun", INSTR + "shotgun_chrome"),
    "冲锋枪（乌兹）": ("Submachine Gun", INSTR + "smg / L4D_Weapon_SMG"),
    "消音冲锋枪": ("Silenced Submachine Gun", INSTR + "smg_silenced"),
    "战术霰弹枪": ("Tactical Shotgun", INSTR + "autoshotgun"),
    "战斗霰弹枪": ("Combat Shotgun", INSTR + "shotgun_spas"),
    "猎枪": ("Hunting Rifle", INSTR + "hunting_rifle / L4D_Weapon_HuntingRifle"),
    "狙击步枪": ("Sniper Rifle", INSTR + "sniper_military"),
    "M-16 突击步枪": ("M-16 Assault Rifle", INSTR + "rifle"),
    "战斗步枪": ("Combat Rifle", INSTR + "rifle_desert（备用说法 Desert Combat Rifle）"),
    "AK-47 突击步枪": ("AK-47", INSTR + "rifle_ak47（备用说法 Soviet Rifle）"),
    "榴弹发射器": ("Grenade Launcher", INSTR + "grenade_launcher"),
    "M60 机枪": ("—（本机未本地化）", "L4D_Weapon_M60 ← 本机未定义，游戏内会显示 #L4D_Weapon_M60"),
    "MP5 冲锋枪": ("—（本机未本地化）", "L4D_Weapon_MP5 ← 本机未定义"),
    "SG552 突击步枪": ("Assault Rifle", "L4D_Weapon_AssaultRifle（与 M16 共用同一 token）"),
    "Scout 狙击枪": ("—（本机未本地化）", "L4D_Weapon_Sniper_Scout ← 本机未定义"),
    "AWP 狙击枪": ("—（本机未本地化）", "L4D_Weapon_Sniper_AWP ← 本机未定义"),
}

SIDEARMS = {
    "手枪（P220）": ("Pistol", INSTR + "pistol / L4D_Weapon_Pistol"),
    "格洛克手枪": ("Pistol", INSTR + "pistol（与 P220 共用同一武器实体，仅模型为 Glock）"),
    "双持手枪": ("Second Pistol", INSTR + "2nd_pistol"),
    "马格南手枪": ("Magnum Pistol", INSTR2 + "magnum_pistol（备用说法 Desert Cobra Pistol）"),
}

MELEE_NAMES = {
    "消防斧": ("Fireaxe", MELEE + "FireAxe"),
    "棒球棍": ("Baseball Bat", MELEE + "Baseball_Bat"),
    "板球棒": ("Cricket Bat", MELEE + "Cricket_Bat"),
    "撬棍": ("Crowbar", MELEE + "Crowbar"),
    "平底锅": ("Frying Pan", MELEE + "Frying_Pan"),
    "高尔夫球杆": ("—（本机未本地化）", "scripts/melee/golfclub.txt（无 L4D_Melee_ 条目）"),
    "电吉他": ("Electric Guitar", MELEE + "Electric_Guitar"),
    "武士刀": ("Katana", MELEE + "Katana"),
    "砍刀": ("Machete", MELEE + "Machete"),
    "警棍": ("Tonfa", MELEE + "Tonfa"),
    "干草叉": ("—（本机未本地化）", "scripts/melee/pitchfork.txt（无 L4D_Melee_ 条目）"),
    "铁铲": ("—（本机未本地化）", "scripts/melee/shovel.txt（无 L4D_Melee_ 条目）"),
    "战斗刀": ("—（本机未本地化）", "scripts/melee/knife.txt（无 L4D_Melee_ 条目）"),
    "电锯": ("Chainsaw", INSTR + "chainsaw"),
    "花园地精": ("Gnome Chompski", "ACH_GNOME_RESCUE_DESC（图鉴名 GARDEN GNOME）"),
    "迪吉里杜管": NA,
    "防暴盾": NA,
}

THROWABLES = {
    "燃烧瓶": ("Molotov", INSTR + "molotov / L4D_Weapon_Molotov"),
    "管状炸弹": ("Pipe Bomb", INSTR + "pipebomb / L4D_Weapon_PipeBomb"),
    "胆汁炸弹": ("Boomer Bile", INSTR + "vomitjar"),
}

CONSUMABLES = {
    "急救包": ("First aid", INSTR + "first_aid（HUD token 为 First Aid Kit）"),
    "止痛药": ("Pain Pills", INSTR + "pills / L4D_Weapon_PainPills"),
    "肾上腺素": ("Adrenaline", INSTR + "adrenaline"),
    "除颤器": ("Defibrillator", INSTR + "defibrillator"),
}

UPG = {
    "高爆弹药": ("Explosive Ammo Pack", INSTR + "upgradepack_explosive"),
    "燃烧弹药": ("Incendiary Ammo Pack", INSTR + "upgradepack_incendiary"),
    "激光瞄准器": ("Laser Sight", INSTR2 + "laser_sight_available"),
    "可乐（可乐瓶）": ("Cola", INSTR2 + "gun_shop_item"),
    "花园地精": ("Gnome Chompski", "ACH_GNOME_RESCUE_DESC"),
    "汽油桶": ("Gas Can", INSTR + "c1m4_finale2（\"Find a gas can\"）"),
    "丙烷罐": ("—（本机未本地化）", "scripts/weapon_propanetank.txt printname = propanetank"),
    "氧气罐": ("—（本机未本地化）", "scripts/weapon_oxygentank.txt printname = oxygentank"),
    "烟花盒": ("—（本机未本地化）", "scripts/weapon_fireworkcrate.txt printname = fireworkcrate"),
    "爆炸油桶": NA,
}

FIXED = {
    "米尼岗机枪": ("—（本机未本地化）", "L4D1 实体 prop_minigun，无本地化条目"),
    "重机枪（.50 口径）": ("Heavy Machine Gun", INSTR2 + "use_mounted_gun"),
    "损坏的重机枪": ("Heavy Machine Gun", INSTR2 + "use_mounted_gun"),
    "榴弹（榴弹发射器弹体）": NA,
    "火箭弹弹体": NA,
    "梯子": NA, "门（检查站/地堡等）": NA, "补给箱": NA, "木箱": NA,
}

OFFICIAL = {
    "生还者": SURVIVORS,
    "特殊感染者": SPECIAL,
    "普通感染者": COMMON,
    "主武器": PRIMARY,
    "副武器": SIDEARMS,
    "近战": MELEE_NAMES,
    "投掷物": THROWABLES,
    "消耗品": CONSUMABLES,
    "场景道具": UPG,
    "固定武器·场景": FIXED,
}
