# Sage RPC — Python Access Guide

> How to call the Sage Wallet RPC from Python using mutual TLS (mTLS).

---

## Prerequisites

- Sage wallet running with RPC enabled (Settings → Advanced → Enable RPC Server)
- Python 3.8+
- `requests` library: `pip install requests`

---

## SSL Certificate Paths

Sage stores its mTLS certs in the system data directory:

| OS      | Path |
| ------- | ---- |
| Windows | `C:\Users\<USER>\AppData\Roaming\com.rigidnetwork.sage\ssl\` |
| macOS   | `~/Library/Application Support/com.rigidnetwork.sage/ssl/` |
| Linux   | `~/.local/share/com.rigidnetwork.sage/ssl/` |

Relevant files inside `ssl/`:

| File          | Role              |
| ------------- | ----------------- |
| `wallet.crt`  | Client certificate |
| `wallet.key`  | Client private key |
| `ca.crt`      | CA cert (optional, for server verification) |

---

## Base Client

```python
import os
import platform
import requests

def get_sage_ssl_dir() -> str:
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ["APPDATA"], "com.rigidnetwork.sage", "ssl")
    elif system == "Darwin":
        return os.path.expanduser("~/Library/Application Support/com.rigidnetwork.sage/ssl")
    else:
        return os.path.expanduser("~/.local/share/com.rigidnetwork.sage/ssl")


class SageRpc:
    def __init__(self, port: int = 9257):
        ssl_dir = get_sage_ssl_dir()
        self.base_url = f"https://localhost:{port}"
        self.cert = (
            os.path.join(ssl_dir, "wallet.crt"),
            os.path.join(ssl_dir, "wallet.key"),
        )
        # Set verify=False to skip server cert check, or pass path to ca.crt
        self.verify = False

    def call(self, endpoint: str, payload: dict = {}) -> dict:
        url = f"{self.base_url}/{endpoint}"
        response = requests.post(
            url,
            json=payload,
            cert=self.cert,
            verify=self.verify,
        )
        response.raise_for_status()
        return response.json()
```

> `verify=False` suppresses the self-signed cert warning. To suppress the
> urllib3 warning, add `import urllib3; urllib3.disable_warnings()` at the top.

---

## Usage Examples

### Login (required before most operations)

```python
rpc = SageRpc()
rpc.call("login", {"fingerprint": 1234567890})
```

### Get Sync Status

```python
status = rpc.call("get_sync_status")
print(status)
```

### Get Balance

```python
balance = rpc.call("get_xch")
print(balance)
```

### Send XCH

```python
result = rpc.call("send_xch", {
    "address": "xch1...",
    "amount": "1000000000000",  # mojos (1 XCH = 1_000_000_000_000 mojos)
    "fee": "100000000",
    "auto_submit": True,
    "memos": ["from python"]
})
print(result)
```

### Send CAT

```python
result = rpc.call("send_cat", {
    "asset_id": "a628c1c2c6fcb74d...",
    "address": "xch1...",
    "amount": "1000",
    "fee": "100000000",
    "auto_submit": True
})
```

### Get CATs

```python
cats = rpc.call("get_cats")
for cat in cats.get("cats", []):
    print(cat["asset_id"], cat.get("name"))
```

### Make an Offer

```python
offer = rpc.call("make_offer", {
    "requested_assets": {
        "xch": "1000000000000"
    },
    "offered_assets": {
        "cats": [{"asset_id": "a628c1c2...", "amount": "1000"}]
    },
    "fee": "100000000",
    "auto_submit": False
})
print(offer["offer"])
```

### Take an Offer

```python
result = rpc.call("take_offer", {
    "offer": "offer1...",
    "fee": "100000000",
    "auto_submit": True
})
```

---

## Full Client with Convenience Methods

```python
import os
import platform
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _sage_ssl_dir() -> str:
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ["APPDATA"], "com.rigidnetwork.sage", "ssl")
    elif system == "Darwin":
        return os.path.expanduser(
            "~/Library/Application Support/com.rigidnetwork.sage/ssl"
        )
    return os.path.expanduser("~/.local/share/com.rigidnetwork.sage/ssl")


class SageRpc:
    def __init__(self, port: int = 9257):
        ssl_dir = _sage_ssl_dir()
        self.base_url = f"https://localhost:{port}"
        self.cert = (
            os.path.join(ssl_dir, "wallet.crt"),
            os.path.join(ssl_dir, "wallet.key"),
        )

    def call(self, endpoint: str, payload: dict = {}) -> dict:
        r = requests.post(
            f"{self.base_url}/{endpoint}",
            json=payload,
            cert=self.cert,
            verify=False,
        )
        r.raise_for_status()
        return r.json()

    # --- Auth ---

    def login(self, fingerprint: int) -> dict:
        return self.call("login", {"fingerprint": fingerprint})

    def logout(self) -> dict:
        return self.call("logout")

    def get_keys(self) -> list[dict]:
        return self.call("get_keys").get("keys", [])

    # --- XCH ---

    def get_balance(self) -> dict:
        return self.call("get_xch")

    def send_xch(self, address: str, amount: str, fee: str = "0", memos: list[str] = [], auto_submit: bool = True) -> dict:
        return self.call("send_xch", {
            "address": address,
            "amount": amount,
            "fee": fee,
            "memos": memos,
            "auto_submit": auto_submit,
        })

    # --- CAT ---

    def get_cats(self) -> list[dict]:
        return self.call("get_cats").get("cats", [])

    def send_cat(self, asset_id: str, address: str, amount: str, fee: str = "0", auto_submit: bool = True) -> dict:
        return self.call("send_cat", {
            "asset_id": asset_id,
            "address": address,
            "amount": amount,
            "fee": fee,
            "auto_submit": auto_submit,
        })

    # --- Offers ---

    def make_offer(self, requested: dict, offered: dict, fee: str = "0") -> str:
        result = self.call("make_offer", {
            "requested_assets": requested,
            "offered_assets": offered,
            "fee": fee,
        })
        return result["offer"]

    def take_offer(self, offer: str, fee: str = "0", auto_submit: bool = True) -> dict:
        return self.call("take_offer", {
            "offer": offer,
            "fee": fee,
            "auto_submit": auto_submit,
        })

    # --- Status ---

    def get_sync_status(self) -> dict:
        return self.call("get_sync_status")
```

---

## Connection Details

| Property     | Value                        |
| ------------ | ---------------------------- |
| Default port | `9257`                       |
| Protocol     | HTTPS (mutual TLS)           |
| Method       | `POST` for all endpoints     |
| Content-Type | `application/json`           |
| Auth         | Client certificate (mTLS)    |

---

## Notes

- All amounts are in **mojos** (strings or int64). 1 XCH = 1,000,000,000,000 mojos.
- `auto_submit: True` broadcasts the transaction immediately. Use `False` to get the unsigned spend bundle for manual review.
- `login` must be called before any wallet operation. Pass the fingerprint shown in Sage's key list.
- Do **not** run the CLI RPC server and Sage GUI simultaneously — they share the same data files.

---

## Related

- [sageRpc.md](../skills/sageRpc.md) — full endpoint reference
- [Sage GitHub](https://github.com/xch-dev/sage)
