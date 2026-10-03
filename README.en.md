# l4d2-addons

An **Agent Skill** that turns a messy Left 4 Dead 2 workshop mod folder into something
you can actually read, search and trust.

Install it into a coding agent (DSH, Claude Code, …), say *"tidy up my L4D2 mods"*,
and it will scaffold its own toolchain and get to work.

[中文说明见 README.md](README.md) · [Contributing](CONTRIBUTING.md)

---

## The problem

Every mod you subscribe to lands on disk as a numeric filename: `3778253592.vpk`.
After a few hundred of them you neither know what each file *is*, nor which mods
are **fighting over the same slot** (install two Hunter replacers and only one wins).

This skill does four things:

1. **Finds out what each mod actually replaces** — it parses the VPK container and
   reads the real internal resource paths, instead of guessing from the filename.
2. **Renames to `category-target-original title`** with 19 category prefixes
   (`survivor-`, `si-`, `primary-`, `melee-`, `material-`, `script-`, …).
3. **Resolves real conflicts newest-wins** — for mods competing over the same target,
   keep the one with the newer workshop `time_updated`, move the loser into `mod备份\`.
4. **Builds a reference workbook** (16 sheets) marking every replaceable game object
   as *replaced / not replaced / only shipped incidentally by a map pack*, naming the
   mod responsible.

## Quick start

On first use the skill asks three questions (**once**):

- where your `left4dead2\addons` folder is
- where the `workshop` staging folder is (defaults to `<addons>\workshop`)
- which working directory to use (defaults to the current one)

It then writes `config.json`, lays down its scripts, renders a `刷新表格.bat`
(refresh-table batch file) and produces the first workbook. After that, **double-clicking
that `.bat` re-scans and refreshes everything** — no agent required.

```
<workDir>\
  config.json
  刷新表格.bat                      <- double-click to rescan & refresh
  求生之路2_可MOD替换物品总表.xlsx     <- 16-sheet reference workbook
  _work\                            <- all tools + intermediate data
```

## Design notes

- **Confidence tiers.** Classification walks
  `S1 map -> S2 object domain -> S3 object domain (texture-only) -> S4 resource type -> S5 keep the existing prefix`.
  At low confidence it **keeps the human-made prefix and reports the item for review** —
  it never guesses silently.
- **Idempotent.** Re-running the naming planner on an already-organised library
  proposes **zero** changes.
- **Decisions are persisted.** Trade-offs you settle are written to `name_exempt.json`
  so a later re-run will not undo them.
- **Conflicts are not judged by filename.** They come from the
  *real VPK paths -> labels -> workbook rows* chain. The filename scanner is only a fallback
  (mods under a resource-type prefix have an empty target segment, so filename grouping cannot see them).
- **No local data ever ships.** The package contains tools and docs only; your whitelist,
  exception tables, batches, scan results and workbooks stay on your machine.

## Repository layout

```
l4d2-addons/
  SKILL.md                 entry point the agent reads (first-run flow, 8-step standard flow, toolbox)
  README.md / README.en.md
  CONTRIBUTING.md          the ten hard invariants -- each one exists because breaking it shipped a bug
  LICENSE                  MIT
  install.ps1              installs this folder into the DSH skills root
  .gitignore / .gitattributes / .editorconfig
  reference/
    naming-rules.md        full classification spec (criteria, adjacency labels, cross-cutting rows, exceptions)
    xlsx-pipeline.md       workbook pipeline + its four hard invariants
    vpk-format.md          VPK binary format, and the two traps
    steam-api.md           workshop API, .url format, unsubscribe-all
    pitfalls.md            Windows / PowerShell 5.1 / encoding gotchas
  scripts/                 every executable tool, driven entirely by config.json
```

## Manual install

```powershell
powershell -File install.ps1
```

Installs into `$env:DSH_HOME\skills\l4d2-addons` (falling back to `~\.dsh\skills\l4d2-addons`);
pass `-Dest "<dir>"` to choose somewhere else. Then just ask your agent to tidy up your L4D2 mods.

## Self-test

```powershell
python scripts\self_test.py
```

Simulates a **brand-new user with an empty library** inside a temp directory and walks all
nine stages: bootstrap, fake-VPK generation, empty-library refresh, workshop scan,
migration, three-file verification, re-refresh, naming idempotence, and conflict/validation checks.
It never touches your real library, and keeps the temp folder if a stage fails.
Run it before touching any script.

## Requirements

- Windows (uses batch files, robocopy and PowerShell)
- Python 3.10+ with **openpyxl**
- Node.js 18+

Paths resolve in three tiers — **environment variable -> `config.json` -> built-in default** —
overridable per run with `L4D2_HOME`, `L4D2_ADDONS`, `L4D2_XLSX_OUT`, `L4D2_MIRROR`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: every `.ps1` must be pure ASCII
(PowerShell 5.1 decodes BOM-less UTF-8 as GBK, and a Chinese *comment* can swallow the next
line), one classification label maps to exactly one workbook row, and `scripts\self_test.py`
must stay green.

## License

MIT — see [LICENSE](LICENSE).
