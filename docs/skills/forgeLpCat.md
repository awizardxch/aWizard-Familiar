# Skill: Forge LP CAT — the pool-controlled TAIL

> The LP CAT handshake as it ships at **V10**. Rewritten 2026-08-27 after the internal audit;
> everything this file previously said about V2 authority coins and the V4 announcement-only
> TAIL described **vulnerable revisions** and has been removed rather than kept as history.
>
> **Testnet only, not externally audited.** Pre-V10 pools are retired and must not be recreated.

---

## Domain

Use this for:

- deriving an LP CAT asset id from a pool launcher id
- the mint and burn handshake between the pool singleton, the TAIL, and the LP coin
- reasoning about who may increase or decrease LP supply
- reviewing a change to the TAIL or either pinned inner

For the pool puzzle itself see `forgePuzzleV10.md`; for the audit method that produced the
current design see `clvmPuzzleAudit.md`.

---

## What the LP CAT is

An ordinary CAT whose TAIL is `forge_lp_cat_tail_FORGE` **curried with
`(launcher_id, protocol_version)`**. The TAIL's tree hash is therefore the asset id, and it is
unique per pool — one pool, one LP asset id, for the life of the pool. Minting more units later
keeps the same asset id.

Supply is governed on chain by the pool singleton. There is no authority key, no admin coin, and
no one-time genesis spend that could be replayed. The V2-era `lp_cat_authority_coin` prototype is
not part of the shipping set and is not created or spent by any current lane.

---

## The three-part lock

Supply moves only when **all three** of these hold. Each was added in response to a separate
finding, and each closes an attack the other two do not.

### 1. The pool derives the action coin's id (stops an impostor *puzzle*)

The pool does not accept an `lp_action_coin_id` from the solution. It rebuilds it:

```
lp_action_coin_id == sha256(lp_parent_id
                            + cat_puzzle_hash(lp_tail_hash, PINNED_INNER)
                            + amount)
```

- on a **remove**, `PINNED_INNER = LP_MELT_INNER_HASH` and `amount` = the burn
- on an **add**, `PINNED_INNER = LP_MINT_INNER_HASH` and `amount` = 1 (the eve)

Through V8 this field was free, checked only `!= 0`, with the link to the pool being a coin
announcement. Any coin running any puzzle can emit any message, so an attacker named a plain coin
they controlled, spent it emitting the acknowledgement, and the pool released reserves with **no
LP destroyed at all**.

### 2. The inner puzzle is pinned (stops a no-op burn)

Binding the id alone is not sufficient. The honest path used a plain `identity` inner, which
imposes no melt — leaving "own the LP, spend it without burning, collect the reserves". The two
pinned inners exist so that binding a coin to their puzzle hash *is* proof of what the coin does.

```clojure
; melt — its whole amount is destroyed, and there is no other path
(mod (lp_tail lp_action) (list (list 51 () -113 lp_tail lp_action)))

; mint — the minted coin plus the TAIL call, nothing else
(mod (settlement_hash amount lp_tail lp_action)
  (list (list 51 settlement_hash amount)
        (list 51 () -113 lp_tail lp_action)))
```

Both are deliberately **unparameterised beyond what the CAT layer already pins**: any extra
argument is another thing a caller could vary, and the security here comes from having nothing to
vary. `lp_tail` cannot be swapped because the coin's puzzle hash commits to the asset id, which
*is* the TAIL's tree hash. On the mint side `settlement_hash` and `amount` are safe to leave
open — the depositor chooses where their own LP lands, the pool independently re-derives the
canonical mint from its invariant and refuses any other figure, and the TAIL checks the delta
against the real CAT ring.

### 3. The TAIL requires a CAT parent on a melt (stops an impostor *coin*)

```
assert parent_is_cat || action.expected_delta > 0;
```

CAT2 lets a coin with no valid lineage be spent when the TAIL authorises it, and for a non-CAT
parent the TAIL scores `amount + delta` rather than `delta`. Without this line an attacker could
`CREATE_COIN` at the melt puzzle hash out of ordinary mojos and pick `delta = -2 * amount` to
make `effective_delta` equal whatever burn the pool asked for — destroying LP that was never
issued while the pool released reserves against it.

A melt destroys supply, so it can only come from a coin that held supply. Minting stays open
because **a genesis eve has no CAT parent by definition** — that is exactly why the branch
exists.

---

## The handshake

Mutual, and neither side can be satisfied by an impostor.

```
pool singleton                                    LP action coin (CAT, pinned inner)
  |                                                        |
  |-- CreateCoinAnnouncement { message } ----------------->|  AssertCoinAnnouncement
  |                                                        |    sha256(pool_coin_id + message)
  |                                                        |
  |<-- AssertCoinAnnouncement -----------------------------|  CreateCoinAnnouncement
  |     sha256(lp_action_coin_id + acknowledgement)        |    { acknowledgement }
```

The TAIL also emits `AssertMyCoinId { coin_id: action.lp_action_coin_id }`, so the coin running
it is the coin the pool named.

### Message format

```
message = tree_hash([
    "forge-lp-action-v3",
    launcher_id,
    current_pool_coin_id,
    lp_action_coin_id,
    effective_delta,
    new_total_lp,
    next_state_root,
])

acknowledgement = tree_hash([message, "lp-ack-v3"])
```

Note it commits to `effective_delta` and `new_total_lp`, not just to "something happened" — the
V4-era gap where the TAIL never compared the CAT delta to the pool-approved `lp_delta` is closed.

### What the TAIL checks, in order

1. `launcher_id != 0`, `protocol_version == PROTOCOL_VERSION` (10)
2. `current_pool_coin_id != 0`, `lp_action_coin_id != 0`, `expected_delta != 0`,
   `new_total_lp >= 0`
3. the coin's own id (from CAT2 truths) equals `action.lp_action_coin_id`, and its amount is
   positive
4. `parent_is_cat || expected_delta > 0`
5. `effective_delta == expected_delta`, where `effective_delta` is `delta` for a CAT parent and
   `amount + delta` for a genesis

The version assert means an LP asset id is pinned to one protocol revision as well as one pool.
Bumping `PROTOCOL_VERSION` changes the TAIL's tree hash and therefore the asset id — a new
revision cannot mint into an existing pool's LP supply.

---

## Mint and burn shapes

```
Add:
  eve coin (1 mojo, wrapped in LP_MINT_INNER, no CAT parent)
  + extra_delta = lp_minted - 1
  = lp_minted LP CAT at the settlement puzzle hash, same asset id

Remove:
  the LP being burned (CAT parent, wrapped in LP_MELT_INNER)
  + extra_delta = -burn
  = no LP CAT output
```

The one mojo on an add is CAT substrate. It does not derive or create a new asset id.

---

## Genesis is creator-trusted, by construction

At pool creation the creator controls both the pool's curried state and the LP supply the TAIL is
told to mint, because the coin authorising that mint is an ordinary coin in their own bundle —
there is no pool yet to authorise it. This is inherent to permissionless creation and was probed
rather than assumed:

- a mismatched state makes the pool **inert** — `AssertMyAmount` fails against the real reserve
  coins — which costs the creator, not the protocol
- burning *all* creator LP returns strictly less than was deposited (the genesis lock:
  `CREATE_COIN ZERO32, 1`, and `burn < total_lp`)

Gating creation to an allowlist or NFT is a product decision on top of this, not a substitute for
it.

---

## Where it lives

Workspace paths — pointers for someone with the monorepo open, not where the knowledge lives
(`projects/` is not published in this repo, so everything needed is above):

| file | purpose |
|---|---|
| `contracts/forge_lp_cat_tail_FORGE.rue` | the TAIL |
| `contracts/forge_lp_melt_inner_FORGE.clsp` | pinned burn inner |
| `contracts/forge_lp_mint_inner_FORGE.clsp` | pinned mint inner |
| `contracts/forge_lp_tail_spend_builder.py` | builds the TAIL spend for both directions |
| `contracts/forge_puzzles.py` | resolves `_FORGE` vs archived revisions; `FORGE_VERSION` |
| `contracts/_test_forge_audit.py` | TAIL probes, including the fabricated-melt case |
| `contracts/_test_forge_lp_binding.py` | id binding **and** the pinned-inner case |
| `contracts/_test_forge_exploit_closed.py` | the V8 drain, accepted then refused |

---

## Rules to carry into any change here

- **Never accept an action coin id from a solution.** Derive it.
- **Never widen a pinned inner.** Its security is that it has nothing to vary.
- **Re-probe the melt path after any TAIL edit** — the fabricated-melt finding was introduced by
  the fix for the unauthenticated burn, and was argued to be impossible before the probe
  disagreed.
- **A hardened TAIL is a new asset id.** Any change to the TAIL changes its tree hash, so
  existing pools keep their old LP asset and a migration means new pools.
