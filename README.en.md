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
3. **Resolves real conflicts newest-wins** — for mods competing over the same target, whatever is
   **still un-consolidated (i.e. just came out of `workshop\`) always wins**; workshop `time_updated`
   only breaks ties between two items that both came from `workshop\`. The loser moves into `mod备份\`
   and is recorded in the manifest.
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

## Workflow

Say *"tidy up my L4D2 mods"* and it walks these five steps:

1. **Move into `addons\` and normalise the names** — subscribed VPKs are moved out of `workshop\` into `addons\`,
   renamed to `<category>-<target>-<original title>`, and given a `.url` shortcut (double-click to open the workshop page).
   e.g. `3778253592.vpk` → `主武器-AK-47 突击步枪-<author's title>.vpk`.
   Once moved, the mod **no longer depends on workshop loading**, and Steam can no longer silently re-download over it.
   - Hand-dropped VPKs (filename is not a bare numeric id) have **no workshop id, so no `.url`** and they are excluded from unsubscribing
   - The now-empty `workshop\` folder is **kept** (deleting it breaks Steam's downloads)
2. **Build a workbook that keeps itself up to date** — 16 sheets marking every replaceable object as
   **replaced / not replaced / only covered incidentally by a map pack**, naming the mod responsible,
   plus "my mod list" and "replacement coverage" sheets. Double-click `刷新表格.bat` to rescan and rebuild; no agent needed.
3. **Detect conflicts and keep the newest** — grouped by replacement target (weapons / survivors / throwables / consumables / props…),
   the newest `time_updated` wins (anything freshly in `workshop\` counts as newest). Losers move to `mod备份\` together with their
   `.jpg` / `.url`, and the reason plus SHA-1 is recorded in `mod备份\backup_manifest.md`.
   - **Multi-part sets are exempt**: a mod's main body plus its materials / scope / sound add-ons are meant to coexist
   - Exemptions are matched against the **declared member list** in `_work\set_exempt.json`, **not** against a group key —
     an undeclared newcomer in the same group is a genuine conflict
   - Your own calls win: anything in `mod白名单.txt` is skipped, and you can revoke a whitelist entry later
4. **Asks before unsubscribing** (double-check) — it stops and asks once, spelling out what would be unsubscribed,
   why it matters, and how to undo it. On your go-ahead it unsubscribes automatically, so you never touch the workshop page.
   - Why it matters: workshop delivery drops the VPK straight into `workshop\`; without unsubscribing, the next game launch
     re-downloads everything you just moved
   - Scope is safe: only `appid=550` is touched; other games' subscriptions are byte-for-byte unchanged in testing
   - **Authorisation does not carry across sessions** — only an explicit "don't ask" in the current session skips the prompt
5. **Refresh the workbook and save the run to memory** — one last `刷新表格.bat` so the scan data matches the disk
   (rename without rescanning and the planner re-proposes the same renames from stale data — it warns with
   `[WARN] addons_scan.json is stale`), then the outcome is condensed into **one compact memory entry** so the next
   session can pick it up without re-exploring, **saving tokens**.

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
