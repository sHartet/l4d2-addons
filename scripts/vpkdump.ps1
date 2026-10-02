param(
  [Parameter(Mandatory=$true)][string]$Path,
  [string]$Match = '\.txt$',
  [int]$MaxChars = 4000,
  [string]$OutName = 'vpk_dump'
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

# VPK entry extractor. Same tree format as vpklist.ps1:
#   header: sig(4) version(4) treeSize(4) [v2: +4 uint32]
#   tree  : ext { path { filename + 18-byte entry } "" } ""
# entryOffset is absolute for archiveIndex 0x7FFF; fall back to dataStart+offset.

$fs = [System.IO.File]::Open($Path,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::ReadWrite)
$br = New-Object System.IO.BinaryReader($fs)
$out = @()
try {
  $sig = $br.ReadUInt32(); $ver = $br.ReadUInt32(); $treeSize = $br.ReadUInt32()
  if ($sig -ne 0x55AA1234) { throw ("bad signature 0x{0:X}" -f $sig) }
  $dataStart = 12
  if ($ver -eq 2) { $null = $br.ReadUInt32(); $null = $br.ReadUInt32(); $null = $br.ReadUInt32(); $null = $br.ReadUInt32(); $dataStart = 28 }
  $tree = $br.ReadBytes([int]$treeSize)
  $dataStart += $treeSize

  $p = 0
  function ReadStr([byte[]]$buf,[ref]$q) {
    $s0=$q.Value
    while ($q.Value -lt $buf.Length -and $buf[$q.Value] -ne 0) { $q.Value++ }
    $s=[System.Text.Encoding]::UTF8.GetString($buf,$s0,$q.Value-$s0)
    if ($q.Value -lt $buf.Length) { $q.Value++ }
    return $s
  }
  $entries = New-Object System.Collections.Generic.List[object]
  while ($p -lt $tree.Length) {
    $ext = ReadStr $tree ([ref]$p); if ($ext -eq '') { break }
    while ($p -lt $tree.Length) {
      $dir = ReadStr $tree ([ref]$p); if ($dir -eq '') { break }
      if ($dir -eq ' ') { $dir = '' }
      while ($p -lt $tree.Length) {
        $nm = ReadStr $tree ([ref]$p); if ($nm -eq '') { break }
        $crc = [BitConverter]::ToUInt32($tree,$p); $p+=4
        $preload = [BitConverter]::ToUInt16($tree,$p); $p+=2
        $archIdx = [BitConverter]::ToUInt16($tree,$p); $p+=2
        $off = [BitConverter]::ToUInt32($tree,$p); $p+=4
        $len = [BitConverter]::ToUInt32($tree,$p); $p+=4
        $term = [BitConverter]::ToUInt16($tree,$p); $p+=2
        if ($term -ne 0xFFFF) { throw ('bad terminator at entry ' + $entries.Count) }
        $pre = @()
        if ($preload -gt 0) { $pre = $tree[$p..($p+$preload-1)]; $p += $preload }
        $full = if ($dir -eq '') { "$nm.$ext" } else { "$dir/$nm.$ext" }
        $entries.Add([pscustomobject]@{ Path=$full; Off=$off; Len=$len; Arch=$archIdx; Pre=$pre })
      }
    }
  }
  $out += ("FILE   : {0}" -f (Split-Path -Leaf $Path))
  $out += ("size   : {0}   version={1}  treeSize={2}  dataStart={3}  entries={4}" -f $fs.Length,$ver,$treeSize,$dataStart,$entries.Count)
  $out += ("MATCH  : {0}" -f $Match)
  $out += ""

  $hit = $entries | Where-Object { $_.Path -match $Match }
  $out += ("matched entries: {0}" -f @($hit).Count)
  $out += ""
  # entryOffset may be relative to the data section (correct per spec) OR absolute -
  # both styles exist in wild addon VPKs. Pick the candidate that reads as text.
  function Score-Bytes([byte[]]$b) {
    if ($b.Length -eq 0) { return 0.0 }
    $ok = 0
    foreach ($x in $b) { if (($x -ge 32 -and $x -lt 127) -or $x -eq 9 -or $x -eq 10 -or $x -eq 13) { $ok++ } }
    return ($ok / $b.Length)
  }
  foreach ($e in $hit) {
    $candRel = $dataStart + $e.Off
    $candAbs = $e.Off
    $pick = $null; $why = ''
    foreach ($c in @(@{base=$candRel;tag='relative(dataStart+off)'}, @{base=$candAbs;tag='absolute(off)'})) {
      if ($c.base + $e.Len -gt $fs.Length) { continue }
      $probe = New-Object byte[] ([Math]::Min(200,[int]$e.Len))
      $fs.Position = $c.base
      $null = $fs.Read($probe,0,$probe.Length)
      $sc = Score-Bytes $probe
      if ($sc -ge 0.95) { $pick = $c; $why = ('printable {0:P0}' -f $sc); break }
      if (-not $pick) { $pick = $c; $why = ('fallback printable {0:P0}' -f $sc) }
    }
    if (-not $pick) { $out += ("---- {0}   SKIPPED (no in-bounds candidate)" -f $e.Path); $out += ""; continue }
    $out += ("---- {0}   off={1} len={2} arch=0x{3:X4}  base={4} ({5})" -f $e.Path,$e.Off,$e.Len,$e.Arch,$pick.tag,$why)
    $bytes = New-Object byte[] $e.Len
    $fs.Position = $pick.base
    $read = $fs.Read($bytes,0,[int]$e.Len)
    $txt = [System.Text.Encoding]::UTF8.GetString($bytes,0,$read)
    $txt = $txt -replace "`r`n","`n"
    if ($txt.Length -gt $MaxChars) { $txt = $txt.Substring(0,$MaxChars) + "`n...[truncated]" }
    $out += $txt
    $out += ""
  }
  $out += ("=== all {0} entry paths ===" -f $entries.Count)
  $out += ($entries | ForEach-Object { $_.Path } | Sort-Object)
} finally { $br.Dispose(); $fs.Dispose() }
if (-not (Test-Path -LiteralPath $L4D2_WORK)) { New-Item -ItemType Directory -Force -Path $L4D2_WORK | Out-Null }
$out -join "`r`n" | Set-Content -LiteralPath (Join-Path $L4D2_WORK "$OutName.txt") -Encoding UTF8
Write-Output ("DONE -> " + (Join-Path $L4D2_WORK "$OutName.txt") -f $OutName)
