param(
  [Parameter(Mandatory=$true)][string]$Batch,
  [string]$RootDir = '',
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
if ($env:L4D2_MIRROR) { $L4D2_MIRROR = $env:L4D2_MIRROR } else { $L4D2_MIRROR = L4D2-Get 'mirrorDir' ($L4D2_HOME + '-backup') }
if ((Get-Variable -Name RootDir -ErrorAction SilentlyContinue) -and -not $RootDir) { $RootDir = $L4D2_ADDONS_DIR }
# ==== injection end ====

# Renames addon files in place: <old>.vpk / .jpg / .url  ->  <new>.<ext>  (all three if present)
# Batch JSON (UTF-8): [ { "old": "...", "new": "...", "held": false }, ... ]
# ASCII-only script: all Chinese text comes from the JSON, never from literals here.

$log = Get-Content -LiteralPath $Batch -Raw -Encoding UTF8 | ConvertFrom-Json
$exts = @('.vpk', '.jpg', '.url')
$logName = [System.IO.Path]::GetFileNameWithoutExtension($Batch) + '_log.txt'
$logPath = Join-Path (Split-Path -Parent $Batch) $logName

$report = New-Object System.Collections.Generic.List[string]
$ok = 0; $skip = 0; $missing = 0; $held = 0
$done = New-Object System.Collections.Generic.List[object]

foreach ($item in $log) {
  $o = [string]$item.old
  $n = [string]$item.'new'
  if ($item.held) { $held++; $report.Add("HELD`t$o`t->`t$n"); continue }
  if (-not $o -or -not $n -or $o -eq $n) { continue }

  $moved = New-Object System.Collections.Generic.List[string]
  $reasons = New-Object System.Collections.Generic.List[string]
  $anySrc = $false
  foreach ($e in $exts) {
    $src = Join-Path $RootDir ($o + $e)
    $dst = Join-Path $RootDir ($n + $e)
    if (-not (Test-Path -LiteralPath $src)) { continue }
    $anySrc = $true
    if (Test-Path -LiteralPath $dst) {
      $reasons.Add("target exists$e")
      continue
    }
    if ($Apply) { [System.IO.File]::Move([string]$src, [string]$dst) }
    $moved.Add($e)
  }

  if (-not $anySrc) { $missing++; $report.Add("MISSING`t$o"); continue }
  if ($reasons.Count -gt 0) { $skip++; $report.Add("SKIP`t$o`t->`t$n`t[$($reasons -join ';')]"); continue }

  $ok++
  $tag = if ($Apply) { 'OK' } else { 'DRY' }
  $report.Add("$tag`t$o`t->`t$n`t[$($moved -join ' ')]")
  $done.Add([pscustomobject]@{ old = $o; new = $n; exts = ($moved -join ' ') })
}

if ($Apply) {
  [System.IO.File]::WriteAllLines($logPath, $report, (New-Object System.Text.UTF8Encoding($false)))
} else {
  [System.IO.File]::WriteAllLines($logPath, $report, (New-Object System.Text.UTF8Encoding($false)))
}

$mode = if ($Apply) { 'APPLY' } else { 'DRY RUN' }
Write-Output "MODE`t$mode"
Write-Output "RENAMED`t$ok"
Write-Output "SKIPPED`t$skip"
Write-Output "MISSING`t$missing"
Write-Output "HELD`t$held"
Write-Output "LOG`t$logPath"
if ($skip -gt 0 -or $missing -gt 0) {
  Write-Output '--- problems ---'
  $report | Where-Object { $_ -like 'SKIP*' -or $_ -like 'MISSING*' }
}
Write-Output '--- file counts ---'
foreach ($e in $exts) {
  $c = (Get-ChildItem -LiteralPath $RootDir -File -Filter ('*' + $e)).Count
  Write-Output ("$e`t$c")
}
