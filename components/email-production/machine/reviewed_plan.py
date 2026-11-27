"""The month as the reviewer approved it — never the plan as first written
(SI-151 (picked subject gated), email-production#11, 2026-10-08).

    import reviewed_plan as RP
    RP.reviewed(cal_dir, slots)    # the slots with the review laid on, cut ones gone

A month is planned by the calendar and then CORRECTED by a person on its
review board (marketing-calendar's review.json). Both readers — run_month,
which writes the sends, and the_slot, which a push reads its audience and day
from — read through here, so a reviewer's date or segment edit reaches the
draft and a cut send is never written or pushed.

FAILS CLOSED. marketing-calendar's own review.load reads a corrupt review.json
as "no review at all", which is right for its board and wrong here: an
unreadable review would quietly push the plan the reviewer corrected. So a
review.json that is there and does not read is a named error, and a missing
review module is an ImportError — never "the plan as written". The review
module itself is read, not edited.
"""
import importlib.util
import json
import sys
from pathlib import Path

if "paths" not in sys.modules:             # a caller may have taken this folder OFF the path on purpose
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # (its email.py shadows Python's `email`)
from paths import calendar_tool                               # noqa: E402


class ReviewUnreadable(Exception):
    """review.json is there and is not a review — nothing is produced or pushed."""


def _review():
    """marketing-calendar's review module, found where run_month found it."""
    mod = sys.modules.get("marketing_calendar_review")
    if mod:
        return mod
    machine = calendar_tool("machine")
    f = Path(machine) / "review.py" if machine else None
    if not f or not f.is_file():
        raise ImportError("the marketing-calendar review module was not found "
                          "(calendar_tool('machine') has no review.py)")
    spec = importlib.util.spec_from_file_location("marketing_calendar_review", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["marketing_calendar_review"] = mod
    return mod


def reviewed(cal_dir, slots):
    """`slots` with the reviewer's edits laid on (review.applied), less every
    slot the reviewer cut. Raises ReviewUnreadable when review.json exists
    and is not a JSON object."""
    rev = _review()
    f = Path(cal_dir) / "review.json"
    if f.exists():
        try:
            data = json.loads(f.read_text())
        except (OSError, ValueError) as e:
            raise ReviewUnreadable(f"{f} cannot be read as a review ({e}) — fix or remove it; "
                                   "the plan as written is not the send the reviewer approved")
        if not isinstance(data, dict):
            raise ReviewUnreadable(f"{f} holds a {type(data).__name__}, not a review — fix or remove it")
    return [s for s in rev.applied(slots, rev.load(cal_dir))
            if s["_review"]["status"] != "cut"]
