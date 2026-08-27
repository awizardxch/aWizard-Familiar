# Skill: Forge Pool Lifecycle & Verification

> What to run, in what order, and what a passing run actually proves — at **V10**.
> Rewritten 2026-08-27. The V2 and V4 flows this file used to describe are gone: those pools are
> retired, their builders are archived, and their guarantees did not hold.
>
> **Testnet only, not externally audited.**

---

## Domain

Use this when the quest touches:

- deploying or bootstrapping a pool on testnet11
- create / add / remove / swap validation
- the routing lanes (multi-hop, split, vault-route)
- the responder, the deployment index, or the offer index
- deciding whether a green test run is evidence

For the puzzle itself see `forgePuzzleV10.md`; for the LP handshake see `forgeLpCat.md`; for how
to write probes see `clvmPuzzleAudit.md`.

---

## The shape of the system

```
wallet (Sage / WalletConnect)          -- signs an Offer, holds the only key
        |
   offer index (.awizard/offer-index.json, local)
        |
   router / responder  api/_forgeResponder.js
        |                 * preflightSnapshot  -> singleton freshness
        |                 * buildTransition    -> python builder, per lane
        |                 * persistSuccessor   -> deployment index
        |
   contracts/forge_stdin.py  build({action, ...})
        |
   pool singleton + reserve coins + LP CAT   (on chain)
```

The router never holds a key and cannot alter what the trader signed. Everything it can do wrong
shows up as a bundle that fails to settle, not as a bundle that steals — with the single
exception of the off-chain offer surface (see below).

---

## Lanes

One builder entry point, dispatching on `action`:

| action | lane | responder export |
|---|---|---|
| `prepare-create`, `create` | pool creation | `router-create-pool-taker.js` |
| `swap`, `add`, `remove` | direct, one pool | `respondToForgeOffer` |
| `multihop-swap` | N pools in sequence | `respondToForgeMultiHopSwap` |
| `split-swap` | branches across pools | `respondToForgeSplitSwap` |
| `vault-route` | swap then redeem at a vault | `respondToForgeVaultRoute` |

A **redemption may end a route but never open one** — it burns LP the route has not acquired
yet. A **wrap leg** (minting a vault's LP mid-route) is a `MODE_ADD` spend and has no settling
lane at all; the quoting adapter must drop precisely those two shapes and nothing more.

`FORGE_PROTOCOL_VERSION` lives in exactly one place (`api/_forgeVersion.js`) and is imported by
every gate, so a listed pool is always an actionable one.

---

## Guardrails that must never be bypassed

**Singleton freshness before every transition.** `preflightSnapshot` confirms the pool coin is
unspent, its puzzle hash matches, and there is no pending mempool spend
(`get_mempool_items_by_coin_name`). Never build or broadcast from a client-cached or unsynced
snapshot.

**Successor state comes only from the builder's own output.** `persistSuccessor` writes the
deterministic snapshot the builder returned. There is no chain-sync path that reconstructs pool
state — the V2-era `sync_pool_from_chain.py` is archived and was removed from `api/pools.js`,
where it had been failing with `ENOENT`, being caught, and reporting `success: true` while doing
nothing.

**The snapshot round trip is load-bearing.** `persistSuccessor` writes `_pool_json(successor)`;
`findForgePool` hands that same field back to `_pool()` on the next action. Config is positional
and V8 inserted two fields at indices 5 and 6, so a reader indexing past them silently returned a
neighbour — **every V10 pool worked exactly once, then failed for good**. Trailing config fields
are now indexed from the END. Any change to the config shape means re-checking this path first.

**Revision filtering runs in both directions.** `normalizeDeploymentIndex` drops any batch that
is not the shipping revision on the way IN as well as OUT — the frontend keeps its own copy of
the index in localStorage and POSTs it back on load, which resurrected seven retired pools on the
next page view. `/api/pools?anchor=<launcher>` needs the same filter as the list endpoint, and no
launcher may be hard-coded as always-allowed.

**Creation offers are bearer instruments.** An all-CAT pool creation manufactures a one-mojo
request that reads, standalone, as "pay one mojo, take the whole genesis reserve".
`redactOfferRecordForPublicRead` blanks them at the HTTP boundary — detection is deliberately
over-broad (source *or* id prefix *or* status) and permanent. Never log one, never mirror it to a
public venue, never render it with a copy button.

---

## The verification surface

### Contract suites — `cd projects/chia-cfmm/contracts`

| suite | what it proves |
|---|---|
| `_test_forge_integrity.py` | every source compiles to the shipped hex, matches the pool's baked constants, agrees with the manifest, byte-identical to its archived snapshot |
| `_test_forge_audit.py` | LP TAIL probes, including the fabricated-melt case |
| `_test_forge_lp_binding.py` | the derived action-coin id **and** the pinned inner |
| `_test_forge_reserve_binding.py` | each of V10's three reserve mechanisms, separately |
| `_test_forge_exploit_closed.py` | the V8 drain: accepted there, refused at the shipping revision |
| `_test_forge_pool_audit.py` | 21 probes — curve bracket, protocol fee, config validation, accounting |
| `_test_forge_payout_audit.py` | 20 probes — `trader + protocol + router == released`, hostile router capped at the surplus |
| `_test_forge_isolation_audit.py` | a hostile pool claiming a victim's reserve coins is refused |
| `_test_forge_mint_parity.py` | builder maths pinned to the puzzle's own numbers |
| `_test_forge_routing.py` | multi-hop, split, vault-crossing build and audit clean; over-asking and pool reuse refused |
| `_test_forge_creation_audit.py` | 12 malformed creations refused; lineage; creator cannot withdraw more than deposited |
| `_test_forge_cycles.py` | balancing cycles including vault-crossing; over-redemption dies inside the vault's own spend |
| `_test_forge_stdin_path.py` | the responder lane, and two successive persist round trips |
| `_test_forge_launch_matrix.py` | every planned pool deploys through the real creation path before any coins are spent |

Locally 28 suites pass and 6 skip. In a published checkout — which excludes
`contracts/development/` — 13 pass and 21 skip, because the superseded-revision suites have no
puzzles to load.

**A skip exits 2, never 0.** A run that exercises nothing must not report success. If a count
looks healthy, check the skip count before believing it.

### Frontend and API checks — `cd projects/chia-cfmm`

```bash
node ./scripts/run-checks.mjs
```

Bundles every `src/lib/__checks__/*.check.ts` with esbuild and runs it under node — no test
runner needed — then runs `api/__checks__/*.check.mjs` directly. `mintParity.check.ts` pins the
TypeScript quote to the same table as `_test_forge_mint_parity.py`, and
`offerRedaction.check.mjs` covers the HTTP boundary. Also:

```bash
npx tsc --noEmit
```

### What a green run does *not* prove

- **A suite pinned to live chain state covers that revision only.** The vault suites passed
  throughout a finding that made every vault route unbuildable, because the pools they load were
  three revisions old.
- **Symmetry hides arithmetic bugs.** Equal weights hide the exponent, a balanced deposit hides
  the imbalance-fee share, a V7 vault hides the vault branch. Probe the asymmetric shape.
- **In-memory fixtures skip the round trip** production performs between every pair of actions.

---

## Environmental failures come first

A failed live run is more often infrastructure than contract logic. Check in this order:

1. Sage may be synced locally while lacking peers for transaction submission
   (`contracts/check_sage_rpc_status.py`).
2. If a new LP CAT asset never lands in the wallet, any validation depending on LP preview spends
   cannot proceed truthfully.
3. Mempool contention on the pool coin — a second action on the same launcher is serialised by
   the responder, not queued indefinitely.

Only after those, change contract logic.

---

## What not to freeze as durable knowledge

Keep these in code, manifests, or quest notes — they churn and a stale copy here is worse than
nothing:

- specific launcher ids and pool tables (the index was cleared and rebuilt on V10)
- puzzle tree hashes (`_test_forge_integrity.py` is the authority)
- one-off manifest files, debug payloads, dry-run artifacts
- transient Sage or mempool failures

The durable parts are the guardrails, the lane map, and the meaning of a passing run.
