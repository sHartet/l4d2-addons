param(
  [string]$Batch = '',
  [switch]$Apply
)
$ErrorActionPreference = 'Stop'

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


$AD = $L4D2_ADDONS_DIR
$WS = Join-Path $AD 'workshop'

function MC([int[]]$cp) { -join ($cp | ForEach-Object { [char]$_ }) }

# full-width replacements for  \ / : * ? " < > |
$illegal = @{
  '\' = MC @(0xFF3C); '/' = MC @(0xFF0F); ':' = MC @(0xFF1A); '*' = MC @(0xFF0A)
  '?' = MC @(0xFF1F); '"' = MC @(0xFF02); '<' = MC @(0xFF1C); '>' = MC @(0xFF1E)
  '|' = MC @(0xFF20)
}
function SanitizeName([string]$s) {
  foreach ($k in $illegal.Keys) { $s = $s.Replace($k, $illegal[$k]) }
  $s = $s -replace "[`r`n`t]", ''
  $s = $s.Trim()
  $s = $s.TrimEnd('.')
  if ($s.Length -gt 120) { $s = $s.Substring(0, 120) }
  return $s
}

$items = Get-Content -LiteralPath $Batch -Encoding UTF8 -Raw | ConvertFrom-Json

$log = @()
$okCount = 0; $skipCount = 0; $manualCount = 0

foreach ($it in $items) {
  $id   = [string]$it.id
  $cat  = [string]$it.cat
  $tgt  = [string]$it.target
  $ttl  = [string]$it.title
  $baseOverride = [string]$it.base
  $srcOverride  = [string]$it.src

  # source file in workshop\ : either explicit 'src' (manual drop-in) or "<id>.vpk"
  $srcName = if ($srcOverride -ne '') { $srcOverride } else { $id + '.vpk' }
  $stem    = [System.IO.Path]::GetFileNameWithoutExtension($srcName)

  # target base name: explicit 'base' wins, otherwise <cat>[-<target>]-<title>
  if ($baseOverride -ne '') {
    $base = SanitizeName $baseOverride
  } else {
    $b = $cat
    if ($tgt -ne '') { $b = $b + '-' + $tgt }
    $base = $b + '-' + (SanitizeName $ttl)
  }

  $srcVpk = Join-Path $WS $srcName
  $srcJpg = Join-Path $WS ($stem + '.jpg')
  $dstVpk = Join-Path $AD ($base + '.vpk')
  $dstJpg = Join-Path $AD ($base + '.jpg')
  $dstUrl = Join-Path $AD ($base + '.url')

  $isManual = ($id -eq '')
  $rec = [ordered]@{
    Id = $id; Cat = $cat; Target = $tgt; Title = $ttl; Src = $srcName
    NewBase = $base; Manual = $isManual
    HasVpk = (Test-Path -LiteralPath $srcVpk)
    HasJpg = (Test-Path -LiteralPath $srcJpg)
    Url = if ($isManual) { 'SKIP (manual, no workshop id)' } else { 'create' }
    Status = ''
  }

  if (-not $rec.HasVpk) {
    $rec.Status = 'SKIP: source vpk missing'
    $skipCount++
    $log += [pscustomobject]$rec
    continue
  }

  $clash = @()
  foreach ($p in @($dstVpk, $dstJpg, $dstUrl)) { if (Test-Path -LiteralPath $p) { $clash += $p } }
  if ($clash.Count -gt 0) {
    $rec.Status = 'SKIP: target occupied -> ' + ($clash -join ' ; ')
    $skipCount++
    $log += [pscustomobject]$rec
    continue
  }

  if ($Apply) {
    [System.IO.File]::Move([string]$srcVpk, [string]$dstVpk)
    if ($rec.HasJpg) { [System.IO.File]::Move([string]$srcJpg, [string]$dstJpg) }

    if (-not $isManual) {
      $urlText = "[InternetShortcut]`r`nURL=https://steamcommunity.com/sharedfiles/filedetails/?id=$id`r`nIconIndex=0`r`n"
      [System.IO.File]::WriteAllText([string]$dstUrl, $urlText, (New-Object System.Text.UTF8Encoding($false)))
    } else {
      $manualCount++
    }
    $rec.Status = 'MOVED'
    $okCount++
  } else {
    $rec.Status = 'DRYRUN ok'
    $okCount++
    if ($isManual) { $manualCount++ }
  }
  $log += [pscustomobject]$rec
}

$lines = @()
$lines += ("Batch: {0}   Apply: {1}   Time: {2}" -f $Batch, [bool]$Apply, (Get-Date -Format 'yyyy.M.d HH:mm:ss'))
$lines += ("OK={0}  SKIP={1}  MANUAL(no url)={2}  TOTAL={3}" -f $okCount, $skipCount, $manualCount, $items.Count)
$lines += ''
foreach ($r in $log) {
  $lines += ("[{0}] id='{1}'" -f $r.Status, $r.Id)
  $lines += ("     src    = {0}   (jpg={1})" -f $r.Src, $r.HasJpg)
  $lines += ("     cat={0}  target={1}" -f $r.Cat, $r.Target)
  $lines += ("     title  = {0}" -f $r.Title)
  $lines += ("     new    = {0}.vpk" -f $r.NewBase)
  $lines += ("     url    = {0}" -f $r.Url)
  $lines += ''
}
$outFile = Join-Path ([System.IO.Path]::GetDirectoryName($Batch)) ([System.IO.Path]::GetFileNameWithoutExtension($Batch) + '_log.txt')
$lines -join "`r`n" | Set-Content -LiteralPath $outFile -Encoding UTF8

Write-Output ("DONE apply={0} ok={1} skip={2} manual={3} -> {4}" -f [bool]$Apply, $okCount, $skipCount, $manualCount, $outFile)
