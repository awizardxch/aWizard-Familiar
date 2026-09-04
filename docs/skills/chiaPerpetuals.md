# Skill: Chia Perpetuals Protocol

> aWizard's authoritative knowledge for building a fully on-chain perpetual futures exchange
> on Chia — the Chia equivalent of Aftermath Perpetuals on Sui.

---

## Vision

Build a **fully on-chain Central Limit Order Book (CLOB) for perpetual futures** on Chia.
All order placement, cancellation, matching, and liquidation logic executes in Chialisp/Rue
smart contracts. No off-chain sequencers. No centralized components.

This is the Transparency Revolution applied to derivatives:
- Every trade is verifiable on-chain
- Collateral is user-controlled, not pooled custody
- Liquidations are permissionless — any participant can liquidate and earn a fee
- Mark price manipulation is prevented by multi-source oracle median

---

## Architecture Overview

```
User Collateral Account (singleton)
       │
       ▼
Order Placement (CLOB singleton spend mode)
       │
       ▼
Matching Engine (on-chain Chialisp logic)
       │
       ├── Fill → Position Update (position singleton)
       │
       └── Liquidation trigger → Liquidation Engine
                                     │
                                     └── Insurance Fund → Socialized Losses → ADL
```

### Key Singletons

| Singleton | Purpose |
|-----------|---------|
| `market_singleton` | Per-market state: orderbook, open interest, funding rate accumulator |
| `account_singleton` | Per-user collateral + positions (isolated margin) |
| `position_singleton` | Individual open position (or embedded in account) |
| `insurance_fund_singleton` | Market-isolated insurance pool |
| `oracle_singleton` | Aggregated price feed checkpoint |
| `aflp_vault_singleton` | Community LP market-making vault |

---

## Collateral Model

- Collateral lives in **user-controlled account singletons** — not pooled custody
- Each market supports **isolated margin mode**: collateral for market A cannot be seized for market B
- Supported collateral: XCH (mojos), CAT tokens (with trusted CAT IDs)
- Deposit: coin → account singleton spend creates position entry
- Withdrawal: blocked if withdrawal would breach initial margin requirement

---

## Order Types

| Type | Description |
|------|-------------|
| Market | Fill immediately at best available price |
| Limit | Rest on book at specified price |
| Stop-Loss (SL) | Trigger market order when mark price ≤ trigger |
| Take-Profit (TP) | Trigger market order when mark price ≥ trigger |
| Reduce-Only | Only decreases position size — never opens new |

---

## Mark Price (Liquidation Trigger)

To prevent manipulation via a single exchange "wick":

$$\text{MarkPrice} = \text{median}(\text{BookPrice},\ \text{FundingPrice},\ \text{TWAPPrice})$$

$$\text{FundingPrice} = \text{IndexPrice} + \text{TWA}_{1m, 1h}(\text{BookPrice} - \text{IndexPrice})$$

- **BookPrice** — mid price from on-chain order book
- **IndexPrice** — aggregated oracle price (multi-source)
- **TWAPPrice** — time-weighted average of recent trades
- Mark price update happens on every market spend (block-triggered or position spend)

---

## Funding Rate

- Funding payments transfer between longs and shorts periodically
- Rate derived from premium (book vs. index price spread)
- Applied on each position spend that crosses a funding interval boundary
- If mark price > index → longs pay shorts (and vice versa)
- Collected funding reduces/increases position collateral

---

## Liquidation Engine

A position enters liquidation when: `margin < maintenance_margin_requirement`

Triggers:
1. Adverse mark price movement (unrealized PnL erodes margin)
2. Accumulated funding payments deplete collateral

### Partial Liquidations (default)
- Only liquidate the **minimum amount** to restore position health
- Target: restore to market's maximum initial leverage (e.g. 10x)
- Liquidator acquires liquidated portion at mark price
- Three fees collected: liquidator fee, insurance fund fee, protocol fee

### Loss Cascade (bad debt resolution)

```
Position hits bankruptcy price → bad debt generated
    │
    Layer 1: Insurance Fund (per-market isolated)
    │         └── Funded by insurance_fee from healthy liquidations
    │
    Layer 2: Socialized Losses (if insurance depleted)
    │         └── Bad debt distributed proportionally to opposing positions
    │         └── Added to funding rate of opposing side
    │
    Layer 3: Auto-Deleveraging — ADL (extreme scenarios)
              └── Highly profitable opposing positions force-closed at bankruptcy price
              └── More equitable than full socialization
              └── Admin-triggered but results verifiable on-chain
```

---

## Oracle System

### Chia Oracle Aggregation
- Primary: 3rd-party oracle CATs that publish price attestations (signed data)
- On Chia: oracles publish signed price coins; protocol reads the latest valid coin
- Aggregation: median of N oracle price coins within acceptable staleness window
- Anti-manipulation: require minimum 3 sources for mark price computation

### Price Feed Architecture
```
Oracle Provider A → signs price coin (price = X, timestamp = T, sig = BLS)
Oracle Provider B → signs price coin
Oracle Provider C → signs price coin
       │
       ▼
Oracle Aggregator Singleton → stores latest validated median → IndexPrice
       │
       ▼
Market Singleton reads IndexPrice on every position spend
```

---

## Position Lifecycle

```
Open Position:
  account_singleton spend → CreatePosition spend mode
    → verifies margin ≥ initial_margin_req
    → creates position_entry in account state
    → places order on market_singleton CLOB

Fill:
  market_singleton matching spend
    → order filled at price P
    → updates position: size, entry_price, collateral

Funding Update:
  any position spend → checks funding_interval_crossed
    → applies accumulated funding delta to collateral

Close / Reduce:
  account_singleton spend → ClosePosition spend mode
    → settle PnL: add to or deduct from collateral
    → release margin back to user

Liquidation:
  permissionless liquidator spend → LiquidatePosition spend mode
    → verify maintenance_margin_breached at current mark price
    → partial liquidation math
    → distribute liquidation fees
    → update or close position
```

---

## PnL Calculation

For a long position:

$$\text{Unrealized PnL} = (\text{MarkPrice} - \text{EntryPrice}) \times \text{Size}$$

For a short position:

$$\text{Unrealized PnL} = (\text{EntryPrice} - \text{MarkPrice}) \times \text{Size}$$

Margin ratio: $\frac{\text{Collateral} + \text{UnrealizedPnL}}{\text{NotionalValue}}$

---

## Market Types

| Market Type | Settlement | Examples |
|-------------|-----------|---------|
| Crypto perpetual | XCH/USDS collateral | XCH-PERP, BTC-PERP |
| Commodity perpetual (24/5) | Weekday-only funding | XAU-PERP, WXAG-PERP |
| Index perpetual | Basket oracle | CHIA-INDEX-PERP |

---

## Chia Implementation Notes

### CLVM Constraints
- All swap/position math done in fixed-point arithmetic (no floating point in CLVM)
- Newton-Raphson solvers are bounded by max iterations (256) to stay under CLVM cost limit
- Mark price median computed from 3 embedded oracle values in the spend solution

### Rue Contracts (planned)
```
perps/
  market_singleton.rue     ← CLOB state, open interest, funding accumulator
  account_singleton.rue    ← Per-user collateral, position map
  position_singleton.rue   ← Optional: individual position as separate coin
  insurance_fund.rue       ← Market-isolated insurance pool
  oracle_aggregator.rue    ← Multi-source price aggregation
  liquidation_engine.rue   ← Permissionless liquidation logic
  aflp_vault.rue           ← Community LP market-making vault
```

### Settlement in Mojos
- All amounts denominated in mojos (1 XCH = 1,000,000,000,000 mojos)
- PnL settled in XCH (or specific CAT if using CAT collateral)
- Minimum position size: 1 mojo (effectively 0.000001 XCH)

---

## CHIP Strategy

This protocol will be submitted as multiple CHIPs:

| CHIP | Title | Category |
|------|-------|---------|
| A | On-Chain CLOB Standard for Chia | Standards Track / Primitive |
| B | Perpetual Futures Position Standard | Standards Track / Primitive |
| C | Oracle Aggregation Standard | Standards Track / Primitive |
| D | Permissionless Vault Standard | Informational / Puzzle |

Start with CHIP-A (CLOB) after testnet proof. Build on CHIP-0050 (Action Layer and Slots) from
the start — Forge V11 adopts it for the CFMM, and the CLOB and position maps are the first
consumers of slots. Reference and audit additions: `chip0050ActionLayer.md`.

---

## Source References

- `chia-cfmm/docs/CHIP_SUBMISSION.md` — CFMM CHIP strategy
- `chia-cfmm/docs/IDEAS.md` — feed ideas (on-chain EMA oracle, limit order book layer)
- `chia-treasure-chest/docs/CHIP_SUBMISSION.md` — kiosk CHIP strategy
- Aftermath Perpetuals docs — https://docs.aftermath.finance/perpetuals/aftermath-perpetuals
- Liquidation architecture — https://docs.aftermath.finance/perpetuals/architecture/liquidations
