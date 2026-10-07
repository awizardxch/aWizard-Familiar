# Chialisp.com rows — audit of four repositories, 2026-10-07

The first run of [`docs/skills/chialisp-audit/spec.md`](skills/chialisp-audit/spec.md): the
checklist the official Chialisp documentation implies, marked PASS / FAIL / not evaluated against
four repositories read at the commits below. One auditor pass per repository, then every finding
re-read at its cited lines by a second pass; the ones marked **re-verified** were additionally
re-executed from a clean scratch copy before being written here. Findings carry the spec's row id
so a reader can go from the claim to the documentation rule it rests on.

**Status: 4 repositories, 34 findings (3 Critical, 4 High, 5 Medium, 9 Low, 13 Info); the seven that the simulator lane can judge (S1, N1, N2, N4, N8, F1, F3) are confirmed on the real mempool manager.**

**Fixed and merged 2026-10-07:** Nightspire-Market N1–N5, N7, N8 in
[awizardxch/Nightspire-Market#12](https://github.com/awizardxch/Nightspire-Market/pull/12)
(N6, N9, N10 left as design decisions); Spellbook S1–S8 in
[awizardxch/Spellbook#109](https://github.com/awizardxch/Spellbook/pull/109) (S4 as a document
amendment). Both PRs carry the simulator suites that show the pre-fix acceptances turning into
pinned refusals. Forge F1 and F2 are fixed in the private monorepo by
[awizardxch/Forge#83](https://github.com/awizardxch/Forge/pull/83) (merged 2026-10-07, main
`055a161`) and F3 by [awizardxch/Forge#86](https://github.com/awizardxch/Forge/pull/86) (main
`399afbf`), both verified below. **Open:** forge-puzzles F4–F8 and forge-ui U2–U7 (U1 fix in a Forge PR, U8 fixed in
Forge#84, U9 in Forge#85), and the public `forge-puzzles` slice until the next sync carries them.
Nothing in any of the four repositories is deployed to mainnet; Forge and Spellbook's Chia lane are
testnet11, Nightspire-Market has no deployment of any kind.

> Repo-resident record, kept here because this repository is the agent's standalone knowledge base.
> Reproduction scripts referenced below were written in the audit session's scratch directory and
> are quoted inline where they matter; the four audited repositories were not modified.
>
> Method: [`skills/clvmPuzzleAudit.md`](skills/clvmPuzzleAudit.md) (how to probe) and
> [`skills/chialisp-audit/spec.md`](skills/chialisp-audit/spec.md) (what the docs say must hold).

| repository | commit | what was audited |
|---|---|---|
| `awizardxch/Spellbook` | `fb21864` | the Chia lane of the wallet daemon: key and address derivation, native offer make/take/cancel, relay, policy |
| `awizardxch/forge-puzzles` | `84ce05c` | the V14 Rue puzzle set and the legacy `.clsp`/`.rue`, drivers, build reproducibility |
| `awizardxch/forge-ui` | `52218f4` | the off-chain surface: API routes, offer handling, CLVM deserialization, quoting mirrors, signing flow |
| `awizardxch/Nightspire-Market` | `e1aba4f` | the Chia HTLC puzzles and their test runner; the relay/worker for offer and bundle handling |

---

## Summary

| id | repository | finding | severity | status |
|---|---|---|---|---|
| S1 | Spellbook | the daemon's "curried" standard puzzle is not the standard curry; every address it derives matches no wallet | **Critical** | confirmed on the simulator |
| S2 | Spellbook | `offer_make` lets the request-token agent choose the payee of the requested leg; the approver never sees it | **Critical** | confirmed (PoC) |
| N1 | Nightspire-Market | HTLC claim has no preimage length bound; the EVM and Solana legs take exactly 32 bytes, so a maker can take the Chia leg and strand the taker | **Critical** when wired | confirmed on the simulator |
| S3 | Spellbook | a crafted offer string crashes the daemon (uncaught `OfferError`) | High | confirmed (PoC) |
| S4 | Spellbook | proposed `forge_swap` signs responder-built spends the daemon does not decode | High | provisional (design) |
| F1 | forge-puzzles | the creation bundle's binding spends are unsigned and separable; a farmer takes every genesis reserve and the fee | High | fixed in Forge#83, refusal verified on the simulator |
| U1 | forge-ui | `POST /api/push-tx` has the host's Sage wallet sign caller-supplied spends | High | fix in Forge PR (route deleted, public-surface check guards it) |
| N2 | Nightspire-Market | claim and refund overlap forever after the timelock; the docs claim they do not | Medium | confirmed on the simulator |
| N3 | Nightspire-Market | `CREATE_COIN` without a hint makes CAT payouts invisible to wallets | Medium | provisional |
| S5 | Spellbook | `offer_delete` on the Sage path makes a live offer uncancellable through the daemon | Medium | provisional |
| F2 | forge-puzzles | untrusted offer puzzle reveals run with no cost cap | Medium | fixed in Forge#83 |
| F3 | forge-puzzles | route-lane payout coin: router fee and trader refund redirectable by a farmer; trader's request untouched | Medium | fixed in Forge#86, refusal verified on the simulator |
| N4, N5, N6 | Nightspire-Market | malleable unused solution fields; test runner overwrites the hex it should compare; classic Chialisp without a sigil | Low | confirmed / provisional |
| S6 | Spellbook | recursive CLVM walker bounded by Python recursion | Low | confirmed |
| F4 | forge-puzzles | two `sha256` derivations where `coinid` belongs | Low | confirmed, fail-closed |
| U2, U3, U4 | forge-ui | multisig board serves offers and partial signatures; backref parser and version-dependent cost cap; one unredacted offer reader | Low | confirmed / provisional |
| U9 | forge-ui | liquidity panel mirrors V12/V13's 1000-mojo locked floor on V14 pools, whose floor is 1 | Low | fix in Forge#85 |
| S7, N7–N10, F5–F8, U5–U8 | all four | documentation contradicted by code, dead announcements, stale comments, logging, test hygiene, a dead swap panel with a fixed 3-decimal input scale | Info | U8 fix in Forge#84 |

Three Critical findings, four High, five Medium. Across the four repositories 61 rows were marked
PASS with a citation each (the per-repository tables below); the rows that could not be evaluated
are listed at the end of each section, most often because the artefact could not be rebuilt from
source on a clean box or because the code the row concerns is not in the repository.

**The row that bit everyone:** something *consistent with itself and wrong against the outside* —
a curry no wallet shares (S1), a bundle whose own suites all pass while a farmer can split it (F1),
an HTLC whose preimage width the other two chains fix and this one does not (N1). None of the three
is visible to a test that compares the system with itself. The spec's toolchain probe step 3, its
A3 row and its A5 row are the three places that compare against the outside; they are the ones to
run first.

---

## Spellbook (`fb21864`)

What is here: no Chialisp source. A Python daemon that derives a BLS key from an Ed25519 root,
hand-rolls CLVM serialisation and `sha256tree`, builds the standard `p2_delegated_puzzle_or_hidden_puzzle`
reveal itself, signs `AGG_SIG_ME`, and makes/takes/cancels native XCH offers through a relay; a Sage
RPC path beside it. Test run on a scratch copy: `2 failed, 666 passed, 1 skipped` — both failures
are stale tests (`tests/test_chia.py:462-470` expect balances `rt_status` now returns only on
request), and `tests/test_message_sign.py` needs `eth-account`, which the `test` extra does not
list.

### S1 — The daemon's "curried" standard puzzle is not the standard curry (Critical, re-verified)

- Status: CONFIRMED. Docs row: **D5** (`standard-transactions`), **B4**, spec toolchain probe step 3.
- Where: `src/spellbook/chia_sign.py:365-394`

```python
def _unwrap_quote(sexpr):
    """(f (q X)) — CLVM's (q X) returns (X); f unwraps to X."""
    return (b"\x05", (_list([b"\x01", sexpr]), b""))
...
    inner = _cons(b"\x04", _cons(_unwrap_quote(synthetic_pk_bytes), _cons(b"\x01", NIL)))
    curried = _cons(b"\x02", _cons(_unwrap_quote(mod), _cons(inner, NIL)))
    return sha256tree(curried)
```

The reveal is `(a (f (q MOD)) (c (f (q PK)) 1))`. It *runs* identically to the canonical curry
`(a (q . MOD) (c (q . PK) 1))` — same conditions, 62 cost units more — but it is a different
program, so its tree hash is a different puzzle hash and a different address. Re-executed against
`chia_rs.tree_hash` for one key:

```
spellbook puzzle_hash_for_synthetic_pk: 614a8f97…56db72
standard curry sha256tree:              da22b403…22f637     (chia_rs agrees with both)
standard curry bytes prefix: ff02ffff01ff02ffff01ff02
spellbook reveal prefix:     ff02ffff05ffff01ffff02ff
```

Every address the daemon prints or serves — `rt_addresses` (`daemon.py:5861-5866`), the relay coin
scan (`_native_relay_coins`, `:2395-2422`), `scripts/make_standard_wallet.py:59-60,92-95` ("RAW
CHIA BLS MASTER KEY — import into Sage … -> testnet11 address"), `install.sh:866-880`,
`ceremony/derive_addresses.py:51,64` — is therefore an address no stock wallet derives from that
key. Consequences: the recovery story the README and the paper backup promise is false (import the
key into Sage, see a different address and a zero balance); the Sage path and the relay path of the
same daemon are two different wallets that cannot see each other's coins; any counterparty or
indexer that computes "the standard puzzle hash for this key" (Forge's wallet-coins-by-pubkeys,
explorers) finds nothing. The existing test only checks determinism (`tests/test_chia_sign.py:117-125`);
no test compares an address against a Sage- or chia-derived vector.

Remediation: build the curry as `(2 (1 . MOD) (4 (1 . PK) 1))`, pin `puzzle_hash_for_synthetic_pk`
to a chia_rs-derived vector in the test suite, and **sweep every existing coin with the old reveal
before shipping** — coins already sitting at the non-standard hashes become unspendable by the fixed
code otherwise.

### S2 — `offer_make` lets the request-token agent choose where the requested XCH is paid; the approver never sees it (Critical)

- Status: CONFIRMED by the auditor with a PoC against a temporary daemon; the cited lines re-read.
  Docs row: **A2**-shaped (the payee is set by the requester, not the authoriser); spec §H.
- Where: `src/spellbook/daemon.py:2712-2740` (`receive_address` is checked only for its bech32
  prefix, then queued as `_receive_ph`), `:5486-5494` (the human-facing queue entry shows
  `offered / requested / fee_mojos / expires_at_second` and sets `"destination": None`),
  `:4342` (policy evaluated with destination `""`), `:4558-4559` (the Sage path forwards
  `receive_address` to `/make_offer` the same way).

An agent holding only the request token submits "offer 1 XCH for 1 XCH" with
`receive_address` pointing at an attacker; the approver sees a fair swap and approves; the signed
`offer1…` pays the requested leg to the attacker, who takes it. With `auto_approve_below`
configured the destination `""` never meets an allowlist and the intent auto-approves
(`policy.py:103-113`). This defeats the two-token split the README names as the product's core
guarantee.

Remediation: require `receive_address` to decode to one of the daemon's own scanned puzzle hashes,
or drop the field and default to `puzzle_hashes[0]`; show the receive address in `_decoded_queue`.

### S3 — A crafted offer string crashes `spellbookd` (High)

- Status: CONFIRMED by the auditor with a PoC; lines re-read. Docs row: **I2 / A5** (untrusted
  CLVM input handling).
- Where: `src/spellbook/daemon.py:2756-2759` — `parse_offer` is wrapped in `except OfferError`,
  the `summarize_offer` call on the next line is not; `handle()` catches only
  `(EvmError, SageError, RelayError, SolanaError, DexError)` (`:648`); `serve()` catches `OSError`
  only (`:5968-5970`).

A well-formed offer whose maker spend creates no settlement output raises
`OfferError("… creates no native settlement output")` out of `summarize_offer`, through `handle`,
and out of `serve`: the daemon exits. Anyone who can submit an `offer_take` with the request token,
or trick the agent into relaying a third-party offer string, stops all signing and approvals.

Remediation: catch `OfferError` around `summarize_offer`; add `OfferError`, `ChiaSignError` and
`RecursionError` to the dispatcher's list; make `serve()` answer `{"ok": false}` on any exception.

### S4 — `forge_swap` (proposed) signs responder-built spends the daemon does not decode (High, provisional)

- Status: PROVISIONAL — design document only, no code. Docs row: **A2**, **H1**, **D2**.
- Where: `docs/FORGE_SWAP.md`, R2 ("The intent is the only decoded view; the spends are opaque")
  and the `forge_swap` proposal ("Approval: returns `{ signature }`"); check T3 requires only that
  the conditions include opcode 63.

The human approves a responder-supplied *intent* while the daemon signs `AGG_SIG_ME` over
responder-supplied *solutions*. Nothing ties the two: the settlement announcement is not recomputed
from the intent's requested leg with the agent's own receive puzzle hash and a nonce over the
agent's input coins. A malicious responder presents an honest intent and spends that pay elsewhere.

Remediation (before the proposal is built): parse each spend with the existing
`chia_offer.parse_conditions`; require exactly the intent's offered amount to `OFFER_MOD_HASH`
plus change to an own puzzle hash, an `ASSERT_PUZZLE_ANNOUNCEMENT` recomputed via the existing
`announcement_for_asset` / `offer_nonce`, and a reveal that hashes to the coin's puzzle hash and is
the daemon's own standard puzzle (after S1 is fixed).

### S5 — `offer_delete` on the Sage path removes the only local record needed to cancel a live offer (Medium, provisional)

- Docs row: **H3** ("it will have to be cancelled on-chain … by spending the coins involved").
- Where: `daemon.py:49-56` lists `offer_delete` among request-token routes; `:5303-5316` calls
  Sage's `delete_offer`, which `chia.py:356-358` correctly documents as "NOT an on-chain cancel";
  `:2265-2283` then refuses `offer_cancel` for an offer Sage no longer shows as open.

An agent can make one of the wallet's own live offers uncancellable through the daemon while the
offer string stays valid in the wild. Route `offer_delete` through the approve token, or refuse it
for maker offers whose status is pending/active.

### S6 — Recursive CLVM (de)serialiser is bounded by Python recursion (Low)

- Docs row: **I2 / A5**. `chia_sign.py:112-126, 153-218`: `deser` of a proper list of ~1000 atoms
  raises `RecursionError`, not `ChiaSignError`. Inside `parse_solutions_bundle` it is caught by a
  broad `except` and becomes a refusal, so this is availability and compatibility (large legitimate
  offers fall through to Sage), not a crash. Backrefs (`0xfe`) are rejected, which is the docs'
  rule. Make the walkers iterative or cap depth with a typed error.

### S7 — Settlement reveal compared by bytes (Info)

- Docs row: **B3**. `chia_offer.py:737` `if spend.puzzle_reveal != OFFER_MOD:` refuses a reveal
  with a legal non-minimal length prefix that has the correct tree hash. Fail-closed, so not
  unsafe; compare `sha256tree(deser(reveal)) == OFFER_MOD_HASH` instead.

### Spellbook — rows that pass

| row | evidence | note |
|---|---|---|
| B1 | `chia_sign.py:487-498` checks 32-byte parent and puzzle hash and `amount >= 0` before `sha256(parent ‖ ph ‖ int_to_bytes(amount))`; relay `streamable.py:316` mirrors it | the CAT1 patch shape |
| B2 | `chia_sign.py:129-138` minimal signed big-endian, `0x80 → 0080` tested (`test_chia_sign.py:196-199`); the taker recomputes announcements from canonical encodings (`chia_offer.py:1258-1269`) | non-canonical maker groups fail closed |
| B4 | `sha256tree` prepends `1`/`2`; module hash reproduces `e9aaa49f…fd52` (`test_module_hash`) | the mirror of the *curry* is the failure (S1) |
| D1 | only `AGG_SIG_ME` is emitted or signed (`chia_sign.py:520-551`); message = `sha256tree((q . conds)) ‖ coin_id ‖ genesis`, genesis pinned per network, wrong-network test present | |
| D2 | `_validate_legs` (`chia_offer.py:953-983`) requires both sides non-empty and positive, so no one-sided offers; cancel is an on-chain spend (`:1324-1356`); signed bundles persist only in the 0600 offer store | |
| D5 (key half) | unhardened path `[12381, 8444, 2, i]` and the synthetic offset verified against 16 chia-puzzle-types vectors (`tests/fixtures/synth_vectors.txt`) | the address half fails (S1) |
| H1 | nonce = tree hash of all maker coin infos sorted by coin id (`offer_nonce`, `:809-821`); payments > 0; announcement = `sha256(OFFER_MOD_HASH ‖ sha256tree((nonce . payments)))` (`:843-857`); taker requires every expected announcement and `settlement total == payments` (`:1206-1210`, `:1258-1269`) | matches the chia-blockchain 2.5.2 construction |
| H2 | ledger stores a digest only (`ledger.py:18-27`); offer store and queue files 0600 (`daemon.py:2331-2353`, `:410-417`); relay logs txid and status only (`server.py:581-585`); no daemon logging of offer strings | the string is returned to requester and approver by design |
| H3 (native) | `offer_cancel` spends a maker coin (`daemon.py:2635-2694`) and always queues for a human | Sage path: S5 |
| I2 | the daemon never evaluates CLVM; `deser` rejects `0xfe`; the relay's `clvm_program_length` is iterative and rejects backrefs (`streamable.py:189-208`) with 2 MB per program and 10k-spend caps; offer decompression capped at 6 MiB (`chia_offer.py:406-429`) | |
| A2 (take/transfer) | `build_standard_spend` refuses when the derived puzzle hash ≠ the coin's (`chia_sign.py:645`); `offer_take` re-parses the immutable offer and compares legs to the approved `_give/_get` (`daemon.py:2599-2607`); txid identity enforced on broadcast | `offer_make` is the exception (S2) |
| policy parity | Chia offers and transfers go through `_run_fund_intent` with `(chain, asset, amount)` legs: per-spend cap, velocity, auto-approve, default-queue (`daemon.py:4333-4350`, `:4438-4460`); approve routes role-gated (`:635-640`); mainnet needs `mainnet_submit_enabled` | destination allowlist is a no-op for offers (S2) |

Not evaluated: every puzzle-side row (A1, A3, C, E, F, G, I1, K) — the only on-chain programs here
are pinned chia-blockchain compiled mods; live Sage and relay behaviour; `relay/test_server.py`
(needs `pytest_asyncio`); the `web/` dashboard (no offer or CLVM handling found);
`docs/HOLDER_REWARD_COIN.md` is an EVM design and none of the Chialisp rows apply to it.

---

## Nightspire-Market (`e1aba4f`)

What is here: two classic-Chialisp HTLC puzzles, `contracts/chia/htlc.clsp` (with an arbiter
branch) and `htlc_noarb.clsp`, sharing `htlc_common.clsp`; a Python runner that compiles them with
`clvm_tools` and drives them with `brun`. They are not wired into anything: the relay marks Chia
offer signatures `UNVERIFIED` (`relay/src/offer_sigs.js:109`), the worker has "no Solana/Chia
legs" (`worker/README.md:114`), and `docs/ARCHITECTURE.md:58` still says the Chia puzzle is "not
started". No deployment anywhere, by the repo's own hard constraints. Toolchain: the pinned
`blspy==2.0.3` does not build on Python 3.13; in a 3.12 venv the suite reports `36/36 passed` and
both committed `.hex` files reproduce byte for byte from source by two compile paths
(`clvm_tools.clvmc` and `run -i contracts/chia … | opc`). The auditor additionally ran the spends
through `chia_rs.get_conditions_from_spendbundle` and `validate_clvm_and_signature` with a real
BLS claim signature (mainnet `AGG_SIG_ME` additional data), which is the offline lane of
`clvmPuzzleAudit.md` Rule 0.5 — the acceptances and refusals quoted below are consensus's, not
`brun`'s.

The password-coin row (**A1**) *passes* here, and it is worth saying why: every branch requires the
right party's `AGG_SIG_ME` over a domain-separated message that names the destination and amount
(`htlc_common.clsp:37-38, 54, 65`), and the destinations are curried. The preimage selects *that*
the coin moves, never *where*. That is the repair the spec prescribes, already in place.

### N1 — The claim branch has no preimage length bound; the EVM and Solana legs require exactly 32 bytes (Critical, when wired)

- Status: CONFIRMED — the puzzle accepted 1-, 31-, 33-, 64- and 1000-byte preimages under both
  `brun` and `chia_rs`; the counterpart widths are explicit types. Docs row: **A5**
  (`attacks-and-countermeasures`: "Bound input sizes — use `strlen`"), cross-chain **A1**.
- Where: `contracts/chia/htlc_common.clsp:50-51`

```chialisp
(defun claim-conditions (hashlock claim-ph claimer-pk fill-id preimage amount)
  (if (= (sha256 preimage) hashlock)
```

against `contracts/evm/src/HTLCEscrow.sol:91` `function withdraw(bytes32 preimage)` and
`contracts/solana/programs/xcm_htlc/src/lib.rs:199` `preimage: [u8; 32]`.

A hashlock reveals nothing about the width of its preimage. The maker, who will be `CLAIMER_PK` on
the Chia leg whenever the offer wants Chia, picks `s` of 33 bytes (or 1), publishes `H = sha256(s)`,
and locks leg A on EVM or Solana with `H`. The taker locks leg B on Chia with the same `H`. The
maker claims the Chia coin with `(0 s AMOUNT)` — accepted. The taker now holds `s`, and
`withdraw(bytes32)` cannot be called with it; leg A refunds to the maker after its timelock. The
taker loses the whole Chia leg, and no off-chain check before the lock can see it coming. The
relay's "iron rule" on offer terms does not inspect preimage width.

Remediation, in the puzzle:

```chialisp
(if (= (strlen preimage) 32)
    (if (= (sha256 preimage) hashlock) (list …) (x))
    (x))
```

and a `run_tests.py` case asserting a 33-byte preimage raises; document `|s| == 32` as the
cross-chain invariant it already is on the other two chains.

### N2 — Claim and refund overlap forever after `TIMELOCK`; the Chia leg has no claim deadline (Medium)

- Status: CONFIRMED (the absence is unambiguous; the race is reasoned). Docs row: **E2**.
- Where: `htlc_common.clsp:52-55` (claim emits 51, 50, 62 only) and `:63` `(list 80 timelock)`;
  contrast `docs/ARCHITECTURE.md:80-82`, which states "at exactly `timelock` only refund is live
  (no overlap window where both branches are callable)" — true of the EVM leg, not of this one.

Both `ASSERT_SECONDS_RELATIVE` (80) and `ASSERT_BEFORE_SECONDS_RELATIVE` (85) are judged against
the previous transaction block, so a complementary pair with the same `TIMELOCK_SECONDS` would make
exactly one branch valid per block. Only the refund half is present. After `birth + TIMELOCK` a
claim and a refund are both valid for the same coin in the same block and the fee decides. With
Chia as the taker's leg, a maker who withholds `s` until the taker's refund is in the mempool can
out-fee it, revealing `s` late and shrinking the taker's remaining window on leg A to
`T1 − T2 − lag`. A standard HTLC race, but one the documentation says does not exist.

Remediation: add `(list 84 timelock)` (`ASSERT_BEFORE_SECONDS_RELATIVE`) to `claim-conditions`. **E1 trade-off:** a relative
`BEFORE` fails on an ephemeral coin, so the lock-and-claim-in-one-bundle shape in
`spend_bundle_template.json:5,19` would stop working; if that shape is wanted, curry an absolute
expiry and use `ASSERT_BEFORE_SECONDS_ABSOLUTE` (opcode 85; the relative form is 84) instead.

### N3 — `CREATE_COIN` carries no hint, so the documented CAT composition creates coins a wallet cannot find (Medium, provisional)

- Docs row: **K6** (`conditions`: Memos and Hinting — "the first memo is exactly 32 bytes long,
  it's used as the hint"). Where: `htlc_common.clsp:53, 64, 90` (three-element `CREATE_COIN`s);
  `contracts/chia/cat_usage.md:17-19` says nothing changes between XCH and CAT use.

For plain XCH the payee scans by puzzle hash and needs no hint. Inside CAT2 the child sits at
`CAT_MOD.curry(tail_hash, inner_ph)` and wallets discover it through the hint. A CAT claim or refund
would settle on chain and show nothing in the recipient's wallet. Emit
`(list 51 claim-ph amount (list claim-ph))` and likewise for refund and each payout; the signed
message does not cover the memo and does not need to, since memos do not enter the coin id.

### N4 — Unconstrained solution fields make valid spends malleable (Low)

- Status: CONFIRMED — `chia_rs` accepted a refund with a 500-byte `PAYLOAD` (cost 19,579,444 →
  25,591,444) and an arbitrate pair `(ph amt "junk")`. Docs row: **A5** ("Constrain unused fields
  … to a known harmless value").
- Where: `htlc.clsp:26` documents `PAYLOAD = () (ignored)` for refund; `htlc_common.clsp:61-66`
  never reads it; `:72-76, 88-92` read only the first two elements of each payout pair.

`AGG_SIG_ME` covers the message, not the solution, so a relayer can rewrite `PAYLOAD` or append to
payout pairs and the spend stays valid under the same signature — a different bundle identity for
mempool purposes and inflated cost at the signer's fee rate. Refuse a non-nil `PAYLOAD` on refund
and assert `(= (r (r (f payouts))) ())` per pair.

### N5 — The test runner overwrites the committed hex, so drift can never be detected (Low)

- Docs row: **K7 / toolchain probe steps 1–2**. Where: `run_tests.py:170`
  `(HERE / f"{variant}.hex").write_text(prog.as_bin().hex() + "\n")`; `:34` imports `chia_rs`,
  which `requirements.txt` does not pin; `:149` runs `brun -x` without `--mempool`/`--strict`;
  `spend_bundle_template.json:25` embeds a third copy of the hex that nothing checks.

Today the hex matches. The suite cannot say so: it rewrites the artefact instead of comparing, so
CI passes with any committed `.hex`. Compile to a temporary path and assert equality with the
committed file; pin `chia_rs`; run `brun --mempool -m 11000000000`; derive the template's reveal at
test time.

### N6 — Classic Chialisp without a sigil: the puzzle hash depends on the compiler version (Low, provisional)

- Docs row: **K7** (`modern-chialisp`). `htlc.clsp:43`, `htlc_noarb.clsp:28` carry no
  `(include *standard-cl-24*)`; `README.md:113` pins `clvm_tools 0.4.10` in prose only. The
  counterparty verifies a puzzle hash on chain, so both parties must either compile with the
  identical toolchain or exchange and pin the hex and tree hash (`d3563f1c…5821b`, `2cc04fae…33cf6`
  at this commit). Adopt the sigil, or make the committed hex the canonical artefact and have every
  builder assert against it (N5).

### N7 — Hashes over concatenated, unchecked solution parts; safety rests on consensus (Info)

- Docs row: **B1 / B2 / B4**. `htlc_common.clsp:75` folds `sha256(acc ‖ ph ‖ amt)` with no width
  check on `ph` and raw `amt` bytes; `:38` likewise for the signature message. Every colliding or
  shifted vector the auditor built was refused downstream by consensus (`InvalidPuzzleHash`,
  `InvalidCoinAmount`, `CoinAmountNegative`), so the arbiter's signature cannot be re-targeted — the
  B1 verdict "sound only when the result meets something consensus commits" holds, narrowly. The
  branch tags `"claim"` / `"refund"` differ at byte 0, so the two messages cannot collide. The
  README's statement that "`sha256tree` is unavailable in this toolchain" (`README.md:142`) is
  wrong: it is a five-line library `defun`, not an operator. Mirror nit: `run_tests.py:107`
  encodes zero as `0x00` where CLVM's canonical zero is the empty atom (`htlc_common.clsp:19` says
  so). Assert `(= (strlen ph) 32)` in `payout-conditions`.

### N8 — No `ASSERT_MY_AMOUNT`; an under-stated `AMOUNT` burns the difference; the docs' "exact-sum" claim is EVM-only (Info)

- Status: CONFIRMED — `AMOUNT = 599999` on a 600000-mojo coin accepted; an empty payout vector
  accepted (whole coin to fees). Where: `htlc.clsp:52-53` enforces `total <= AMOUNT` only, and
  `AMOUNT` is solution-supplied (`README.md:80-84`); `docs/runbooks/audit-prep.md:62-64` says
  "`arbitrate` requires exact-sum payouts (no fee skim)". For claim and refund the signature covers
  `amount`, so under-stating is self-harm; for arbitrate an arbiter-signed under-total vector burns
  the remainder. Add `(list 73 amount)` to all three branches and `(= (payout-total payouts)
  amount)` to arbitrate if parity with EVM is intended; fix the runbook.

### N9 — The announcements are dead weight on the deprecated condition (Info)

- Docs row: **C1 / C3**. `CREATE_PUZZLE_ANNOUNCEMENT` (62) at `htlc_common.clsp:55, 66` and
  `htlc.clsp:56` is asserted by nothing; announcements are not persisted, so an off-chain watcher
  attributing a spend must already run puzzle and solution, at which point the curried `FILL_ID`
  and the `MODE` identify the fill. Cost without information. Drop them, or use `SEND_MESSAGE`
  when a consumer exists.

### N10 — The offer schema cannot curry the puzzle; documentation contradicts the code (Info)

- `venue-api/openapi.yaml:410-411` carries `makerAddr` / `makerRecvAddr` (addresses, i.e. puzzle
  hashes) while `htlc.clsp:10-11` needs 48-byte BLS keys for `CLAIMER_PK` / `REFUNDER_PK`;
  `relay/src/offer_sigs.js:109` says "the offer format carries no BLS pubkey". The Chia leg cannot
  be constructed from an offer without a key exchange no document specifies.
  `docs/runbooks/testnet-pilot.md:49-50` conflates the TAIL with the HTLC inner puzzle
  (`cat_usage.md:11-15` has it right); `docs/ARCHITECTURE.md:3` links a spec not in the repo.

### Nightspire-Market — rows that pass

| row | evidence | note |
|---|---|---|
| A1 | `htlc_common.clsp:54, 65`; `htlc.clsp:54-55` | every branch needs the right party's `AGG_SIG_ME`; destinations curried; a real signature validated end to end with `chia_rs` |
| A2 (partial) | `htlc_common.clsp:53-55` | a claim spend is self-contained; splitting cannot move value; the mutable fields are N4 |
| B2 (amounts) | `chia_rs`: `AMOUNT = 0x000927c0` → `InvalidCoinAmount` | non-canonical amounts refused by consensus, and the signed message would differ anyway |
| B4 | `run_tests.py:122-135` vs `htlc_common.clsp:38, 75` | the Python mirror byte-matches on all three branches; only the zero-encoding nit (N7) |
| C2 | all three puzzles | no hard-coded `ASSERT_*_ANNOUNCEMENT` |
| C4 | `htlc_common.clsp:45` | 32-byte puzzle announcements; the CAT `0xcb` rule is not triggered |
| D1 | grep: no opcode 49 | |
| D2 | `htlc_common.clsp:54` | a leaked claim signature is valid for this coin and this exact outcome only |
| E1 | `htlc_common.clsp:52-55` | the claim branch has no relative or birth assertion, so lock-and-claim in one bundle works; refund's `80` can never sit on an ephemeral coin by construction |
| I1 | `brun -c`: claim 7,973; refund 7,444; arbitrate with 2 payouts 17,961; with 200 payouts 898,525 | linear in payout count; a full claim costs 19.87M with reveal bytes |
| I4 / K7 | `htlc_common.clsp:37-92` | real `defun`s, no inline duplication; three linear passes |
| toolchain 1–2 | `cmp` of regenerated vs committed `.hex` | identical by both compile paths |
| K1 | `run_tests.py:175-180`; `htlc_common.clsp:9-14` | a leaked-symbol test guards the classic "unbound name becomes a string" footgun |
| K2 | `htlc_common.clsp:51, 73, 80, 89`; hex `ff02ffff03…` = `(a (i …) 1)` | lazy `if` throughout; no `all`/`any` |
| K4 | `htlc_common.clsp:56`; `htlc.clsp:53, 58, 66` | `(x)` on every failure path |

Not evaluated: D3–D5 and F (no singletons or standard-transaction code); G and H1 (the CAT
composition and "bridge TAIL" are described, not built); H2/H3/I2 (no Chia offer files or
untrusted-CLVM evaluation exist; the relay's "offers" are JSON terms plus signatures); K3/K5 (no
division or OR'd prefixes); E2 wall-clock drift on testnet11, which the repo itself flags as
validation required (`docs/runbooks/audit-prep.md:23-25`).

---

## forge-puzzles (`84ce05c`)

What is here: the V14 Rue puzzle set (six leaves, the multi-reserve finalizer, the reserve
launcher, the registry, the LP CAT TAIL), two `.clsp` LP inners, CNI's CHIP-0050 puzzles vendored
and pinned, the Python drivers and 30-odd suites. Four external reviews and the repo's own runbook
(`skills/n-asset-pool-audit/SKILL.md`) precede this pass, so what follows is the delta the
chialisp.com rows add. Ran, verbatim: `scripts/revision-fingerprint.py` → `contracts/v14: 89 files`,
`6298777e…147ab4`; `_test_v14_actions.py` `89/89`; `_test_v14_create.py` `22/22`;
`_test_v14_reserves_proved.py` `21/21`; `_test_v14_integrity.py` skipped with exit 2 (no `rue`
compiler on the box, so source→hex reproduction was **not** evaluated); every committed `.hex`
matches its `.hash`, the manifest, the upstream pins, the baked LP-inner hashes and the merkle root
(`BAD = 0`, by an independent pure-Python tree hash). The mempool validator refuses leading-zero
integer atoms in every condition probed, and `coinid` refuses a non-canonical amount outright.

### F1 — The creation bundle's binding spends are unsigned and separable: a farmer takes every genesis reserve and the fee (High, re-verified)

- Status: CONFIRMED against the offline validator (`chia_rs.get_conditions_from_spendbundle`, the
  mempool's own), honest control in the same probe, re-executed from a clean scratch copy. Docs
  row: **A3** (`common_issues`: Spend Bundle Splitting — "unless all of the coin spends in a spend
  bundle are linked together, the spend bundle can be split"), **F3** (the launcher is protected
  only by a *signed* parent asserting its announcement), **A2**.
- Already recorded? No. `_test_v14_create.py:123-135` covers a hostile router rewriting the LP
  payment; `_test_v14_reserves_proved.py` proves `register` refuses a mis-aimed launcher — always
  with the registry spend present. The spec's hostile-router lanes are payout lanes.
- Where: `contracts/forge_v14_create.py:196-211` — the creator's only signed conditions:

```python
conditions = [[CREATE_COIN, SINGLETON_LAUNCHER_HASH, 1, memos] …, [CREATE_COIN, eve_ph, 1]]
conditions.append([CREATE_COIN, drv.RESERVE_LAUNCHER_HASH, xch_reserve])   # V14: the launcher, not the reserve
conditions.append([CREATE_COIN, OFFER_PH, fee])
conditions.append([ASSERT_PUZZLE_ANNOUNCEMENT, lp_payment_announcement(…)])
```

and `contracts/v14/puzzles/forge_reserve_launcher.rue:28-39`, where `created_puzzle_hash` is
solution-supplied and its announcement is asserted only by `forge_registry_register.rue:107`.

The creator's p2 spends emit `AGG_SIG_ME`, five `CREATE_COIN`s and one
`ASSERT_PUZZLE_ANNOUNCEMENT` (observed opcodes `[50, 51, 51, 51, 51, 51, 63]`). The singleton
launcher's announcement, each reserve launcher's `forge-reserve-v14` announcement and the fee
settlement's announcement are asserted only inside the keyless registry singleton spend and its
0-mojo slot spends. Nothing signed asserts the registry's own `forge-registered-v14` announcement
or `ASSERT_CONCURRENT_SPEND` of the registry coin. So the three unsigned spends can be dropped,
each reserve launcher's `created_puzzle_hash` and the fee settlement's payee rewritten, and the
creator's spends kept byte for byte so the aggregate signature still verifies:

```
[control] honest creation bundle validates, cost 337,504,530, 11 spends
[attack] dropped unsigned spends: ['65032a72', '7da4d321', '98e5087b']
[attack] ACCEPTED by the mempool validator, cost 181,484,318
[attack]   XCH to attacker: [('99999999', 100000000), ('99999999', 1000000)]
[attack]   CAT A to attacker (CAT-wrapped p2): [('fbdf1315', 50000)]
[attack]   creator still receives LP: [49999]
[attack]   pool eve singleton still created: True
[attack]   reserve coins the pool's state names exist: [False, False]
```

The attacker takes the genesis reserves and the creation fee; the creator holds LP of a pool whose
`reserve_parents` name coins that were never created, so no finalizer message ever finds a
receiver and the pool is dead. The TAIL's genesis branch does not help: `genesis_pool_puzzle_hash`
(`forge_lp_cat_tail.rue:118`) is read from the eve's unsigned solution, so launcher and eve can be
rewritten consistently. Who can do it: a farmer directly; anyone else only by racing the honest
bundle to a farmer, since RBF requires superset removals. Testnet-only today.

Remediation (composer, Python — the puzzles are not wrong, the bundle is unlinked): add to the
creator's signed conditions in `forge_v14_create.py` an `ASSERT_COIN_ANNOUNCEMENT` of the singleton
launcher (`sha256(launcher_id ‖ tree_hash([pool_ph, 1, [total_lp, eve_id]]))`), one
`ASSERT_COIN_ANNOUNCEMENT` per reserve launcher (`sha256(P_i ‖ reserve_launcher_message(…))`,
emitted from the CAT coin's own conditions for CAT reserves), the fee settlement's
`ASSERT_PUZZLE_ANNOUNCEMENT`, and an `ASSERT_PUZZLE_ANNOUNCEMENT` of the registry's
`forge-registered-v14` so the registry spend is inseparable. Pin it with a `_test_v14_create.py`
case that drops the registry spends and rewrites the launchers, expecting refusal — the "before"
asserted as loudly as the "after" (`clvmPuzzleAudit.md`, test hygiene).

### F2 — Untrusted offer puzzle reveals are executed with no cost cap (Medium)

- Status: CONFIRMED. Docs row: **I2** ("all production `run_program` calls should use
  `MAX_BLOCK_COST_CLVM`"). Not previously recorded: the 2026-09-26 review fixed `_trader_ph`'s
  selection logic, not its evaluation.
- Where: `contracts/forge_v14_offer.py:241`

```python
conditions = Program.from_bytes(bytes(spend.puzzle_reveal)).run(Program.from_bytes(bytes(spend.solution)))
```

chia-blockchain 2.5.6's `Program.run` takes `max_cost=INFINITE_COST`; the maker's spends come from
a user-supplied offer. **Fixed in Forge#83:** `_reveal_conditions` runs the reveal with
`run_with_cost(MAX_REVEAL_COST = 11_000_000_000, …)` and returns `None` past the cap;
`_test_surplus_refund_binding.py` checks the cap and that a reveal past it is `None`, not a hang. `forge_offer.py:263-267` beside it passes `11_000_000_000`. A maker puzzle
that loops stalls the responder in `_asserted_announcements`; the surrounding `except Exception`
never returns. `Program.from_bytes` here uses the non-backref parser, so the deserialiser half of
I2 passes on this path. Use `run_with_cost(11_000_000_000, …)` or
`conditions_dict_for_solution(…, 11_000_000_000)` as the sibling file does.

### F3 — Route-lane payout coin: the router fee and trader refund groups are bound by nothing signed (Medium, confirmed on the simulator)

- Docs row: **A2 / A3**. `contracts/forge_v14_offer.py:300-316` appends `[surplus_ph, fee]` and
  `[back, refund]` to a `(payout_coin.name() . payments)` group that the trader's offer does not
  assert. A farmer can rewrite that group to pay itself the fee and the slippage refund while the
  trader's requested payment stays intact, so the bundle stays valid. Review finding 14 (a
  relayer-prepended requested group) is fixed in `_trader_ph`; this redirection is not recorded.
  Have a signed coin assert the `OFFER_MOD` announcement for the group, or route fee and refund
  through the trader's requested groups, which the maker asserts. Confirmed on the simulator — see Simulator verification.

### F4 — Two coin-id derivations use `sha256` over solution bytes where the repo's own rule says `coinid` (Low, fail-closed)

- Docs row: **B1 / B2** (`common_issues`: Unchecked Hashing — "there is no reason not to use
  [`coinid`]"). `forge_action_common.rue:475`
  `sha256(lp_parent_id + cat_puzzle_hash(…) + (amount as Bytes))` and
  `forge_registry_register.rue:74` `sha256(launcher_parent_id + SINGLETON_LAUNCHER_PUZZLE_HASH +
  (1 as Bytes))`; `forge_action_remove.rue:87` feeds the solution's `burn` in as that `amount`
  with no canonical-encoding check. Both results are only ever used as a message receiver or
  announcement id that consensus must match, so a malformed input names a coin that exists nowhere
  and the spend fails — class 15's "sound only when compared against something committed". The
  other derivations (`common.rue:442`, `registry_common.rue:158`, `finalizer.rue:133,175`) already
  use `coinid`, which hard-rejects wrong widths and non-canonical amounts and is cheaper. Finish
  the job.

### F5 — The "one time in 256" rationale for the announcement prefix is wrong (Info)

- Docs row: **C4**. `docs/FORGE_PUZZLE_V14.md:91-92`, `docs/FORGE_V14_CLVM_PASS.md:252` and
  `forge_action_common.rue:463-464` say a bare 32-byte tree hash would hit CAT2's `0xcb` refusal
  one time in 256. CAT2 refuses an inner `CREATE_COIN_ANNOUNCEMENT` only when it is **33 bytes**
  *and* starts `0xcb` (`cats`: `morph_condition`, confirmed by disassembling `CAT_MOD`). A 32-byte
  hash is never refused. The 49-byte `"forge-reserve-v14" ‖ hash` is fine as a namespace; the
  stated reason is not.

### F6 — Stale comments in shipping sources (Info)

`forge_multi_reserve_finalizer.rue:13` says the reserve id is "derived from the reserve's parent
id (solution)" while `:224-225` reads `old_state.reserve_parents` from the truth;
`forge_lp_cat_tail.rue:24-25` cites `_test_v12_*` suites the repo does not ship.

### F7 — Non-canonical `h` stored raw in state (Info, provisional)

- Docs row: **B2**. `forge_action_common.rue:378` `last_height: h` and `forge_action_dao_fee.rue:47`
  `dao_fee_bps: new_bps` place raw solution atoms in the hashed state. A leading-zero `h` would
  make `tree_hash(state)` diverge from every canonical mirror (`forge_v14_resync.py:143`). The
  mempool validator refuses `ASSERT_HEIGHT_ABSOLUTE` with such an atom, so it cannot be pushed;
  block-mode validation by a farmer was not evaluated. Cheap hardening: store `h` after
  arithmetic.

### F8 — `_test_v14_consensus_timelocks.py` blames an absent V14 build when the blocker is the private V11 control (Info)

Runbook rule 9 asks a failure to say which of two reasons it has; this skip names the wrong one.

### forge-puzzles — rows that pass

| row | evidence | note |
|---|---|---|
| A1 (leaves) | `common.rue:439-458` settlement id via `coinid` + `AssertConcurrentSpend`; `_test_v14_settlement_amount.py`, `_test_v14_action_binding.py` | the composer-side gaps are F1/F3 |
| A5 | `common.rue:144-149` `nth_int` raises past end; `zip_add`/`zip_sub` assert equal length; `add.rue:36` `deposit >= 0`; `coinid` width-checks `settlement_parent` and `reserve_grandparents` | no `strlen` anywhere, as the runbook says; see F4 |
| B1 (`coinid`) | `common.rue:442`, `registry_common.rue:158`, `finalizer.rue:133,175`; opcode 48 in swap/add/register/finalizer disassembly | except F4 |
| B3 | drivers compare `get_tree_hash()` (`forge_v14_resync.py:59,143`); `_test_v14_integrity.py` compares recompiled hex on purpose | |
| B4 | `forge_v14_driver.py:97,131-134` minimal big-endian; `reserve_launcher_message` mirror = `b"forge-reserve-v14" + Program.to([…]).get_tree_hash()` | matches `common.rue:466` |
| C1 | launcher announcement names `eve_coin_id` (`tail.rue:118`, `register.rue:121`); reserve-launcher announcement asserted from a derived id (`registry_common.rue:177`); `_test_v14_genesis.py` | `observe` is a read-only broadcast by design |
| C2 | puzzle-emitted `AssertCoinAnnouncement` only in TAIL genesis (`tail.rue:114`) and `register` (`register.rue:120`), both one-shot against coins in the same bundle | the registry is not bricked by a failed `register` |
| C3 | mode `SENDER_PUZZLE \| RECEIVER_COIN` = 23 in TAIL, dao_fee, finalizer, upstream p2; slot uses 18; messages are 32-byte hashes | sender = singleton puzzle hash, receiver = derived coin id |
| C4 | launcher announcement is 49 bytes; LP inners emit no announcements | F5 for the rationale text |
| D1–D3 | no `AGG_SIG` in any V14 puzzle; `dao_fee` authorised by a mode-23 message | |
| E1 | relative and birth conditions only on the pool singleton (`common.rue:390`), by design (class 13) | settlement, LP eve, melt and launcher coins emit none |
| E2 | `AssertHeightAbsolute h` + `AssertBeforeHeightAbsolute h+window` + `birth > last_height` (`common.rue:363-364, 390-393`) | `_test_v14_consensus_timelocks.py` not runnable here |
| E3 | reserve ids derived from state parents and pre-spend amounts (`finalizer.rue:226`) | |
| F1 | finalizer recreates the singleton at amount 1 (`finalizer.rue:248`); `AssertMyAmount 1` (`common.rue:393`); the only even output is the 0-mojo slot | |
| F4/F5 | reserves are `p2_delegated_by_singleton` receiving mode-23 messages from the singleton's full puzzle hash (`finalizer.rue:168-181`) | the modern form of the puzzle-announcement rule |
| G1–G3 | TAIL: `effective_delta == expected_delta` (`tail.rue:87-88`), `parent_is_cat \|\| expected_delta > 0` (`:85`), genesis requires `!parent_is_cat` (`:110`); `_test_v14_lp_receive_forgery.py`, `_test_v14_genesis.py` | |
| H1 | `register.rue:91-97, 113-116` assert exact notarized payments; nonce = launcher id | |
| H2 | no offer text logged or written; `forge_stdin.py:634` returns the offer to the caller only | |
| I1 | `collect` indices self-bound (`collect.rue:54-55`); vectors forced to length n; `MAX_ASSETS = 10`, weights ≤ 20 bound `pow_int`; measured 185–266M per action, 337.5M creation | |
| K1, K2, K4, K5, K6, K7 | all hex literals carry `0x`; Rue `&&` compiles lazy; divisors provably > 0 (`curve.rue`); indices range-checked (`swap.rue:52-53`, `finalizer.rue:217`); rebuilt reserve `CreateCoin` carries `memos [HINT]` (`finalizer.rue:160-166`) | |
| K8 | suites validate with `chia_rs.get_conditions_from_spendbundle`, not `brun` | |
| toolchain 2–4 | `.hex`/`.hash`/pins/manifest/merkle all reproduce from committed bytes | step 1 (source → hex) needs `rue` 0.8.4 |

Not evaluated: source→hex reproduction and the `defconst` placement question (no `rue`);
`Offer.from_bech32` → chia_rs `SpendBundle` backref policy; F7 under block-mode flags; F2 (eve
proof) and G2 (ring arithmetic), which are upstream `singleton_top_layer_v1_1` / `cat_v2`
behaviour; `_test_v14_consensus_timelocks.py` (needs the private V11 control); F3 was read, not
run.

---

## forge-ui (`52218f4`)

What is here: the Vite/React app, Node serverless routes under `api/`, Python drivers under
`contracts/` (a one-way slice of the monorepo), the quoting mirrors under `src/lib`. Ran, verbatim:
`npm install --legacy-peer-deps` clean; `node ./scripts/run-checks.mjs` with a venv Python → 116
sections, exit 0, including `141/141 relay assemble`, `63/63 relay settle`, and `walletCreate`
("a bundle that validates as a testnet11 mempool would"); with the system Python the same runner
fails on `No module named 'chia_rs'`, which is finding U5. Drift against forge-puzzles: all 19
`contracts/v14/compiled/*.hash`, every `.hex`, `manifest.json`, `pins.json`, the drivers and the
math mirrors byte-identical. Library probes: `Program.from_bytes` accepts `0xfe` back-references
and expands them; a ladder bomb is stopped by chia_rs's allocator after about one second of CPU
("SExp exceeds maximum size"); `Program.run` defaults to `INFINITE_COST`, which is
`11_000_000_000` in the resolved 2.5.6.

### U1 — `POST /api/push-tx` makes the responder host's Sage wallet sign caller-supplied spends (High, provisional)

- Status: PROVISIONAL — exploitable where the responder process can reach a Sage RPC with the
  wallet certificate (operator and developer launches); the hosted container has none, where the
  route degrades to an unauthenticated push relay to the pinned node. Docs row: **D2**
  (signatures produced for untrusted spends), same class as the 2026-09-26 review's finding 01,
  which closed `sage-offers` and did not list this route.
- Where: `api/push-tx.js:24-27, 51` — `const payload = request.body ?? {}` is written straight to
  `contracts/push_spend_bundle.py` with no gate, token or admin check; `push_spend_bundle.py:283-284`
  routes any payload carrying `sign_coin_spends[]` and `full_spend_bundle{}` to
  `sign_and_submit_via_sage`, which calls Sage's `sign_coin_spends` with the process's client
  certificate and submits the result. Nothing in `src/` or the docs references the route.

On a machine running the responder beside Sage (the router wallet that signs a creation), an
attacker lists that wallet's coins through the public `/api/wallet-coins`, builds standard spends
paying themselves, and POSTs them; Sage signs without a prompt. Delete the route (it is dead), or
gate it with `localWalletRoutesEnabled()` + `requireAdmin()` and drop the signing branch; add it
to `publicSurface.check.mjs`.

### U2 — The multisig board serves executed offer text and every partial signature to anyone naming the lock (Low)

- Docs row: **H2** (bearer offer), **D2** (individual signatures persisted and served).
  `api/_multisigIndex.js` `publicProposal` is a plain clone; proposals carry `shares[].signature`
  (96-byte BLS per signer), `spendBundle` and `offer.text` (`api/multisig-execute.js:117,123`,
  `contracts/vault_tool.py:2031-2032`); `GET /api/multisig-proposals?safeId=` returns them all. Ids
  of `public: true` locks are listed by `/api/multisig-safes`. The offer is two-sided and the
  shares are `AGG_SIG_ME` over the lock's own coin id, so this is an information leak, not theft;
  it is still an offer the owners may not mean to publish. Drop `shares[].signature`, `offer.text`
  and `spendBundle` from `publicProposal` unless the request carries an owner proof.

### U3 — Python drivers parse untrusted CLVM with the back-reference parser and run with a version-dependent `INFINITE_COST` (Low)

- Docs row: **I2**. `contracts/parse_offer.py:34` `Offer.from_bech32` on every settle lane;
  `forge_offer_build.py:202,250,375-376` `Program.fromhex` on caller puzzles; `vault_tool.py`
  `spend_from_json` from the unauthenticated `POST /api/multisig-execute { feeSpends }`;
  `forge_v14_offer.py:241`, `forge_names.py:54`, `breadcrumb_proof.py:215` `.run(solution)` on
  chain reveals. chia_rs bounds the bomb at about one second of CPU per crafted offer per lane, and
  `INFINITE_COST` is the block limit in 2.5.6 — but the requirements floor `chia-blockchain>=2.3`
  predates that value, so a different resolution would uncap these calls (not verified). Pass an
  explicit `max_cost` at the five `.run(` sites, prefer `conditions_dict_for_solution(…,
  11_000_000_000)` as `forge_offer.py:263` does, raise the floor or assert the constant, and put a
  small global semaphore on settle children (`_forgeResponder.js` has per-launcher locks only).

### U4 — `router-taker` GET serves raw offer strings outside the create-pool redaction (Low, provisional)

- Docs row: **H2**. `api/router-taker.js:346, 367, 535` read `searchOfferRecords({status:'open'})`
  and return `record.offer` directly; `redactOfferRecordsForPublicRead` is applied only in
  `api/v1/offers/index.js`, and `offerRedaction.check.mjs` exercises only the helper. Open swap
  offers being public is the order-book design; the gap is a create-pool record in status `open`
  (`router-create-pool-taker.js:155` treats `open` as live) whose first assets match the queried
  pair. No code path that writes `open` onto a create-pool record was found, hence provisional. Wrap
  every HTTP read of the index in the redaction and have the check scan route files for
  `searchOfferRecords` / `readOfferIndex` callers — Forge finding 10's rule, "detect over-broadly".

### U5 — The audit response's verification list and `run-checks.mjs` depend on files and interpreters not in this slice (Info)

`docs/FORGE_AUDIT_RESPONSE_2026-09-26.md`'s "Verification" block names `contracts/_test_*.py`
suites that live in forge-puzzles, not here; `scripts/run-checks.mjs` fails on a machine without
`chia_rs` for a reason unrelated to quoting. Point the doc at forge-puzzles; skip, not fail, the
api section when `PYTHON_BIN` lacks `chia_rs`.

### U6 — The browser console logs the wallet's aggregated signature (Info)

- Docs row: **D2** ("presume that all signatures are public" is the docs' stance; the UI should
  still not widen it). `src/lib/walletConnect.ts:2517` logs `aggregated_signature` in production
  builds. Guard with `import.meta.env.DEV` like the debug-capture posts.

### U7 — Owner proof signs an `AGG_SIG_UNSAFE` digest with a ten-minute replay window (Info, recorded)

- Docs row: **D1**. `src/lib/multisig.ts:348-373` signs `sha256("forge-multisig|action|subject|issuedAt")`
  under `(49 key digest)`; `api/_multisigAuth.js` `PROOF_WINDOW_MS = 10 min`. The prefix and
  `issuedAt` are the binding D1 asks for; a captured proof replays only the same idempotent action
  for ten minutes. Documented under review finding 11; acceptable.

### forge-ui — rows that pass

| row | evidence | note |
|---|---|---|
| A3 (bundle integrity) | `forge_v14_create.py:246-258` refuses signed creator spends that differ from the plan, then `drv.validate(bundle)`; maker spends assert settlement announcements; `inAppSettle.ts` `checkBundle` runs every puzzle and checks every assertion in-bundle | the router never pushes a caller's bundle unmodified except the dead route in U1; the composer-side gap is forge-puzzles F1 |
| H1 | `forge_offer_build.py:282-293` uses chia's `Offer.notarize_payments`, `amount <= 0` raises; `trader.ts:99-106` nonce = tree hash of the coins spent sorted by id; `settle.ts` positive amounts | |
| H2 gates | `_gates.js` `localWalletRoutesEnabled`, `requireBearer` (unset = 403), `gateClosed` 404; `publicSurface.check.mjs` green | covers sage-*, debug-capture, deployment-index, admin/* |
| H2 redaction | `_offerIndex.js:231-245` `offer: ''`, `offerRedacted: true`, applied at `api/v1/offers/index.js:398,427,436` | U4 for the one uncovered reader |
| H3 | `MultisigPanel.tsx:3812` "Cancelling means spending the coins the offer was written against"; `multisig-execute.js` marks sibling offers `stale` when their coins are spent | no "delete = cancel" UI |
| D2 (one-sided) | `forge-offer-build.js` and `multisig-proposals.js` `normalizeSide` require positive requested legs; create-pool 1-mojo offers never served | |
| D5 | `api/wallet-coins.js` derives `p2_delegated_puzzle_or_hidden_puzzle` addresses from shared keys; `walletCreate` check proves keys → coins → wallet signature → a validating bundle | the hidden-puzzle path is not exercised |
| I2 (TypeScript) | `relay/clvm.ts:129-166` refuses `0xfe` and trailing bytes, iterative; `clvmRun.ts:78-80` `run_program(…, maxCost)`; `settle.ts:60`, `inAppSettle.ts:135`, `assemble.ts:268` cap at `11_000_000_000`, cumulative in `checkBundle`; `coinid` implemented per clvm_rs | |
| I2 (Python, capped paths) | `forge_v14_driver.py:816`, `forge_fee_estimate.py:123`, `vault_tool.py:1761` `get_conditions_from_spendbundle(…, MAX_BLOCK_COST_CLVM)`; `parse_offer.py:46`, `forge_offer.py:263` `conditions_dict_for_solution(…, 11_000_000_000)`; zlib capped at 6 MiB | the uncapped sites are U3 |
| B4 / parity | `relayV14*` checks pinned to Python-recorded fixtures (141 + 63 + 52 pass); `protocolFeeMirror` expected values from the puzzle suites; `revisionAgreement.check` ties the protocol version across Node, TS and the driver | the live comparator lives in the monorepo |
| drift | every `.hash`, `.hex`, `manifest.json`, `pins.json` identical to forge-puzzles | |
| limits | `nodeUrlPinned.check`, `hostLimits.check` green; `_subprocess.js` 90 s kill; `MAX_CONCURRENT_BUILDS = 2`, 64 coins, 256 KiB reveals | |

Not evaluated: every puzzle-side row (forge-puzzles' section); `sage-app-sdk` and WalletConnect
relay internals; Dexie trust; operator scripts beyond grepping for offer logging; behaviour under
chia-blockchain 2.3.x; `api/admin/*` beyond confirming every handler imports `requireAdmin`;
whether any deployment actually runs the responder beside a Sage wallet, which decides U1's live
severity.

---

### G4 addendum — 1 CAT = 1000 mojos, checked across Forge (2026-10-07, after the main pass)

The one `cats` row the main pass left unevaluated: "Chia Network has made the design decision to
map 1 CAT to 1,000 XCH mojos … the official Chia wallet will not support CATs with a ratio other
than 1:1000." Checked read-only across forge-ui `52218f4` and forge-puzzles `84ce05c`.

**PASS.** Every live path holds the ratio:

| where | evidence |
|---|---|
| unit constants | `src/lib/coinUtils.ts:12` `MOJOS_PER_CAT = 1_000n`, `MOJOS_PER_XCH = 1_000_000_000_000n` |
| CAT and LP display | `formatCatAmount(mojos, decimals = 3)` (`src/lib/cfmm.ts:693`); LP rendered with `LP_DECIMALS = 3` in `LiquidityPanel.tsx` and `poolAnalytics.ts`, and `PoolStats.tsx:88` |
| per-asset decimals | 12 for the native asset, 3 for every CAT, at every source: `createPoolFlow.ts:129,139`, `poolIndexer.ts:1299`, `agent/serverQuote.ts:103`, `offerAssets.ts:71-77`, `RouteBreakdown.tsx:decimalsFor`; no token record in `data/` carries any other value |
| agent API | amounts are mojo strings; pool slots carry `decimals` 12 / 3 (`docs/FORGE_AGENT_API.md:16,104-105`) |
| LP accounting | LP is a CAT: one LP mojo is one XCH mojo of backing (`forge_create_pool.py:296-340`, `createPoolFlow.ts:189-195`); `lpRatio` changes granularity only, is single-asset-vault-only, and is refused on baskets (`_test_lp_ratio.py`) — the ratio to XCH mojos is untouched, so wallets display LP correctly as a 3-decimal CAT |

Three Info-level nits, none a ratio defect:

- **U8 (Info)** `src/components/SwapPanel.tsx:37` parses the typed amount as `parseFloat(x) * 1000`
  regardless of the input asset, so an XCH input would be scaled at 3 decimals instead of 12.
  The component is imported by nothing (dead code since the aggregator-based swap replaced it);
  delete it or scale by the slot's `decimals` as line 167 of the same file already does.
- `MOJOS_PER_CAT` is defined twice (`coinUtils.ts:12`, `types.ts:9`) and `LP_DECIMALS` twice
  (`LiquidityPanel.tsx:64`, `poolAnalytics.ts:23`), with literal `3` beside them in
  `LiquidityPanel.tsx:778,965,1070,1117` and `PoolStats.tsx:88`. All agree today; one exported
  constant would keep them that way.
- Nightspire's `cat_usage.md` composition (now hinted, N3) and Spellbook's native lane (XCH only)
  raise no ratio question.

Both nits are now PRs on the monorepo: [awizardxch/Forge#84](https://github.com/awizardxch/Forge/pull/84)
removes `SwapPanel` (U8); [awizardxch/Forge#85](https://github.com/awizardxch/Forge/pull/85) gives the
unit constants one definition each. Consolidating them surfaced one more finding:

- **U9 (Low)** `LiquidityPanel.tsx` capped withdrawals at `total_lp − 1000` for every pool at
  protocol 13 or later, mirroring V12/V13's `MIN_LOCKED_LP`; V14 (protocol 15) cut the floor to
  `LOCKED_BURN = 1` (`forge_action_common.rue:110`, `forge_v14_driver.py:69`). On V14 pools the
  panel left the last 0.999 LP unwithdrawable through the UI. Mirror drift of a puzzle constant
  (`clvmPuzzleAudit.md` class 7/9); fixed per protocol version in Forge#85's second commit.

## Simulator verification

The simulator lane (`clvmPuzzleAudit.md` Rule 0.5): `chia._tests.util.spend_sim`, the real mempool
manager and coin store, chia-blockchain 2.5.6, with real BLS `AGG_SIG_ME` signatures where a puzzle
asks for one. Every probe below carries its honest control in the same run and pins the refusal
code. The scripts ship in [`docs/chialisp-audit-probes/`](chialisp-audit-probes/); each takes the
path to the audited checkout as its argument and modifies nothing in it.

### Nightspire-Market — `sim_nightspire_htlc.py <path to contracts/chia/htlc.hex>`

```
== control: 32-byte preimage claim; wrong preimage refused
  [ok ] wrong preimage (32 bytes): REFUSED GENERATOR_RUNTIME_ERROR
  [ok ] correct 32-byte preimage: ACCEPTED
== N1: preimage width is unbounded (EVM/Solana legs take exactly 32 bytes)
  [ok ] claim with 1-byte preimage: ACCEPTED
  [ok ] claim with 33-byte preimage: ACCEPTED
  [ok ] claim with 64-byte preimage: ACCEPTED
  [ok ] claim with 1000-byte preimage: ACCEPTED
== N2: claim and refund overlap after TIMELOCK; refund refused before it
  [ok ] refund before timelock: REFUSED ASSERT_SECONDS_RELATIVE_FAILED
  claim after timelock: SUCCESS; refund after timelock: SUCCESS  (both in mempool together)
== N4: refund PAYLOAD is unconstrained; a relayer can rewrite it under the same signature
  [ok ] refund with 500-byte junk PAYLOAD: ACCEPTED
  [ok ] refund with a list PAYLOAD: ACCEPTED
== N8: AMOUNT below the coin's value is accepted; the remainder goes to the farmer
  [ok ] claim with AMOUNT = coin.amount - 12345: ACCEPTED   (12345 mojos became fee)
  [ok ] claim with AMOUNT = coin.amount + 1: REFUSED MINTING_COIN
```

N1, N2, N4 and N8 move from "confirmed offline" to **confirmed on the simulator**. The N2 run is
the one the offline lane could not give: after `pass_time(TIMELOCK + 60)` and a block, a claim on
one HTLC coin and a refund on a sibling coin of the same puzzle sat in the mempool together and
both settled in the next block. The control for E2 also holds: a refund before the timelock is
refused with `ASSERT_SECONDS_RELATIVE_FAILED`, not with a generic runtime error.

### Spellbook — `sim_spellbook_curry.py <path to spellbook/src>`

```
synthetic pk equal to chia-blockchain's: True
spellbook puzzle hash : b101c4876bcec381613a844d5f7596a932c13491fd8df34d2d02f3a84b0ffcdb
standard  puzzle hash : 3cdc48afc736233e5c9739adb28ae7f940d4be38f8904bb4141245e5e522001f
same address: False
[control] daemon reveal spends daemon coin: SUCCESS
[S1] daemon spending a coin at the standard address for its own key: refused by its own builder — coin puzzle hash does not match this key/index
[S1] standard wallet reveal spending the daemon's coin: FAILED WRONG_PUZZLE_HASH
[control] standard wallet reveal spends standard-address coin: SUCCESS
```

S1 is **confirmed on the simulator** in both directions, and the shape of the defect is now
exact: the *key* half agrees with chia-blockchain (the synthetic public key is identical), the
*puzzle* half does not. The daemon's coins are not lost — its own reveal spends them — but a coin
sent to the address a stock wallet derives from the same key is invisible to the daemon's builder,
and a stock wallet's reveal cannot spend the daemon's coin (`WRONG_PUZZLE_HASH`). That is the
recovery failure the finding describes, demonstrated end to end.

### forge-puzzles — F1 and F3

**F1 — `sim_forge_creation_split.py`** (run from the checkout's `contracts/` directory;
builds the pool through the production `forge_v14_create` lane with a keyed
`p2_delegated_puzzle_or_hidden_puzzle` creator and real `AGG_SIG_ME` signatures, a permissive
test CAT issued as the repo's own `_sim_harness` does, and the registry minted as `scripts/sim-v14.py`
does; each phase runs in a fresh simulator):

```
CONTROL: honest creation bundle on a fresh simulator
  bundle has 11 spends (2 creator / 9 router)
  push_tx verdict: SUCCESS  cost 337,504,530
  pool singleton on chain: True
  both reserves on chain:  [True, True]
  registry child on chain: True
ATTACK (full): drop register + slots, redirect reserves + fee to the attacker
  dropped unsigned spends: ['63af391c', 'ae4efe04', 'ab3477cb']
  push_tx verdict: SUCCESS  cost 181,484,318
  XCH coins now at ATTACKER_PH:            [100000000, 1000000]
  CAT(d036c44f) coins at ATTACKER_PH: [50000]
  pool eve singleton created:              True
  creator still receives genesis LP:       [49999]
  reserve coins the pool state names exist: [False, False]
HALF ATTACK: keep register + slots, rewrite ONLY the reserve launcher targets
  push_tx verdict: FAILED / ASSERT_ANNOUNCE_CONSUMED_FAILED
```

F1 is **confirmed on the simulator**, re-run independently of the pass that wrote it. The real
mempool — coin existence, lineage, ephemeral rules and signature verification all enforced —
accepts the full attack and pays the attacker the native reserve, the CAT reserve and the creation
fee, with the creator's two signed spends reused byte for byte under their genuine aggregate
signature. The half attack pins the mechanism: with the registry spend present, rewriting a
launcher's target is refused by `register`'s announcement assertion
(`ASSERT_ANNOUNCE_CONSUMED_FAILED`); drop that spend and nothing else objects.

**Fix verified (Forge#83, main `055a161`).** The creator's XCH spend now asserts, read off the
router spends as built (`announcement_binds` in `forge_v14_create.py`), the singleton launcher's
coin announcement, each reserve launcher's coin announcement (whose message names the created
puzzle hash, so a redirected launcher changes the message), the fee settlement's puzzle
announcement and the registry's own `forge-registered-v14` puzzle announcement. The same probe
against the fixed composer:

```
CONTROL: honest creation bundle on a fresh simulator
  push_tx verdict: SUCCESS  cost 339,830,730
  pool singleton on chain: True   both reserves on chain: [True, True]   registry child on chain: True
ATTACK (full): drop register + slots, redirect reserves + fee to the attacker
  push_tx verdict: FAILED / ASSERT_ANNOUNCE_CONSUMED_FAILED
HALF ATTACK: keep register + slots, rewrite ONLY the reserve launcher targets
  push_tx verdict: FAILED / ASSERT_ANNOUNCE_CONSUMED_FAILED
```

The repo's own `_test_v14_create.py` carries the three farmer variants (drop and redirect, drop
only, redirect only) and reports `29/29`; no puzzle changed, so the revision fingerprint is
unchanged. The before-and-after rule holds: the shipped probe is the one that was accepted on
`84ce05c` and is refused on `055a161`.

One refinement to the finding's description: the attack does not abort the creation. The eve
singleton is still minted and the creator still receives LP, so F1 is a *reserve and fee
redirection that leaves a registered-looking pool with no reserves*, not a denial of creation.
The remediation stands as written — link the creator's signed spends to the registry spend and
to each launcher's announcement.

**F3 — `sim_forge_payout_redirect.py`** (same lane and funding as the repo's `scripts/sim-v14.py`;
a CAT→XCH swap through `forge_v14_offer.settle_swap` with a 300 bps router fee, so the payout coin
carries both a fee group and a refund group; each phase in a fresh simulator):

```
CONTROL  push honest -> status=SUCCESS
  TRADER xch sum=947,710 (want 946,710 + refund 1,000) | ROUTER sum=29,310 | ATTACKER sum=0
ATTACK A  redirect BOTH fee+refund -> ATTACKER (every non-payout spend byte-identical: True)
  push -> status=SUCCESS
  TRADER sum=946,710 | ROUTER sum=0 | ATTACKER sum=30,310
ATTACK B  keep the fee group, redirect ONLY the refund -> ATTACKER
  push -> status=SUCCESS
  TRADER sum=946,710 | ROUTER sum=29,310 | ATTACKER sum=1,000
```

F3 moves from PROVISIONAL to **confirmed on the simulator**, re-run independently. The reading
behind it also held up: the swap leaf asserts only the *input* settlement's announcement
(`forge_action_swap.rue:90-99` emits `settlement_binding(asset_in, …)` and a bare `CreateCoin` of
the payout coin), the trader's offer asserts only its own requested group
(`forge_v14_offer.py:238-252`), and the group with nonce `payout_coin.name()` is asserted by no
spend in the bundle. The payout coin is a `settlement_payments` coin, keyless by design on mainnet
too, so the harness's keyless trader takes nothing away from the result. What is stealable is the
router fee plus the trader's slippage refund, bounded by `fee_bps` and the quote's overage; the
notarized request itself is bound and cannot be moved. Severity raised from Low to **Medium**: it
is a live theft of protocol revenue and of the trader's refund on every route-lane swap, not a
hypothetical.

**Fix verified (Forge#86 "Exact settlement", main `399afbf`).** The lane no longer carves a
fee or refund out of the payout coin. A pool pays exactly what it releases, to exactly the groups
the maker's signed spends assert (`bound_groups`, `exact_payout_solution`); the router's fee on an
XCH output is a requested payment to the router inside the trader's own group, and on an input
leg it is paid by the trader's own spend (`router_fee_paid`). An offer that asks for less than the
release, or omits the fee payment, is refused by the lane itself before anything is built ("quote
again" / "rebuild the offer with the fee payment"). The original probe no longer applies, since
its under-asking offer is refused at the lane; the adapted probe
(`sim_forge_payout_redirect_exact.py`) builds the exact offer and attacks the payout coin's
solution:

```
CONTROL  trader 947,710 + router fee 29,310 in the trader's one group: SUCCESS; paid as asked, attacker 0
ATTACK A redirect the router's fee payment:   FAILED / ASSERT_ANNOUNCE_CONSUMED_FAILED
ATTACK B redirect the trader's payment:        FAILED / ASSERT_ANNOUNCE_CONSUMED_FAILED
ATTACK C add an unsigned group (1 mojo):       FAILED / MINTING_COIN
```

Every mutation leaves every other spend byte-identical, so the refusals are the maker's own
`ASSERT_PUZZLE_ANNOUNCEMENT` over the whole group and the pool's exact release, not a harness
artefact. No puzzle changed.


## What the run says about the spec

- **The password-coin row is the HTLC row.** Nightspire's puzzles pass A1 exactly the way the
  spec prescribes (signature plus curried destination), and fail A5 in the way the spec's DoS page
  predicts (no `strlen` on the preimage) — with a cross-chain consequence the docs page could not
  have named. Keep A1 and A5 adjacent; they are one review question.
- **Unlinked bundles are a composer defect the puzzle rows do not see.** forge-puzzles passes every
  puzzle-side row that four reviews taught it and fails A3 in the Python that assembles the
  creation. The spec's routine step 9 (off-chain pass) earns its place; the finding format's
  "where" must be allowed to name a composer, not only a leaf.
- **"Mirror drift" has a worse cousin: a mirror that is internally consistent and wrong.**
  Spellbook's curry is self-consistent — its own coins spend fine — and matches no wallet on
  earth. Toolchain probe step 3 (curry as the builder does, hash, compare to a *foreign* vector)
  is the only row that catches it. The spec now says so in D5.
- **Fail-closed hashing is still worth naming.** F4 and N7 are both `sha256` over solution bytes
  that consensus happens to rescue. The B1 verdict column already distinguishes the two cases;
  reports should keep writing them down, because the rescue is a property of *where* the value is
  compared, and a refactor can move it.
- **Two of four repositories cannot rebuild their artefacts from source on a clean box** (no `rue`;
  `blspy` does not build on Python 3.13). Toolchain probe step 1 should say what to do then:
  verify bytes against committed hashes, record the gap, and say so in the report — which is what
  both sections above do.
