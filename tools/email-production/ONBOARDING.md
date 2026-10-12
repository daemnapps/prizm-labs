# Running a brand on this system — the contract

RULED (the owner, 2026-08-31): this system is completely brand-agnostic. Numerous
brands run through it. **The tool carries the machinery; the brand carries
every fact.** A new brand onboards by filling its folder — never by editing a
tool, a prompt, or a check. If onboarding a brand requires touching anything
in this folder, that is a defect in the system, not a task for the brand.

## What the tool owns (this folder — brand-free, verified 2026-08-31)

- The chain (`email.py`, 10 stage prompts), the composer (`compose.py`,
  `prompts/composer-v3-damon.md`), the briefs (`brief.py`), the HTML
  reconstructor (`render_email.py`), the image filler (`fal_generate.py`),
  the sweep tools (`sweep/`), the pulls (`pull/`), the page
  (`build_dashboard.py`), and the rules (SLOT.md, CONTRACT.md, DOCTRINE).
- the starter type catalogue a brand copies and then owns — now
  `lab/marketing-calendar/definitions/send-types.seed.json`, since
  the calendar is what types a send against it (moved 2026-09-13).

No prompt, check, or renderer names a brand, an avatar, a segment, a look,
or a number. Where one used to (the type catalogue, the segment vocabulary,
one avatar's offer rule, the photographic register, the page header), it now
resolves through the brand's folder.

## What the brand must own — `brands/<brand>/`

| The brand fact | File | Read by |
|---|---|---|
| Avatars + sub-avatars + language | `core-avatars/<avatar>/…` + `language-index.json` | chain, composer, page |
| Products | `products/*.md` | chain, composer |
| Offers, sectioned `## <avatar>` — **an avatar with no section carries no offers** | `products/offer-bank.md` | chain, composer, checker |
| Objections | `core-avatars/objection-bank.md` | chain |
| Cultural moments, per avatar, four streams | `calendar/moments.json` | composer |
| Sender identity | `email/identity/sender.md` | chain |
| Variable map for this surface | `variables/email.md` | chain |
| **The type catalogue** — copied from the seed, then owned: counts, notes, brand-born types | `email/email-types.json` | composer, chain, page |
| Segment vocabulary + sizes (from the platform) | `email/audience-matrix.json` (built by `pull/matrix.py`) + `email/segments.md` | composer, checker |
| The sent record: ledger, sends, classified, performance, learnings | `email/…` (built by `pull/*`, proposed under `runs/email-production/<brand>/facts-<YYYY-MM-DD>/`; a person folds it in) | composer, chain, page |
| **The design skin**: palette, type, layout, footer, `photo_register` | `email/design-formats/components.json` | reconstructor, image filler |
| Design formats + census + sweep records | `email/design-formats/…` | page, production |
| The adopted calendar, per month | `email/calendar-<YYYY-MM>.json` | everyone |
| Affiliate partner roster — real partners only, empty is honest | `email/affiliates.json` | calendar flow (schedules one a week the moment this has entries — RULED 2026-09-01, an investor commitment, not a data signal) |

Anything missing prints a NOTE or refuses honestly — nothing is invented.

## Onboarding a new brand, in order

1. Create `brands/<brand>/` with avatars, products, offer bank, objections,
   moments, sender identity, and `variables/email.md` (copy brand-b's map as
   the shape).
2. Copy `lab/marketing-calendar/definitions/send-types.seed.json` →
   `brands/<brand>/email/email-types.json`.
   Add the brand's own types and voices; the seed never carries them.
3. Point the pulls at the brand's platform account (`pull/accounts.json`) and
   run them: orders, ledger, sends, classify, performance, learnings. Then
   the segments — **`pull/make_segments.py --brand <brand> --dry-run`** first
   (metric ids resolve per account by name; a metric the brand does not have
   skips its segment rather than guessing), then for real, then
   **`pull/matrix.py --brand <brand>`** (proposes its file under
   `runs/email-production/<brand>/facts-<YYYY-MM-DD>/`; a person folds it
   in). Full nuance, including a brand with
   no segments and a brand with no history: **`CELLS.md`**.
4. Extract the design skin: run the email-teardown lane on the brand's design
   file → `design-formats/` (formats, census, `components.json` with
   `photo_register`).
5. Verify wiring, spending nothing:
   `python3 compose.py <month> --brand <brand> --dry-run` and
   `python3 email.py <a sent email> --brand <brand> --avatar <a> --dry-run`.
6. Compose, adopt, produce — same commands, different `--brand`.

## Known remainders (recorded, not hidden)

- `model.py` / `build_system.py` (the system-map page) still tell the first
  brand's build story; new brands live on the dashboard until the map page
  is generalized.
- `build_dashboard.py` serves one brand per port today (the brand comes from
  the latest compose run); multi-brand serving is a later step.
- The learnings page header still says the first brand's name.
