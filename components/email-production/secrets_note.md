# Keys moved out of this folder

2026-09-11 (the owner: "this should not just live in email production secrets —
these tools should be able to be accessed by anything I choose to do").

The key reader is shared now, not this tool's private thing — the one key
loader, `components/keys/loader.py` (env standard, 2026-10-17):

```python
import ep_keys            # this folder's shim over the loader
ep_keys.key("BRAND_A_NEXTCOMMERCE_ACCESS_TOKEN")
```

Every value is a `NAME=value` line in this repo's `.env`, the one key file on
every person's machine. The loader reads the environment first, then that file.

It is deliberately NOT called `secrets`: Python has a stdlib module by that
name, and a file shadowing it breaks unrelated imports in the same folder —
the same trap `email.py` in this folder already set for `urllib`.
