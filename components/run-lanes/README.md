# run-lanes

Keeps what you make private, and lets a team see only the brand lanes that are theirs.

You say "keep my runs private" or "share this run with the team". Claude runs it. You never type a command.

| | |
|---|---|
| **Private by default** | This repo's `runs/` is a folder on your own computer, never pushed and never shared |
| **Brand lanes** | Each brand you list links to the team's own run folder, so the team sees that brand's work and nothing else |
| **The past stays reachable** | Run folders the team already had are linked in on the day you switch, so no tool loses its history |
| **Share on purpose** | `share` moves one private run into the team's folder and links it back |
| **Undo** | Refuses while private work is in the folder, so nothing is lost |

The settings name brands and folders, so they live outside this repo (`~/.prizm/lanes.json`, or `LANES_FILE`):
`{"team_runs": "<the team's runs folder>", "shared_brands": ["brand_a"]}`.

Run `relink` when the team adds a brand folder a tool did not have before.

## Keys this tool needs

None.
