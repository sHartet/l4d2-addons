# Contributing

Thanks for taking a look. This project organises Left 4 Dead 2 mod libraries, and
most of its value is in details that are **easy to break by accident**. This document
exists mainly to put those details in writing.

[中文说明见 README.md](README.md)

---

## Development setup

Windows only (the toolchain uses batch files, robocopy and PowerShell).

```powershell
# 1. dependencies
python -m pip install openpyxl      # Python 3.10+
node --version                      # Node 18+

# 2. run the full self-test -- this is the fastest way to know your checkout is sane
python scripts\self_test.py
```

`self_test.py` simulates a brand-new user with an empty library inside a temp
directory and walks nine stages (bootstrap -> fake VPKs -> refresh -> workshop scan ->
migration -> verification -> re-refresh -> naming idempotence -> conflict/validation).
It never touches a real library, and **keeps the temp folder if a stage fails** so you
can inspect it.

---

## The hard invariants

These are not style preferences. Each one is here because breaking it caused a real,
user-visible defect.

### 1. Every `.ps1` file must be 100% ASCII — comments included

PowerShell 5.1 decodes a BOM-less UTF-8 `.ps1` as GBK/ANSI. A single non-ASCII byte
corrupts the parse, and the damage is not limited to the offending line: a Chinese
comment once **swallowed the following line**, so a variable stayed `$null` and the
script failed with a confusing error.

```powershell
python scripts\verify_ps1_ascii.py     # must print {"ok": true, ...}
```

Rules that follow from this:

- Write `.ps1` comments **in English**. Do not write Chinese anywhere in a `.ps1`.
- Chinese data (titles, category names, targets) belongs in **UTF-8 JSON batch files**
  that the script reads at runtime — never inline in the script.
- The same applies to Chinese *paths*: `Join-Path $addons 'mod备份'` silently resolves
  to a nonexistent path and `Test-Path` returns `$false` without an error.
- `.py` and `.mjs` are read as UTF-8 and are fine with Chinese.

### 2. One label ↔ one table row

`scan_addons.mjs` produces classification labels; `enrich_ref_xlsx.py` maps each label
to **exactly one** workbook row. If two rows share a label, both rows display the same
mod list — a real mis-attribution that shipped once (a "Zoey (lightweight)" row showed
Francis's mod).

`enrich_ref_xlsx.py` self-checks on startup and prints:

```
[OK] 标签与表格行一一对应：221 个标签，无共用
```

Anything else is a `[WARN]` listing the offenders. Fix the labels, do not silence it.

### 3. Object-domain rules must anchor `^(models|materials)/`

Both sides of the alternation are load-bearing:

- Anchoring only `^models/` misses texture-only object mods. A ladder mod whose 36 paths
  were **all** `materials/` dropped that row from `✅ 已替换` to `⚠ 仅附带覆盖`.
- Not anchoring at all lets the rule steal same-named `sound/` directories — a
  `weapons/50cal` rule swallowed `sound/weapons/50cal/`, so the sound row lost its mod.

Any new prop / scene / fixed-weapon rule follows `^(models|materials)/`.

### 4. Multi-value cells carry full paths

- Every value is a **full path**; multiple values are joined with `、`.
- Wildcards are written `*`; whole directories end with `/`.
- Files sitting at the **VPK root** are written as bare filenames
  (e.g. `l4d2_background01.bik`) — that still counts as a complete path.
- Explanatory prose goes in the remarks column, never inside the value.

```powershell
python scripts\verify_fixes.py     # 缺陷4_多值单元格全路径.不合格条目数 must be 0
```

### 5. Paths go through `normalizePath()` before classification

Some packers wrap the whole tree in extra directories:

```
left 4 dead 2/left4dead2/media/valve.bik
for_users/error_fix/left 4 dead 2/left4dead2/particles/x.pcf
for_modders/particles/3p/x.pcf
```

None of these match a `^`-anchored rule. Normalisation strips wrapper directories
(`for_users/`, `for_modders/`, …) and then cuts to the earliest game root
(`models|materials|sound|particles|scripts|resource|maps|missions|modes|media|scenes|…`).

**Acceptance criterion: `unclassifiedPaths` must be `0`.** A new mod that makes this
number climb means either a rule or the normaliser is missing something.

### 6. Changing the prefix table means changing three places

The category prefix list lives in more than one file. Miss one and you get either silent
mis-grouping or **false conflicts**:

| File | What to update |
|---|---|
| `scripts/plan_v4.py` | `PREFIX` |
| `scripts/scan_targets.ps1` | `$cats` (keep legacy names for compatibility) |
| `scripts/verify_overlaps.py` | `CATS` |

A stale `CATS` once reported "`特感-Boomer-…` and `特感-Hunter-…` are fighting over the
same object" — two different objects entirely. Real conflicts went back to 0 once the
table was current.

> Note: `scan_targets.ps1` treats a line as a whitelist entry only when the line
> **starts** with `<prefix>-`. When writing Chinese prose in that file, do not let a
> continuation line begin with a prefix, or it will be swallowed as an entry.

### 7. `scripts/` is the single source of truth

The skill scripts in `scripts/` are authoritative. `bootstrap.py` copies only **tool**
scripts into a user's working directory (extension allowlist plus a data-name denylist),
so dropping a data file into `scripts/` can never overwrite a user's own file — but do
not rely on that; keep data out of `scripts/`.

### 8. Never ship user data

Whitelists, exception tables (`name_exempt.json`, `set_exempt.json`), batch files,
scan results (`addons_scan.json`, `label_map.json`, …) and workbooks are **gitignored**.
The published package contains tools and documentation only. Before opening a PR, check:

```powershell
git status --porcelain
git ls-files | Select-String -Pattern 'exempt|白名单|_scan|label_map|\.xlsx$|ws_batch'
```

### 9. Do not hand-edit the injected path-resolution block

Every script carries a generated preamble between

```
# ==== L4D2 skill: path resolution (injected; do not edit) ====
...
# ==== injection end ====
```

Paths resolve in three tiers: **environment variable → `config.json` → built-in
default**. Change the resolution logic where it is generated, not inside each script.

### 10. Naming must stay idempotent

Running the planner over an already-organised library must propose **zero** changes.
The implementation guards this by matching an existing name against the expected
prefix instead of splitting on `-`, because targets legitimately contain dashes
(`AK-47 突击步枪`). Any change to naming logic has to keep `plan_v4.py` reporting
`需改名 0`.

---

## Adding a classification rule

1. Add the rule to `RULES` in `scripts/scan_addons.mjs`. Remember invariant 3.
2. Map the new label to exactly one workbook row in `scripts/enrich_ref_xlsx.py`
   (invariant 2).
3. Add an assertion for it in `scripts/verify_rules.mjs` — that file is the regression
   suite for classification and currently runs 67 classification assertions plus 6
   normalisation assertions.
4. Run:

```powershell
# IMPORTANT: these verifiers read config.json to find the working directory, and their
# fallback assumes the script sits in <workDir>\<scriptsDir>\. Running them straight from
# a fresh clone's scripts\ folder does NOT work (they would look for <repo>\_work\...).
# So run the deployed copies, or point L4D2_HOME at a configured working directory first.
$env:L4D2_HOME = "<workDir>"            # or just cd into <workDir>\_work\

node   <workDir>\_work\verify_rules.mjs        # all assertions pass (currently 67 + 6)
python <workDir>\_work\verify_fixes.py         # 不合格条目数 == 0
python <workDir>\_work\verify_overlaps.py      # no false conflicts
python scripts\self_test.py                     # end-to-end still green (uses a temp dir,
                                                 # so this one DOES work from the clone)
```

If your rule is object-domain, also confirm `probe_unclassified.mjs` on a real mod
reports the paths you expect.

---

## Pull requests

- Keep the subject line in English, imperative mood
  (`scan_addons: anchor melee rules to models|materials`).
- One concern per commit where practical.
- **`self_test.py` and `verify_rules.mjs` must pass.** Say so in the PR description.
- If you changed a prefix or a rule, mention which of the three tables you updated
  (invariant 6).
- Screenshots of the workbook are welcome when a change alters a sheet.

## Reporting a bug

The most useful report includes the raw evidence rather than a description of it:

```powershell
# the mod's internal resource paths
& scripts\vpklist.ps1 -Path @("<path to .vpk>") -OutName bug_report -TopN 50

# which of those paths failed to classify
node scripts\probe_unclassified.mjs "<path to .vpk>"

# a VPK's own addoninfo.txt (authoritative when the workshop page is gone)
& scripts\vpkdump.ps1 -Path "<path to .vpk>" -Match '^addoninfo\.txt$' -OutName dump -MaxChars 3000
```

Then include the resulting file plus the produced (wrong) name vs the expected name.

## License

By contributing you agree that your contributions are licensed under the MIT License
(see [LICENSE](LICENSE)).
