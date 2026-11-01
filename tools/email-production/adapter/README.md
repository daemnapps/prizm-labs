# the team's emails: what her Claude does

Moved here from lab/steph/eve-email-page/ on 2026-10-22 (the team: "go lab-flow move"), with team-outlier/ renamed to adapter/. Built in the team's lab 2026-10-21. Owner line: tools/email-production/CLAUDE.md. Kept short: the team's Claude reads it once per session. Background and history: HISTORY.md.

the team is a designer and does not use the terminal. Do every step yourself, say in one plain sentence what you did, and
stop only for what only she can do (a file to drag in, what a picture shows, a yes). Never print a key value.

Every command runs with `/usr/bin/python3`: the page's email list needs Pillow, which is installed there (plain `python3` on a Homebrew Mac lacks it).

## "Start my email session"

1. `git pull`, then make the emails whole on this Mac (built pictures are media, so git doesn't bring them):
   `/usr/bin/python3 tools/email-production/adapter/prepare.py`. It rebuilds only the emails that need it, from
   the Drive with her key: about a minute per email the first time, nothing after. Tell her it's getting her emails
   ready.
   **Then, when the person has her own live page, bring the shared page's changes into it** (the team, 2026-10-22: apply
   them, don't ask). prepare.py ends with a `PAGE ·` block listing them (from `page_sync.py status --person <person>`,
   which reads her sync record `platform/views/viewers/<person>/emails.sync.json`). Do the same after any later pull
   in the session, and whenever she says "check the team's page changes". For each listed change, bring it in with
   `/page-change` on a draft of her page, then `/page-live`. A change that came FROM her page (its message says
   "the team's …") is already hers: skip it. Leave out a change that would undo something she changed on purpose (her
   page's `emails.changes.jsonl` or her commits say what) and say which. When all are in, run
   `/usr/bin/python3 tools/email-production/adapter/page_sync.py mark --person <person> --into own` and commit
   the sync record with the page. Tell her in one line per change what she now has. If the going-live check fails,
   leave her live page as it is, don't mark, and tell the team.
2. Open the page, in the background, and leave it running. Open the person's OWN live page when one exists
   (`platform/views/viewers/<person>/emails.html`, e.g. the team's), else the family template:
   `/usr/bin/python3 components/page-features/kit/serve.py platform/views/viewers/<person>/emails.html --open`
   (or `.../_templates/emails.html --open`). Both read the same data. The template is the page everyone shares (the family template, like the PM tool: an improvement there reaches
   everyone). PF-4 (page starter kit) fills it with today's emails from this clone at http://127.0.0.1:8765/. The
   numbers can be hidden with the eye on the "Numbers" button. If it can't read the emails, run
   `/usr/bin/python3 tools/email-production/adapter/sync.py list --brand <brand>` and tell the team its last line.
3. Tell the team: "Your emails are open. Add your changes on the page, then paste them here."

## When she pastes requests

Every line starting `Request (` or `Email request (` is one request. Save everything she pasted, as it is, to a file
in your scratchpad, then run once for the whole batch:

    /usr/bin/python3 components/page-features/kit/requests.py <that file> --family emails

It reads the shared line (QB-5 (production contract): `Request (<email id>, part <n|->): <word> …`) and, for one
release, the old `Email request (` change lines; carries out each change through this folder's `adapter.py apply`
(which wraps `sync.py apply`); tells the team about any word change (a review request); commits only the changed paths and
pushes. The lines it lists as still to do with ask.py (use my own picture, Done: send to the team, the Go, I scheduled it
in Klaviyo) are not change words: save just those lines to a second file and run

    /usr/bin/python3 tools/email-production/adapter/ask.py <second file>

which tells the team about the team's Done (a review request) and commits and pushes. Never give ask.py a line requests.py
already ran.

Tell the team in one line per request what happened (✓ / ✗ and why), and to reload the page to see it. If the git line says
"not pushed" or "not shared", tell the team. Never force.

If she says it in her own words instead ("nov-02 S1: …" is a part, "oct-20 P2: warmer light" a picture: S is a
part, P is a picture), write the request line yourself in the same form
(`/usr/bin/python3 tools/email-production/adapter/own_picture.py list <email>` shows each picture's P code and its S
address, S<part>.<picture>, both counted from 1 as the page shows them) and run ask.py the same way. If her words
could mean two pictures, show her the two codes and ask.

**A picture change in her words is a TRY first** (LD-83 (picture try first)): ask.py's `change this picture` line
makes try 1 into the run's `tries/<P>/` (gitignored), opens it on her screen the moment it exists, and changes nothing
in the email: no rebuild, no learning, no commit. The judge's verdict prints beside it and is advice only. Every try
first prints `N paid generation(s) on <model> — <price, or "price not on record">`. For what she says next, run
`/usr/bin/python3 tools/email-production/adapter/try_picture.py` yourself:
- "again" → `try <email> <P> "<the same change>"` (the next try number);
- "give me 3 options" → `--count 3`; "more like try 2 but softer" → `--from-try 2 "softer"` (try 2 is the picture edited);
- "with gemini", "one from each model" → `--model <registry id>[@<door>]`; `try_picture.py models` lists what she may
  pick (the model house's choices, house default first). A model with no door yet, or whose key is not on this Mac,
  is refused by name and nothing is made — say so, never swap in another;
- "use try 3" / "add try 3" → write that line for ask.py (`… · use try 3`): try 3 goes into the email (the old picture
  kept in its history), its record and one picture learning are written, and it is committed and pushed;
- "throw those away" → `try_picture.py clear <email> <P>` (her tries of that picture only).

**"nov-02 P1: use my newest"** (LD-90 (the team takes newest); the words are the team's): ask her what made it (Higgsfield,
Photoshop, a real photo…) and what the new picture shows, then write `… · use my newest (made with <tool>): <what it
shows>` for ask.py. The newest picture in that email's returned folder for her role,
`Shared Assets/runs/handoffs/graphic-designer/<brand>/<email label>/returned/` (or one folder down; the role is read from
tools/image-edit/delivery.json `roles`, never a person's folder: the owner, 2026-10-27, "make this name agnostic ...
the name of the folders need to be the same for both repo and drive"), is MOVED to the email's
`Shared Assets/runs/email-production/<brand>/<label>/media/` and goes into the email as an own picture does; the reply
names the file, where it went and the drive-move record. If it is still in returned/, it did not move (Drive on the web
is the truth if her Mac's Drive folder lags). `own_picture.py newest <email>` shows which file it would take, moving
nothing. Dragging a file in or pasting a link (`own_picture.py place`) still works.

**"remake from the brief instead?"** (LD-81 (portable picture records)): a picture change comes back ✗ with this
question when its record names a file this Mac can't read, here or on the Drive (each one is named). Show her the
reason and the question, word for word, and do nothing until she answers. A yes re-sends the same change with
`"from_brief": true`: write that one call as a JSON list (`brand`, `label`, `action: "picture"`, `section`,
`picture`, `note`, `by`, `from_brief`) and run `/usr/bin/python3 tools/email-production/adapter/sync.py apply <file>`.
The picture is then made fresh from its brief with her change, not edited from the old one. A no leaves it as it is.

## When she wants the page itself to look or work differently

Bigger text, other colours, a different order: improvements are welcome and go to everyone.
1. First time only: `/page-draft emails --name eve-ideas` (a copy of the shared page, in her folder).
2. Make each change with `/page-change` on `platform/views/viewers/eve/drafts/emails--eve-ideas.html`, by number
   or in her words, and show it to her: `serve.py` on that draft with `--port 8766`.
3. When she likes it, run `/review-request` asking the team to put it on the shared page, naming the draft and what
   changed. the team's Claude runs `/usr/bin/python3 components/page-features/features.py promote <her draft> --check`, then
   without `--check`: her draft becomes the shared page, with its change log; from then on everyone sees it.
   If the shared page changed after her draft was made, promote refuses: she makes a new draft and redoes it.
Gather her page changes and do them together: the page is a big file, so each round costs more than an email request.

## A picture she made in Higgsfield ("use my last Higgsfield picture for nov-02 P1")

the team, 2026-10-22: pictures go between Claude and Higgsfield with no download, drag or copy-paste. She says which
picture and which slot; do everything else.
1. Find it through the Higgsfield connector (tools named `higgsfield`, or `mcp.higgsfield.ai`): list her recent
   generations, newest first. "my last" = the newest picture; "the last 3" = show three and let her pick by number;
   a description ("the one with the window") = pick the closest and say which. Show it to her before placing.
2. Take that generation's file link and run step 3 below with the link in place of a file (own_picture.py reads an
   https picture link; `--made-with Higgsfield --source-id <the generation's id>`). The email keeps the link and the
   id under `made_from`, and one model-outcome record is written, so the picture traces back to its generation the
   way "use my newest" traces back to its Drive file (the team, 2026-10-23, the team Drive flow). Nothing moves out of
   her team folder on this path, so tell her the proof is different: the picture shows in the email when she reloads
   the page (the team, 2026-10-23).
3. No Higgsfield tools in this session: tell her, in one message, "Settings → Connectors → Add custom connector →
   name Higgsfield, URL https://mcp.higgsfield.ai/mcp → sign in with your Higgsfield account, then open a new chat".
   Until then she can paste the picture's link from Higgsfield, or drag the file in. Never ask for a password or key.
4. If the link is refused (it needs a login, or it is a page, not a picture), say so in one line and ask her to drag
   the file in instead.

## Her own picture ("use my own picture", listed by ask.py as still to do)

1. She drags the file into this window, pastes a Google Drive link, or pastes a picture's link (a Higgsfield result).
2. Look at it and write the alt text: one plain sentence saying what it shows. Show it to her; use her correction.
3. Run (the address is the one ask.py printed, e.g. `s1.0`):
   `/usr/bin/python3 tools/email-production/adapter/own_picture.py place <label> <address> "<file or Drive link>" --alt "<alt>" --made-with Higgsfield --commit`
   (leave out `--made-with` for a real photo; add `--ratio slot` to crop to the old photo's shape).
4. Tell her to reload the page.

## Limits

the team's Done marks the email ready for the team and sends her a review request; nothing goes to Klaviyo. the team makes the
Klaviyo DRAFT and schedules it with one Go after her words (the team, 2026-10-22, replacing 2026-10-21's "schedules it in
Klaviyo herself": her Go comes after she has seen the email, so it means approved to go out). The schedule is
approve_klaviyo's guarded step: approver, off-switch, not on a machine, final check, Klaviyo's draft unchanged since it
was made, at least 30 minutes ahead. A refusal leaves the draft and says why; the same Go again only schedules. ask.py
refuses a Go or a "scheduled" from anyone but the team. Nothing is scheduled without her Go, and nothing is ever sent now.
Pictures stay out of git (they live on the Drive). the team's deadlines: `runs/email-production/<brand>/deadlines.json`,
set by the team.

## The Outlier Emails artifact page (the owner's team page, formerly team-outlier/)

the owner's Outlier is a local page on his Mac. the team's and the team's is an **artifact**: `outlier-emails.html` in this
folder, published once from the team's Claude and shared with the team. It shows every designed email and records each
call as a row in the page's shared store. the team's Claude moves things between the page and the email line with
`sync.py`. The page never reaches Klaviyo and never sends anything.

### Who does what on the page

The email shows whole, cut into its sections. Click any section to adjust just that section.

- **the team** (pick "I'm the team"), per section: remake a picture with one change, redesign the section, move it up or down,
  remove it, or mark it right. For the whole email: **Go · make the Klaviyo draft**, or **Send it back** with a note.
- **the team** ("I'm the team"), per section: edit every line of its words in place and save, or mark it right. For the
  whole email: **I scheduled it in Klaviyo**, or Send it back.

### Publish it (once, from the team's Claude)

Publish `outlier-emails.html` with the Artifact tool, title **Outlier Emails**, with these capabilities:

```json
{"db": {"rules": [{"path": "emails", "read": "view", "write": "admin"}, {"path": "steps", "read": "view", "write": "admin"}]}, "user": {}, "assets": {}}
```

Share it with the team as a Contributor, so she can add calls. Only the team's side (Editors) can change the email rows.
Record the link in `tools/email-production/context/artifacts.md`.

### Fill it (after every calendar run)

1. `/usr/bin/python3 tools/email-production/adapter/sync.py list --brand <brand>` prints one row per designed email:
   its sections (where each sits on the picture, its words, its pictures) and `_picture`, the whole email. Built emails
   tag every row with its section (`data-sec`, design/build.py), which is how the sections are found.
2. Upload each `_picture` to the page's asset store (Artifact tool, `asset: true`) and put the returned url in the
   row as `image` and `thumb`. Drop `_picture`.
3. Write the rows into the page's `emails` collection (ArtifactData `batch`, one `set` per row, doc id = the row's `id`),
   leaving out `_steps`.
4. Write each row's `_steps` into the `steps` collection: one doc per step, id `<row id>__<order>` (zero-padded to two
   digits), with `email` set to the row's id. This is the email's full index, shown on the page's "How it was made"
   tab: every step in order, who ran it, the prompt as sent, what came out, the reviewer's verdict, every picture's
   record. The same index is on file at `<run>/index.json`.

Two lighter reads for other pages (LD-76 (email layout file)); the steps above keep using plain `list`:

- `sync.py list --no-steps [--brand B]` — the same rows without `_steps` (most of the output's size).
- `sync.py steps <brand>__<label>` — one email's `_steps` alone, as JSON; exit 2 for an email that is not there.

Section places come from `<run>/klaviyo/layout.json`, written by `design/build.py` when it builds the email, so
`list` launches no Chrome for an email built since; an older email is measured and named on stderr. A row's
`layout_stale` is true when the layout changed after that build.

### Apply the calls (whenever the team says "apply the email calls")

1. ArtifactData `list` the `calls` collection; keep rows whose `state` is `waiting`. Save them as a JSON list, with
   each doc's id as `id`.
2. `/usr/bin/python3 tools/email-production/adapter/sync.py apply calls.json` carries them out:
   - section `words`: the new words go into the layout, the email is rebuilt and checked; a copy learning per line.
   - section `picture`: that picture is remade from its old brief plus the change; a picture learning.
   - section `look`: a design learning, then the email is redesigned with it.
   - section `move` / `remove`: the layout changes, the email is rebuilt; a design learning.
   - section `ok`: kept on the card as right; nothing rebuilt.
   - `fill`: the system fills every gap the brand's files answer (design/gaps.py), rebuilds, and says what still
     needs a person. The page offers this first on any email with gaps; manual changes come after.
   - `go`: makes the Klaviyo draft, then schedules it through the guarded step when the caller is an approver (the team, 2026-10-22). Never sends now.
   - `send_back`: the note becomes a learning, then the email is redesigned, rebuilt and checked.
   - `scheduled`: the email is marked scheduled.
3. Write each result back to its call (`update` with `state` and `result`), then run **Fill it** again so the
   pictures and statuses are current.

Every call becomes a learning in `runs/learnings/` that every later email reads, for every brand.
