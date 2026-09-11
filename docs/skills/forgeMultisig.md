# Skill: Forge Multisig — M-of-N safes on CNI's `p2_m_of_n_delegate_direct`

> Added 2026-09-03, during the pause for feedback on the pool protocol. **Testnet only, not
> externally audited.** The puzzle is Chia Network's, unchanged; Forge owns the coordination
> service, the signing flow, and the UI.

---

In the UI the feature is only the lock emoji (tab `🔐`) and a safe is a "lock" (constant `SIGIL`
in `MultisigPanel.tsx`: 🔒 watching, 🔐 yours, 🔓 inside yours); code, registry and memo tags keep "safe".

## Domain

Use this for:

- how a Forge safe address is derived, and why it cannot be rekeyed in place
- the propose → sign → execute flow and what each side actually signs
- reviewing or extending `contracts/multisig_tool.py` and the `api/multisig-*` routes
- the replay guard (`ASSERT_MY_COIN_ID`) and the signing-view trick for selectors
- what Sage signs for over WalletConnect, and why "your signer key" is `wallet.publicKey`

Source of truth: [FORGE_MULTISIG.md](../../projects/chia-cfmm/docs/FORGE_MULTISIG.md).
For the audit method see `clvmPuzzleAudit.md`; for Sage's RPC and partial signing see `sageRpc.md`.

---

## The puzzle in one paragraph

`p2_m_of_n_delegate_direct` (mod hash `0f199d52…1504457`, in `chia_puzzles_py`) is curried
with `(M, pubkeys)` and solved with `(selectors, delegated_puzzle, delegated_solution)`. It
asserts exactly `M` selectors are set, emits `AGG_SIG_UNSAFE(key, sha256tree(delegated_puzzle))`
for each selected key, then runs the delegated puzzle. The safe address is the curried puzzle's
tree hash; CATs held by the safe use it as the inner puzzle.

## The two facts that shape everything

1. **The signed message is only the delegated puzzle hash.** No coin id, no genesis challenge.
   Every delegated puzzle Forge builds therefore contains `ASSERT_MY_COIN_ID`; without it a
   signature would replay against every coin the safe ever holds. `validate_bundle` refuses
   any plan whose spends do not pin their coin. Consequence: a proposal dies when its coins
   move, which is also how a fully-signed proposal is cancelled (pay the safe to itself).
2. **Selectors are in the solution and M is exact.** The signer set is fixed at assembly, not
   proposal. Each owner gets a *signing view* — selectors set to them plus the first `M−1`
   others — signs via `chip0002_signCoinSpends` with `partial: true`, and the service proves
   which keys the returned aggregate covers by `aggregate_verify` over subsets. At execution
   the service picks disjoint shares totalling exactly `M`, rewrites the selectors, aggregates,
   re-runs every puzzle, verifies, pushes.

## What Sage signs for

Its derivations' synthetic keys and the master key (`sign.rs`: unknown key → skip when
`partial`, else `UnknownPublicKey`). `chip0002_getPublicKeys` returns derivation keys, so the
first key a wallet reports is one it will sign with. Forge already used this partial path for
the V4/V5 launch guard. The standard puzzle for that same key is the owner's own wallet
address; `derive` returns it per owner and the safe record stores it (`owners[].address`).

`chip0002_getPublicKeys` is now a *required* method in `connectWallet`; older sessions report no
key, and the tab falls back to `/api/multisig-signer-key` (local Sage RPC, derivation 0) with a
Reconnect button. Verified live: Sage's address for derivation 0 == the tool's derived address.

Gotcha: names and labels may carry emoji. `runPythonJson` sets `PYTHONIOENCODING=utf-8` and the
tools reconfigure stdin/stdout to UTF-8 themselves; without that a Windows Python decodes the
pipe in cp1252 and an emoji becomes a lone surrogate ("surrogates not allowed"). `clean_text`
also drops stray surrogates so a bad byte can never poison a record. Never write a file with a
plain `open(p, 'w')` from a script whose string may hold surrogates — the write truncates first.

Gotcha: `local-test-host.mjs` cache-busts only the route module per request, not what it
imports — after editing `api/_multisigIndex.js` or `_multisigTool.js`, restart the host.

## The on-chain profile

Which safes a key owns or watches is **not** stored by Forge. It is a 1-mojo coin sent to the
signer's own address with memos: `[hint, "forge-multisig-profile/1", "<name>|<m>|<label>=<pk>;…"…]`.
Newest 1-mojo coin with the tag wins; reading runs the parent spend's puzzle to recover memos
(the consensus condition parser drops them). Publishing builds a standard-puzzle spend from the
wallet's own coins (`chip0002_getAssetCoins` gives the reveals) and the wallet signs in full.
A safe describes itself with a **manifest**: a 1-mojo coin at its own address tagged
`forge-multisig-safe/1` carrying `name|m|owners`; accepted only if the policy hashes to that
address (self-verifying, forgeries skipped). With one, a profile entry is just `"<display name>|<ph>"`
and "Observe safe" needs only the address; without one the manual owners form is the fallback.
`contracts/multisig_profile.py` (`read`, `build-publish`, `manifest-read`, `manifest-build`),
`api/multisig-profile.js`, `api/multisig-manifest.js`. The list's "Mine" = owned (registry) ∪
profile; "Publish to chain" writes the draft; the safe page offers "Publish manifest". Creating a
safe with a wallet connected is one spend posting manifest + profile together (`build-publish`
with `manifest`); the creator is the implicit first owner and a solo safe is 1 of 1.

Co-owners are entered by address. A Chia address is a puzzle hash, so no key can be derived from
it; `key-for-address` instead finds any spend from the address and reads the synthetic key out of
the standard puzzle's reveal (verified against the hash). A profile publish is such a spend.

Re-key is a **vote**, not a unilateral mint: the 🗝️+ control builds a proposal on the current lock
(`propose` with `successor`) that pays all XCH and CATs to the successor policy's address and creates
the successor's 1-mojo manifest coin in the same spend (outputs addressed `"successor"` are resolved
by the builder). The proposer signs in Sage at once; others sign yes or reject (`/api/multisig-reject`);
reaching M auto-executes; a rejection that leaves fewer than M able to sign marks it `rejected`.
On confirmation the refresh route stamps the successor's manifest from chain. The proposer's wallet
**sponsors** the re-key: a standard-puzzle coin of theirs (AGG_SIG_ME, message + coin id + genesis
challenge, `AGG_SIG_ME_DATA`) pays the fee and the manifest mojo, cross-linked by announcements to
the lock's primary spend; shares may carry the sponsor key, which never counts towards M.

## Vault locks (current)

New locks use CNI's vault puzzles via `contracts/vault_tool.py` (same command shape; routes pick the
tool by `safe.puzzle`). Singleton with `delegated_puzzle_feeder(m_of_n(M, merkle root of bls_member
leaves))`; funds in `p2_singleton_via_delegated_puzzle` coins at a **fixed deposit address**; payment =
singleton spend announcing `sha256tree([funds_id, funds_dph])` + funds spends; re-key = singleton
recreated with the new inner hash + policy memo (`forge-vault/1`), nothing moves; launch plants a
pointer coin at the deposit address naming the launcher; `read` walks the lineage for the policy
history. Signatures are `AGG_SIG_ME(owner, dph)` + singleton coin id + genesis. Legacy
`p2_m_of_n_delegate_direct` locks still work; their re-key moves funds. The mock node now runs
pushed bundles through `contracts/mock_apply.py`, so lineages read in a dry run.

## Direction: the custody layer under vault actions (planned, 2026-09-05)

Not yet built. The intent is for a vault lock to become the **shared custody layer** other Forge
features hold assets in — an LP position, a future Liquidity Manager strategy balance, a treasury
— instead of each feature inventing its own authorization path or sitting behind a raw wallet key.

The claimed advantage holds even at **M = 1** (a single-signer safe), because the win isn't "more
signers," it's what the vault puzzle already gives any owner count:

- **Address-stable rekey.** A vault lock's re-key recreates the singleton with a new inner hash at
  the *same* deposit address (see "Vault locks (current)" above) — nothing moves. A raw wallet key
  has no equivalent: rotating it means a new address and manually migrating every position into it.
- **Scoped delegated puzzles, not a master key.** Every vault spend is a delegated puzzle the owner
  signs into existence (`AGG_SIG_ME` + coin id + genesis), not a standing permission. A future
  "vault action" (an automated rebalance, a keeper-triggered collect) can be handed a signing view
  restricted to one delegated-puzzle shape without ever exposing the account's master key — the
  same signing-view mechanism the legacy locks already use for M-of-N shares, generalized to
  single-owner automation.

This is what "vault actions" should mean going forward: an action (rebalance, collect, treasury
payout) whose authorization check is "this vault's owner(s) signed this specific delegated
puzzle," reusable across every feature that needs custody, rather than each feature re-deriving
its own signature scheme. Note the naming risk: CHIP-0050's action layer (`chip0050ActionLayer.md`)
already calls its registry leaves "actions" (swap/add/remove/observe/collect) — those leaves came
*after* this vault idea, so if a vault-gated action ever becomes a literal registry leaf, name it
distinctly (e.g. "vault-gated action") rather than overloading "action" a second way.

**Named first consumer — future work, after phase 8, not current focus (2026-09-05): Forge's own
`/balancer` tab.** Current focus is phase 8 (V10 parity on V11, `FORGE_V11_FOUNDATIONS.md`); this
section documents direction only. `BalancerPanel.tsx` already
does arb-cycle discovery and equilibrium planning; its own source comment says the only missing
piece is a keeper — "there is no keeper yet, so each one is a deliberate click rather than an
automatic response to a spread opening." The plan is to close that gap with a vault action, not a
hot key: assets sit in a vault lock, and the balancer keeper holds a signing view scoped to one
delegated-puzzle shape (the balance/arb-cycle spend), authorized to fire **only when it clears a
criterion checked before signing** — at minimum, that the cycle's realized output is not less than
what the vault's own offer/quote already committed to (received units ≥ the offer's stated
output). This makes the keeper trustless in the way that matters: it can only ever produce a
trade at least as good as one the owner already agreed to the shape of, never worse, and it never
holds a key that can do anything else. Not yet built — this is the target shape, not shipped
behavior.

This makes the earlier "candidate first consumer: the Liquidity Manager" framing obsolete: that
project (`projects/chia-vaults/`, TODO_DEFI Phase 10) predates the CHIP-0050 leaves, isn't vetted
against them, and its rebalancing scope is what `/balancer` already covers — see the "three
things called vault" note in [docs/skills/README.md](README.md#forge-defi-primitives).

**Site plan:** this feature is currently the `🔐` tab inside `forge.awizard.dev` (`chia-cfmm`).
The plan is to split it into its own subdomain, `lock.awizard.dev` — not because custody is
unrelated to Forge (it isn't; see the direction above), but so it can be worked on as its own
parallel workstream instead of every change queueing through the Forge tab. See
[docs/ARCHITECTURE.md](../ARCHITECTURE.md#-lockawizarddev--the-lock-multisig--vault-custody).

## Files

| | |
|---|---|
| `contracts/multisig_tool.py` | derive · balance · propose · sign-request · verify-share · assemble · status |
| `contracts/tests/test_multisig_tool.py` | 14 checks incl. owner-address derivation, CAT with XCH fee, forged/crossed sigs, two-key shares, replay guard |
| `api/_multisigIndex.js` + `api/multisig-*.js` | registry (`.awizard/multisig-index.json`) and routes |
| `src/lib/multisig.ts`, `src/components/MultisigPanel.tsx` | client and the Multisig tab |
| `scripts/multisig-mock-host.mjs` | app on :4185 against an in-memory node (`/mock/fund`), own state dir |

## Limits to state up front

- Owners/threshold are the address. Rekey = new safe + transfer. The CNI vault member puzzles
  (`M_OF_N`, `BLS_MEMBER`, `TIMELOCK`, secp/passkey members, all in `chia_puzzles_py`) are the
  successor once Sage can sign for them; the plan JSON is versioned for that swap.
- Collected shares are bearer until the coins move. Cancel is bookkeeping.
- Only XCH and CATs Forge knows about are scanned for balance; no wallet watches the address.
- A CAT minted straight into the safe has no CAT parent and cannot be spent from it.
- Max 40 coins per proposal; largest-first selection; a CAT proposal's fee needs safe XCH.

## Working rules

- Never return a signing view or assemble without `validate_bundle` — it is the only place the
  summary is tied to what the puzzles emit.
- Never trust the client's `signer` claim; it only shapes the signing view.
- A push rejection leaves the proposal open: shares are still valid.
- Do not add AGG_SIG_ME to this puzzle's plans; a revision that wants it moves to the vault set.
