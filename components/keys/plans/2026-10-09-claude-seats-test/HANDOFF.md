# Claude seats on the mini: test and plan handoff (D6)

From ◆ PLAN · mn · dev-developer [fab344], 2026-10-09, read from 2a378e7fa8. For the stream session that runs this afternoon's test with Operator B and keeps the keys migration plan current. Files in this folder:

- `HANDOFF.md`: this file. What's decided, what's open, your scope, and where things route.
- `CHECKLIST.md`: the afternoon test, step by step, with copy-paste commands.
- `RESULTS.md`: what was already tested on 9 Oct, plus empty rows for the afternoon results.

The plan itself is `../3-implementation-plan.html`, live at (team page) (the "Each person's Claude on the mini" section, D6).

## The goal (the developer, 9 Oct)

Each person's automation on the mini runs on **their own Pro or Max subscription**, not the developer's. The slot a job runs in, and the kind of work, don't matter: **the person who requested the job decides whose subscription runs it.** No Mac user per person. Team members get **no direct access to the mini**.

## Decided

1. **Tokens are managed by the admins, the same way as keys** (the developer, 9 Oct). the ops lead or Operator B sit with each person while they run `claude setup-token` on their own laptop. The token travels by the D1 method. The admins update the mini's files.
2. **The per-person file.** A token lives in a per-person file on the mini (for example `~/.claude-tokens/<person>`), **never in the mini's shared key file** (`~/.workflow-worker.env`). This follows the 9 Oct revert of SI-193 (video-teardown keys reader): a loader that read that file from disk turned a job's 2 granted keys into 13. The worker reads only the requester's file at job start and hands the token to that job's environment. Decision log 2026-10-09: the token is never read from a shared file a job can open.
3. **The token rule** (decision log 2026-10-09, 30eed268b0, the developer typed in the lead's pane). A person's token is used only for (a) worker `claude -p` jobs and (b) per-session `claude --remote-control <name>` sessions that the developer or Operator B start and end. Never the `claude remote-control` service mode, and never in a background service (LaunchAgent). Reason: the mini already runs `claude remote-control` as a standing service under the developer's login (`com.brand-d.claude-remote-control`). Under a person's token, the same service would give them standing access.
4. **Supervised sessions**, CLI-36 (supervised mini sessions), carded and HELD for this test. the developer sometimes wants Operator B to work on the mini through Claude under his eye: he starts the session with her token, she drives it from her own Claude app, and he ends it. Example use: setting up env files under his control.
5. **The sandbox** goes into the next-step plan (the developer, 9 Oct). It is skipped for today's test only, because the developer watches live.
6. **Operator B's token stays after the test as the first pilot token** (the developer, 9 Oct). No cleanup. Kill-condition: if the routing cards haven't started within two weeks, she revokes it.

## Open: what the afternoon test settles (`CHECKLIST.md`)

1. ★ Does Remote Control work on a `setup-token` token at all? If not, supervised sessions would need her full claude.ai login on the mini. PLAN recommends against that.
2. Does the developer's personal `~/.claude` setup (CLAUDE.md, memory, hooks such as the task greeting) load into her session? If yes, CLI-36 (supervised mini sessions) gets a per-person `CLAUDE_CONFIG_DIR`.
3. Can the developer approve or refuse her prompts from tmux?
4. Her laptop and the mini on her subscription at the same time, and her usage meter.
5. Does the session survive her app reconnecting? Can she restart it after the developer ends it (she must not be able to)?
6. Whose name her commits would carry (`git var GIT_AUTHOR_IDENT`).

## After the test: the D6 fold to the lead

Send this to the live ★ LEAD · mn · dev-developer, by bare name. Run `ListAgents` first.

1. **Requester routing.** The job's requester picks the per-person token file. Strip `ANTHROPIC_API_KEY`, which outranks the token (per the docs). Strip whitespace from the token. No token means the job is refused, never run on someone else's subscription. The mini's own jobs run on the system account (the developer's login today), or inherit the original requester when the record carries one. The worker checks the git author who added the record against `team/people/*/identity.json`.
2. **The prefix filter.** Per-person token names never reach any job's environment. Extend WM-109 (person tokens held).
3. **The sandbox card.** Use `Read(//absolute/path/**)` deny rules on token and key paths. Add a canary: the worker tries a forbidden read, and refuses to start if the read succeeds. Network allowlist built from the atlas's host list (116 hosts named in code). Applies to person-token jobs and supervised sessions. Kill-condition: if missed hosts break more than a couple of jobs in week one, sandbox only person-token jobs.
4. **Release CLI-36 (supervised mini sessions)** with the profile the test settles: config dir, git identity, sandbox. Also: once she edits and commits in supervised sessions, give her her own clone (`the workspace-operator-b`, `core.hooksPath .githooks`), the same pattern as the worker lanes' clones.
5. **D1 goes to the developer's list as the remaining decision.** PLAN recommends a company password vault for the two admins: they keep the master copy there and share it into supervised sessions without values ever reaching a chat.

Every fold carries `Reuses / could be reused by:`. Relays quote the developer verbatim, with `date -u` and the line his words answer. Secrets and keys need the developer's own typed word in the lead's pane; the lead won't act on a relay for these.

## Your scope

- **You write** only in `components/keys/plans/` (this folder, `RESULTS.md`, and the plan page `3-implementation-plan.html`). You republish the page to its artifact URL. Commit by pathspec, `note:` prefix, and name the commit you read from.
- **You never write:** any CLAUDE.md, `team/*.json`, `the-org/`, task-cards, records, or code. Registry-shaped items route to the lead as proposals.
- **Never handle a token value.** Never open, print, copy or pass a token file in your own commands. the developer runs every command that touches a token himself, with `!`. The 9 Oct tests used `$(cat …)` inside his own commands, single-quoted when inside tmux, so the value never reached the process list or the chat.
- **The shared clone** (`the workspace`): commit by path, never reset, never switch branches. Operator B's session in it today is read-only by plan.
- Ids carry their tag on every mention; CLI-13 (id-tag lint) checks at commit.

## Traps already hit on 9 Oct

1. A single leading `/` in a deny rule silently allows everything. Use `//` for absolute paths.
2. A token copied from a terminal wraps at character 80, and Claude refuses it. Strip whitespace on save.
3. A `!` command must start the message, on one line. The leading spaces in a pasted command, and a path split across two lines, both failed.
4. `claude setup-token` needs an interactive terminal and a browser. Never run it through `!`.
5. A hat seat may not read credential files. The auto-mode classifier refused PLAN's check of the stray key files, correctly. Those checks are the developer's or Operator B's.

## Status at park (≈ STREAM [31a838], 2026-10-11 02:08Z, read from bf0fed61be)

The test is over; D6 went live instead (decision log 2026-10-09: WM-138 (requester token routing), D1 deferred, WM-140 (runs lane token) parked). Plan page v23 (9ed0df05b4) and `RESULTS.md` carry it all.

1. **Done:** results recorded; the page republished at each step (v19–v23); the D6 fold sent to ★ LEAD [c0ae5c], with a correction dropping D1.
2. **With the lead, to put to the developer (no the developer words yet):** the sandbox card (it closes the accepted gap: any mini job can open `~/.claude-tokens/operator-b`); CLI-36 (supervised mini sessions) stays held (Remote Control refuses a token).
3. **Proposal, not ruled:** fold the prefix filter into WM-138 (requester token routing) as one line plus a test. Add `CLAUDE_CODE_OAUTH_TOKEN` to `job_env`'s `VENDOR_KEYS`, so a token in the worker's own environment never reaches a job. It is a grant surface, so the developer types it.
4. **Open check:** the first job record showing `token:operator-b` proves the routing works; billing to her account is accepted, not proven. Work the dev-developer lead dispatches for her carries `--developer--` and stays on the login (the developer's call whether to change that; this stream recommended leaving it).
5. **Kill-conditions to watch:** another requester's job shows `token:operator-b` → revert the same day; her lab-run records show material Claude usage before 20 Oct → ship WM-140 (runs lane token) r2, lab runs only.
6. **Trap earned:** `claude auth status` on a token names no account or plan, so it can't prove whose meter moves. A session started with a token shows "Claude API" in its header.

Successor: whoever next edits the plan page reads the live artifact once, then edits `3-implementation-plan.html` and republishes to the same URL.
