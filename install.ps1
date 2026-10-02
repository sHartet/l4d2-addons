param(
  [string]$Dest = ''
)
$ErrorActionPreference = 'Stop'
# Installs THIS folder as a skill into the DSH skills root (or -Dest).
# ASCII only: a non-ASCII byte in a .ps1 breaks PowerShell 5.1 parsing
# (it decodes BOM-less UTF-8 as GBK -- even inside a comment).

$src = $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $src 'SKILL.md'))) {
  throw "SKILL.md not found next to install.ps1: $src"
}

if (-not $Dest -or $Dest -eq '') {
  $root = $env:DSH_HOME
  if (-not $root -or $root -eq '') { $root = Join-Path $HOME '.dsh' }
  $Dest = Join-Path (Join-Path $root 'skills') 'l4d2-addons'
}

$Dest = $Dest.TrimEnd('\')
if ($Dest -eq $src.TrimEnd('\')) { throw "destination equals source; nothing to do" }

if (Test-Path -LiteralPath $Dest) {
  Write-Output ("removing old copy: " + $Dest)
  Remove-Item -LiteralPath $Dest -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dest) | Out-Null
Copy-Item -LiteralPath $src -Destination $Dest -Recurse -Force

# never ship a bytecode cache
Get-ChildItem -LiteralPath $Dest -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Output ("INSTALLED  " + $Dest)
Get-ChildItem -LiteralPath $Dest | Select-Object Mode, Name, Length | Format-Table -AutoSize | Out-String -Width 120
Write-Output ("scripts: " + (Get-ChildItem -LiteralPath (Join-Path $Dest 'scripts') -File).Count + " files")
Write-Output ("total:   " + (Get-ChildItem -LiteralPath $Dest -Recurse -File).Count + " files")
Write-Output "Next: ask your agent to tidy up your L4D2 mods."
