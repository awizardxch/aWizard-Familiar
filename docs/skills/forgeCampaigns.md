# Skill: FLPCR — Forge Liquidity Pool Campaign Rewards (🪎)

> Merkl-style reward campaigns for Forge LP, CAT and NFT holders, on the CHIP-0050 action layer.
> Repo: <https://github.com/awizardxch/forge-campaign> (puzzles live there, not in `forge-puzzles`).
> **On testnet11 (five distributors, all on older pins), not on mainnet, no external review yet.**
> The puzzles were re-pinned on 2026-11-09 (NEW-1 to NEW-4, FLPCR-08): testnet needs a new distributor.
>
> **Source of truth, in that repo:**
> - `CLAUDE.md` (build, rules, decisions; read first);
> - `docs/SPEC.md` (design) and `docs/PUZZLES.md` (leaves as built);
> - `docs/TESTNET.md` (what ran where);
> - `docs/AGENT_TOOLS.md` (agent tool contracts);
> - `docs/FORGE_SITE_TAB.md` (the forge.awizard.dev 🪎 tab);
> - `docs/SAGE_CHECKS.md` (what still needs a real wallet);
> - `reviews/2026-10-19/FINDINGS.md` (the pre-testnet review and its status).
>
> This file is a summary. Where it and the repo disagree, the repo is right.

---

## Domain

Use this for:

- creating, scoring, claiming or reclaiming a campaign, and disputing or resolving a root;
- the distributor singleton: its ten leaves, state, emission ceiling, claim and delegation slots, the bond;
- NFT campaigns and gates (minter DID or `col1` collection), excluded addresses, address links;
- the hosted service: operator, claim sequencer, create intake, watcher, HTTP API;
- the forge.awizard.dev 🪎 tab and the `flpcr.*` agent tools.

Load it with:
- `chip0050ActionLayer.md` for the action layer;
- `forgePuzzleV16.md` for the pools campaigns target;
- `clvmPuzzleAudit.md` for any puzzle review;
- `forgeMultisig.md` for the guardian, the admin and lock holders;
- `sageRpc.md` for signing.

---

## The shape in one paragraph

**Creating.** A creator escrows a reward (XCH, or a CAT in a Forge registry pool) for a target:
- `LP_HOLD`: holders of a **Forge V16 (or newer) pool's** LP;
- `CAT_HOLD`: holders of a CAT;
- `NFT_HOLD`: holders of an NFT collection.

Each campaign covers the blocks `[start, end)`. 3% is the dev fee, paid in the create spend to the dev
multisig; the rest is the budget, emitted equally every day.

**Scoring and claiming.**
- An off-chain engine scores past holdings, time-averaged, so a flash position earns about nothing.
- An operator posts a cumulative claim root to the distributor:
  `singleton(action_layer(reserve_finalizer, 10 leaves, state))`, one per reward asset.
- A root becomes claimable after the dispute window, unless someone opens a bonded dispute or the guardian
  vetoes it.
- Holders claim whenever they like.
- After `end + claim_window`, the creator, the creator's delegate or the admin may reclaim what is left,
  always paid to the creator. Until then, holders can still claim.

## Rules to carry in your head

- **Leaves:** `init`, `create`, `post_root`, `veto`, `claim`, `reclaim`, `rotate`, `delegate`, `dispute`,
  `resolve`. There is also a bond launcher, a plain coin puzzle compiled and pinned beside them.
  `flpcr/leaves.py` is the one list, and its order fixes every puzzle hash.
- **Who can do what:**
  - `create`: our router's message **and** the creator's own coin spend sending `"k" + id` (mode 23).
  - `post_root`: the operator.
  - `veto`: the guardian, and never while a dispute is open.
  - `dispute`: anyone, with a bond in XCH (production 5 XCH, testnet 0.1). The disputer's own coin
    creates the bond launcher, curried with the bond's destination, the distributor, the refund address
    and the pending Merkle root; it creates the bond only on the `dispute` leaf's message. That funding
    spend must also `ASSERT_CONCURRENT_SPEND` every id in `Prepared.concurrent` (the singleton coin), or
    it can be lifted out of the bundle. The guardian or the admin resolves it. If upheld, the root is revoked and the bond refunded. If rejected, the bond goes to the
    dev multisig and the window restarts.
  - `rotate`: the guardian proposes, it takes effect `rotate_delay` later (production one day, testnet
    24 blocks), and the admin can cancel it.
  - `claim`: the holder, or a delegate the holder granted.
  - `reclaim`: the creator, the creator's delegate, or the admin; refused while a dispute is open or
    while the pending root raises the campaign's total.
  - `delegate`: the owner grants or revokes, and each costs `delegate_fee`.
  - The admin (the dev multisig) can never take funds.
- **Claims name no generation.** A claim is authorized by `AUTH_SIGNATURE`, `AUTH_MESSAGE` or
  `AUTH_DELEGATE` (whose delegate uses either of the first two):
  - `AUTH_SIGNATURE`: `AGG_SIG_UNSAFE` of the leaf by the address's synthetic key, with no coin needed.
  - `AUTH_MESSAGE`: a coin at the address sends `"k" + leaf` in mode 16; this is how locks and vaults
    claim.

  So the sequencer packs many claims into one bundle across chained generations. A replay pays nothing,
  and the payout always goes to the leaf's puzzle hash. Every other action uses mode 23 or
  `AGG_SIG_ME`, bound to the current singleton coin.
- **Emission ceiling:** a root's per-campaign total is at most `budget × elapsed / length` at its `end`.
  Totals never fall, and `end ≤ h`. No key can release money faster than the schedule.
- **Timing:**
  - the dispute window counts from `h + 32`;
  - `start` runs from `h + 32` to `h + max_campaign_length`;
  - campaign length: testnet from 16 blocks, production from 77, at most 365 days;
  - the claim window floor is `4 × (dispute_blocks + 32)` (testnet 160, production 280).
- **Exclusions:** the burn address `0x…dead` never earns. A creator may exclude up to 16 addresses; they are
  stored as a tree hash, and the claim leaf refuses them.
- **NFT collections:** a collection is identified by its minter DID, or by a `col1` id, which is
  `sha256(DID hex + metadata collection.id)`. An NFT counts only if the DID minted it **and** its
  hash-checked metadata names the collection. Membership is proven from the DID's own spends (it created the
  launcher, or announced it in the eve's block), never from the owner-DID field alone.
- **Pools:** Forge V16 and newer only (owner, 2026-11-09). V15 and V14 pools are not supported, even
  while they stay live.

## Traps

- **A slot this spend creates can be spent in the same bundle**, ephemerally. A slot proof must never be
  satisfiable by the spend's own output. The 2026-10-19 review (FLPCR-02) found exactly this in the old
  delegation slots. The fix is a delegation slot list with a use counter.
- **Equal outputs collide.** `Distributor.prepare` raises `BundleCollision` when two actions in one spend
  would touch the same slot or pay the same `(puzzle hash, amount)`. Claims go through
  `Distributor.sequence` instead, which splits them for you.
- **A refusal test must be refused for its own reason.** Every puzzle refusal is the same `clvm raise`, so
  only the mutation run tells which assertion fired. Consensus refusals name their rule, and the tests pin
  those names.
- **`State` and `Config` layouts are part of every puzzle hash.** A leaf change is a re-pin, and
  distributors already launched keep their old puzzles. To spend an old testnet distributor, rebuild its
  exact leaves and set `FLPCR_COMPILED`.
- **`Clvm.alloc([83, 5])` is a byte string**, not a list. Build values with `flpcr/chain/values.py`.
- **Never run two scripts against one distributor state file.**
- **The creator's create message is mode 23**, so a signed create goes stale when anything else spends the
  singleton. The service's create intake holds a short lease on the next generation for it.

## Where things run

- **Testnet11:** five distributors (`docs/TESTNET.md` §5) proved:
  - campaigns end to end;
  - disputes both ways;
  - generation-free claims;
  - excluded addresses;
  - NFT and `col1` campaigns.

  `scripts/deploy_testnet.py` drives them through the local Sage RPC. Its commands are `launch`,
  `create`, `post`, `claim`, `claim-all`, `reclaim`, `delegate`, `dispute`, `resolve`, `rotate --to`,
  `status` and `resync`.
- **Service** (`flpcr/service/`, Dockerfile, to be hosted on Hetzner beside the Forge routers):
  - boots by resync;
  - serves `GET /api/v1/status` and `GET /api/v1/claimable/<address>`;
  - takes `POST /api/v1/claims` (the sequencer).

  - `POST /api/v1/campaigns/quote` and `/create` (the create intake), and `GET /api/v1/watch`.

  It holds the operator key; the router key lives with the create intake. The guardian and the admin
  stay multisigs.
- **Site:** a 🪎 tab on forge.awizard.dev (`awizardxch/forge-ui`), planned in `docs/FORGE_SITE_TAB.md`.
  - The claim flow is one `chip0002_signCoinSpends` over a stand-in spend `(q . ((49 pk leaf) ...))` plus
    one fee spend.
  - `fixtures/vectors.json` is what the TypeScript mirrors check against.

## Still open (2026-11-09)

- **Sage and real-chain checks** (`docs/SAGE_CHECKS.md`):
  - signatures over WalletConnect;
  - CAT rewards live;
  - a lock claim;
  - the hosted service, and rotating the operator to it.
  - a new distributor on the 2026-11-09 pins, and a dispute both ways on it;
  - a fee-weighted V16 campaign, the watcher and the create intake, live.
- **Built on 2026-11-09, simulator only:** V16 fee events, the watcher, the create intake (quote, lease,
  router co-sign), manifests, following foreign singleton spends, and the review probes rerun on the
  current pins (all ok; 476 tests).
- **Owner decisions:** the 160/280 floor, CAT/CAT fee valuation, `RouterRules` values, where the router
  key lives, who pays the create network fee.
- **The site tab itself**, in forge-ui.
- **Not built yet:** the distributor registry, cost under load on the current pins, the guardian as a
  Forge multisig safe, an external review, and mainnet.
