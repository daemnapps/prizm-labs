# trials — viewer-check test runs (yours, not shipped)

A trial is one hand-run of the viewer check, kept so the scoring can be tested
against a real answer. One folder per trial, `<date>-<ad>/`:

| File | What it holds |
|---|---|
| `viewer-<n>-sent.md` | exactly what viewer n was sent (their card and the feed) |
| `viewer-<n>-answer.json` | viewer n's answer, `{"posts": [...]}` as the viewer-check prompt asks |
| `key.json` / `key-<n>.json` | where our ad sat in each viewer's feed, `{"ours": <post number>}` |
| `viewer-cut.json` | the brief as a viewer sees it (the viewer-cut prompt's answer) |
| `VERDICT.md` | the scored result and the viewers' words |

Everything in here except this file is ignored by git: trials carry your
avatar's real feed and your ad.
