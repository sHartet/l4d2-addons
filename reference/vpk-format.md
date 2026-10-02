# VPK 格式要点

L4D2 的 addon 就是 Source 引擎的 VPK。要「解出 mod 到底替换了什么」，只能自己解析它。
下面两个坑是**必踩**的，踩过一次就别再踩。

## 头部

```
sig(4) = 0x55AA1234
version(4)
treeSize(4)
-- 仅 version == 2 时再跟 4 个 uint32：
fileDataSectionSize / archiveMD5SectionSize / otherMD5SectionSize / signatureSectionSize
```

⚠️ **坑 1：VPK v1 也有 `treeSize` 字段**，不是只有 v2 有。
头部固定是 `sig + version + treeSize`。v1 漏读 treeSize 会在第一条就失步，报 `bad terminator` 或乱码扩展名。

数据段起点：v1 = `12 + treeSize`，v2 = `28 + treeSize`。

## 目录树

三层嵌套，**不是扁平列表**：

```
ext { path { filename + 18字节 entry } "" } ""
```

- 每层用**空串作结束哨兵**
- 根目录写成**单个空格 `" "`**（读到它要归一化回空串）
- 18 字节 entry = `crc(4) preloadBytes(2) archiveIndex(2) entryOffset(4) entryLength(4) terminator(2)=0xFFFF`
- entry 之后紧跟 `preloadBytes` 字节的预载数据，必须跳过

⚠️ **坑 2：当成扁平列表解析会在第二条就错位。**

## 自检

解析完 **`consumed == treeSize`** 才算对。实测：
`光海夜岚瞄准镜.vpk` 359/359、`材质` 5086/5086、`牢米音频库` 7403/7403。

## entryOffset 有两种写法

- 按规范是「**相对数据段起点**」：真实偏移 = `dataStart + entryOffset`
- 但有工具写成「**文件绝对偏移**」

**不要写死一种。** 提取文本类条目（`addoninfo.txt` 等）时的判定法：
读出来按两种 base 各取前 200 字节，哪边可打印字符比例 ≥95% 就用哪边。

若还是定不了，直接在原始字节里搜特征串（如 `"AddonInfo"`）拿真实偏移，减去 tree 里记的 `entryOffset` 即得 base。

## 拆分式 VPK

有些 addon 是 `<name>_dir.vpk` + `<name>_000.vpk` 的拆分布局，**目录树只在 `_dir.vpk` 里**。
扫 addons 时要额外纳入这种 `_dir.vpk`（通常位于子目录，如 `addons\cfhd\pak01_dir.vpk`），
但要在清单里标明来源，别和顶层 VPK 混为一谈。

## 识别未知 mod：读它自带的 `addoninfo.txt`

工坊页失效（API `result=9`）或手工件没有标签时的**唯一权威依据**。所有正规打包的 addon 都在根目录放它：

```
"AddonInfo"
{
	addonSteamAppID		550
	addontitle		"..."
	addonauthor		"..."
}
```

用 `vpkdump.ps1 -Path <vpk> -Match '^addoninfo\.txt$' -MaxChars 3000` 提取（它会自动判 base，并在末尾附全部条目路径）。

## 顺带：`.mdl` 必须三件齐全

任何 `.mdl` 都要同时提供同名 `.vvd` / `.dx90.vtx`（有的还要 `.phy` / `.ani`）。
只换 `.mdl` 不换贴图会出现白模；`.vmt` 是指向 `.vtf` 的材质脚本。
判断「一个 mod 是不是真的替换了某个物件」时，**有没有该物件的 `.mdl`** 是关键证据。
