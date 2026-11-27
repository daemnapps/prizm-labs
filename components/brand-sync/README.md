# Brand sync

**Keys this tool needs:** `BRAND_API_URL`, `BRAND_API_KEY` (from whoever shares the brand with you). See `.env.example`.

Pulls a shared brand folder into `brands/<brand>/` from its owner's brand-folder server, shows what changed, and
pushes your changes back when your key allows it. Nobody has to add you to a repo: the owner gives you an access
key for the brands you work on, read only or read and write, and can turn it off at any time.

Say **pull the brand folder for &lt;brand&gt;**, **what changed in &lt;brand&gt;**, or **push my changes to &lt;brand&gt;**.

| Command | Does |
|---|---|
| `python3 components/brand-sync/sync.py brands` | which brands your key reaches, and whether it can write |
| `python3 components/brand-sync/sync.py status <brand>` | what is new or changed on the server, here, or both |
| `python3 components/brand-sync/sync.py pull <brand>` | brings the server's changes in |
| `python3 components/brand-sync/sync.py push <brand>` | sends your new and changed files (read-and-write keys only) |

Safe by design:

- Nothing is deleted on either side. Removals are reported, never carried over.
- A file changed both here and on the server is a conflict and is left alone in both places.
- A push only lands if the server copy is still the one you last pulled; otherwise pull first.
- `.env` files, `.git`, links and files over 25 MB never travel.
- `brands/<brand>/` is gitignored, so a pulled brand folder is never committed. What was last synced is kept in
  `brands/<brand>/.brand-sync.json`.

The server side is any brand-folder API with this contract (`GET brand-folders/`, `GET brand-folders/<brand>/`
for the file list with SHA-256 hashes, `GET`/`PUT brand-folders/<brand>/files/<path>` with `X-Base-SHA256`).
`BRAND_API_TENANT` is only for local testing against a server that picks the store by header.

| File | What it is |
|---|---|
| `sync.py` | the tool |
| `test_sync.py` | tests, against a stand-in server |

Neighbours: [keys](../keys/), [setup page](../onboarding/), [creator kit](../creator-kit/),
[brand template](../../brands/_TEMPLATE/).
