# Skill: dg_xch_utils (DruidGarden XCH)

> A second, independent Chia implementation in native Rust, read for what it can teach.
> Use it to cross-check consensus constants, condition and signing rules, offer and CAT
> mechanics, mempool fee rules, and to borrow a spend-level simulator that runs real
> consensus checks.

Repository: `https://github.com/GalactechsLLC/dg_xch_utils` (Apache-2.0, Galactechs).
Studied at commit `ca437be` (2026-10-04, workspace version 3.0.0). File references below
are relative to that checkout. Re-check them before quoting this skill as current.

---

## Domain

Use this skill for:

- confirming network constants: genesis challenge, AGG_SIG additional data, fork heights, cost limits
- the exact message each `AGG_SIG_*` variant signs
- condition opcode numbers and parsing edge cases
- how a clean-room implementation builds, encodes, takes and cancels XCH/CAT2 offers
- CAT2 ring construction, lineage proofs, eve issuance, and finding unhinted CAT coins
- mempool admission and replace-by-fee rules, as a second reading beside the reference node
- the `CoinsetSimulator` spend sandbox, and `sim_node` for a full-node RPC that farms on demand
- PlotNFT v1, experimental v2 (CHIP-0059), and PoS2 status

Do not use it for:

- **the Forge puzzles themselves.** Use `forgePuzzleV14.md` and `clvmPuzzleAudit.md`.
- **WalletConnect or Sage behavior.** Use `bowAppReference.md`, `sageRpc.md` and `sageAppLane.md`.
- **a wallet SDK to depend on.** `chiaWalletSdk.md` (xch-dev) stays the canonical engine reference. dgx is a second opinion, not a replacement.

### Trust level

dgx states plainly that it is under development. Its wallet syncs from a trusted node. Its
pool is "not ready to hold real pool funds". Its mainnet PoS2 constants are placeholders.

- Treat dgx as a **cross-check**. Where it disagrees with `chia_rs` or the Python reference node, the reference node decides what mainnet accepts.
- dgx does not use `chia_rs` or `clvmr`. Its CLVM VM, condition parser and mempool are its own (`core/src/clvm/runtime.rs`). That independence is what makes it useful as a cross-check, and also why it can differ from the reference.

---

## Workspace map

| Crate | What to read it for |
| --- | --- |
| `core` | Consensus constants, CLVM runtime and dialect, condition parsing, block generator rules, tree hash and curry hash, wire protocol types, TLS helpers |
| `puzzles` | Canonical puzzle bytes from `chia_puzzles` `ff0016e1…`, plus Rust drivers for standard, singleton, CAT2, NFT1, DID1, pool v1 and pool v2 |
| `wallet` | Sync, signing, XCH/CAT2 offers, CAT/NFT/DID actions, reservations |
| `keys` | BIP39 → master key, EIP-2333 hardened and unhardened derivation, paths, fingerprints, bech32m |
| `node`, `full-node` | Mempool, full-node RPC, wallet peer protocol |
| `simulator` | `CoinsetSimulator` (spend sandbox) and `sim_node` (block-producing RPC node) |
| `pool`, `farmer`, `plotter`, `proof_of_space` | Pooling v1 and v2, PoS1 and PoS2 |
| `tools` | Weight proofs, block fetch, corpus import, Docker stack helpers |
| `fuzz` | `parse_program`, `roundtrip` and `run_program` fuzz targets |

The CLI binary is `dgx`. `docs/running-a-full-node.md` still names an older `dg` binary.

---

## Network constants (`core/src/consensus/constants.rs`)

| | Mainnet | Testnet11 |
| --- | --- | --- |
| Genesis challenge, which is also the AGG_SIG additional data | `ccd5bb71183532bff220ba46c268991a3ff07eb358e8255a65c30a2dce0e5fbb` | `37a90eb5185a9c4439a91ddc98bbadce7b4feba060d50116a067de66bf236615` |
| Genesis **header hash**, the wallet trust anchor | `d780d22c7a87c9e01d98b49a0910f6701c3b95015741316b3fda042e5d7b81d2` | `3068458e6ce87dbb5e2ace5378bb84185cb0638da84ab28c39153f665e7b2c97` |
| `hard_fork_height` (2.0) | 5,496,000 | 0 |
| `soft_fork8_height` / `soft_fork9_height` | 8,655,000 / 8,655,000 | 3,755,000 / 3,924,000 |
| `hard_fork2_height` | `0xFFFFFFFA` (not scheduled) | inherited from mainnet |
| bech32 prefix | `xch` | `txch` |

- **The genesis challenge and the genesis header hash are different values.** Use the challenge for signing and reward-coin parents. Use the header hash when a client checks that a node really is on the network it claims (`get_block_record_by_height(0).header_hash`).
- `max_block_cost_clvm` is 11,000,000,000 and `cost_per_byte` is 12,000. A single transaction may use at most half a block, 5.5e9.
- `CREATE_COIN` costs 1,800,000 and an `AGG_SIG_*` costs 1,200,000.
- Pool reward coins have a parent built from the first 16 bytes of the genesis challenge. Farmer reward coins use the last 16 bytes.
- SF8 brings DISABLE_OP (modpow is off until HF2) and LIMITS. SF9 brings SIMPLE_GENERATOR, CANONICAL_INTS and LIMIT_SPENDS (at most 6,000 spends per block, canonical serialization, no generator back-reference lists).

---

## Signing (`core/src/blockchain/utils.rs`, `core/src/clvm/condition_utils.rs`)

| Opcode | Signed message |
| --- | --- |
| 49 `AGG_SIG_UNSAFE` | `msg` alone. Refused if it ends with any of the six derived suffixes below |
| 50 `AGG_SIG_ME` | `msg ‖ coin_id ‖ additional_data` |
| 43–48 `AGG_SIG_PARENT/PUZZLE/AMOUNT/PUZZLE_AMOUNT/PARENT_AMOUNT/PARENT_PUZZLE` | `msg ‖ selected fields ‖ sha256(additional_data ‖ opcode_byte)` |

- Amounts in these messages use minimal CLVM integer encoding.
- The scheme is BLS AUG, DST `BLS_SIG_BLS12381G2_XMD:SHA-256_SSWU_RO_AUG_`.
- A bundle with no AGG_SIG at all must carry the infinity signature: `0xc0` followed by 95 zero bytes.
- The G1 infinity public key is refused inside AGG_SIG conditions.
- `get_aggsig_additional_data` RPC returns the additional data as plain hex.

**Synthetic key** (`puzzles/src/p2_delegated_puzzle_or_hidden_puzzle.rs:76-117`):

- `offset = sha256(pk ‖ hidden_puzzle_hash)`, read as a **signed** big-endian integer, mod r.
- `synthetic_pk = pk + offset·G`.
- The default hidden puzzle is `(=)`, hex `ff0980`, tree hash `711d6c4e…`.
- A test vector sits at `:166-175`.

The standard solution is `(() (q . conditions) ())`.

---

## Conditions (`core/src/blockchain/condition_opcode.rs`, `condition_with_args.rs`)

| Number | Opcode |
| --- | --- |
| 1 | `REMARK` |
| 43–50 | `AGG_SIG_*` |
| 51 | `CREATE_COIN` |
| 52 | `RESERVE_FEE` |
| 60–63 | `CREATE/ASSERT` `COIN/PUZZLE` `ANNOUNCEMENT` |
| 64 | `ASSERT_CONCURRENT_SPEND` |
| 65 | `ASSERT_CONCURRENT_PUZZLE` |
| 66 | `SEND_MESSAGE` |
| 67 | `RECEIVE_MESSAGE` |
| 70–76 | `ASSERT_MY_COIN_ID`, `ASSERT_MY_PARENT_ID`, `ASSERT_MY_PUZZLEHASH`, `ASSERT_MY_AMOUNT`, `ASSERT_MY_BIRTH_SECONDS`, `ASSERT_MY_BIRTH_HEIGHT`, `ASSERT_EPHEMERAL` |
| 80–83 | `ASSERT_SECONDS/HEIGHT` `RELATIVE/ABSOLUTE` |
| 84–87 | `ASSERT_BEFORE_*` |
| 90 | `SOFTFORK` (cost = arg × 10,000) |

Parsing edge cases worth knowing when writing or auditing puzzles:

- An opcode atom that is not exactly one byte is an error. An unknown one-byte opcode is a no-op.
- A pair argument is accepted only for `REMARK` and for the memo slot of `CREATE_COIN`.
- The hint is the **first memo**, and only when it is at most 32 bytes.
- Two `CREATE_COIN`s with the same puzzle hash, amount **and hint** fail. Two payouts of equal amount to one address need distinct hints, or they collide as DUPLICATE_OUTPUT.
- Non-integer arguments are capped at 1,024 bytes. A condition list is capped at 65,536 nodes.
- **CHIP-25 messages:**
  - `mode` is one byte, and bits 6–7 must be 0.
  - The sender commitment is `mode >> 3` and the receiver commitment is `mode & 7`. `0b111` means coin id.
  - Sends and receives must net to zero per `(source, destination, message)`.
  - A message is at most 1,024 bytes.
- `ASSERT_EPHEMERAL` passes when the parent is spent in the same block and created this puzzle hash and amount.
- The 1,024-announcement cap is a mempool rule only. Consensus has no such cap.

---

## Tree hash and currying (`core/src/curry_and_treehash.rs`)

- An atom hashes as `sha256(0x01 ‖ atom)`. A pair hashes as `sha256(0x02 ‖ L ‖ R)`.
- A curried puzzle hashes as `(a (q . MOD) (c (q . arg1) (c (q . arg2) … 1)))`. `curry_and_treehash(quoted_mod_hash, [arg hashes])` computes it from the argument **tree hashes**, without running anything.
- Coin id is `sha256(parent ‖ puzzle_hash ‖ amount)`. The amount uses minimal CLVM encoding, with a `0x00` prefix when the high bit is set.
- `uncurry` only recognizes `(2 (1 . mod) args)`. On anything else it returns `(self, nil)`, so check that the result really was curried.

---

## Offers (`wallet/src/offers.rs`, `offers/encoding.rs`)

dgx's offers cover XCH and CAT2 only. Read them as a clean, compact restatement of the
settlement protocol.

### Making an offer

- **Nonce:** `sha256tree(list of the maker's input coin ids sorted by bytes)`.
- **Requested payment:** `(nonce (maker_ph amount (maker_ph)))`. The trailing memo hints the maker's own puzzle hash.
- **The maker's spend asserts** `ASSERT_PUZZLE_ANNOUNCEMENT` (63) on `sha256(settlement_ph_for_requested_asset ‖ sha256tree(payment))`.
  - For a CAT, `settlement_ph_for_requested_asset` is the CAT-wrapped settlement puzzle hash.
  - This 63 is the line that makes it an offer and not a gift. Test a built offer for opcode 63, not for the payout.
- **Inputs bind each other with `ASSERT_CONCURRENT_SPEND` (64).** dgx uses that instead of a coin-announcement ring.
- **Where the offered amount goes:** to the bare settlement puzzle, unhinted. Change returns hinted, and `RESERVE_FEE` sits in the XCH group.
- **The requested side** is a placeholder CoinSpend with parent `0x00…00`, amount 0, puzzle = settlement, solution = the notarized payments.
- **Settlement puzzles:** current is `cfbfdeed…`. v1 `bae24162…` appears only in the compression dictionary.

### Taking an offer

- **First coin of each asset group:** its settlement spend carries the maker's payments plus the taker's own claim. The claim's nonce is `sha256tree` of the group's coin ids, unsorted.
- **Other coins:** solution `()`.
- **CAT settlement coins** are spent through the CAT ring with the settlement puzzle as the inner puzzle.
- **Before taking:** the wallet checks every maker input is unspent (`get_coin_records_by_names`), then validates the combined bundle locally.

### Cancelling an offer

- **How:** respend exactly the maker's inputs back to the maker.
- **Fee:** the fee can only be paid from the XCH group, so a CAT-only offer cancels with fee 0.
- **Not cancelled until confirmed.** A signed offer stays takeable until that self-spend is on chain. Recheck an offer's input coins before relying on it.

### Encoding

- 2-byte version, currently 6.
- zlib level 6 with a preset dictionary. The dictionary is these puzzles in order: standard, CAT1, settlement v1, singleton v1.1, NFT state, NFT ownership, NFT metadata updater, NFT royalty transfer, CAT2, settlement.
- **bech32m**, hrp `offer`.
- Reference vector: the empty bundle is `offer1qqr83wcuu2rykcmqvpsrsqpzdqyqqjryqrqsl3uv6v`.

### Limits and review

- Limits: 1 MiB of text, 64 spends, 500M cost, 256 KiB per puzzle or solution, 4,096 outputs.
- `review` nets offered against requested per asset. It checks terms, not whether the coins are still spendable.

---

## CAT2 (`puzzles/src/cats.rs`, `wallet/src/assets.rs`)

- **Curry:** `CAT2(mod_hash, tail_hash, inner)`. The mod hash is `37bef360…`. CAT1 (`72dec062…`) is read-only in dgx.
- **Solution:** `(inner_sol lineage_proof prev_coin_id this_coin_info next_coin_proof prev_subtotal extra_delta)`.
  - `lineage_proof` is `(parent_parent_id parent_inner_ph parent_amount)`.
  - `next_coin_proof` is `(parent inner_ph amount)`.
- **Ring (`spend_ring`, `:303-387`):**
  - Each coin's delta is its input amount minus its outputs. Outputs skip the `-113` magic amount.
  - `prev_subtotal = running_subtotal − min(running subtotals)`.
  - Neighbors are cyclic in caller order.
  - The total delta must be 0, so dgx never melts.
  - CAT2 also refuses an inner-puzzle coin announcement that is exactly 33 bytes starting with `0xcb`; that prefix is reserved for the ring.
- **Eve issuance:**
  - The TAIL is `genesis_by_coin_id` (`493afb89…`) curried with the funding coin id.
  - The eve inner puzzle is `(q . conditions)` and includes `(51 0 -113 TAIL 0)`.
  - The eve lineage proof is `()`. The supply is fixed.
- **Finding unhinted CATs (`watch_cat`):** for each derived puzzle hash, query by puzzle hash for `curry_and_treehash(CAT, [mod, asset_id, owner_ph])` alongside the hint query. This finds old CAT coins that no hint index will return.
- **Fee coin with an asset spend:** the fee coin and the asset spend assert each other's coin announcements, so the fee cannot be stripped off and the asset spend replayed alone.

---

## NFT1 and DID1 (`puzzles/src/nft.rs`, `puzzles/src/dids.rs`)

### NFT1

- **Puzzle stack:** `singleton_v1_1(struct, STATE(…, metadata, updater_hash, OWNERSHIP(…, owner_did|(), TRANSFER(struct, royalty_ph, royalty_bps), inner)))`.
  - State layer `a04d9f57…`, ownership layer `c5abea79…`.
- **Mint:**
  - The launcher solution is `(eve_ph 1 ())`.
  - The funding coin asserts `61 sha256(launcher_id ‖ sha256tree(launcher_solution))`.
  - Royalty is at most 10,000 bps.
- **Transfer:** `CREATE_COIN(dest, 1, (dest))` plus `(-10 () () ())`, which clears the DID owner.
- **Metadata:** keys `u`, `h`, `sn`, `st`. URIs must be `https://` or `ipfs://` and at most 2,048 bytes.

### DID1

- **Puzzle:** `singleton_v1_1(struct, DID_INNERPUZ(p2, recovery_list_hash, num_verifications, struct, metadata))`.
- **Spend:** the solution `(lineage amount (1 p2_solution))` runs the inner puzzle (mode 1).
- **Launch:** sets an empty recovery list, so social recovery is off.
- **Owner:** the p2 slot takes a puzzle. Curry in its hash without being able to reveal the puzzle and the DID confirms but can never be spent.
- **`DidType::Julia`** is a placeholder that refuses every spend.

---

## Keys (`keys/src/lib.rs`)

- **Master key:** `key_gen_v3` over the BIP39 seed with an empty passphrase. New mnemonics have 24 words.
- **Paths:** `m/12381/8444/<role>/…`.

  | Role | Path |
  | --- | --- |
  | farmer | `0/0` |
  | pool | `1/0` |
  | wallet | `2/i` |
  | local | `3/0` |
  | backup | `4/0` |
  | singleton owner | `5/i` |
  | pool auth | `6/…` |

- **Derivation:**
  - Unhardened: `sk + sha256(pk ‖ index_be32) mod r`, with public-only derivation available.
  - Hardened: EIP-2333.
- **Fingerprint:** the first 4 bytes of `sha256(G1 pk)`.
- Addresses are bech32m and must decode to exactly 32 bytes.
- **Gotcha:** `get_address` uses the hardened wallet key, while the wallet's receive address is unhardened. Never assume an owner key sits at index 0 or on one side of that split; match across a window of both.

---

## Wallet sync (`wallet/src/accounts.rs`, `sync.rs`)

**Per sync, in order:**

- Pin the genesis header hash.
- Require `get_blockchain_state` to be synced.
- Scan **both** hardened and unhardened derivations in batches of 20, up to 100,000.
- Re-read the peak. If it moved, discard the scan and keep the last good snapshot.

**Node calls:**

- `get_coin_records_by_puzzle_hashes(…, include_spent)`
- `get_coin_records_by_hint`, once per derived hash
- `get_coin_record_by_name` on the parent
- `get_puzzle_and_solution(parent, parent.spent_block_index)`

**Limits:** more than 1,000 hinted coins per hash, or more than 1,000 parents, aborts the scan ("refusing a partial balance") instead of showing a wrong total.

**Reservations:**

- A signed transaction is stored, and its inputs reserved, **before** `push_tx`.
- A FAILED push keeps the inputs reserved until it is reconciled.
- Never delete the database to clear a pending transaction. The signed spend can still land.

---

## Mempool rules (`node/src/mempool.rs`)

- **Capacity:** one transaction may use at most `max_block_cost / 2`. The mempool holds `max_block_cost × 10`.
- **Minimum fee:**
  - When the mempool is **not full**, dgx's minimum fee is 0.
  - When it is full, a fee must be ≥ 5 mojos per cost **and** above the fee rate of the item it would evict.
  - The reference node refuses a nonzero fee under 5 per cost, so a dgx node can accept a fee that mainnet strands. Measure fee floors against the reference node, not dgx.
- **Replace-by-fee:**
  - The new bundle must spend a superset of the old coins.
  - Its fee per cost must be strictly higher.
  - The fee must rise by at least 10,000,000 mojos.
  - Timelocks must be equal.
  - Fast-forward and dedup eligibility must be preserved.
- **Virtual cost:** adds 500,000 per spend.
- **Timelocks:** height-locked bundles are parked, up to 100. Seconds-locked bundles fail.
- **Validation height:** `push_tx` validates at peak + 1.
- **Push results:**
  - `SUCCESS`.
  - `PENDING` for pending-class rejects. Pending is never success: often a timelock asserted against the peak instead of the last transaction block.
  - `success:false` with the error name.
- **Errors:** an error comes back as HTTP 200 with `success:false`. Read the body, not the status code.

---

## Full-node RPC (`full-node/src/routes/rpc/`)

**Endpoints:** the reference set, plus `get_coin_records_by_hints`. `farm_block`, `set_auto_farming` and `get_auto_farming` exist only on `sim_node`; a production node answers 404.

**Index features:**

- `get_coin_records_by_puzzle_hash(es)`, `by_parent_ids` and `get_additions_and_removals` need the `coin-index` feature.
- `by_hint(s)` needs `hint`.
- The default `dgx` install includes both.

**Behavior:**

- **`get_puzzle_and_solution`** re-runs the block generator. It errors unless the coin was spent at exactly that height.
- **Coin query windows:** `start_height` is inclusive and `end_height` exclusive. Up to 32,690 ids per request.
- **`get_fee_estimate`** needs exactly one of `cost` or `spend_bundle`. It ignores `spend_type`.

**Ports:**

- **dgx:** RPC and peer traffic share one TLS 1.3 listener on 8444.
- **Reference node:** RPC on 8555, with its own private-CA certificates. A client pointed at the wrong port or CA fails at the TLS handshake.

**Wallet peer protocol:**

- Versions run to 0.0.37.
- `RequestPuzzleState` takes `previous_height`, `header_hash`, filters (`include_spent`, `include_unspent`, `include_hinted`, `min_amount`) and `subscribe_when_finished`.
- Subscription caps: 200,000 for an untrusted peer, 2,000,000 for a trusted one.

---

## Simulators (`simulator/`)

| Tool | What it is | Use it for |
| --- | --- | --- |
| `CoinsetSimulator` (`simulator/src/coinset.rs`) | In-memory coin set running the real condition, aggregate-signature, fee and reserve-fee checks. A rejected bundle leaves the state unchanged | Unit-testing custom puzzle spends from Rust. It is the counterpart of Chia's Python `SpendSim` |
| `sim_node` (feature `server`) | The real dgx full node over SQLite with `farm_block` / `set_auto_farming` RPCs | A local RPC endpoint that includes `push_tx`ed bundles on demand |
| `dgx simulator` (default binary) | A server with **no routes registered** in this checkout | Nothing yet |

Pitfalls:

- `CoinsetSimulator::new()` uses Testnet11 constants at height 1. Height and timestamp never advance; set `sim.height` and `sim.timestamp` yourself before testing timelocks.
- `sim_node` reuses the **mainnet genesis challenge and AGG_SIG data**, so a spend signed for it is valid on mainnet and the other way round. Keep it on loopback, and never sign real keys against it.
- `sim_node`'s `farm_block` ignores `guarantee_tx_block`.
- Neither simulator proves mainnet acceptance. For Forge work the simulator lane in `forgePoolLifecycleTesting.md` and `chia_rs.validate_clvm_and_signature`, which checks signatures as well as CLVM, remain the checks of record. dgx is an extra, independent opinion.

---

## Pooling and PoS2

- **PlotNFT v1:**
  - Built on singleton **v1.0**.
  - The inner puzzle is the waiting room (states 1 and 2) or member (state 3).
  - The launch solution carries `p` (PoolState), `t` (delay) and `h` (delay hash).
  - `relative_lock_height` must be 1–1000. The pool URL must be `https://` and at most 2,048 bytes. The delay must be ≥ 3,600.
- **PlotNFT v2 (CHIP-0059, experimental):**
  - Built on singleton v1.1 with a MIPS inner puzzle: user branch and pool branch under 1-of-N.
  - The user branch is wrapped by `fixed_create_coin_destinations` or `heightlock`, and by `send_message_banned`.
  - The pool branch is a fixed puzzle that claims rewards.
  - Memos follow the CHIP-0043 layout.
  - It is a two-step launch: launcher, then a revision singleton.
  - Auth signs `timestamp ‖ launcher_id ‖ target_ph` with the key at unhardened child 12381 of the synthetic key, ±60 s.
  - Pinned to CHIP-0059 `3f7a2cc8`, pool2-reference `acc8803a` and chia-blockchain vectors `23d9f9d2`.
- **PoS2:**
  - Targets `chia-pos2 0.6.0`, with even k from 18 to 32 and a "strength" parameter. The default is k28, strength 2.
  - Plotting is RAM-only, about 9 GiB at k28.
  - Not active on mainnet: `hard_fork2_height` is a placeholder. After HF2, PoS1 proofs are phased out at random per proof across epochs.
- The pool and farmer crates are reference material only. Nothing in Forge depends on them.

---

## Where it helps this repo

1. **Second-opinion constants.** When a script, router or test needs the genesis challenge, header hash, fork heights or cost limits, check them against the table above and against `chia_rs`. If the two disagree, stop and find out why.
2. **Offer and CAT mechanics in a small readable form.** `wallet/src/offers.rs` is about 840 lines and covers make, take, cancel, encoding and review. Read it beside the Forge offer lane when an offer-builder change touches nonces, notarized payments, the 63 assertion or CAT settlement.
3. **A spend sandbox in Rust.** If a Rust-side tool (rue builds, wallet-sdk drivers) needs a quick consensus check without Python, `CoinsetSimulator::new_transaction` is the drop-in.
4. **Differential checking.** A spend that `chia_rs` accepts and dgx refuses, or the reverse, points at an edge case: canonical ints, condition argument shapes, message modes. Write it down and resolve it against the reference before relying on it.

---

## Skill combinations

- `chiaWalletSdk.md`: the canonical wallet engine. dgx is the cross-check.
- `chiaDevTooling.md`: docs hubs, Coinset, tracing, rue.
- `clvmPuzzleAudit.md`: when a dgx parsing rule bears on an audit finding.
- `forgePoolLifecycleTesting.md`: the Forge simulator lane, which stays the check of record.
- `chiaPrimitivesPatterns.md`: singleton, CAT and NFT design patterns.
