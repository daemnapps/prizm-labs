*v1 (2026-09-28, Damon: "anytime any of that language is used, we clearly mark it as used in X asset, right? We can index and search between things that have been used and things that have not been used, and then we can get performance metrics on what has been used and what's not been used."). No model runs this stage. `machine/mark_used.py` runs it after the brief, on every chain.*

# 5u · MARK USED — what this stage does

After the brief is written, every customer-language row the asset used is
marked as used in that asset.

**Where it looks:**

1. **Cited rows.** The stages that are handed language rows (injection,
   hooks, expansion) end with a `LANGUAGE USED:` block naming each row's id.
   Every id listed there is recorded as `cited`.
2. **Matched rows.** The brief is read against the bank. A row whose words
   appear verbatim in the brief is recorded as `matched`, even if no stage
   cited it. The row must be long enough to mean something: a row under
   four words is only ever recorded when a stage cited it.

**Where it writes:** `brands/<brand>/core-avatars/<avatar>/language/used/<run>.json`,
one file per asset, in the shape `brands/language-schema.md` sets out under
"The used lane".

**What it never does:** edit a bank row. A row's `status` (active, retired or
burned) stays Damon's call.

**What it reports:** how many rows were used, split into cited and matched,
and where the file landed.
