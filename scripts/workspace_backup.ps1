param(
  [ValidateSet('save','restore')][string]$Mode = 'save'
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

$WS = $L4D2_HOME
$BK = $L4D2_MIRROR

# Some host apps (e.g. an NSIS-installed desktop app) replace their whole install dir
# on upgrade, wiping anything kept inside it. So keep this mirror OUTSIDE that tree.
# Verified after a real upgrade wiped the in-tree copy.

if ($Mode -eq 'save') {
  if (-not (Test-Path -LiteralPath $WS)) { throw "workspace missing: $WS" }
  New-Item -ItemType Directory -Force -Path $BK | Out-Null
  # robocopy /MIR mirrors exactly, including deletions. Exit codes 0-7 are success.
  $null = robocopy $WS $BK /MIR /NFL /NDL /NJH /NJS /NP
  if ($LASTEXITCODE -ge 8) { throw "robocopy failed with $LASTEXITCODE" }
  Write-Output ("SAVED  {0}  ->  {1}" -f $WS, $BK)
} else {
  if (-not (Test-Path -LiteralPath $BK)) { throw "backup missing: $BK" }
  New-Item -ItemType Directory -Force -Path $WS | Out-Null
  $null = robocopy $BK $WS /MIR /NFL /NDL /NJH /NJS /NP
  if ($LASTEXITCODE -ge 8) { throw "robocopy failed with $LASTEXITCODE" }
  Write-Output ("RESTORED  {0}  ->  {1}" -f $BK, $WS)
}

Write-Output "--- workspace now ---"
Get-ChildItem -LiteralPath $WS -Force | Select-Object Mode,Name,Length | Format-Table -AutoSize | Out-String -Width 140
Write-Output ("_work files = " + (Get-ChildItem -LiteralPath (Join-Path $WS $L4D2_SCRIPTS) -File -ErrorAction SilentlyContinue).Count)
