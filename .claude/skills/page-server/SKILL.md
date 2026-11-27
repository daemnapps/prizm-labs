---
name: page-server
description: Switch your own always-on page server on or off, or ask how it is — one private server on your Mac for ALL your pages, running even when Claude is closed, syncing through its own private copy of the repo. Use when someone says "turn my page server on", "turn my page server off", "is my page server on", "restart my page server", "push my page server", "remove my page server", "my page buttons don't work when Claude is closed", "/page-server". macOS only; the Windows form is PF-14b (Windows page server).
---

# page-server — your pages, always on

> **Activates component:** `components/page-features` — `kit/server.py`, PF-14 (page server).

A thin wrapper over `components/page-features/kit/server.py`. It installs ONE background
agent on this Mac (`~/Library/LaunchAgents/com.upright.page-server.plist`) and keeps its own
private copy of the repo under `~/Library/Caches/upright-page-server/<you>/`. It never runs a
git command in your own working folder except to make, and later remove, that private copy.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/page-features/kit/server.py` (and `kit/serve.py`, `pages.py` beside it).
- `components/run-kit/run_kit/people.py` — who you are, from your git email.

## Do this

Run every command from the repo root with `/usr/bin/python3` (the Python the agent uses), and
print its output as it is, in a code block. Exit 0 = done, 2 = refused (the output names the
fix — say it in plain words), 1 = failed (say what it says and offer "restart my page server").

| They say | Run |
|---|---|
| "turn my page server on" | `/usr/bin/python3 components/page-features/kit/server.py on` |
| "turn my page server off" | `/usr/bin/python3 components/page-features/kit/server.py off` |
| "is my page server on" | `/usr/bin/python3 components/page-features/kit/server.py status` |
| "restart my page server" | `/usr/bin/python3 components/page-features/kit/server.py restart` |
| "push my page server" | `/usr/bin/python3 components/page-features/kit/server.py push` |
| "remove my page server" | `/usr/bin/python3 components/page-features/kit/server.py remove` |

1. **on**: before the first `on` on this Mac, say once what it installs (one background agent
   that starts at login, a private copy of the repo in your Caches folder, a local server on
   127.0.0.1 only) and go on. It prints the address — each person's own fixed port from their
   identity record, http://localhost:8740/ for the developer (PF-16 (fixed port)); a held port is refused with the
   holder named, never moved — and opens your page index. A `warning:` line means that family's pages may show
   "down" until the named thing is installed; it is not a failure.
2. **status**: after the output, one line only if it applies: "N not pushed" → "say 'push my
   page server' and I'll push them"; a "NOT OK" sync or "behind" → "say 'restart my page
   server'; if it still says so, tell the page-features owner (the email lead)".
3. **push**: pushes the clicks the background agent could not push itself (it has no git login
   of its own). Run it from this session, where your git login is.
4. **remove**: refused while something is not pushed — run `push` first. Only on their typed
   "remove my page server anyway" run `remove --force`.

## Never

- Never run `server.py run` — it is what the background agent starts.
- Never edit, commit or run git in `~/Library/Caches/upright-page-server/` by hand.
- Never switch the server off from one of its own page buttons (it refuses: that would cut the
  page you are using).
- Not macOS → say "the page server's Windows form is PF-14b (Windows page server)" and stop.
