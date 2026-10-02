param(
  [string]$OutName = 'workshop_scan'
)
$ErrorActionPreference = 'Stop'

# ==== L4D2 skill: path resolution (injected at build time; do not edit) ====
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
# ==== injection end ====

# Scan the workshop staging folder with the SAME classify rules used for addons.
# Why: newly subscribed VPKs are not in addons yet, so the library scanner cannot
# see them and the naming step would have no evidence.
$WS = L4D2-Get 'workshopDir' (Join-Path $L4D2_ADDONS_DIR 'workshop')
if (-not $WS -or $WS -eq '') { $WS = Join-Path $L4D2_ADDONS_DIR 'workshop' }
if (-not (Test-Path -LiteralPath $WS)) { Write-Output ("NO-WORKSHOP  " + $WS); exit 0 }

$env:L4D2_SCAN_DIR = $WS
$env:L4D2_SCAN_OUT = Join-Path $L4D2_WORK ($OutName + '.json')
$env:L4D2_SCAN_TARGETS_OUT = Join-Path $L4D2_WORK ($OutName + '_by_target.json')

$node = L4D2-Get 'nodePath' 'node'
$scanner = Join-Path $L4D2_WORK 'scan_addons.mjs'
if (-not (Test-Path -LiteralPath $scanner)) { throw ("scanner not found: " + $scanner) }
& $node $scanner
Write-Output ("OUT -> " + $env:L4D2_SCAN_OUT)
