# Skill: Warp Bridge — Cross-Chain Chia ↔ EVM

> Extracted from the live `warp-ui-love` (Next.js 14) codebase at
> `C:\Users\Ricardo\Documents\Web_Connect\warp-ui-love`.
>
> Full implementation constants (all puzzle hashes, network addresses, NOSTR relay
> URLs, validator keys, token assetIds, fee conventions) are in:
> `warp-ui-love/docs/agent-swarm/IMPLEMENTATION_CONSTANTS.md`
>
> Detailed per-domain skill files are in:
> `warp-ui-love/docs/agent-swarm/skills/`
>
> This skill covers the complete bridge architecture. For quests touching offer
> construction, wallet adapters, or cross-chain EVM flows, read this skill first
> before reaching for the more granular files.

---

## Domain

aWizard can guide:

- **Bridge offer lifecycle** — Sage WC, Ozone WC, Goby browser extension offer creation
- **Chia-side driver selection** — lockCATs / burnCATs / unlockCATs / mintCATs with correct branching
- **EVM-side entry** — bridgeEtherToChia, bridgeToChia (with approve), bridgeBack via wagmi
- **NOSTR validator signatures** — routing key encoding, threshold collection, EIP-712 verification
- **Portal singleton mechanics** — bootstrapPortal, findLatestPortalState, PortalInfo
- **Message contents semantics** — 2-item vs 3-item contents array determining destination driver
- **StepTwo confirmation** — Chia block polling vs EVM receipt + MessageSent event decode
- **StepThree acceptance** — Chia mintCATs/unlockCATs or EVM portal.receiveMessage

---

## Project Quick Reference

```
warp-ui-love/
  src/app/bridge/
    config.tsx                       ← ALL network configs, tokens, NOSTR config, wagmiConfig
    page.tsx                         ← Step router (reads ?step= URL param)
    steps/
      StepZero.tsx                   ← Route/token/amount/wallet selection
      StepOne.tsx                    ← Source tx: ChiaButton (offer) or EthereumButton (wagmi)
      StepTwo.tsx                    ← Confirmation wait: Chia poll or EVM receipt
      StepThree.tsx                  ← Destination acceptance
      urls.tsx                       ← getStepOneURL / getStepTwoURL / getStepThreeURL
    ChiaWalletManager/
      WalletContext.tsx              ← createOffer, addCAT, connectWallet context
      wallets/
        sage.tsx                     ← WalletConnect — chia_createOffer
        walletconnect.tsx            ← WalletConnect Ozone — chia_createOfferForIds
        goby.tsx                     ← Browser extension — window.chia (NOT WalletConnect)
        index.ts                     ← walletConfigs: [{id:'sage'},{id:'goby'},{id:'chiawalletconnect'}]
        types.ts                     ← createOfferParams, asset, addCATParams
    drivers/
      offer.tsx                      ← offerToRawSpendBundle, parseXCHOffer, parseXCHAndCATOffer
      portal.tsx                     ← getSigsAndSelectors, receiveMessageAndSpendMessageCoin,
                                        findLatestPortalState, bootstrapPortal, spendOutgoingMessageCoin
      catbridge.tsx                  ← lockCATs, unlockCATs (Chia-native tokens)
      erc20bridge.tsx                ← burnCATs, mintCATs, getWrappedERC20AssetID (EVM-origin tokens)
      cat.tsx                        ← getCATPuzzle, getCATSolution
      singleton.tsx                  ← getSingletonStruct
      util.tsx                       ← buildSpendBundle, initializeBLSWithRetries, stringToHex
      rpc.tsx                        ← getCoinRecordByName, pushTx, getCoinRecordsByPuzzleHash
      abis.tsx                       ← ERC20BridgeABI, PortalABI, WrappedCATABI, L1BlockABI
  docs/agent-swarm/
    IMPLEMENTATION_CONSTANTS.md      ← ALL puzzle hashes, addresses, keys, tokens — read first
    WARP_BRIDGE_AGENT_CAPABILITY_SPEC.md
    WARP_BRIDGE_ROUTE_CALL_GRAPH_RUNBOOK.md
    skills/                          ← offer-lifecycle, chia-contract-drivers,
                                        cross-chain-eth-base, validator-signature-acceptance
```

---

## The 4-Step Bridge Wizard

All state lives in URL query params. `page.tsx` reads `?step=` to render the correct component.

```
Step 0  /bridge              — select route, token, wallets, amount
Step 1  /bridge?step=1&...   — initiate source tx (Chia offer OR EVM wagmi call)
Step 2  /bridge?step=2&...   — wait for source confirmation, extract nonce
Step 3  /bridge?step=3&...   — accept message on destination chain
```

---

## Route Decision Matrix

| Source | Destination | Token origin | StepOne call | StepThree call |
|--------|-------------|--------------|--------------|----------------|
| Chia | EVM | COINSET (XCH/CAT) | `lockCATs` | `portal.receiveMessage` (EVM) |
| Chia | EVM | EVM (wrapped ERC20 CAT) | `burnCATs` | `portal.receiveMessage` (EVM) |
| EVM | Chia | EVM (ERC20 bridging in) | `bridgeToChia` / `bridgeEtherToChia` | `mintCATs` |
| EVM | Chia | COINSET (wrapped token returning) | `bridgeBack` | `unlockCATs` |

---

## Three Chia Wallet Adapters

| id | Name | Mechanism |
|----|------|-----------|
| `sage` | Sage | WalletConnect @walletconnect/sign-client — `chia_createOffer` |
| `goby` | Goby | **Browser extension `window.chia.request()`** — NOT WalletConnect |
| `chiawalletconnect` | Ozone | WalletConnect @walletconnect/sign-client — `chia_createOfferForIds` |

**Critical**: Goby is a browser extension. Attempting WalletConnect methods with Goby will fail.

```typescript
// Goby connect + offer:
await window.chia.request({ method: "connect" })
const address = window.chia.selectedAddress  // puzzle hash directly
const offer = await window.chia.request({ method: "createOffer", params })

// Sage (WalletConnect):
client.request({ method: "chia_createOffer", params: { offerAssets, requestAssets, fee: 2500000000 } })
// Sage adapter hardcodes fee: 2500000000 in wallets/sage.tsx

// Ozone (WalletConnect):
// Calls chia_getWallets first to find wallet_id per assetId, then:
client.request({ method: "chia_createOfferForIds", params: { offerAssets, requestAssets, fee } })
```

---

## createOfferParams Shape

```typescript
interface asset { assetId: string; amount: number }
// assetId = "" for XCH; hex TAIL hash for CATs

interface createOfferParams {
  offerAssets:   asset[]   // what the wallet offers
  requestAssets: asset[]   // always [] in bridge flows
  fee: number              // mojos
}
```

---

## Chia Driver Selection (StepOne)

```typescript
// token.sourceNetworkType determines which driver to call:
if (token.sourceNetworkType === NetworkType.EVM) {
  // These are wrapped ERC20 CATs on Chia being redeemed back to EVM
  [sb, nonce] = await burnCATs(offer, coinsetNetwork, evmNetwork,
    token.contractAddress, ethReceiver, updateStatus)
} else {
  // Chia-native CATs or XCH being locked to mint wrapped on EVM
  [sb, nonce] = await lockCATs(offer, evmNetwork, coinsetNetwork,
    tokenTailHash, wrappedCatContractAddress, ethReceiver, updateStatus)
}
// tokenTailHash = null when token is XCH (assetId = "00".repeat(32))
```

---

## Destination Driver Selection (StepThree)

```typescript
const isNativeCAT = rawMessage.contents.length === 2
// contents.length === 2 → Chia-origin token returning from EVM
// contents.length === 3 → EVM-origin ERC20 minted on Chia

if (isNativeCAT) {
  [sb, txId] = await unlockCATs(portalBootstrapCoinId, offer, rawMessage,
    tokenTailHash, evmNetwork, coinsetNetwork, updateStatus)
  // contents: [xchReceiverPH_b32, tokenAmount_b32]
} else {
  [sb, txId] = await mintCATs(portalBootstrapCoinId, offer, rawMessage,
    coinsetNetwork, updateStatus)
  // contents: [ethAssetContractAddr_b32, xchReceiverPH_b32, tokenAmount_b32]
}
```

---

## EVM Source Entry (StepOne — EthereumButton)

```typescript
// ETH native:
writeContract({ address: portalAddress, abi: PortalABI,
  functionName: "bridgeEtherToChia",
  args: [receiver_bytes32, messageToll],
  value: parseEther(amount) + messageToll
})

// EVM ERC20 (USDT/USDC/EURC):
// Step 1 — approve (USDT requires USDTABI, not erc20ABI):
writeContract({ address: tokenAddr, abi: erc20ABI, functionName: "approve",
  args: [erc20BridgeAddress, mojoAmount] })
// Step 2 — bridge:
writeContract({ address: erc20BridgeAddress, abi: ERC20BridgeABI,
  functionName: "bridgeToChia",
  args: [tokenAddr, receiver_bytes32, mojoAmount],
  value: messageToll
})

// Chia-origin wrapped CAT on EVM (no approval needed):
writeContract({ address: token.contractAddress, abi: WrappedCATABI,
  functionName: "bridgeBack",
  args: [receiver_bytes32, amount],
  value: messageToll
})
// messageToll = ethers.parseEther("0.00001")
```

---

## StepTwo — Extracting the Nonce

### Chia source
```typescript
// Poll getCoinRecordByName(rpcUrl, txHash) until coin_record.spent === true
// Then wait confirmationMinHeight blocks (32 mainnet, 5 testnet)
// nonce = the message coin id (returned by lockCATs/burnCATs)
```

### EVM source
```typescript
// wagmi useWaitForTransactionReceipt → parse MessageSent event
const eventSig = ethers.id("MessageSent(bytes32,address,bytes3,bytes32,bytes32[])")
const log = receipt.logs.find(l => l.topics[0] === eventSig)
const nonce = log.topics[1]  // indexed bytes32, "0x" + 64 hex
const [source, destChain, destination, contents] =
  AbiCoder.decode(["address","bytes3","bytes32","bytes32[]"], log.data)
```

---

## NOSTR Signature Collection

```typescript
// Build routing bech32m key (hrp "r") from 38 bytes:
const routingDataBuff = Buffer.from(sourceChainHex + destinationChainHex + nonce, "hex")
const routingData = bech32m.encode("r", bech32m.toWords(routingDataBuff))

// Coin data (Chia destination only — hrp "c"):
const coinData = GreenWeb.util.address.puzzleHashToAddress(portalCoinId, "c")

// Filter: { kinds: [1], "#r": [routingData], "#c": [coinData] }  // Chia dest
//         { kinds: [1], "#r": [routingData] }                     // EVM dest

// Threshold: 6/10 mainnet, 2/3 testnet (coinset and EVM both)
```

### EVM signature verification (EIP-712)
```typescript
const domain = { name: "warp.green Portal", version: "1",
  chainId: destinationNetwork.chainId,
  verifyingContract: destinationNetwork.portalAddress }
const types = { Message: [
  { name: "nonce",           type: "bytes32"   },
  { name: "source_chain",    type: "bytes3"    },
  { name: "source",          type: "bytes32"   },
  { name: "destination",     type: "address"   },
  { name: "contents",        type: "bytes32[]" }
]}
const recovered = ethers.verifyTypedData(domain, types, msgStruct, sig)
// Must match expected validator address; sort ascending by address
```

---

## Key Puzzle Hashes

```
CAT_MOD_HASH                       = 37bef360ee858133b69d595a906dc45d01af50379dad515eb9518abb7c1d2a7a
SINGLETON_MOD_HASH                 = 7faa3253bfddd1e0decb0906b2dc6247bbc4cf608f58345d173adb63e8b47c9f
SINGLETON_LAUNCHER_HASH            = eff07522495060c066f66f32acc2a77e3a3e737aca8baea4d1a64ea4cdc13da9
BRIDGING_PUZZLE_HASH               = a09eb1ea8c6e83c0166801dabcf4a70d361cc7f6d89c4a46bcd400ac57719037
OFFER_MOD_HASH                     = cfbfdeed5c4ca2de3d0bf520b9cb4bb7743a359bd2e6a188d19ce7dffc21d3e7
P2_CONTROLLER_PUZZLE_HASH_MOD_HASH = a8082b5622ccb27e89f196f024f9851dee0bcb0f2d8afd395caa6d4432f6f85f
CAT_MINT_AND_PAYOUT_MOD_HASH       = 2c78140b52765a1c063062775d31a33a452410e9777c01270c1001db6e821f37
WRAPPED_TAIL_MOD_HASH              = 2d7e6fd2e8dd27536ebba2cf6b9fde09493fa10037aa64e14b201762c902f013
BURN_INNER_PUZZLE_MOD_HASH         = 69b9ac68db61a9941ff537cbb69158a7e1015ad44c42cff905159909cd8e1f90
```

---

## Network Addresses (Mainnet)

```
Chia portalLauncherId  = 46e2bdbbcd1e372523ad4cd3c9cf4b372c389733c71bb23450f715ba5aa56d50
Ethereum portalAddress = 0x2593C582B7a24d94Ba0056B493Fd4048bd99fc3F   (chainId 1)
Ethereum erc20Bridge   = 0x208b80E85dAC3354DD80f72cC272297909EE81b7
Base portalAddress     = 0x382bd36d1dE6Fe0a3D9943004D3ca5Ee389627EE      (chainId 8453)
Base erc20Bridge       = 0x8412f06e811b858Ea9edcf81a5E5882dbf70aC96
Chia rpcUrl (mainnet)  = https://api.coinset.org
Chia rpcUrl (testnet)  = https://testnet11.api.coinset.org/
```

---

## Network / Token Identifiers

```
Chia chain id          = "xch"   → hex "786368"
Ethereum chain id      = "eth"   → hex "657468"
Base chain id          = "bse"   → hex "627365"
XCH assetId (sentinel) = "00".repeat(32)  (null tailHash in drivers)
messageToll (Chia)     = 1_000_000_000 mojos
messageToll (EVM)      = ethers.parseEther("0.00001")
Protocol fee           = 0.3% (30/10000), minimum 1 mojo
Offer fee (Sage)       = 2_500_000_000 mojos (hardcoded in sage.tsx)
```

---

## XCH Token — EVM Contract Addresses

```
XCH → Base mainnet:  0x36be1d329444aeF5D28df3662Ec5B4F965Cd93E9
XCH → Base testnet:  0xf374cF9D090E19E8d39Db96eEDc8daf62a6C435a
XCH → ETH mainnet:   0x1be362F422A862055dCFF627D33f9bD478e6C7d7
XCH → ETH testnet:   0x3df856f8d94BAF6527b89Cf07fAFea447A4418CA
```

---

## NOSTR Relay URLs (Mainnet)

```
wss://relay.fireacademy.io
wss://relay.bufflehead.org
wss://xch-relay.tns.cx
wss://relay.spacescan.io
wss://relay.chainhq.tech
wss://relay.ozonewallet.io
wss://warpgreen-relay.232220.xyz
wss://relay.msmc.dev
wss://warpgreen-mainnet-relay.midl.dev
wss://relay.giritec.com
```

---

## WalletConnect Project IDs

```
EVM (wagmi/web3modal): e47a64f2fc7214f6c9f71b8b71e5e786
XCH (Sage/Ozone WC):   777b63154ba9ec11877caf45a17b523e
```

---

## getWrappedERC20AssetID

Deterministic Chia CAT assetId from EVM chain + ERC20 contract:
```typescript
// sha256tree of wrappedTAIL curried with portal launcher id + source chain info
// Changes if portalLauncherId changes
function getWrappedERC20AssetID(sourceChain: Network, erc20ContractAddress: string): string
// Location: src/app/bridge/drivers/erc20bridge.tsx
```

---

## BLS Initialization

All four driver entry points (`lockCATs`, `burnCATs`, `unlockCATs`, `mintCATs`) call:
```typescript
const blsOk = await initializeBLSWithRetries()  // max 2 retries, 1s delay
if (!blsOk) return [emptySpendBundle, ""]        // surfaces as UI error
```

---

## Security Coin Pattern

Every spend bundle includes a security coin (ephemeral, random BLS key `tempSk`).
Prevents offer replay — same offer cannot be submitted twice.
`parseXCHOffer` and `parseXCHAndCATOffer` both extract the security coin and tempSk.

---

## PortalInfo Type

```typescript
type PortalInfo = {
  coinId: string
  messageCoinAlreadyCreated: boolean
  mempoolPendingThings: [RawMessage, number][]
  mempoolSb: SpendBundle | null
  mempoolSbCost: BigNumber
  mempoolSbFee: BigNumber
}
```

---

## Common Pitfalls

| Mistake | Correct Behavior |
|---------|-----------------|
| Using WalletConnect methods with Goby | Goby uses `window.chia.request()` — no WC session |
| Calling `burnCATs` for Chia-native tokens | `burnCATs` is for EVM-origin wrapped CATs; use `lockCATs` for Chia-native |
| Expecting `contents.length === 3` to mean native CAT | `length === 3` = EVM ERC20 arriving (`mintCATs`); `length === 2` = Chia token returning (`unlockCATs`) |
| Missing ERC20 approve before bridgeToChia | Always call `approve(erc20BridgeAddress, amount)` first, except for ETH and bridgeBack |
| Using erc20ABI for USDT | USDT requires `USDTABI` — USDT.approve has no return value |
| Hardcoding USDT decimals | Fetch from contract; USDT is 6 decimals on EVM, 3 on Chia |
