# Keys moved out of this folder

2026-09-11 (the owner: "this should not just live in email production secrets —
these tools should be able to be accessed by anything I choose to do").

The key reader is machine-level now, not this tool's private thing:

```python
import daemn_keys
daemn_keys.key("Brand B_NEXTCOMMERCE_ACCESS_TOKEN", required=True)
```

It lives at `~/.daemn/daemn_keys.py` and is on the Python path for every
interpreter on this Mac, so any script anywhere can import it. Every value is
in the macOS Keychain — service `daemn-<NAME>`, account `damon`.

It is deliberately NOT called `secrets`: Python has a stdlib module by that
name, and a file shadowing it breaks unrelated imports in the same folder —
the same trap `email.py` in this folder already set for `urllib`.
