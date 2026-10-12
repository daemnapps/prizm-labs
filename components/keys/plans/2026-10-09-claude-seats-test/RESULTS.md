# Results: Claude seats on the mini

Read from 2a378e7fa8. All tests ran on the mini (Claude Code 2.1.288). No real token value was ever printed, committed or seen by a session. The fake token files were literal strings. the developer ran every command that touched a real token himself.

## Morning, 9 Oct (◆ PLAN [fab344] with the developer)

| # | Test | Result |
|---|---|---|
| M1 | Sandbox, deny rule `Read(//abs/path/tokens/**)`: read a fake token file by the Read tool, `cat`, Python `open()`, and a Python child `cat` | **All four blocked.** The Read tool: "File is in a directory that is denied by your permission settings". The other three: "Operation not permitted", at the OS level, child processes included |
| M2 | The same, with the rule written `Read(/abs/path/…)` (one slash) | **All four read the token.** No error, no warning. A one-slash rule fails open |
| M3 | Sandbox network, nothing allowlisted | Blocked: `Tunnel connection failed: 403`, "deny network-outbound example.com:443" |
| M4 | `sandbox.network.allowedDomains: ["example.com"]` | example.com returns 200; www.iana.org stays blocked |
| M5 | Write outside the working folder, under `/private/tmp` | Allowed. A write elsewhere in the home folder: unchecked |
| M6 | Does `~/.anthropic.env` exist? | **No.** The worker's `claude_env()` layers it only if present (`worker.py:3519`). Today's jobs authenticate through the developer's logged-in session |
| M7 | the developer's throwaway `setup-token` token, `claude auth status`, with the developer's login also present | `"authMethod": "oauth_token"`: **the token wins over the logged-in session** |
| M8 | The first token copy | Refused: "contains a line break at character 80 (110 characters on 2 lines)". Fixed with `tr -d ' \t\r\n'` (108 characters) |
| M9 | Two `claude -p` jobs at the same moment on one token, `ANTHROPIC_API_KEY` unset | **Both PASS** (601 and 604 words, 50 seconds) |
| M10 | Revoking a token | The list is at claude.ai → Settings → Claude Code, with a trash icon per token (per GitHub issues #57400, #48373, #59378; the developer found the entry). the developer revoked and deleted his test token. **Whether a revoke takes effect immediately: not tested.** |
| M11 | Remote Control on the mini | `claude --remote-control [name]` exists. The mini already runs `claude remote-control` as a standing service under the developer's login (`com.brand-d.claude-remote-control`, ProgramArguments `claude remote-control`) |

Docs facts (code.claude.com/docs/en/authentication, via the claude-code-guide agent): the token lasts one year; it is read from `CLAUDE_CODE_OAUTH_TOKEN`; `ANTHROPIC_API_KEY` outranks it; `--bare` ignores subscription credentials. Not in the docs: driving `setup-token` from a script with no browser, the sandbox read keys, and any terms language about shared machines.

### What M1–M5 used, as text (scratch copies are gone with the PLAN seat)

The sandbox settings for M1 and M4:
```
{"sandbox":{"enabled":true,"autoAllowBashIfSandboxed":true,"allowUnsandboxedCommands":false,
            "network":{"allowedDomains":["example.com"]}},
 "permissions":{"deny":["Read(//<absolute path>/tokens/**)"]}}
```
Run as `claude -p "<task>" --settings <file> --permission-mode acceptEdits --allowedTools "Bash(python3:*)" "Bash(cat:*)" < /dev/null`, which mirrors the maker jobs' flags (`worker.py:8778`).

The two-jobs script for M7–M9 (run by the developer as `CLAUDE_CODE_OAUTH_TOKEN=$(cat <file>) bash twojobs.sh`). It prints the token's length and its 10-character public prefix, never the token. It unsets `ANTHROPIC_API_KEY`, runs `claude auth status`, then starts two `claude -p` jobs (a 600-word story each) in parallel and prints pass or fail for each, plus the elapsed time.

## Afternoon, 9 Oct (Operator B's token)

Step C as the developer ran it, from ◆ PLAN [fab344]'s session, which read the screen with `tmux capture-pane` (no token value appears on it): `tmux new-session -d -s val-rc -c the workspace 'CLAUDE_CODE_OAUTH_TOKEN=$(cat ~/.claude-val-token) env -u ANTHROPIC_API_KEY claude --remote-control val-supervised'`. the developer added `env -u ANTHROPIC_API_KEY` himself. Results relayed by PLAN, about 06:30Z.

**New observation:** the session header reads "Opus 5.5 with high effort · **Claude API**", not a subscription label, although this morning's `claude auth status` on a token said `oauth_token` (M7). Whether a token job bills to her subscription is now D7's question.


| # | Test (`CHECKLIST.md`) | Result | Note |
|---|---|---|---|
| D1 | Remote Control on a `setup-token` token | **FAIL** | "Remote Control disconnected — Claude.ai login was rejected — run /login, then /remote-control"; the header shows "/rc failed". Not retried with /login: the session shares the developer's `~/.claude`, so a login would likely replace his, and the workers run on his (inferred) |
| D2 | Runs on her subscription | Not run | Needs Remote Control (D1) |
| D3 | the developer's `~/.claude` setup loads into her session | **YES** | Came up in auto mode, high effort, with the developer's [MN] status line |
| D4 | the developer can refuse her prompt from tmux | Not run | Needs Remote Control (D1) |
| D5 | `git var GIT_AUTHOR_IDENT` | Not run | Needs Remote Control (D1); can also be checked in a `claude -p` job |
| D6 | Her laptop and the mini at the same time | | |
| D7 | A mini job moves **her** usage meter (and by how much) | Not run | Replaced by the per-job credential record in the routing card (below). `claude auth status` names no account, so it cannot prove whose meter moves |
| D8 | Survives an app reconnect | Not run | Needs Remote Control (D1) |
| E1 | The phase 0 stray files | | |
| E2 | What a dev-operator-b lane would need | | |
| F | She can't restart after kill; the transcript's location | | |

### More checks, 9 Oct afternoon (relayed by ◆ PLAN [fab344])

| # | Check | Result |
|---|---|---|
| A1 | `CLAUDE_CODE_OAUTH_TOKEN=$(cat <her file>) env -u ANTHROPIC_API_KEY claude auth status` | `oauth_token` / `firstParty` |
| A2 | The same with `--text` | "Auth token: CLAUDE_CODE_OAUTH_TOKEN". It names no account or plan |
| A3 | Where the worker reads a job's requester | The record's file name (`worker.py:3004`, `requester_of`) |
| A4 | Does `CLAUDE_CODE_OAUTH_TOKEN` survive the job environment filter? | Yes: it is not in `job_env`'s `VENDOR_KEYS` or prefixes, so `scoped_env` passes it through |

### Outcome: no longer a test

the developer, typed to ◆ PLAN [fab344], verbatim: "lets stop thinking this like a test, we might as well just set it up so she can actually use the dev slots with her usage from now on". On billing: "worse case it ends up using my subscription, which woudl have been the case anywyas"; "she has plenty of usage"; "This is her dev work anyways".

- **Routing card (the developer's own, typed in the lead's pane; secrets class).** `claude_env` sets `CLAUDE_CODE_OAUTH_TOKEN` from `~/.claude-tokens/<requester>` when that file exists (whitespace stripped, `ANTHROPIC_API_KEY` unset for that call). No file keeps today's login. Each job's status record names the credential used (`token:<person>` or `login`). A limit error fails as today, with no fallback. Merge on the developer's word. Tests: her token reaches only her job; other requesters unchanged; a token with an embedded line break still works; no `ANTHROPIC_API_KEY` in her call.
- **Her token** is at `~/.claude-tokens/operator-b` (folder 700, file 600, 108 characters), moved by the developer's hand (relayed by ◆ PLAN [fab344]).
- **D1 deferred** (the developer, typed to ◆ PLAN [fab344], verbatim: "skip D1 until the actual migration"). Until Track B, a new person's token moves the way Operator B's did: a one-time link or a password-manager share, never chat, Slack or email.
- **Accepted gap, on record:** until the sandbox card lands, any job on the mini can open her file. Kill-condition: any other requester's job shows `token:operator-b` → revert the same day.
- **Card id:** WM-138 (requester token routing), dispatched by ★ LEAD [c0ae5c] on the developer's own typed card. It merges only on the developer's word, with all slots idle.
- **Whose name her jobs carry** (★ LEAD [c0ae5c]): records from her own lead carry `--operator-b--` in the file name (for example `20261006T075315Z--operator-b--impl-wm137b…`), so they route to her token. The dev-developer lead's dispatches of her work carry `--developer--` and stay on the developer's login, as noted on the card.

