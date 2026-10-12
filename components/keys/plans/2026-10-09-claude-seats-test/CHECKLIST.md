# Afternoon test with Operator B: her token, a supervised session, her subscription

From ◆ PLAN · mn · dev-developer [fab344], 2026-10-09, read from 2a378e7fa8. About 40 minutes, with the developer watching live, and **no sandbox today** (the developer's call: he watches every step). Record every result in `RESULTS.md`.

Every `!` line is typed by the developer in a Claude session on the mini. The `!` must be the first character, and the command must sit on one line.

## Before the call

- [ ] Agree how the token reaches the developer: a password-manager share if either of you has one, otherwise a one-time secret link. **Not** Slack, chat or email. This stands in for D1.
- [ ] Tell Operator B: you'll drive a Claude session on the mini from your own Claude app, on your own subscription. In the shared clone: commit by path only, never reset, never switch branches. Today is read-only.

## A. Operator B makes her token (her laptop)

- [ ] In a **wide** terminal window, so the token doesn't wrap: `claude setup-token`. Sign in, then copy the printed token.
- [ ] Send it by the agreed channel.

## B. the developer saves it (MacBook, then the mini)

- [ ] MacBook terminal, with the token copied:
  `pbpaste | tr -d ' \t\r\n' > ~/.claude-val-token && chmod 600 ~/.claude-val-token && pbcopy < /dev/null && wc -c ~/.claude-val-token`
  Expect about 108.
- [ ] Mini: `!scp developers-macbook-pro:~/.claude-val-token ~/.claude-val-token && chmod 600 ~/.claude-val-token`
- [ ] MacBook terminal: `rm ~/.claude-val-token`

## C. the developer starts her session (mini)

- [ ] `!tmux new-session -d -s val-rc -c the workspace 'CLAUDE_CODE_OAUTH_TOKEN=$(cat ~/.claude-val-token) claude --remote-control val-supervised'`
  (The single quotes are deliberate. The token is read inside the new session, so it never shows in the process list.)
- [ ] `!tmux capture-pane -p -t val-rc | tail -20`. If it's waiting at a "trust this folder" prompt, run `!tmux send-keys -t val-rc Enter`.

## D. The tests (Operator B, in her Claude app, session **val-supervised**)

| # | She does | Expected | Settles |
|---|---|---|---|
| 1 ★ | "say ok" | It answers | Remote Control works on a `setup-token` token |
| 2 | She checks her own app's session list | The session is in **her** app | It runs on her subscription |
| 3 | "What tasks are on me? What do your memory and instructions say?" | the developer's task greeting, memory or CLAUDE.md show up (inferred) | CLI-36 (supervised mini sessions) needs a per-person `CLAUDE_CONFIG_DIR` |
| 4 | Asks Claude to create a file in /tmp. the developer checks `!tmux capture-pane -p -t val-rc \| tail -15`, then tries `!tmux send-keys -t val-rc Escape` | The prompt shows in tmux too; the developer may be able to refuse it | Whether the developer has live control, not only the end switch |
| 5 | "run: git var GIT_AUTHOR_IDENT" | Shows **the developer** | Her commits would carry his name; CLI-36 (supervised mini sessions) sets hers |
| 6 | Runs Claude Code on her laptop at the same time | Both keep working | One subscription carries both at once |
| 7 | Notes her usage in claude.ai → Settings → Usage. the developer runs `!CLAUDE_CODE_OAUTH_TOKEN=$(cat ~/.claude-val-token) claude -p "write 300 words about lighthouses" < /dev/null \| wc -w`. She checks the meter again | The meter moves on **her** account | A mini job bills to her, and roughly what one job costs her limit |
| 8 | She closes her app and reopens it | The session is still there | It survives a disconnect |

## E. Real the developer-only jobs, read-only

| # | She asks the session | Why |
|---|---|---|
| E1 ★ | `ls -l ~/.workflow-worker.envprintf ~/.workflow-worker.env.bak-091107`, and whether `~/.ecom-analysis.env` still holds the pasted Supabase token line (variable **names** only, never values) | The phase 0 check, open since 29 Sep. If the stray files exist, deleting them is her call with the developer watching; the rotations stay owed either way |
| E2 | Read `~/Library/LaunchAgents/com.brand-d.workflow-worker-runs.plist` and say what a dev-operator-b lane would need | Planned 25 Aug, never loaded. Read only; loading a lane is a real change |

Not today: key values, or env-file setup (values would land in the transcript; that waits for D1's vault); applying CLI-33 (brands write hook), which has an ordering dependency; switching branches or resetting; the Drive app; Claude Code updates.

## F. End

- [ ] `!tmux kill-session -t val-rc`. Her app shows the session ending.
- [ ] Can she restart it from her side? Expected: **no**. If she can, the control model is broken: stop and report.
- [ ] `!ls -t ~/.claude/projects/*/ | head -3`: where the session's transcript landed (the audit trail).
- [ ] **No token cleanup.** Her token stays as the first pilot token (the developer, 9 Oct). She can revoke it at any time in claude.ai → Settings → Claude Code (the trash icon).
