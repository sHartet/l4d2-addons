param(
  [Parameter(Mandatory=$true)][string]$Batch,
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
# ==== injection end ====

# ---------------------------------------------------------------------------
# Conflict resolution: keep the newest, move the losers into backupDir.
#
# THE CORE RULE (user-specified, 2026-10-02 / restated 2026-10-03):
#   Anything that came out of workshop\ is ALWAYS the "new" one.
#   Dates are only a tie-breaker BETWEEN two workshop items -- a resident mod
#   never wins against a freshly subscribed one, no matter how new it looks.
#
# This script only performs the MOVE + the manifest row. Deciding who wins is the
# caller's job (the agent), because "which one is the workshop item" only exists
# during the run -- after consolidation they all sit in addons/.
#
# Batch JSON (UTF-8, array):
#   [ { "target": "<replacement target>",
#       "keep":   "<stem of the WINNER, must exist in addons>",
#       "move":   ["<stem of a loser>", ...],
#       "reason": "<why: dates / workshop-new / user call>" } ]
#
# Safety: if the WINNER has no .vpk in addons, the whole entry is skipped --
#         never move files away without keeping a replacement for that target.
# Dry run by default; -Apply to actually move.
# ASCII only: every label comes from the UTF-8 batch JSON.
# ---------------------------------------------------------------------------

$enc = New-Object System.Text.UTF8Encoding($false)
$plan = Get-Content -LiteralPath $Batch -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $L4D2_BACKUP)) { New-Item -ItemType Directory -Force -Path $L4D2_BACKUP | Out-Null }
$manifest = Join-Path $L4D2_BACKUP 'backup_manifest.md'

$rows = New-Object System.Collections.ArrayList
$skipped = New-Object System.Collections.ArrayList
$moved = 0

foreach ($g in $plan) {
  $keep = [string]$g.keep
  if ($keep -eq '') { [void]$skipped.Add('entry without keep: ' + [string]$g.target); continue }
  if (-not (Test-Path -LiteralPath (Join-Path $L4D2_ADDONS_DIR ($keep + '.vpk')))) {
    [void]$skipped.Add('KEEP-MISSING (nothing moved): ' + $keep)
    continue
  }
  foreach ($m in $g.move) {
    $stem = [string]$m
    if ($stem -eq '' -or $stem -eq $keep) { continue }
    foreach ($ext in 'vpk', 'jpg', 'url') {
      $src = Join-Path $L4D2_ADDONS_DIR ($stem + '.' + $ext)
      if (-not (Test-Path -LiteralPath $src)) { continue }
      $dst = Join-Path $L4D2_BACKUP ($stem + '.' + $ext)
      $k = 0
      while (Test-Path -LiteralPath $dst) { $k++; $dst = Join-Path $L4D2_BACKUP ($stem + ' (' + $k + ').' + $ext) }
      if ($Apply) {
        [System.IO.File]::Move([string]$src, [string]$dst)
        $moved++
      }
      [void]$rows.Add([pscustomobject]@{
        Target = [string]$g.target
        File   = (Split-Path -Leaf $dst)
        Reason = [string]$g.reason
        Kept   = $keep
      })
    }
  }
}

Write-Output (($(if ($Apply) { 'APPLY' } else { 'DRY RUN' })) + "  entries=" + @($plan).Count + "  files=" + $rows.Count + "  skipped=" + $skipped.Count)
foreach ($r in $rows) { Write-Output ('  ' + $(if ($Apply) { 'MOVED ' } else { 'WOULD ' }) + $r.File + '   (kept: ' + $r.Kept + ')') }
foreach ($s in $skipped) { Write-Output ('  ! ' + $s) }
if (-not $Apply) { return }

if ($rows.Count -gt 0) {
  $lines = @()
  if (Test-Path -LiteralPath $manifest) { $lines = @(Get-Content -LiteralPath $manifest -Encoding UTF8) }
  if ($lines.Count -eq 0) {
    $lines = @('# mod backup manifest', '',
               'Mods moved out of addons because a newer mod replaces the same target.',
               '', '| target | backed up file | reason | kept instead |', '|---|---|---|---|')
  }
  # Insert at the end of the table: the last table row before the notes separator.
  $ins = $lines.Count
  $sep = -1
  for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].TrimStart().StartsWith([string][char]0x2500)) { $sep = $i; break } }
  if ($sep -ge 0) { $ins = $sep; while ($ins -gt 0 -and $lines[$ins - 1].Trim() -eq '') { $ins-- } }
  $new = New-Object System.Collections.ArrayList
  foreach ($r in $rows) { [void]$new.Add('| ' + $r.Target + ' | ' + $r.File + ' | ' + $r.Reason + ' | ' + $r.Kept + ' |') }
  $out = @()
  if ($ins -gt 0) { $out += $lines[0..($ins - 1)] }
  $out += $new
  if ($ins -lt $lines.Count) { $out += $lines[$ins..($lines.Count - 1)] }
  [System.IO.File]::WriteAllText($manifest, (($out -join "`r`n") + "`r`n"), $enc)
  Write-Output ('  manifest rows appended: ' + $rows.Count + '  -> ' + $manifest)
}
Write-Output ('  backupDir now holds: ' + @(Get-ChildItem -LiteralPath $L4D2_BACKUP -File).Count + ' files')
