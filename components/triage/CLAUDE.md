# components/triage — one engine, a theme per list

**Status: PROPOSED design, partly built.** Run by hand on two themes on 2026-10-02. The first code here is `tools/file_record.py`, which files one act to the decision log (tests in `tests/`). The tools that produce today's lists are in `new-workflow-design/builds/atlas/tools/` until the refactor moves them (open issue triage #11).

## Owners (the developer, 2026-10-02)

Components rule 6 (two owner roles) applies:
- **Engine owner: the developer, "for now".** The nine steps, the item shape, the queue page, the decision log, and the cross-reference resolvers. Any change every theme would feel.
- **Theme (definition) owners, who are also the triage owners:**
  - the email lead: `themes/atlas.json` (components / atlas);
  - the designer: `themes/operations.json` (operations).

  A theme owner changes their own theme file without asking.

## Rules that bind work here

1. **The engine names no person, folder or rule.** What an item is, how items group, how actions rank, who decides and what an item links to all come from the theme file. A change that only one theme needs goes in its theme file. A change that would alter every theme goes to the engine owner.
2. **Born with the eight parts** (the developer, 2026-10-02, a standing rule). Anything triage creates arrives with the SCHEMA §5 summary from the start: a signal, an action group, an issue it files, or a card it proposes. Nothing is summarised later. Items read from elsewhere without one are listed as gaps, never invented.
3. **Every act goes to the decision log.** Each act on an item is one `triage` record (kind ATL-28 (triage record kind)); there is no weekly digest. The org's decision log (`the-org/decision-log.md`) holds rulings; a `decide` record points at a ruling and never copies it.
4. **The walls bind every theme**, and no theme file may loosen one.
5. **The triage owner works the list first.** "Ready" means the triage owner can do it alone.

## Opening a list

Use the team skill `/triage <theme>` (`.claude/skills/triage/`). It refreshes, renders, opens and explains a list from its data; nobody needs a shared link.

## Where things are

`README.md` (start here) · `HANDOFF.md` (current state) · `CONTRACT-themes.md` (the engine and theme contract) · `themes/` (one file per theme, plus findings) · `flow-triage.json` (the atlas flow; `/atlas-view` draws `triage-atlas-page.html` from it) · `approach-two-themes.html` (the meeting page) · `proposals/` (Option 3, the decision log) · `history/` (red tests, paused, and superseded pages).
