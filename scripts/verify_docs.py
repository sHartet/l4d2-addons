#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_docs.py -- guard for the token-diet docs.

Why this exists
---------------
2026-10-09 the workflow docs were slimmed hard to cut the per-turn context bill:
AGENTS.md 37 KB -> 10 KB, SKILL.md 26 KB -> 13 KB, with the detail pushed into
`reference/`.  Slimming is exactly the kind of edit that silently deletes hard-won
knowledge -- and a deleted rule does not fail any test, it just makes the next
run wrong.

So this guard checks three things:

  1. COVERAGE  -- every critical topic is still findable somewhere in the skill
                  docs (SKILL.md + reference/*.md + CONTRIBUTING.md) or AGENTS.md.
  2. REFS      -- every `reference/x.md` / `scripts/x` / `_work\\x` path mentioned
                  in the docs actually exists (no dangling pointers).
  3. BUDGET    -- AGENTS.md / SKILL.md stay under their size caps, so the diet
                  does not silently regress (the whole point was the per-turn bill).

Usage:
    python verify_docs.py [<workDir>]        # default: two levels up from this file
Exit code 0 = ok, 1 = at least one problem (details on stdout as JSON).

The topic list is deliberately ABOUT SEMANTICS, not about wording: each entry
needs ONE of several alternative keywords, so rewording is fine but dropping the
knowledge is not.
"""

import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- size budget
# Caps are generous (current size + ~30% headroom).  Exceeding them means someone
# pasted history/detail back into a per-turn file -- move it to reference/ instead.
BUDGET = {
    'AGENTS.md': 14 * 1024,
    'skill/l4d2-addons/SKILL.md': 17 * 1024,
}

# ---------------------------------------------------------------- topic coverage
# (topic, [any-of keywords], where it must be findable)
#   'skill' = skill docs only (SKILL.md + reference/* + CONTRIBUTING.md)
#   'any'   = skill docs OR AGENTS.md
TOPICS = [
    # -- conflict resolution: the rules that decide which mod survives --------
    ('核心标准：未整理的算新', ['未整理的', '永远按新算'], 'any'),
    ('留新移旧工具', ['resolve_conflicts'], 'skill'),
    ('豁免按成员不按组键', ['按成员', '组键'], 'skill'),
    ('多件套跟随主体', ['多件套'], 'skill'),
    ('白名单可撤销', ['撤销'], 'skill'),
    ('OUTSIDER 标注', ['OUTSIDER'], 'skill'),
    ('冲突两条腿', ['scan_targets', 'overlap_scan'], 'skill'),

    # -- the known blind spot + its history -----------------------------------
    ('扫描盲点（前缀+第二段分组）', ['盲点', '第二段'], 'skill'),
    ('集合名词识别层', ['集合名词'], 'skill'),
    ('专项分类优先于资源类型', ['专项分类优先'], 'skill'),
    ('同系列分卷跟主体', ['分卷', '同一张地图'], 'skill'),

    # -- naming ---------------------------------------------------------------
    ('63 字节硬约束', ['63'], 'any'),
    ('S1-S5 判据', ['S1'], 'skill'),
    ('上位名', ['上位名'], 'skill'),
    ('规则例外表', ['name_exempt'], 'skill'),
    ('人工标签覆盖', ['label_override'], 'skill'),
    ('前缀表三处同步', ['PREFIX', 'CATS'], 'skill'),
    ('全角化 U+FF5C', ['FF5C', '全角'], 'skill'),

    # -- pipeline invariants --------------------------------------------------
    ('unclassifiedPaths 为 0', ['unclassifiedPaths'], 'skill'),
    ('物件域规则锚定 models|materials', ['models|materials'], 'skill'),
    ('归一化 normalizePath', ['normalizePath'], 'skill'),
    ('刷新必须在最后 / stale', ['stale', 'addons_scan.json 已过期'], 'any'),
    ('改名幂等（前缀匹配）', ['幂等'], 'skill'),

    # -- environment traps ----------------------------------------------------
    ('ps1 必须 ASCII', ['ASCII'], 'any'),
    ('ExecutionPolicy Bypass -File', ['ExecutionPolicy Bypass'], 'any'),
    ('PowerShell 变量名大小写不敏感', ['大小写不敏感'], 'skill'),
    ('自测用 config.json 的 pythonPath', ['pythonPath'], 'any'),
    ('mod暂存绝不动', ['mod暂存', 'stagingDir'], 'any'),

    # -- steam / unsubscribe --------------------------------------------------
    ('退订端点 unsubscribeall', ['unsubscribeall'], 'skill'),
    ('退订每次都要问', ['每次'], 'skill'),
    ('result=9 已删除条目', ['result=9', 'result = 9'], 'skill'),
    ('.url 格式', ['InternetShortcut'], 'skill'),

    # -- tooling (the token-diet additions) -----------------------------------
    ('flow.mjs 总入口', ['flow.mjs'], 'any'),
    ('lib.mjs 共用底座', ['lib.mjs'], 'skill'),
    ('verify_all.py 一行总验', ['verify_all'], 'skill'),
    ('self_test 14 阶段', ['self_test'], 'skill'),
]

DOC_GLOBS = ['SKILL.md', 'CONTRIBUTING.md']
REF_DIR = 'reference'


def read(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ''


def collect(workdir):
    """Return (skill_text, agents_text, skill_files) for the given workDir."""
    skill_root = os.path.join(workdir, 'skill', 'l4d2-addons')
    files = []
    for name in DOC_GLOBS:
        p = os.path.join(skill_root, name)
        if os.path.exists(p):
            files.append(p)
    refd = os.path.join(skill_root, REF_DIR)
    if os.path.isdir(refd):
        for n in sorted(os.listdir(refd)):
            if n.endswith('.md'):
                files.append(os.path.join(refd, n))
    skill_text = '\n'.join(read(p) for p in files)
    agents = read(os.path.join(workdir, 'AGENTS.md'))
    return skill_text, agents, files


def check_topics(skill_text, agents_text):
    missing = []
    for topic, kws, where in TOPICS:
        hay = skill_text if where == 'skill' else (skill_text + '\n' + agents_text)
        if not any(k in hay for k in kws):
            missing.append({'topic': topic, 'looked_for': kws, 'scope': where})
    return missing


REF_RE = re.compile(r'`?(reference[/\\][\w.-]+\.md)')


def check_refs(workdir, skill_files):
    """Every `reference/x.md` mentioned in the docs must exist.

    Skip placeholders: docs legitimately write things like `reference/x.md` to mean
    "some file under reference/".  A single-character stem is a placeholder, not a
    pointer -- treating it as a broken link is a false positive, and a guard that
    cries wolf gets ignored.
    """
    skill_root = os.path.join(workdir, 'skill', 'l4d2-addons')
    mentioned = set()
    for p in skill_files + [os.path.join(workdir, 'AGENTS.md')]:
        for m in REF_RE.finditer(read(p)):
            rel = m.group(1).replace('\\', '/')
            stem = os.path.basename(rel)[:-3]          # drop .md
            if len(stem) <= 1:                          # `x.md` / `a.md` = placeholder
                continue
            mentioned.add(rel)
    broken = []
    for rel in sorted(mentioned):
        if not os.path.exists(os.path.join(skill_root, rel)):
            broken.append(rel)
    return sorted(mentioned), broken


def check_budget(workdir):
    over = []
    sizes = {}
    for rel, cap in BUDGET.items():
        p = os.path.join(workdir, rel.replace('/', os.sep))
        if not os.path.exists(p):
            continue
        n = os.path.getsize(p)
        sizes[rel] = n
        if n > cap:
            over.append({'file': rel, 'bytes': n, 'cap': cap})
    return sizes, over


def main():
    workdir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
    workdir = os.path.abspath(workdir)

    skill_text, agents_text, skill_files = collect(workdir)
    if not skill_files:
        print(json.dumps({'ok': False, 'error': 'skill docs not found under %s' % workdir},
                         ensure_ascii=False, indent=1))
        return 1

    missing = check_topics(skill_text, agents_text)
    mentioned, broken = check_refs(workdir, skill_files)
    sizes, over = check_budget(workdir)

    ok = not (missing or broken or over)
    out = {
        'ok': ok,
        'workDir': workdir,
        'docs': [os.path.relpath(p, workdir) for p in skill_files],
        'topics': {'total': len(TOPICS), 'covered': len(TOPICS) - len(missing)},
        'refs': {'mentioned': len(mentioned), 'broken': broken},
        'sizes': sizes,
        'overBudget': over,
        'missing': missing,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if not ok:
        print('\n[FAIL] docs guard', file=sys.stderr)
        for m in missing:
            print('  missing topic: %s  (looked for %s in %s)' % (m['topic'], m['looked_for'], m['scope']),
                  file=sys.stderr)
        for b in broken:
            print('  broken ref: %s' % b, file=sys.stderr)
        for o in over:
            print('  over budget: %s %d B > %d B' % (o['file'], o['bytes'], o['cap']), file=sys.stderr)
        print('  -> knowledge may have been lost in the slimming; restore it into reference/ '
              'or AGENTS.md (do NOT just widen the budget).', file=sys.stderr)
        return 1
    print('docs guard OK  topics=%d/%d  refs=%d  sizes=%s'
          % (len(TOPICS), len(TOPICS), len(mentioned),
             ' '.join('%s=%dB' % (k.split('/')[-1], v) for k, v in sizes.items())),
          file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
