# Onboarding

**Keys this tool needs:** none of its own; it is where you put the others.

One local page to set up Prizm: name your brand (or link the brand folder that lives in its own repo), save your
keys, connect your Meta ad account. Keys go into your own `.env` (never saved to git, readable only by you); the page
only ever shows "set" or "missing".

You don't run it by hand. Say **activate Prizm Lab** (Claude Code or Codex) and it opens this page; or ask to
"open the setup page".

| File | What it is |
|---|---|
| `serve.py` | the page's local server, http://127.0.0.1:8890, this computer only |
| `page.html` | the page |
| `test_onboarding.py` | tests |

The key list is read from `.env.example`, so a new key appears on the page as soon as it is added there.
Neighbours: [keys](../keys/) (how tools read a key), [brand template](../../brands/_TEMPLATE/).
