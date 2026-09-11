# Skill: Greenwood Lockboxes — Chia custody held by an Ethereum key

> A Chia vault whose only seat is a MetaMask key, wrapped in a singleton and named by an
> ERC-721 on Robinhood Chain. No seed phrase, no BLS key, no bridge.
> Project: `projects/greenwood` (front and back end). Puzzles:
> `projects/chia-cfmm/contracts/greenwood/`. Audit: `projects/greenwood/docs/AUDIT-2026-09-07.md`.
> Published as `greenwood-puzzles` and `greenwood-ui`.
> **Testnet only. Not externally audited.**

---

## Domain

Load this when the quest touches Greenwood: the EIP-712 custody puzzle, the Lockbox singleton,
the hand-over, listings, the declaration steward, or the on-chain art. For the MIPS shapes the
Lockbox borrows see `forgeMultisig.md`; for the auditing method see `clvmPuzzleAudit.md`.

## The trust model, which is the whole point

**Only the MetaMask key can move Chia assets.** Every spend needs an EIP-712 signature over the
exact coin id and the exact delegated puzzle hash. There is no admin key, no server key, no BLS
key anywhere in the design.

The server is a convenience, never a custodian: it reads the chain, assembles spends, pushes
them, and holds no secret. Compromised, it can *propose* a bad spend; it cannot execute one.
Coinset is trusted for liveness, not safety — a lying node can hide coins, but the signature and
the chain's own conservation rule make a wrong spend fail rather than steal.

## The two shapes

**A plain vault** is a one-seat MIPS custody puzzle whose seat is the Ethereum member. Its
address *is* its key, so it can never change hands. Several deposits are several coins, each
withdrawn by its own signature.

**A Lockbox** (`server/lockbox.py`) is that same custody inside a singleton — the Forge lock's
shape with one seat:

- **identity** is the launcher id, and that is what the EVM token names.
- **deposit address is fixed for life**, across every key rotation. XCH, CATs and NFTs all go
  there. This is the same property the Forge lock has, and for the same reason: funds sit in
  coins curried with the singleton struct, not with the inner puzzle.
- **one signature per spend**, however many assets move — the singleton spend authorises each
  asset coin by announcement.
- **rotation** hands it to another key; the new owner goes in the recreated coin's memos and the
  first in the launcher, so the full ownership history reads off the launcher id.

## The binding that matters

A vault is bound to the chain its wallet signed on: **the chain id is in the EIP-712 domain**, so
the same key on a different chain is a different vault. `VERIFYING_CONTRACT` likewise changes
every vault address, which is why it is pinned in `server/app.py` and never accepted from the
client. Chain ids: 4663 Robinhood mainnet, 46630 testnet.

## The hand-over, bound by one secret

Owning the token and controlling the Chia key must never diverge, and neither chain can see the
other. So:

1. Buyer bids on the EVM with `sha256(secret)`, their Chia key, price in escrow, a deadline.
2. Seller accepts with **one signature**, rotating the box into a pending custody of two
   signature-free seats: `hashlock_rotate` (to the buyer, given the secret, only before the
   window ends) and `timed_rotate` (back to the seller, only after). The box is frozen and the
   seller's own key is not a seat.
3. Buyer sees it frozen on Chia and settles on the EVM by revealing the secret. `Settled`
   publishes it.
4. Anyone finishes on Chia with that secret.

Plain `transferFrom` reverts — the token moves only through `settle`, because a bare transfer
would leave the Chia key behind. The EVM deadline sits **inside** the Chia window, so a
settlement always leaves time to finish. Every failure mode is "nothing happens": no settle means
the escrow refunds and the box returns to the seller.

Listings (v4) sit on top: `list` / `unlist` is an offer, not a lock; `buy` opens a bid that is
already accepted; the seller still signs once on Chia to freeze.

## Files

| Where | What |
|---|---|
| `contracts/greenwood/puzzles/eip712_check.rue` | verifies the EIP-712 signature over coin id + delegated puzzle hash |
| `…/hashlock_rotate.rue`, `…/timed_rotate.rue` | the pending custody's two seats |
| `…/_test_eth_member.py`, `_eth_member_vectors.json` | vectors from well-known development keys — labelled, never real |
| `greenwood/server/lockbox.py` | the singleton: launch, withdraw, rotate, freeze |
| `greenwood/server/keccak.py` | pure-Python Keccak-256, so the Chia venv carries no Ethereum dependency; pinned against ox's vectors |
| `greenwood/evm/contracts/Lockbox.sol` | ERC-721, token id = the Chia launcher id |
| `…/LockboxArt.sol`, `src/art.ts` | the art, a pure function of `keccak256(launcherId ‖ creationHeight)`, held to byte equality across both languages |
| `…/LockboxSteward.sol` | lets any caller refresh a declared balance without a new collection |

## Suites

`server/_test_lockbox.py` runs the whole life offline — launch, withdraw, rotate, install,
execute, cancel — and the seats' refusals: wrong secret, drains, the seller's key while pending.
`evm/test/Lockbox.ts` covers bids, settlement, refunds, disabled transfers, and the shared-secret
fixture that ties the two chains' hashes together. Run the Python side with the workspace venv
(`aWizard-Familiar/.venv/Scripts/python.exe`); the EVM side with `npx hardhat test` in `evm/`.

## Traps

- **A declaration is a statement, not a proof.** A declared balance goes stale on every deposit
  or withdrawal. The page always shows the live balance beside it, and it is deliberately *not*
  monotonic — a "height must increase" rule would let one lie lock every correction out.
- **Robinhood's public RPC** answers browsers with a malformed CORS header
  (`Access-Control-Allow-Origin: *,*`). The page's chain reads go to `/rpc` on its own origin and
  the API forwards them; don't try to fix this in the browser.
- **Deploy keys come from the keystore or env, never a file**:
  `npx hardhat keystore set ROBINHOOD_DEPLOYER_KEY`.
- Two processes, both in `.claude/launch.json`: `greenwood-api` (uvicorn, 8787) and
  `greenwood-dev` (Vite, 4190).
