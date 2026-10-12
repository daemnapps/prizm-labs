# meta-strategy

## How to use it → (team dashboard)

**The Meta strategy, as a system.** It sets up the account, the ad sets and every creative the way Meta's delivery system rewards, with each rule cited to Meta's own words. Read `STRATEGY.md` first.

| File | What |
|---|---|
| `STRATEGY.md` | The playbook: setup, the new-creative rules, the weekly loop, where each rule is enforced |
| `rules.json` | The same rules, machine-readable; each one says whether it's Meta's or ours |
| `audit.py` | Grades a brand's live account against the rules: `python3 components/meta-strategy/audit.py <brand>` → `runs/meta-strategy/<brand>/<date>/scorecard.json`. One structure read from Meta per brand per day, cached. |

Works with:
- `components/creative-diversity/`: the live library read (pull · tag · matrix), the brief checker (`check.py`) and the sources (`META.md`)
- `components/meta-upload/`: approval-card checks `offer`, `sound`, `new_footage` and `diversity`; Approve → On / Paused; one broad ad set per offer

**Owner:** the owner. Built 2026-10-07. Meta is read lightly: one pull per brand per day.
