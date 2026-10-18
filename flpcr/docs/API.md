# FLPCR — HTTP API (draft)

Read side modeled on Merkl's v4 (`/opportunities`, `/campaigns`, `/users/{address}/rewards`),
so integrators who know Merkl find their way. Base `https://<host>/api/flpcr/v1`. Amounts are
strings of mojos (Forge snapshot convention: they survive `JSON.parse`). Addresses accept
`xch1…`/`txch1…` or a 64-hex puzzle hash; responses carry both.

## Read

### `GET /opportunities?kind=&asset=&pool=&status=live|upcoming|ended`

One row per target with at least one campaign:

```json
{ "target": "<pool launcher | cat asset id>", "kind": "LP_HOLD", "name": "TXCH/wUSDC",
  "tvl_xch": "1234500000000", "apr_bps": 2310,
  "daily_rewards": [{ "asset": "<id>", "symbol": "wUSDC", "amount": "41000000" }],
  "campaigns": ["<campaign id>", "..."] }
```

APR = Σ daily reward value / eligible TVL, valued at the pools' oracle TWAP (SPEC §6.6).

### `GET /campaigns?creator=&target=&reward_asset=&status=` and `GET /campaigns/{id}`

The struct from SPEC §3.1 in full (params expanded), plus `created_height`, `distributor`,
`emitted` (`emittable(peak)`), `allocated` (posted), `unallocated`, `reclaimed`.

### `GET /users/{address}/rewards?reward_asset=`

```json
{ "puzzle_hash": "…", "address": "xch1…",
  "rewards": [{
    "distributor": "…", "reward_asset": "…", "symbol": "…",
    "accrued": "…",        // engine's floor(accrued) across campaigns, posted or not
    "pending": [{ "epoch_id": 12, "amount": "…", "activates_at": 4712345 }],
    "payable": [{ "epoch_id": 11, "index": 37, "amount": "…",
                  "proof": { "path": 5, "hashes": ["…"] } }],
    "paid": "…",
    "by_campaign": [{ "id": "…", "accrued": "…", "allocated": "…" }] }] }
```

### `GET /epochs/{distributor}/{epoch_id}`

The manifest exactly as pinned (see `flpcr/manifest.py`), with its `manifest_hash` and the
`post_epoch` spend's coin id and height.

### `GET /distributors`

Registry contents: per reward asset, the launcher, config, current state summary.

## Write (keyless, Sage offers)

### `POST /campaigns/quote`

Body: the campaign fields minus `distributor_id` (resolved from `reward_asset`). Returns the
validated struct, `campaign_id`, `fee`, `deposit = amount + fee`, per-day emission, and the
**offer to make**: give `deposit` of `reward_asset`, request nothing. Validation errors use the
same rules as the `create` leaf, so a quote that passes builds.

### `POST /campaigns/create`

Body: `{ quote_id, offer }`. The responder takes the offer's settlement coin as the `create`
leaf's input, adds the network fee from the offer, pushes and returns the spend bundle id.

### `POST /payouts/build`

Body: `{ distributor, epoch_id, indices[] }` or `{ address }` for all of a user's payable entries.
Returns an unsigned bundle; the caller attaches a fee (or an offer that pays one). Keepers use the
same endpoint in bulk.

## Rate limits and keys

Anonymous: 10 req/s (Merkl's number). An `X-API-Key` header lifts it. The read side is a cache
of chain data plus manifests, so anything it serves can be recomputed from chain.
