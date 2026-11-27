# Client copies

**Keys this tool needs:** none of its own. It uses `git` and `gh` (signed in to GitHub).

Run Prizm Labs for many businesses. Each client gets their own private copy:
every tool and prompt from Prizm Labs, plus one brand folder that is only theirs.
New tools and prompts reach every copy by themselves each morning. The brand
folder is never touched.

You don't run these by hand. In Prizm Labs, tell Claude:

| Say | What happens |
|---|---|
| set me up | first time on a computer: GitHub sign-in, your keys |
| new client: Joe's Pizza | makes the copy, then asks you about the business |
| my clients | every client, how far their setup is, last change |
| work on Joe's Pizza | brings that copy up to date, then works in it |
| update all clients | the morning update, right now |
| share Joe's Pizza with &lt;github name&gt; | that person sees that one copy only |

## The parts

| File | What it does |
|---|---|
| `new_client.py` | makes a copy: toolkit + brand folder + daily update job + your keys file, saved as a private repo tagged `prizm-client` |
| `clients.py` | lists, fetches, updates and shares copies |
| `apply_toolkit.py` | copies the toolkit in, used when a copy is made and every morning |
| `toolkit-paths.txt` | what counts as the toolkit (what each copy gets and keeps getting) |
| `toolkit-update.yml` | the daily job that goes into each copy |
| `home.json` | which GitHub team space holds the copies |

Copies live on this computer in `~/prizm-clients/<client>/` (change it with
`PRIZM_CLIENTS_DIR`). Your `.env` is copied into each one so your keys work
everywhere; it is never saved to GitHub.

The daily job reads Prizm Labs with a read-only key (`PRIZM_TOOLKIT_KEY`),
saved once for the whole team space, so a new copy needs no setup of its own.
