# Upstream

Vendored verbatim from <https://github.com/cursor/plugins>, directory `cursor-team-kit/`, at commit
`6b78e9f4e46c75d1697d837e51f07c2692e60b24` (2026-10-19). MIT, Copyright (c) 2026 Cursor; see `LICENSE`.

Nothing in this directory is edited. Our routing and notes live in `docs/skills/README.md` (section
"Engineering Workflow — Cursor Team Kit"), and our adapted copy of the code-quality review is
`docs/skills/thermoNuclearCodeReview.md`.

To update, re-copy the directory from a newer upstream commit, change the commit above, and check that
`thermoNuclearCodeReview.md` still matches `skills/thermo-nuclear-code-quality-review/SKILL.md` below
its front matter:

```bash
git clone --depth 1 https://github.com/cursor/plugins /tmp/cursor-plugins
rm -rf vendor/cursor-team-kit/{skills,agents,rules,assets,.cursor-plugin}
cp -r /tmp/cursor-plugins/cursor-team-kit/. vendor/cursor-team-kit/
diff <(sed -n '/^# Thermo-Nuclear Code Quality Review$/,$p' docs/skills/thermoNuclearCodeReview.md) \
     <(sed -n '/^# Thermo-Nuclear Code Quality Review$/,$p' vendor/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md)
```
