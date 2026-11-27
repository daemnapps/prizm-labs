#!/usr/bin/env python3
"""Promote a reviewed draft to its family's template: anyone's draft, the
family owner's act (email_lead, 2026-10-21: when editor improves the shared emails
page, the improvement reaches everyone, as on the PM tool).

    python3 features.py promote <draft page> [--person P] [--check] [--no-share]
        exit 0 promoted (or, with --check, would promote) · 2 refused or a
        bad argument · 3 unreadable

Why not /page-share: the share check (share.py) asks every page to prove it
works for someone else, and no page can pass it yet (it has no page scan,
and every wired action waits for PF-4 (page starter kit)'s router). That
check guards a FIRST template. A promotion replaces a template that is
already shared, so the question here is narrower: is the draft no worse than
the template it was cut from?

In order, each one refusing with nothing written:
  1. the person is the family's owner (its features.json `owner`);
  2. the page is a draft of the family, in any person's drafts/ folder;
  3. the draft passes the going-live check (live.check_live: the family
     list, anchors and actions, the overlay untouched, no unmarked demo,
     valid change lines, the data, the live form);
  4. the draft was cut from the template as it is now (its base stamp
     equals the template's git blob id); a template that moved since means
     the author cuts a new draft and redoes the change;
  5. the share check finds no blocker on the draft that it does not also
     find on the template.

Then: the draft's template form (share.template_form) is written to
_templates/<family>.html; its change lines not already there are appended to
_templates/<family>.changes.jsonl; one "live" line goes to
_templates/<family>.live.jsonl (by = the owner, from = the draft); exactly
those paths are shared. The draft and its log are never touched.
Stdlib only, Python 3.9.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import features  # noqa: E402  PF-1 (page-features skeleton), same component
import live  # noqa: E402  PF-7 (working versions), same component
import share  # noqa: E402  PF-9 (share check), same component


def _refused(why, lines=()):
    return {"result": "refused", "lines": ["refused: %s" % why] + list(lines),
            "written": [], "shared": ""}


def _key(blocker):
    return (blocker["level"], blocker["tag"], blocker["what"])


def promote(page, *, person=None, root=None, runner=None, now=None, share_it=True,
            check_only=False):
    """{"result": "promoted" | "would promote" | "refused", "lines", "written",
    "shared"}; see the module docstring."""
    root = os.path.abspath(root or features.ROOT)
    runner = runner or features.run_git
    person = features._person(person, root, runner)
    if not person:
        return _refused("no person — pass --person or set git config user.email")
    rel = features._relpath(page, root)
    match = features.DRAFT_RE.match(rel)
    if not match:
        return _refused("%s is not a draft (%s/<person>/drafts/<family>--<name>.html)"
                        % (rel, features.VIEWERS))
    author, family = match.group(1), match.group(2)
    list_rel = "%s/%s.features.json" % (features.TEMPLATES, family)
    tmpl_rel = "%s/%s.html" % (features.TEMPLATES, family)
    for need in (rel, list_rel, tmpl_rel):
        if not os.path.isfile(os.path.join(root, need)):
            return _refused("%s does not exist" % need)
    try:
        doc = features.load(os.path.join(root, list_rel))
        template = live._read_text(os.path.join(root, tmpl_rel))
    except (OSError, UnicodeDecodeError) as exc:
        return _refused("UNREADABLE: %s" % exc)
    except features.LoadError as exc:
        return _refused(str(exc))

    # 1. owner only
    owner = doc.get("owner") if isinstance(doc, dict) else None
    if not features._nonempty_str(owner):
        return _refused("%s has no owner in its family list; promoting is owner only" % family)
    if owner != person:
        return _refused("only %s promotes a draft to the %s template" % (owner, family))

    # 3. the going-live check, run as the draft's author (it is their draft)
    ctx = live._check(rel, author, root, runner)
    if ctx["refused"] or ctx["unreadable"]:
        return _refused(ctx["refused"] or ctx["unreadable"])
    if ctx["failures"]:
        return _refused("the draft does not pass the going-live check (%d)"
                        % len(ctx["failures"]), ["  %s" % f for f in ctx["failures"]])

    # 4. cut from the template as it is now
    code, out, err = runner(["git", "hash-object", "--", tmpl_rel], root)
    if code != 0:
        return _refused("cannot hash %s: %s" % (tmpl_rel, features._first_line(out, err)))
    now_sha, base = out.strip(), ctx["base"]
    if base != now_sha:
        return _refused("the template changed since this draft was cut (base %s → now %s): "
                        "%s cuts a new draft and redoes the change there"
                        % (base[:7] if base else "none", now_sha[:7], author))

    # 5. no new share-check blocker
    mine = share.share_check(rel, root=root, runner=runner)
    theirs = share.share_check(tmpl_rel, root=root, runner=runner)
    for result in (mine, theirs):
        if result["refused"]:
            return _refused(result["refused"])
    known = set(_key(b) for b in theirs["blockers"])
    new = [b for b in mine["blockers"] if _key(b) not in known]
    if new:
        return _refused("the draft adds %d share-check blocker%s the template does not have"
                        % (len(new), "" if len(new) == 1 else "s"),
                        ["  %s %s: %s (fix: %s; %s)" % (b["level"], b["tag"], b["what"],
                                                       b["fix"], b["owner"]) for b in new])

    log_rel = live._log_rel(tmpl_rel)
    record_rel = "%s/%s.live.jsonl" % (features.TEMPLATES, family)
    have = live._parsed(os.path.join(root, log_rel))
    fresh = []
    for obj in ctx["objs"]:
        if obj not in have and obj not in fresh:
            fresh.append(obj)
    if check_only:
        return {"result": "would promote", "written": [], "shared": "",
                "lines": ["would promote: %s → %s · %d change line%s"
                          % (rel, tmpl_rel, len(fresh), "" if len(fresh) == 1 else "s")]}

    html = live._read_text(os.path.join(root, rel))
    live._write_atomic(os.path.join(root, tmpl_rel), share.template_form(html, template))
    live._append(os.path.join(root, log_rel), features.dumps_changes(fresh))
    at, _ = live._stamp(now)
    record = {"kind": "live", "at": at, "by": person, "from": rel, "base": base,
              "old": None, "changes": len(fresh)}
    live._append(os.path.join(root, record_rel), features.dumps_changes([record]))
    written = [tmpl_rel, log_rel, record_rel]
    lines = ["promoted: %s is now %s's draft %s" % (tmpl_rel, author, os.path.basename(rel)),
             "%d change line%s logged" % (len(fresh), "" if len(fresh) == 1 else "s")]
    shared = live._shared(written, "page: template %s from %s's draft (%s promoted it)"
                          % (family, author, person), root, runner, share_it)
    return {"result": "promoted", "lines": lines, "written": written, "shared": shared}


def main(argv=None, *, root=None, runner=None):
    """`<draft page> [--person P] [--check] [--no-share]` (argv excludes "promote")."""
    parser = argparse.ArgumentParser(prog="features.py promote", add_help=False)
    parser.add_argument("page")
    parser.add_argument("--person")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-share", action="store_true")
    try:
        opts = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit:
        return 2
    result = promote(opts.page, person=opts.person, root=root, runner=runner,
                     share_it=not opts.no_share, check_only=opts.check)
    for line in result["lines"]:
        print(line)
    if result["shared"]:
        print(result["shared"])
    if result["result"] in ("promoted", "would promote"):
        return 0
    return 3 if result["lines"][0].startswith("refused: UNREADABLE") else 2


if __name__ == "__main__":
    sys.exit(main())
