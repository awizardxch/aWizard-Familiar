# Skill: Thermo-Nuclear Code Quality Review

> A deliberately harsh **maintainability** review: code-judo restructurings, the 1k-line rule, spaghetti
> conditionals, thin wrappers, boundary and type cleanliness, canonical layers, atomic updates.
> The rubric is Cursor's (MIT), and it is **not copied here**. Fetch it (below) and apply it in full; this
> file holds our notes on using it in this workspace. Other kit skills: `cursorTeamKit.md`.

## Using it in this workspace

- **It is not a security audit.** It asks "is this the simplest correct structure?", never "can this be
  drained?". For any puzzle, run it **alongside** `clvmPuzzleAudit.md` and the forge-puzzles runbook
  (`skills/n-asset-pool-audit/SKILL.md`), never instead of them. The two together are what we call a
  "thermonuclear review" before a testnet or mainnet step.
- **Puzzles have a cost the rubric doesn't know about.** A refactor of a Rue leaf, or of a curried
  `Config`/`State` layout, moves puzzle hashes and re-pins (`pins.json` in forge-campaign, the
  revision's pin table in forge-puzzles). Once a puzzle is on chain, its hash can't change. Every
  puzzle remedy must therefore say whether it moves a hash and what it does to CLVM cost. Before launch
  that is a fair trade; after launch it is a new revision.
- **Upstream or vendored puzzles are out of scope**, e.g. slot-machine `upstream/` and CNI's multisig.
- **Intentional mirrors are not duplication.** A Python reference model that mirrors a puzzle (FLPCR's
  `flpcr/distributor.py`, held to it by a differential suite) is a test oracle. Collapsing it into the
  driver defeats its purpose. Duplication *within* a layer is still fair game.
- **Findings format.** When the review is part of an audit report, give each finding an ID, priority (the
  rubric's order below), file:line, the observation, a concrete remedy (signatures, files that shrink,
  rough line delta), hash/cost impact, and confidence. End with the approval-bar verdict.
- **When there is no base branch** (a new repo), treat the whole tree as the change.

## Getting the rubric

```bash
curl -sSL https://raw.githubusercontent.com/cursor/plugins/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md
```

Browse: <https://github.com/cursor/plugins/blob/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md>.
The companion subagent is `cursor-team-kit/agents/thermo-nuclear-code-quality-review.md`; it loads the
skill and applies it to the diff and file contents its parent collected. Last checked at
`6b78e9f4e46c75d1697d837e51f07c2692e60b24`. If upstream has changed since, re-read it before you apply it.

**In short:**
- Be ambitious about code-judo restructurings that delete complexity.
- Treat any change that pushes a file past 1000 lines, or adds ad-hoc branching, as a presumptive
  blocker.
- Flag thin wrappers, casts and optionality that hide an invariant.
- Keep logic in its canonical layer.
- Prefer atomic updates.
- Prioritize, in order: structural regressions, missed simplifications, spaghetti growth, boundaries,
  file size, modularity, legibility.
- Prefer a few high-conviction findings to many nits.
- Don't approve just because the code works.
