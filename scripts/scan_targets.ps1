param(
  [string]$RootDir = '',
  [string]$OutFile = ''
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
if ($env:L4D2_MIRROR) { $L4D2_MIRROR = $env:L4D2_MIRROR } else { $L4D2_MIRROR = L4D2-Get 'mirrorDir' ($L4D2_HOME + '-backup') }
if ((Get-Variable -Name RootDir -ErrorAction SilentlyContinue) -and -not $RootDir) { $RootDir = $L4D2_ADDONS_DIR }
# ==== injection end ====

$AD = $RootDir
$WK = $L4D2_WORK
function MC([int[]]$cp){ -join ($cp | ForEach-Object { [char]$_ }) }
$cats = @(
  (MC @(0x666E,0x901A,0x611F,0x67D3,0x8005)),
  (MC @(0x7279,0x6B8A,0x611F,0x67D3,0x8005)),
  (MC @(0x573A,0x666F,0x9053,0x5177)),
  (MC @(0x6D88,0x8017,0x54C1)),
  (MC @(0x6295,0x63B7,0x7269)),
  (MC @(0x751F,0x8FD8,0x8005)),
  (MC @(0x526F,0x6B66,0x5668)),
  (MC @(0x4E3B,0x6B66,0x5668)),
  (MC @(0x666E,0x611F)),
  (MC @(0x5730,0x56FE)),
  (MC @(0x8FD1,0x6218)),
  (MC @(0x5176,0x5B83)),
  (MC @(0x754C,0x9762)),
  (MC @(0x573A,0x666F)),
  (MC @(0x811A,0x672C)),
  (MC @(0x7279,0x6548)),
  (MC @(0x6A21,0x578B)),
  (MC @(0x6750,0x8D28)),
  (MC @(0x97F3,0x6548)),
  (MC @(0x7279,0x611F))
)
$out = @()

# --- whitelist: full mod names (extension stripped). Only lines that START with <cat>- count. ---
$wlNames = @()
$wlFile = Join-Path $AD ('mod' + (MC @(0x767D,0x540D,0x5355)) + '.txt')
$wlRx = '^(' + ($cats -join '|') + ')-'
if (Test-Path -LiteralPath $wlFile) {
  foreach ($ln in (Get-Content -LiteralPath $wlFile -Encoding UTF8)) {
    $t = $ln.Trim()
    if ($t -match $wlRx) { $wlNames += $t }
  }
}
$out += "=== category prefixes: " + ($cats -join " / ")
$out += "=== whitelist names parsed: $($wlNames.Count) ==="
$out += $wlNames
$out += ""

# --- multi-piece sets: matched by MEMBER, not by group key ---
$setMembers = @{}
$setInfo = @()
$setFile = Join-Path $WK 'set_exempt.json'
if (Test-Path -LiteralPath $setFile) {
  $j = Get-Content -LiteralPath $setFile -Encoding UTF8 -Raw | ConvertFrom-Json
  foreach ($s in $j) {
    $setInfo += ("{0}  ({1} members, declared {2})" -f $s.name, @($s.members).Count, $s.declared)
    foreach ($m in $s.members) { $setMembers[[string]$m] = [string]$s.name }
  }
}
$out += "=== declared multi-piece sets: $($setInfo.Count) ==="
$out += $setInfo
$out += ""

# --- group all vpk by (category, 2nd field) ---
$groups = @{}
$noTarget = @()
foreach ($f in (Get-ChildItem -LiteralPath $AD -Filter '*.vpk' -File)) {
  $name = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
  $catHit = $null
  foreach ($c in $cats) { if ($name.StartsWith($c + '-')) { $catHit = $c; break } }
  if (-not $catHit) { $noTarget += $f.Name; continue }
  $rest = $name.Substring($catHit.Length + 1)
  $i = $rest.IndexOf('-')
  if ($i -le 0) { $noTarget += $f.Name; continue }
  $tgt = $rest.Substring(0, $i)
  $key = $catHit + '-' + $tgt
  if (-not $groups.ContainsKey($key)) { $groups[$key] = @() }
  $groups[$key] += $name
}

$out += "=== groups with >1 member ==="
$conflictCount = 0
$any = $false
foreach ($k in ($groups.Keys | Sort-Object)) {
  if ($groups[$k].Count -le 1) { continue }
  $any = $true
  $outsiders = @($groups[$k] | Where-Object { -not $setMembers.ContainsKey($_) })
  $inSet = ($outsiders.Count -eq 0)
  $allWl = $true
  foreach ($m in $groups[$k]) { if ($wlNames -notcontains $m) { $allWl = $false } }

  $verdict = 'CONFLICT'
  if ($inSet) { $verdict = 'set (all members declared)' }
  elseif ($allWl) { $verdict = 'all members whitelisted' }

  if ($verdict -eq 'CONFLICT') { $conflictCount++ }
  $out += ("[{0}] {1}   members={2}" -f $verdict, $k, $groups[$k].Count)
  foreach ($m in $groups[$k]) {
    $tag = if ($setMembers.ContainsKey($m)) { 'set:' + $setMembers[$m] } elseif ($wlNames -contains $m) { 'whitelisted' } else { '*** OUTSIDER ***' }
    $out += ("        {0}   <{1}>" -f $m, $tag)
  }
}
if (-not $any) { $out += "(none)" }

$out += ""
$out += ("=== CONFLICTS REQUIRING ACTION: {0} ===" -f $conflictCount)
$out += ""
$out += "=== no-target / unparsed ($($noTarget.Count)) ==="
$out += ($noTarget | Sort-Object)
$out += ""
$out += "=== total parsed groups: $($groups.Count) ==="
if ($OutFile -eq '') { $OutFile = Join-Path $WK 'target_conflicts.txt' }
$out -join "`r`n" | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Output ("DONE  conflicts={0}  -> {1}" -f $conflictCount, $OutFile)
