# Quest Management Workflow

**Domain:** Project management, task tracking, iterative development  
**When to use:** Complex multi-phase projects, DeFi protocol development, feature scaffolding  
**Pattern:** Foundation First → Backlog Later → Maximum Velocity

---

## Philosophy: Foundation First, Polish Later

The aWizard quest system prioritizes **shipping viable foundations quickly** over perfect implementations. This maximizes completion velocity while maintaining organized backlogs for future enhancements.

### Core Principle
> **Complete quests at 30-60% implementation by delivering foundations, then backlog remaining polish.**

**Why this works:**
- ✅ Maximizes quest completion count (morale boost, progress visibility)
- ✅ Prevents multi-week quests from blocking new work
- ✅ Creates clear handoff points for future sessions
- ✅ Foundation code provides reference for enhancements
- ✅ Backlogs are better documented when written immediately after foundation

**Anti-pattern:**
- ❌ Attempting 100% completion before moving quest to done/
- ❌ Leaving incomplete quests in active folder indefinitely
- ❌ Creating massive quest files with 50+ unchecked items

---

## Quest Folder Structure

```
docs/quests/
├── *.md                    # Active quests (1-2 max recommended)
├── backlog/
│   ├── *.md                # Future quests (not started)
│   └── enhance-*.md        # Completion backlogs for done quests
├── done/
│   └── *.md                # Completed quests (foundation delivered)
├── diagrams/
│   └── *.md                # Mermaid flow diagrams (shared)
└── sidequests/             # Parallel side quest lane
    ├── README.md           # Side quest system overview
    ├── patent-incubator.md # Active patent research side quest
    └── ideas/              # Patent idea cards
```

### Folder Definitions

**Active (`docs/quests/*.md`)**
- Quests currently being worked on
- **Limit:** 1-2 active quests maximum
- **Criteria:** Has clear next action, actively coding/implementing
- **Move to done/ when:** Foundation complete (30-60%), not 100%

**Side Quests (`docs/quests/sidequests/`)**
- Run **in parallel** with all main quests — never block the critical path
- Patent incubator: capture novel ideas as they emerge from build work
- Subagent-delegated research — main conversation stays focused on shipping
- See `sidequests/README.md` for the side quest system
- **Standing order:** After completing any main quest foundation, check if it produced a patentable idea

**Backlog (`docs/quests/backlog/`)**
- Future quests not yet started
- Enhancement quests waiting on dependencies
- **Two types:**
  1. **New quests** (`bootstrap-*.md`, `build-*.md`) — Not started
  2. **Enhancement quests** (`enhance-*.md`) — Remaining work from completed foundations

**Done (`docs/quests/done/`)**
- Quests with viable foundation delivered
- **NOT** 100% complete — just functional enough to use
- Keep original quest file intact with completion note at bottom

**Diagrams (`docs/quests/diagrams/`)**
- Shared Mermaid diagrams
- Flow charts, sequence diagrams, architecture diagrams
- Referenced by multiple quests

---

## Quest Lifecycle

### 1. Create Quest (Backlog)

```markdown
# Quest: Build [Feature Name]

**Status:** BACKLOG
**Created:** YYYY-MM-DD
**Priority:** High/Medium/Low
**Estimated Effort:** X hours

## Objective
Clear 1-2 sentence goal.

## Why Now
Context for why this quest matters.

## Implementation Plan
- [ ] Step 1
- [ ] Step 2
...

## Success Criteria
✅ Criterion 1
✅ Criterion 2
```

**File location:** `docs/quests/backlog/build-<feature-name>.md`

---

### 2. Activate Quest (Move to Active)

When ready to start work:

```powershell
Move-Item "docs/quests/backlog/build-feature.md" "docs/quests/build-feature.md"
```

**Update quest status:**
```markdown
**Status:** ACTIVE → IN PROGRESS
```

**Update TODO file:**
```markdown
**🚧 In Progress:**
- **Feature Name** — [docs/quests/build-feature.md](quests/build-feature.md) — Step 2/10 (20%)
```

---

### 3. Work on Quest (Foundation Phase)

**Foundation = 30-60% complete**

Typical foundation deliverables:
- ✅ Research document / reference implementation studied
- ✅ Math library / core logic (TypeScript)
- ✅ Project scaffold (Vite/React/Node setup)
- ✅ Core types and interfaces
- ✅ README.md with comprehensive docs
- ✅ 1-3 key components or functions working
- ✅ Dev server runs (`npm run dev` works)

**NOT required for foundation:**
- ❌ All UI components (just core ones)
- ❌ Charts and visualizations (defer to backlog)
- ❌ Advanced features (polish items)
- ❌ Smart contracts deployed
- ❌ Testnet deployment
- ❌ Full test coverage

**Checkpoint:** Can another developer understand the project and continue? → Foundation ready.

---

### 4. Complete Quest (Move to Done)

When foundation is viable (30-60%), mark quest complete:

#### Step 4a: Update Quest File

Add completion summary at bottom:

```markdown
---

## ✅ Quest Complete — Foundation Delivered

**Status:** FOUNDATION COMPLETE (YYYY-MM-DD)
**Completion:** X% (Research, math, scaffold, core components)
**Production Ready:** localhost:PORT ✅

**Delivered:**
- ✅ Item 1
- ✅ Item 2
...

**Remaining work moved to:** [enhance-feature-name.md](backlog/enhance-feature-name.md)

**Foundation Progress:** X / Y phases complete (Z%)

---

**Last updated:** YYYY-MM-DD
**Quest moved to done/:** Foundation complete, enhancements backlogged
```

#### Step 4b: Create Enhancement Backlog Quest

Create `docs/quests/backlog/enhance-<feature-name>.md`:

```markdown
# Quest: Enhance [Feature Name] — Advanced Features

**Status:** BACKLOG
**Created:** YYYY-MM-DD
**Priority:** Medium
**Depends On:** [build-feature-name.md](../done/build-feature-name.md) ✅ COMPLETE

## Objective
Complete [Feature Name] with:
- Advanced UI components
- Production deployment
- Full feature set

## Foundation Status ✅
**Already delivered:**
- ✅ Item 1
- ✅ Item 2

**Current state:** X% complete — foundation works, enhancements needed.

## Enhancement Checklist
- [ ] Polish item 1
- [ ] Polish item 2
...

## Estimated Effort
**Total:** Y hours
```

#### Step 4c: Move Quest to Done

```powershell
Move-Item "docs/quests/build-feature.md" "docs/quests/done/build-feature.md"
```

#### Step 4d: Update TODO File

```markdown
**✅ Completed Frontends (N phases):**
- Phase X: **Feature Name** ([subdomain.awizard.dev](http://localhost:PORT)) — Foundation complete ✅

...

**📦 Deferred to Backlog:**
- Advanced features (charts, advanced UI)
- Production deployment
- Full feature set
```

Add completion log entry:

```markdown
## 🏁 Completed

- ✅ **YYYY-MM-DD** — Phase X: Feature Name Foundation ✅ COMPLETE (X%)
  - Quest: [build-feature-name.md](quests/done/build-feature-name.md) moved to done/
  - Foundation delivered: core logic, scaffold, key components
  - Enhancements backlogged: [enhance-feature-name.md](quests/backlog/enhance-feature-name.md)
```

---

## TODO File Phase Tracking

The master TODO file (`docs/TODO_DEFI.md` or `docs/TODO_WORLD.md`) tracks phases:

### Phase Structure

```markdown
### Phase X — Feature Name ✅ STATUS

**Quest:** [docs/quests/done/build-feature.md](quests/done/build-feature.md) ✅
**Enhancements:** [docs/quests/backlog/enhance-feature.md](quests/backlog/enhance-feature.md) (backlog)
**Status:** Foundation delivered (X%), enhancements deferred

**✅ Delivered (Foundation):**
- [x] Core item 1
- [x] Core item 2

**📦 Deferred to Backlog:**
- Enhancement 1
- Enhancement 2
```

### Status Labels

| Label | Meaning | Action |
|-------|---------|--------|
| `✅ COMPLETE` | Foundation delivered | Quest in done/, backlog created |
| `🚧 IN PROGRESS` | Actively working | Quest in active folder |
| `⏸️ BLOCKED` | Waiting on dependency | Quest in active, note blocker |
| `🔮 PLANNED` | Not started yet | Quest in backlog/ |

---

## Best Practices

### ✅ Do This

1. **Ship foundations in 20 minutes**
   - Research → Math → Scaffold → 1 component → Done
   - Example: Bank of Wizards (60% in 20 min)

2. **Create enhancement backlog immediately**
   - While foundation work is fresh in mind
   - Document exactly what's left
   - Estimate effort for future prioritization

3. **Keep active quests minimal (1-2 max)**
   - Prevents context switching
   - Clear what to work on next session

4. **Update TODO after every quest completion**
   - Progress summary
   - Completion log entry
   - Phase status update

5. **Reference related quests**
   - Link foundation quest from enhancement quest
   - Link enhancement quest from completed foundation
   - Cross-reference in TODO file

### ❌ Don't Do This

1. **Don't aim for 100% before moving to done/**
   - You'll never finish
   - Creates multi-week quests
   - Blocks new work

2. **Don't leave quests in active indefinitely**
   - If stuck, move to backlog with blocker note
   - Keep active folder clean

3. **Don't create mega-quests**
   - Break into foundation + enhancements
   - Each quest should be shippable in 1-4 hours

4. **Don't skip the backlog quest**
   - Future you needs to know what's left
   - Creates technical debt visibility

5. **Don't move to done without updating TODO**
   - Completion log is historical record
   - Helps track velocity

---

## Example Workflow Session

**Goal:** Complete Bank of Wizards quest in 20 minutes.

### Minutes 0-5: Assess Foundation Status
```bash
# Check what exists
ls projects/chia-bank/src/components/  # PortfolioOverview.tsx, AssetList.tsx, LpPositionList.tsx ✅
ls projects/chia-bank/src/lib/          # bankAggregator.ts, bankTypes.ts ✅

# What's the foundation?
# ✅ Aggregation engine works
# ✅ Core components render
# ✅ Types defined
# ❌ Charts missing
# ❌ Tabs missing
# ❌ Oracle integration missing
```

**Decision:** Foundation = 60% complete. Ready to ship.

### Minutes 5-10: Update Quest File

Mark completed phases:
```markdown
### Phase 1: Scaffold & Types ✅ COMPLETE
- [x] Copy chia-cfmm → chia-bank
- [x] Update package.json (name, port 5184)
- [x] Create comprehensive types
```

Add completion summary:
```markdown
## ✅ Quest Complete — MVP Delivered
**Delivered:**
- ✅ Portfolio aggregation engine
...
**Remaining work moved to:** [enhance-bank-of-wizards.md](backlog/enhance-bank-of-wizards.md)
```

### Minutes 10-15: Create Enhancement Backlog

Create `docs/quests/backlog/enhance-bank-of-wizards.md`:
```markdown
# Quest: Enhance Bank of Wizards — Advanced Features

**Depends On:** build-bank-of-wizards.md ✅ COMPLETE

## Foundation Status ✅
- ✅ Portfolio aggregation engine
...

## Enhancement Checklist
- [ ] Tab structure (5 tabs)
- [ ] Charts (Recharts)
- [ ] Quick action modals
- [ ] Oracle integration
- [ ] Testnet deployment
```

### Minutes 15-20: Move Files & Update TODO

```powershell
# Move quest to done
Move-Item "docs/quests/backlog/build-bank-of-wizards.md" "docs/quests/done/"

# Update TODO_DEFI.md
```

Update progress summary:
```markdown
**✅ Completed Frontends (6 phases):**
- Phase 6: **Bank of Wizards** — Portfolio aggregation MVP ✅
```

Add completion log:
```markdown
- ✅ **2026-03-06** — Phase 6: Bank of Wizards MVP ✅ FOUNDATION COMPLETE
  - Quest: [build-bank-of-wizards.md](quests/done/build-bank-of-wizards.md)
  - Enhancements backlogged: [enhance-bank-of-wizards.md](quests/backlog/enhance-bank-of-wizards.md)
```

**Result:** Quest complete, TODO updated, backlog documented — all in 20 minutes.

---

## Velocity Metrics

Using this workflow, typical completion velocity:

| Foundation Complexity | Time to Complete | Completion % |
|----------------------|------------------|--------------|
| **Simple** (Scaffold + 1 component) | 10-20 min | 40-50% |
| **Medium** (Math lib + scaffold + 2-3 components) | 20-40 min | 30-60% |
| **Complex** (Research + math + scaffold + 5+ components) | 1-2 hours | 20-40% |

**Key insight:** Even complex quests can ship foundation in 1-2 hours.

**Backlog completion:** Each enhancement quest typically takes 4-12 hours to fully complete later.

**Total time savings:** ~30-50% faster than attempting 100% completion upfront.

---

## Migration: Converting Old Quests

If you have quests sitting at 20% complete for weeks:

### Step 1: Assess Current State
```markdown
# What exists?
- [x] Research done
- [x] Types defined
- [ ] All UI components (only 2/10 done)
- [ ] Deployment
```

### Step 2: Draw the Line
**Foundation = research + types + 2 components.** ✅ Ship it.

### Step 3: Create Enhancement Quest
Document the 8 missing components in `enhance-*.md`.

### Step 4: Move to Done
Original quest → done/, enhancement quest → backlog/.

### Step 5: Celebrate
You just completed a quest that was stalled for weeks. 🎉

---

## Summary: The aWizard Quest Pattern

```
1. Create quest in backlog/ with full spec
2. Move to active when starting work
3. Build foundation (30-60% complete)
   - Research ✅
   - Math/core logic ✅
   - Scaffold ✅
   - Core components ✅
   - README ✅
4. Create enhancement backlog quest
5. Move foundation quest to done/
6. Update TODO with completion log
7. Repeat
```

**Result:** Maximum quest completion velocity, organized backlogs, clear progress tracking.

---

**Pattern established:** 2026-03-06  
**Example quests:** Bank of Wizards (60%), Liquidity Manager (30%)  
**Velocity:** 2 quests completed in 20 minutes each  
**Future work:** 2 enhancement backlogs created (8-12 hours each)

*Ship foundations, backlog polish, maximize velocity* 🧙✨
