# Skill: FLPCR — Forge Liquidity Pool Campaign Rewards

> Merkl-style incentive campaigns for Forge LP and Chia CATs, on the CHIP-0050 action layer.
> Repo: <https://github.com/awizardxch/forge-campaign> (its own repo; puzzles live there, not in
> `forge-puzzles`). **Simulator-tested, not yet on testnet. Not audited.**
> Source of truth, in that repo: `docs/SPEC.md` (design), `docs/PUZZLES.md` (puzzles as built),
> `docs/API.md` (HTTP), `docs/AGENT_TOOLS.md` (agent tool contracts), `docs/TESTNET.md` (testnet plan),
> `CLAUDE.md` (build, rules, starting point). This file is the summary; the repo wins on any
> disagreement.

---

## Domain

Use this for:

- creating, scoring, claiming or reclaiming an incentive campaign on a Forge pool or a CAT
- the distributor singleton: its leaves, state, emission ceiling, claim slots, delegation slots
- gating or boosting a campaign by NFT collection (minter DID) or CAT holdings; address links
- operator work: posting roots, the dispute window, the guardian's veto
- the agent tools `flpcr.*` and what each one needs signed

Load with `chip0050ActionLayer.md` for the action layer, `clvmPuzzleAudit.md` for any puzzle review,
`forgeMultisig.md` for the guardian and for vault holders, and `sageRpc.md` for signing.

---

## The shape in one paragraph

A creator deposits a reward (XCH or a CAT in a Forge registry pool) on a target: a Forge pool's LP
holders, or a CAT's holders, over `[start, end)` blocks. 3% is the **dev fee**, paid in the create spend
to the Speechless dev multisig (`dev_fee_ph`); the rest is the budget. An off-chain engine scores
holders per block (share of eligible supply; optionally fee-weighted, gated, boosted) and the operator
posts a cumulative claim tree to the **distributor**:
`singleton(action_layer(reserve_finalizer, 8 leaves, state))`, one per reward asset per router. A root
becomes claimable after a dispute window unless the guardian vetoes it. Holders claim whenever they like.
After `end + claim_window` the creator may reclaim everything left; until they do, holders can still claim.

## Rules to carry in your head

- **Leaves:** `init`, `create`, `post_root`, `veto`, `claim`, `reclaim`, `rotate`, `delegate`. The set is
  fixed per distributor.
- **Who can do what:**
  - `create`: our router's message only.
  - `post_root`: the operator (`engine_ph`).
  - `veto` and `rotate`: the guardian.
  - `claim`: the holder, or a delegate the holder granted.
  - `reclaim`: the creator, or the creator's delegate.
  - `delegate`: the holder or creator granting or revoking.

  Nothing anyone else can submit moves funds.
- **Authorization** (`authorize_or_delegate` in `shared.rue`) takes one of three forms:
  - mode 0: `AGG_SIG_ME` by the address's synthetic key, which must curry into the address;
  - mode 1: a mode-23 message `"k" + msg` from a coin at the address (vaults, multisig);
  - mode 2: a delegate's own mode 0 or 1, plus the owner's delegation slot (spent and recreated).

  One hop only: a delegate cannot delegate.
- **Emission ceiling:** a root's per-campaign total must not exceed `budget × elapsed / length` at its
  `end`, totals never fall, and `end ≤ h`. No key can release money faster than the schedule.
- **Claims are cumulative.** Each claim pays `cumulative − claimed`, recorded in a claim slot (a sorted,
  doubly linked list). The ordering assert is what stops a double claim.
- **Deposits are enforced by conservation**, not by a named coin. Conservation is bundle-wide: spare XCH
  anywhere in the bundle can cover a short XCH deposit.
- **The height pin:** every solution starts with `h`; a later action in one spend must name the same `h`.
- **Campaign length:** testnet 16 blocks to 365 days, production 77 blocks (≈24 min) to 365 days. The
  claim window is the creator's choice, at least 2 × `dispute_blocks`.
- **Gates and boosts** live in the params the campaign id commits to; the puzzle reads only
  `time_bps`/`fees_bps`. An NFT collection is identified by its **minter DID**: found by walking the
  DID's own spends, never by metadata or the owner-DID field.
- **Address links** join a wallet's addresses for gates and boosts only. Both sides sign
  (`signMessageByAddress`); payouts stay with the LP address.

## Traps

- **`Clvm.alloc([83, 5])` is a byte string**, not a list; build values with `flpcr/chain/values.py`.
- **A refusal test must fail for its own reason.** Accept only `clvm raise` or a `Simulator error`, and
  authorize hand-built claims, or the probe passes on missing authorization.
- **`State` and `Config` layouts are part of every puzzle hash.** Changing a field re-pins every leaf and
  orphans every launched distributor's puzzles.
- **Upstream puzzles are never edited:** slot-machine@2d37ba1, built with rue 0.8.4 (upstream says 0.9.0;
  0.8.4 reproduces the hashes).
- **Two actions in one spend must not touch the same slot.** A slot created in a spend cannot be spent
  in the same block.

## Evidence

All on the chia-wallet-sdk 0.36.0 simulator:
- 166 tests, XCH and CAT rewards;
- a differential suite (reference model vs puzzles on random scenarios);
- a mutation run in which every assertion is pinned by a test or argued.

The first mutation run, with every test green, found three unpinned asserts that each guarded an attack:
a double claim through slot ordering, early release through a future root, and early reclaim through
the height pin. Same lesson as `forgePuzzleV14.md` §4.

## Still open

- Testnet deployment with real keys.
- The dev multisig address.
- A live engine `Source` and a node adapter for NFTs.
- Checking that Sage produces the claim, link and delegate signatures.
- The distributor registry.
- A second reader.
