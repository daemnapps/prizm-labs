#!/usr/bin/env python3
"""WM-25 (verdict cap one source) — the cap this repo obeys, declared ONCE.

ONE constant, `MAX_VERDICT_BYTES`. Every module on this side that writes a
record to the review plane imports it; none keeps a literal. Before this file
the number lived as `CAP = 16 * 1024` in six writers by hand, and the name the
server gives it appeared nowhere here at all.

WHO OWNS THE NUMBER — ai-dev, not us. The review API declares it in
`review-app/lib/record-validate.mjs` as

    export const MAX_VERDICT_BYTES = 16384;

and `validateRecordShape()` REFUSES a record whose verdict exceeds it with
`400 verdict too large (16KB max)`. Nothing is written. This file is a MIRROR
of that declaration, kept by hand and guarded by a test, and the name is
deliberately identical so a reader searching either repo finds both.

WHY MIRRORED AND NOT READ. A worker must import its cap without an ai-dev
checkout on the box — the two repos are cloned independently, and a writer
that cannot start because a sibling directory is missing is a worse failure
than the drift this guards against. So the number is copied, and the copy is
policed: `new-workflow-design/builds/worker-multirepo/test_verdict_cap.py`
reads record-validate.mjs when that checkout is present and FAILS LOUDLY if
the two disagree. When it is absent the test SKIPS WITH A STATED REASON — it
never passes on having found nothing, because a green light earned by an
empty search is the exact failure WM-25 (verdict cap one source) was carded
to end.

MOVING THE NUMBER IS A SEPARATE ACT. Raising or lowering it here without
ai-dev moving first buys nothing: the server refuses regardless, and a higher
local cap only means the refusal arrives after the work instead of before it.
Change ai-dev's declaration, then this mirror, then run the test.

WHAT IT DOES *NOT* GOVERN. This bounds the VERDICT — the JSON body of one
record. It is not the blob upload ceiling (`UPLOAD_MAX_BYTES`, 4 MiB), not the
snapshot's per-record embed ceiling (`RECORD_MAX`, 1 MiB), and not any
writer's own smaller inline budget (mint_round's `INLINE_MAX_BYTES`, 12 KB —
deliberately under this, so a brief that fits the round still fits the plane).
Those are different questions with different answers.

BEHAVIOUR AT THE CAP IS THE WRITER'S, NOT THIS FILE'S. What a writer does on
reaching the cap — refuse, shed, re-serialize compact — belongs to that writer.
candidate_scan.py's WM-24 (index truncation) ladder (pretty -> compact -> shed
`where` -> RAISE)
is the reference shape: whitespace is spent before data, and data is dropped
whole-field or not at all. A blind `body[:CAP]` slice writes a truncated
record that no longer parses, which is how three records died in September.
"""

# The mirror of ai-dev's `record-validate.mjs` line 29. Keep the literal HERE
# and nowhere else — the declared test asserts no other module under
# platform/workers/ carries it.
MAX_VERDICT_BYTES = 16384

# Where the number comes from, in machine-readable form so the cross-repo test
# and a human reading a traceback agree on what to go look at.
SOURCE_REPO = "ai-dev"
SOURCE_FILE = "review-app/lib/record-validate.mjs"
SOURCE_CONST = "MAX_VERDICT_BYTES"

__all__ = ["MAX_VERDICT_BYTES", "SOURCE_REPO", "SOURCE_FILE", "SOURCE_CONST"]
