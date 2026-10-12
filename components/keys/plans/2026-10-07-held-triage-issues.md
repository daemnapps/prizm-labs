# Keys triage issues held for the keys migration

Read from the components triage model at 2ef6f2c6c8 (queue/model-components-2026-10-07.json), 7 Oct 2026.

**Ruling (the developer, 2026-10-07, typed to ◆ PLAN · dev-developer, relayed verbatim to the lead):** "hold keys all, and make sure these all get updated to the keys work coming up". Every key-related triage issue below waits for the keys migration (expected in 1–2 weeks; plan: `3-implementation-plan.html` in this folder) instead of being fixed piecemeal. The immediate goal is that things work; none of these breaks a run today (checked 7 Oct: no key in git, no live run failing on a key).

**Moved out 7 Oct:** copywriter#7 and meta-upload#4 are Drive-mount reads, now under triage page #8 (Drive) — see components/gdrive-creator/plans/2026-10-07-held-drive-issues.md.

**Moved out 8 Oct:** audio-teardown#16 (video-teardown counts the Sound Sheet's effects wrongly, `tools/video-teardown/machine/transcript.py:280`) reads no key — misfiled here; back to the owner's normal merge window (the developer, typed to the lead 2026-10-08 before 01:34:23Z: "hunhold", answering the lead's "Say 'unhold 16'"; the 10-08 audio-teardown review C7).

**Moved out 9 Oct (keys Track A ruling):** 19 issues that read no key go back to normal triage — run-kit#1, run-kit#5, run-kit#7, video-teardown#16, ad-handoff#7, asset-index#11, chain-runner#5, meta-upload#15, meta-upload#22, qc-checks#13, swipe-paid#3, system-integration#8, image-production#22, video-production#2, marketing-chain-checks#6, marketing-chain-checks#20, marketing-chain-checks#21, image-edit#6, video-edit#15 (the developer, relayed verbatim by ◆ PLAN [fab344] at or before 04:41:48Z: "go on Track A with the guards"; decision log 2026-10-09). PLAN proposed 22; the lead KEPT three as key work: audio-teardown#21 (ELEVENLABS_API_KEY in neither env.template nor the lab-run ceiling, plus a grant row), video-teardown#6 and audio-teardown#11 (both edit a keys.py that SI-193 (video-teardown keys reader) / SI-194 (readers use loader) rewrite — fixed with them to avoid two hands on one loader). video-production#2 is un-held for its by-file loads; its sound.py keys.py import rides SI-194 (readers use loader). Track A cards: SI-192 (keys loader) to SI-196 (key checks report-only), new-workflow-design/builds/system-path/task-cards.md. keys#11 (D1) stays held for Track B.

**Not held** (done now on the developer's word): keys#9 and research-gatherer#6 (a database password visible in the process list; fixed with the existing pg_argv helper), keys#7 (stale docs that still describe a closed Slack token leak).

**Also tied to the migration, outside triage:** the Junip store key rotates with the migration (decision log 2026-09-30). The Meta token renewal before 2026-10-22 is NOT held: it is on Operator B's list.

**What the hold costs:** four components stay blocked for anyone but the owner because of a key read by path: video-teardown, video-production, video-edit, image-teardown (their 6 Oct /system-ready reports). They run on the owner's Mac today.

## The held issues, by component (67 on 7 Oct; 19 moved out 9 Oct)

| Issue | Priority | What | Triage action |
|---|---|---|---|
| ad-handoff#1 | P0 | A key read by path, through video-teardown's keys module | A-read-every-key-by-name-through-the-keys-register |
| ad-handoff#9 | P2 | No key on any mini lane it could ride | A-give-the-mini-the-key-names-and-grants-it-needs |
| audio-teardown#2 | P2 | Two keys are not in env.template | A-read-every-key-by-name-through-the-keys-register |
| audio-teardown#3 | P2 | Keys travel on the command line | A-read-every-key-by-name-through-the-keys-register |
| audio-teardown#11 | P2 | The docs trail the code | L-audio-teardown |
| audio-teardown#15 | P2 | keys.py is one of four loaders the keys component would replace | A-read-every-key-by-name-through-the-keys-register |
| audio-teardown#21 | P2 | No component run row | A-read-every-key-by-name-through-the-keys-register |
| casting#3 | P1 | OPENAI_API_KEY is not in env.template and has a person-bound Keychain fallback | A-read-every-key-by-name-through-the-keys-register |
| copywriter#15 | P1 | The mini proof is nine days old and its inputs moved | A-give-the-mini-the-key-names-and-grants-it-needs |
| email-production#7 | P1 | The declared test fails on any machine without the owner's key helper | A-read-every-key-by-name-through-the-keys-register |
| email-production#9 | P1 | Keys come through the owner's Keychain helper, loaded by path from ~/.daemn | A-read-every-key-by-name-through-the-keys-register |
| image-edit#4 | P2 | The edit model's key is not on the mini | A-give-the-mini-the-key-names-and-grants-it-needs |
| image-production#1 | P1 | Six key reads by path (the WALL) | A-read-every-key-by-name-through-the-keys-register |
| image-production#3 | P2 | Every picture spends a key the mini does not hold | A-give-the-mini-the-key-names-and-grants-it-needs |
| image-production#7 | P2 | The key lookup falls back to a Keychain the org dropped | A-read-every-key-by-name-through-the-keys-register |
| image-teardown#1 | P0 | Keys are read by path, not by name | A-read-every-key-by-name-through-the-keys-register |
| image-teardown#11 | P2 | Keys reached through the dropped Keychain route | A-read-every-key-by-name-through-the-keys-register |
| image-teardown#21 | P1 | Who runs it besides the owner is not written anywhere | A-read-every-key-by-name-through-the-keys-register |
| keys#1 | P2 | The contract does not name pg_argv, and keys has no Residents row | A-read-every-key-by-name-through-the-keys-register |
| keys#3 | P2 | The test reaches into the worker to assert plane_loader's re-export | L-keys |
| keys#5 | P2 | The plan moves or re-points env.template and adds atlas nodes | L-keys |
| keys#6 | P2 | The planned loader is copy N+1 of three candidate rows and a resident | A-read-every-key-by-name-through-the-keys-register |
| keys#8 | P2 | The register must follow 'component runs get the keys their code reads' | A-give-the-mini-the-key-names-and-grants-it-needs |
| keys#10 | P2 | The phase-1 card is not minted | L-keys |
| keys#11 | P2 | D1 — how files are sent, and whether admins keep a copy — is open | L-keys |
| keys#12 | P2 | Two coined id tags are not in team/id-tags.json | L-keys |
| marketing-chain-checks#15 | P2 | The viewer check reads OPENAI_API_KEY only through daemn_keys, and GEMINI_API_KEY falls back to it (review C1, fit C1) | A-read-every-key-by-name-through-the-keys-register |
| marketing-chain-checks#29 | P2 | Operator B adds OPENAI_API_KEY to env.template, only if the owner keeps the fallback (ready task 3, CONDITIONAL) | A-read-every-key-by-name-through-the-keys-register |
| meta-upload#3 | P1 | The Meta token is read from one person's Keychain, never the environment | A-read-every-key-by-name-through-the-keys-register |
| meta-upload#26 | P2 | Technical finish for a second person: the Meta key handed over by name | A-read-every-key-by-name-through-the-keys-register |
| metrics#16 | P2 | Two contracts are missing: reorder-model.js and the keys library | A-read-every-key-by-name-through-the-keys-register |
| research-gatherer#2 | P2 | Six key names outside env.template, and a vault fallback only the owner's Mac has | A-read-every-key-by-name-through-the-keys-register |
| research-gatherer#10 | P2 | Not runnable on the mini | A-give-the-mini-the-key-names-and-grants-it-needs |
| run-kit#20 | P2 | No key route for the model call | L-run-kit |
| swipe-organic#4 | P1 | One script reads the Apify key from one person's Keychain only | A-read-every-key-by-name-through-the-keys-register |
| swipe-paid#9 | P2 | ADPLEXITY_API_KEY is not in env.template or the owner's grant; SUPABASE_DB_URL is not in his grant | A-give-the-mini-the-key-names-and-grants-it-needs |
| triage#17 | P0 | The Slack census test commits a Slack extract and reads a token name the mini does not know | A-read-every-key-by-name-through-the-keys-register |
| run-kit#20 | P2 | No key route for the model call (added 2026-10-07 ~10:15Z, triage seven item 3) | L-run-kit |
| video-edit#21 | P0 | WALL: the edit-map line reads the ElevenLabs key through ~/.daemn/daemn_keys | A-read-every-key-by-name-through-the-keys-register |
| video-edit#22 | P2 | The ElevenLabs key rides curl's command line | A-read-every-key-by-name-through-the-keys-register |
| video-production#1 | P0 | Keys are read by path, and the board writes one to a file | A-read-every-key-by-name-through-the-keys-register |
| video-production#6 | P2 | Three keys are not on the mini | A-give-the-mini-the-key-names-and-grants-it-needs |
| video-production#10 | P2 | Nine files carry their own key reader | A-read-every-key-by-name-through-the-keys-register |
| video-production#26 | P2 | Who runs it besides the owner is not written anywhere | A-read-every-key-by-name-through-the-keys-register |
| video-teardown#1 | P0 | Keys are read by path, not by name — a WALL | A-read-every-key-by-name-through-the-keys-register |
| video-teardown#6 | P2 | Pointers that do not resolve | L-video-teardown |
| video-teardown#22 | P2 | Three keys missing from the template, and no by-name loader | A-read-every-key-by-name-through-the-keys-register |
| video-teardown#23 | P2 | Second-person verify on one real input, then the end-user SOP | A-read-every-key-by-name-through-the-keys-register |

Totals: {'P0': 6, 'P2': 53, 'P1': 9, 'P3': 1}. When the migration lands, each issue is closed with the migration commit as evidence, or re-checked by the next triage refresh.
