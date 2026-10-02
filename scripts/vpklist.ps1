param(
  [Parameter(Mandatory=$true)][string[]]$Path,
  [int]$TopN = 30,
  [string]$OutName = 'vpk_tree'
)
$ErrorActionPreference='Stop'

# ==== L4D2 skill: path resolution (injected; do not edit) ====
$L4D2_HOME = if ($env:L4D2_HOME) { $env:L4D2_HOME } else { Split-Path -Parent (Split-Path -Parent $PSCommandPath) }
$L4D2_CFG = $null
$L4D2_CFGPATH = Join-Path $L4D2_HOME 'config.json'
if (Test-Path -LiteralPath $L4D2_CFGPATH) { $L4D2_CFG = Get-Content -LiteralPath $L4D2_CFGPATH -Raw -Encoding UTF8 | ConvertFrom-Json }
function L4D2-Get([string]$name, [string]$fallback) {
  if ($L4D2_CFG -and $L4D2_CFG.PSObject.Properties[$name]) { return [string]$L4D2_CFG.PSObject.Properties[$name].Value }
  return $fallback
}
$L4D2_SCRIPTS = L4D2-Get 'scriptsDir' '_work'
$L4D2_WORK = Join-Path $L4D2_HOME $L4D2_SCRIPTS
if ($env:L4D2_ADDONS) { $L4D2_ADDONS_DIR = $env:L4D2_ADDONS } else { $L4D2_ADDONS_DIR = L4D2-Get 'addonsDir' 'D:\Steam\steamapps\common\Left 4 Dead 2\left4dead2\addons' }
$L4D2_BACKUP = L4D2-Get 'backupDir' (Join-Path $L4D2_ADDONS_DIR 'mod\u5907\u4efd')
if ((Get-Variable -Name RootDir -ErrorAction SilentlyContinue) -and -not $RootDir) { $RootDir = $L4D2_ADDONS_DIR }
# ==== injection end ====


# L4D2-era VPK notes (ASCII only on purpose - PS 5.1 mis-decodes UTF-8 .ps1 as GBK):
#   header: sig(4)=0x55AA1234, version(4), treeSize(4); if version==2 then 4 more uint32.
#   The tree is a THREE-LEVEL NESTED structure, not a flat list:
#     ext { path { filename + 18-byte entry } "" } ""
#   An empty string terminates each level. The root path is written as a single space.
function Get-VpkEntries([string]$file) {
  $fs = [System.IO.File]::Open($file, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
  $br = New-Object System.IO.BinaryReader($fs)
  try {
    $sig = $br.ReadUInt32()
    if ($sig -ne 0x55AA1234) { return @{ Error = ("bad signature 0x{0:X}" -f $sig); Entries = @(); Version = $null } }
    $ver = $br.ReadUInt32()
    if ($ver -ne 1 -and $ver -ne 2) { return @{ Error = ("unsupported version $ver"); Entries = @(); Version = $ver } }
    $treeSize = $br.ReadUInt32()
    if ($ver -eq 2) { $null = $br.ReadUInt32(); $null = $br.ReadUInt32(); $null = $br.ReadUInt32(); $null = $br.ReadUInt32() }
    if ($treeSize -le 0 -or $treeSize -gt $fs.Length) { return @{ Error = ("bad treeSize $treeSize"); Entries = @(); Version = $ver } }
    $tree = $br.ReadBytes([int]$treeSize)

    $p = 0
    function ReadStr([byte[]]$buf, [ref]$q) {
      $start = $q.Value
      while ($q.Value -lt $buf.Length -and $buf[$q.Value] -ne 0) { $q.Value++ }
      $s = [System.Text.Encoding]::UTF8.GetString($buf, $start, $q.Value - $start)
      if ($q.Value -lt $buf.Length) { $q.Value++ }
      return $s
    }

    $list = New-Object System.Collections.Generic.List[string]
    $err = $null
    while ($p -lt $tree.Length) {
      $ext = ReadStr $tree ([ref]$p)
      if ($ext -eq '') { break }
      while ($p -lt $tree.Length) {
        $dir = ReadStr $tree ([ref]$p)
        if ($dir -eq '') { break }
        if ($dir -eq ' ') { $dir = '' }
        while ($p -lt $tree.Length) {
          $nm = ReadStr $tree ([ref]$p)
          if ($nm -eq '') { break }
          if ($p + 18 -gt $tree.Length) { $err = 'truncated tree'; break }
          $null = [BitConverter]::ToUInt32($tree,$p); $p += 4
          $preload = [BitConverter]::ToUInt16($tree,$p); $p += 2
          $null = [BitConverter]::ToUInt16($tree,$p); $p += 2
          $null = [BitConverter]::ToUInt32($tree,$p); $p += 4
          $null = [BitConverter]::ToUInt32($tree,$p); $p += 4
          $term = [BitConverter]::ToUInt16($tree,$p); $p += 2
          if ($term -ne 0xFFFF) { $err = ('bad terminator at entry ' + $list.Count); break }
          if ($preload -gt 0) { $p += $preload }
          if ($dir -eq '') { $list.Add("$nm.$ext") } else { $list.Add("$dir/$nm.$ext") }
        }
        if ($err) { break }
      }
      if ($err) { break }
    }
    return @{ Error = $err; Version = $ver; TreeSize = $treeSize; Consumed = $p; Entries = $list }
  } finally { $br.Dispose(); $fs.Dispose() }
}

$out = @()
foreach ($p in $Path) {
  $out += ("=== {0} ===" -f (Split-Path -Leaf $p))
  if (-not (Test-Path -LiteralPath $p)) { $out += "(missing)"; $out += ""; continue }
  $r = Get-VpkEntries $p
  $e = @($r.Entries)
  $out += ("version={0}  treeSize={1}  consumed={2}  entries={3}" -f $r.Version, $r.TreeSize, $r.Consumed, $e.Count)
  if ($r.Error) { $out += ("PARSE NOTE: " + $r.Error) }

  $out += "--- top-level dirs (by entry count) ---"
  $tops = @{}
  foreach ($x in $e) {
    $seg = ($x -split '/')[0]
    if ($seg -eq $x) { $seg = '(root)' }
    if ($tops.ContainsKey($seg)) { $tops[$seg]++ } else { $tops[$seg] = 1 }
  }
  $out += ($tops.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "{0,7}  {1}" -f $_.Value, $_.Key })

  $out += "--- extensions ---"
  $exts = @{}
  foreach ($x in $e) { $ex = ($x -split '\.')[-1]; if ($exts.ContainsKey($ex)) { $exts[$ex]++ } else { $exts[$ex] = 1 } }
  $out += ($exts.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "{0,7}  {1}" -f $_.Value, $_.Key })

  $out += "--- paths under models/ (first 25) ---"
  $sel = $e | Where-Object { $_ -match '^models/' } | Select-Object -First 25
  if ($sel) { $out += $sel } else { $out += "(none)" }

  $out += "--- sample: weapon/infected/hud/scout/sound/scripts ---"
  $sel2 = $e | Where-Object { $_ -match 'weapon|infected|charger|scout|vgui|scripts/|sound/|hud' } | Select-Object -First $TopN
  if ($sel2) { $out += $sel2 } else { $out += "(none)" }
  $out += ""
}
if (-not (Test-Path -LiteralPath $L4D2_WORK)) { New-Item -ItemType Directory -Force -Path $L4D2_WORK | Out-Null }
$out -join "`r`n" | Set-Content -LiteralPath (Join-Path $L4D2_WORK "$OutName.txt") -Encoding UTF8
Write-Output ("DONE -> " + (Join-Path $L4D2_WORK "$OutName.txt") -f $OutName)
