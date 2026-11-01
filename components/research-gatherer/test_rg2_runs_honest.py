#!/usr/bin/env python3
"""SI-160 (gatherer runs honest)'s declared test.

    python3 components/research-gatherer/test_rg2_runs_honest.py

No pytest, no network, no key — same convention as test_research_gatherer.py.
Every Apify-touching call is stubbed and every write lands in a temp dir.
Five cases:

1. the declared test's inputs case leaves the real runs/research/ exactly as
   it found it — listing and mtimes — and deletes nothing outside its temp dir;
2. a confirmed rooms block in `rooms` mode never calls discovery;
3. a deep pull's cap is a TOTAL: cap 1 over 2 questions requests at most 1;
4. a voiceprint dry run off a cached transcript writes no file;
5. the report's bands count only posts an accepted entry carries.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import research_gatherer.engine as R  # noqa: E402
import research_gatherer.annotate as A  # noqa: E402
import research_gatherer.voiceprint as V  # noqa: E402

_FAILURES = []


def check(label, ok, detail=""):
    if ok:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s%s" % (label, (" — " + detail) if detail else ""))
        _FAILURES.append(label)


def section(title):
    print("\n%s" % title)


class _Patch:
    """Set an attribute for the life of a `with` block, then put it back."""

    def __init__(self, obj, name, value):
        self.obj, self.name, self.value = obj, name, value
        self._had = hasattr(obj, name)
        self._old = getattr(obj, name, None)

    def __enter__(self):
        setattr(self.obj, self.name, self.value)
        return self

    def __exit__(self, *a):
        if self._had:
            setattr(self.obj, self.name, self._old)
        else:
            delattr(self.obj, self.name)


def _boom(*a, **k):
    raise AssertionError("this should never have been called")


def _snapshot(root):
    """{relative path: mtime_ns} for root itself and everything under it;
    None when root does not exist."""
    root = Path(root)
    if not root.exists():
        return None
    out = {".": root.stat().st_mtime_ns}
    for d, dirs, files in os.walk(str(root)):
        for n in dirs + files:
            p = Path(d) / n
            try:
                out[str(p.relative_to(root))] = p.lstat().st_mtime_ns
            except OSError:
                pass
    return out


def _files_under(root):
    return sorted(str(p.relative_to(root)) for p in Path(root).rglob("*") if p.is_file())


class _Door:
    """Stands in for components/apify/reddit.py — score and date off the row."""

    @staticmethod
    def score(r):
        return r.get("ups")

    @staticmethod
    def when(r):
        return r.get("createdAt") or ""


CONFIRMED_SUB = ("---\nid: x\n---\n\n### sub-01-x — X\n\n"
                 '- **Core desire:** "I want my dark spots to fade for good"\n\n'
                 "### rooms — Where they talk\n\nconfirmed by: Tester\n- r/one — a room\n\n"
                 "### language-delta\n\n- keep me\n")
SEEDED_SUB = CONFIRMED_SUB.replace("confirmed by: Tester\n", "")
CONFIRMED_EMPTY_SUB = CONFIRMED_SUB.replace("- r/one — a room\n", "")


def _sub_tree(tmp, text):
    subs = tmp / "brands" / "b" / "core-avatars" / "a" / "sub-avatars"
    subs.mkdir(parents=True, exist_ok=True)
    f = subs / "sub-01-x.md"
    f.write_text(text)

    def _fake_sub_file(brand, avatar, sub, root=None):
        return f if (brand, avatar, sub) == ("b", "a", "x") else None
    return f, _fake_sub_file


# ---------------------------------------------------------------- 1. the inputs case touches nothing real

def test_inputs_case_leaves_real_runs_alone():
    section("1. test_research_gatherer's inputs case leaves the real runs/research/ untouched")
    # Imported and called in-process (not a subprocess), so the rmtree spy
    # below sees every delete the case asks for.
    import test_research_gatherer as T
    real_ws = Path(R.WORKSPACE).resolve()
    real_research = real_ws / "runs" / "research"
    before = _snapshot(real_research)

    deletes, refused = [], []
    real_rmtree = shutil.rmtree

    def _spy_rmtree(path, *a, **k):
        p = Path(path).resolve()
        deletes.append(str(p))
        if p == real_ws or real_ws in p.parents:
            refused.append(str(p))      # never let it through — that is the wall
            return None
        return real_rmtree(path, *a, **k)

    n_fail = len(T._FAILURES)
    with _Patch(shutil, "rmtree", _spy_rmtree), contextlib.redirect_stdout(io.StringIO()) as buf:
        T.test_no_key_never_raises()
    after = _snapshot(real_research)

    check("the inputs case itself is still green", len(T._FAILURES) == n_fail,
          str(T._FAILURES[n_fail:]) + "\n" + buf.getvalue())
    check("R.WORKSPACE is put back after the case", Path(R.WORKSPACE).resolve() == real_ws,
          str(R.WORKSPACE))
    check("the real runs/research/ listing and mtimes are identical before and after",
          before == after,
          "added %s, removed %s, changed %s" % (
              sorted(set(after or {}) - set(before or {}))[:5],
              sorted(set(before or {}) - set(after or {}))[:5],
              sorted(k for k in set(before or {}) & set(after or {})
                     if before[k] != after[k])[:5]))
    check("nothing under the real workspace was asked to be deleted", refused == [], str(refused))
    check("the case still cleans up its own temp dir", len(deletes) >= 1, str(deletes))


# ---------------------------------------------------------------- 2. a confirmed block never triggers discovery

def test_confirmed_rooms_block_never_discovers():
    section("2. rooms mode: a confirmed block never calls discovery")
    tmp = Path(tempfile.mkdtemp())
    try:
        calls = []

        def _stub_detail(brand, avatar, sub, **kw):
            calls.append((brand, avatar, sub))
            return dict(ok=False, why="[UNFILLED: stub]", rooms=[], dropped=[], spend=0.0)

        for label, text in (("confirmed", CONFIRMED_SUB), ("confirmed but empty", CONFIRMED_EMPTY_SUB)):
            f, fake = _sub_tree(tmp, text)
            for extra in ([], ["--dry-run"]):
                del calls[:]
                with _Patch(R, "WORKSPACE", tmp), _Patch(R, "sub_file", fake), \
                        _Patch(R, "_find_rooms_detail", _stub_detail), _Patch(R, "_run_reddit", _boom), \
                        contextlib.redirect_stdout(io.StringIO()) as buf:
                    rc = R.main(["rooms", "--brand", "b", "--avatar", "a", "--sub", "x"] + extra)
                out = buf.getvalue()
                tag = "%s%s" % (label, " --dry-run" if extra else "")
                check(f"{tag}: _find_rooms_detail is never called", calls == [], str(calls))
                check(f"{tag}: returns 0", rc == 0, str(rc))
                check(f"{tag}: the file is untouched", f.read_text() == text)
                if extra:
                    check(f"{tag}: says `confirmed — no discovery`, not `would search`",
                          "confirmed — no discovery" in out and "would search" not in out, out)
                if label == "confirmed but empty":
                    check(f"{tag}: surfaced as a hold, never silently re-discovered",
                          "HELD: confirmed but empty" in out, out)
                else:
                    check(f"{tag}: no hold on a confirmed block that lists rooms",
                          "HELD" not in out, out)

        # Sanity: the same stub IS reached for a seeded block, so (2) proves something.
        f, fake = _sub_tree(tmp, SEEDED_SUB)
        del calls[:]
        with _Patch(R, "WORKSPACE", tmp), _Patch(R, "sub_file", fake), \
                _Patch(R, "_find_rooms_detail", _stub_detail), \
                contextlib.redirect_stdout(io.StringIO()):
            R.main(["rooms", "--brand", "b", "--avatar", "a", "--sub", "x"])
        check("a seeded block still runs discovery (the stub is reachable)", len(calls) == 1, str(calls))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 3, 5. deep pull: cap is a total; bands count what passed

TWO_QUESTIONS = [{"id": "q-one", "tags": ["mechanism"]}, {"id": "q-two", "tags": ["objection"]}]


def _deep(tmp, cap, rows_for, enrich=None):
    """deep_for over a confirmed temp sub-avatar, every door stubbed.
    -> (result, [cap requested per call])."""
    f, fake = _sub_tree(tmp, CONFIRMED_SUB)
    caps = []

    def _stub_reddit(rooms, queries, c, out_dir, sort=None, time_window=None, no_comments=False):
        caps.append(c)
        return rows_for(len(caps), c), "", 0.0

    with _Patch(R, "WORKSPACE", tmp), _Patch(R, "sub_file", fake), \
            _Patch(R, "_find_rooms_detail", _boom), _Patch(R, "_run_reddit", _stub_reddit), \
            _Patch(R, "schwartz_questions", lambda: (list(TWO_QUESTIONS), False)), \
            _Patch(R, "reddit_door", lambda: _Door), \
            _Patch(A, "enrich_deep", enrich or (lambda entries, *a, **k: entries)), \
            contextlib.redirect_stdout(io.StringIO()):
        res = R.deep_for("b", "a", "x", cap)
    return res, caps


def _post(n, ups):
    return {"title": "post %d" % n, "body": "body %d" % n, "communityName": "one", "ups": ups,
            "url": "https://reddit.com/r/one/%d" % n, "createdAt": "2026-10-01"}


def test_cap_is_a_total():
    section("3. a deep pull's cap is a total across questions")
    tmp = Path(tempfile.mkdtemp())
    try:
        res, caps = _deep(tmp, 1, lambda i, c: [_post(i, 5)][:c])
        check("cap 1, 2 questions -> at most 1 row requested in total", sum(caps) <= 1, str(caps))
        check("...and the one request was made", caps == [1], str(caps))
        check("the pull still files its row", res.get("rows_written") == 1, str(res))

        tmp2 = Path(tempfile.mkdtemp())
        try:
            _res, caps2 = _deep(tmp2, 10, lambda i, c: [_post(100 * i + k, 1) for k in range(c)])
            check("cap 10, 2 questions -> never above 10 in total", sum(caps2) <= 10, str(caps2))
            check("...shared across both questions", len(caps2) == 2 and all(c >= 1 for c in caps2),
                  str(caps2))
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_bands_count_only_accepted_entries():
    section("5. the report's bands are built from the accepted entries only")
    tmp = Path(tempfile.mkdtemp())
    try:
        kept = _post(1, 50)
        dropped = _post(2, 999)    # the loudest post — it would top band 1 if it were counted

        def _drop_one(entries, *a, **k):
            return [e for e in entries if e["source"]["ref"] != dropped["url"]]

        res, _caps = _deep(tmp, 10, lambda i, c: [kept, dropped] if i == 1 else [], enrich=_drop_one)
        check("one row filed", res.get("rows_written") == 1, str(res))
        check("the bands count one post, not two",
              (res.get("room_count"), res.get("diff_count")) == (1, 0),
              "%s / %s" % (res.get("room_count"), res.get("diff_count")))
        md = (Path(res["out"]) / "research.md").read_text()
        check("the dropped post is absent from the bands", dropped["url"] not in md, md[-600:])
        check("the accepted post is in band 1", kept["url"] in md, md[-600:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 4. voiceprint dry run writes nothing

def test_voiceprint_dry_run_writes_nothing():
    section("4. a voiceprint dry run off a cached transcript writes no file")
    tmp = Path(tempfile.mkdtemp())
    scratch = Path(tempfile.mkdtemp())
    try:
        handle = "someone"
        tdir = V.research_root("b", tmp) / handle / "transcripts"
        tdir.mkdir(parents=True)
        words = [{"text": w, "start": i * 0.4, "end": i * 0.4 + 0.3, "type": "word"}
                 for i, w in enumerate("Okay so I am gonna show you why this works. Right?".split())]
        (tdir / "T-01.json").write_text(json.dumps({"text": "", "words": words}))
        before = _files_under(tmp)

        def _no_ffmpeg(video, out, ffmpeg=None):
            return True, ""

        posts = [{"id": "T-01", "name": "t", "post": "u", "video": str(scratch / "v.mp4"), "exists": True}]
        with _Patch(V, "extract_wav", _no_ffmpeg), _Patch(V, "energy_profile", lambda wav: {}), \
                _Patch(V, "transcribe", _boom), contextlib.redirect_stdout(io.StringIO()):
            vp = V.run_creator("b", handle, posts, None, dry_run=True, root=tmp, scratch=scratch)
        check("the cached transcript was measured", bool(vp) and vp["denominators"]["words"] == len(words),
              str(vp and vp.get("denominators")))
        check("the roll-up is still returned", vp is not None and "avatar_fit" in vp)
        check("no file written under the temp root", _files_under(tmp) == before,
              str(sorted(set(_files_under(tmp)) - set(before))))
        check("no voiceprint.json / voiceprint.md",
              not (tdir.parent / "voiceprint.json").exists() and not (tdir.parent / "voiceprint.md").exists())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(scratch, ignore_errors=True)


def main():
    test_inputs_case_leaves_real_runs_alone()
    test_confirmed_rooms_block_never_discovers()
    test_cap_is_a_total()
    test_voiceprint_dry_run_writes_nothing()
    test_bands_count_only_accepted_entries()
    print("")
    if _FAILURES:
        print("FAILED: %d" % len(_FAILURES))
        for f in _FAILURES:
            print("  - %s" % f)
        return 1
    print("PASSED: all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
