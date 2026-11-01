# Moved → `components/marketing-chain-checks/`

## How to use it → https://dashboard.the company.com/atlas#c-components-quality-checks

Renamed 2026-10-02 on the owner's word: *"we need to name this thing something else
… call it marketing chain checks."* The old name sat one letter-group away from
the team's `components/qc-checks/`, which is a different component.

This folder is a **tombstone**: `quality_checks` here forwards every import to
`marketing_chain_checks`, so sessions and worktrees opened before the rename
keep running. Nothing lives here. Remove it once no caller imports
`quality_checks` (check: `grep -rn "quality_checks" components lab platform`).
