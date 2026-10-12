#!/usr/bin/env python3
"""research-gatherer's declared test.

    python3 components/research-gatherer/test_research_gatherer.py

No pytest, no network, no dependency — same convention as
`components/marketing-doctrine/test_doctrine.py`. Every Apify-touching call
is monkeypatched; nothing here spends a cent or reaches the network. Proves
the things that would quietly rot: a missing key never raises, a row with no
permalink never gets written, a cache hit skips the pull, a dry run spends
nothing, pick-thinnest actually picks the thinnest, a room that plainly
belongs to a different set of people is dropped before a row is filed from it,
and the video-teardown shim still exposes a plain `inputs(st)` wired to this
engine (the LL-1 precedent: the shim is a re-export, not a second
implementation).
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import research_gatherer.engine as R  # noqa: E402

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
    """Set an attribute on a module for the life of a `with` block, then put
    back whatever was there before — including "there was nothing"."""

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


# ---------------------------------------------------------------- 1. no key -> [UNFILLED], never raises

def test_no_key_never_raises():
    section("1. no Apify key -> [UNFILLED], never raises")

    def _no_key(*a, **k):
        raise SystemExit("no APIFY_TOKEN — set the env var or add one line to ~/.daemn/keys.env")

    with _Patch(R, "_run_reddit", _no_key):
        try:
            res = R.pull_forums("brand", "avatar", None, ["r/test"], ["word"], 10,
                                Path(tempfile.mkdtemp()), use_cache=False)
            raised = False
        except Exception:
            raised = True
        check("pull_forums does not raise when the door has no key", not raised)
        check("pull_forums records [UNFILLED]", not res["ok"] and "[UNFILLED" in res["md"], res.get("md", ""))

    def _no_key_layer():
        raise SystemExit("no key")

    with _Patch(R, "apify_layer", _no_key_layer):
        try:
            res = R.pull_comments("https://www.tiktok.com/@x/video/1", 10, use_cache=False)
            raised = False
        except Exception:
            raised = True
        check("pull_comments does not raise when the apify layer has no key", not raised)
        check("pull_comments records [UNFILLED]", not res["ok"] and "[UNFILLED" in res["md"], res.get("md", ""))

    # inputs(st, chain_profile) end to end, with NO chain_profile at all —
    # the language section must say so, and nothing may raise. Uses a temp
    # run_dir so this never writes into the real repo's runs/ tree (found
    # the hard way: an earlier version of this test left a "nobrand" run
    # sitting in the real runs/research/ until this fix).
    tmp_run = Path(tempfile.mkdtemp())
    try:
        with _Patch(R, "_run_reddit", _no_key), _Patch(R, "apify_layer", _no_key_layer):
            st = {"brand": "nobrand", "audience": {"_avatar": "noavatar", "_topics": ["x"]},
                 "source_url": "https://www.tiktok.com/@x/video/1"}
            try:
                out = R.inputs(st)  # no chain_profile -> engine's own fallback out_dir
                raised = False
            except Exception as e:
                raised = True
                out = {"research": str(e)}
            check("inputs(st) never raises with no chain_profile and no key", not raised)
            check("inputs(st) always returns a 'research' string", isinstance(out.get("research"), str))
            check("no chain_profile -> language section says so",
                 "no chain profile given" in out["research"])
    finally:
        shutil.rmtree(tmp_run, ignore_errors=True)
        # inputs(st) with no chain_profile falls back to the engine's own
        # runs/research/_unfiled/ — clean up whatever it wrote there so
        # repeat test runs don't leave debris in the real repo tree.
        shutil.rmtree(R.WORKSPACE / "runs" / "research" / "_unfiled", ignore_errors=True)


# ---------------------------------------------------------------- 2 & 3. bank row schema + permalink drop

def test_bank_row_schema_and_permalink_drop():
    section("2. row schema is the bank's; 3. a row without permalink is dropped")
    posts = {
        "https://reddit.com/r/x/1": {"row": {"title": "T1", "body": "B1",
                                            "communityName": "x", "ups": 12,
                                            "createdAt": "2026-08-01"},
                                     "tags": {"mechanism"}},
        "": {"row": {"title": "no ref, should be dropped", "communityName": "x"},
            "tags": {"objection"}},
    }
    comments = {
        "https://reddit.com/r/x/1/c1": {"row": {"body": "a comment", "communityName": "x",
                                                "score": 3, "created": "2026-08-02"},
                                        "tags": {"role-claimed"}},
    }
    entries = R.build_bank_rows("brand", "avatar", "sub-x", posts, comments)
    check("two entries written (the ref-less one dropped)", len(entries) == 2, str(len(entries)))
    refs = {e["source"]["ref"] for e in entries}
    check("no entry carries an empty ref", "" not in refs)

    required = {"id", "text", "avatar", "sub", "funnel", "speaker", "source",
               "signal", "topics", "use", "status", "fit"}
    for e in entries:
        check(f"entry {e['id']} has every schema field", required <= set(e), str(sorted(e)))
        check(f"entry {e['id']} source has name/type/date/ref",
             {"name", "type", "date", "ref"} <= set(e["source"]), str(e["source"]))
        check(f"entry {e['id']} signal has likes/tier",
             {"likes", "tier"} <= set(e["signal"]), str(e["signal"]))
        check(f"entry {e['id']} avatar/sub match the call", e["avatar"] == "avatar" and e["sub"] == "sub-x")
        check(f"entry {e['id']} use carries the question tags",
             set(e["use"]) & {"mechanism", "role-claimed"} != set())

    post_entry = next(e for e in entries if e["speaker"] == "prospect")
    check("post text combines title and body", post_entry["text"] == "T1 — B1", post_entry["text"])
    comment_entry = next(e for e in entries if e["speaker"] == "commenter")
    check("comment-only row keeps its body as text", comment_entry["text"] == "a comment")

    dropped_only = R.build_bank_rows("brand", "avatar", "sub-x",
                                     {"": {"row": {"title": "x"}, "tags": set()}}, {})
    check("a ref-only-empty bucket yields zero rows", dropped_only == [])


# ---------------------------------------------------------------- 4. cache hit skips the pull

def test_cache_hit_skips_pull():
    section("4. a cache hit skips the pull entirely")
    tmp = Path(tempfile.mkdtemp())
    try:
        with _Patch(R, "_cache_root", lambda: tmp):
            key = ("forums", "brand", "avatar", "", tuple(sorted(["word"])), tuple(sorted(["r/test"])))
            R._cache_put("forums", dict(md="# cached\n", posts=[{"title": "cached post", "url": "u"}],
                                        comments=[]), *key)
            with _Patch(R, "_run_reddit", _boom):
                res = R.pull_forums("brand", "avatar", None, ["r/test"], ["word"], 10, tmp / "out",
                                    use_cache=True)
            check("pull_forums never called the door on a cache hit", res.get("cached") is True)
            check("pull_forums returned the cached posts", len(res["posts"]) == 1)
            check("a cache hit costs nothing", res["spend"] == 0.0)

            key2 = ("comments", "https://www.tiktok.com/@x/video/2")
            R._cache_put("comments", dict(md="# cached comments\n", rows=[{"text": "hi", "likes": 1}]), *key2)
            with _Patch(R, "apify_layer", _boom):
                res2 = R.pull_comments("https://www.tiktok.com/@x/video/2", 10, use_cache=True)
            check("pull_comments never touched the apify layer on a cache hit", res2.get("cached") is True)
            check("cached comments came back", len(res2["rows"]) == 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 5. --dry-run spends nothing

def test_dry_run_spends_nothing():
    section("5. dry_run=True builds queries and spends nothing")
    tmp = Path(tempfile.mkdtemp())
    try:
        avatars = tmp / "brands" / "b" / "core-avatars" / "a" / "sub-avatars"
        avatars.mkdir(parents=True)
        (avatars / "sub-01-thin.md").write_text(
            "---\nid: thin\n---\n\n### sub-01-thin\n\n"
            '- **Core desire:** "I want this fixed for good"\n\n'
            "### rooms — Where they talk\n\n- r/test — a room\n")
        f = avatars / "sub-01-thin.md"

        def _fake_sub_file(brand, avatar, sub, root=None):
            return f if (brand, avatar, sub) == ("b", "a", "thin") else None

        with _Patch(R, "_run_reddit", _boom), _Patch(R, "sub_file", _fake_sub_file), \
                _Patch(R, "_find_rooms_detail", _boom):
            res = R.deep_for("b", "a", "thin", 150, dry_run=True)
        check("dry-run reports dry_run=True", res.get("dry_run") is True)
        check("dry-run names the room it would have used", res.get("rooms") == ["r/test"])
        check("dry-run built at least one query", len(res.get("queries") or []) > 0)
        check("_run_reddit was never called (would have raised if it had been)", True)
        check("dry-run never ran discovery either (would have raised if it had)", True)
        check("dry-run says the block is seeded", res.get("rooms_state") == "seeded",
             str(res.get("rooms_state")))
        check("dry-run says discovery WOULD run on a real run", res.get("would_discover") is True)
        check("dry-run names the discovery query it would fire",
             bool(res.get("discovery_query")), str(res.get("discovery_query")))

        # And the same guarantee on the `rooms` CLI: --dry-run spends nothing.
        with _Patch(R, "_run_reddit", _boom), _Patch(R, "sub_file", _fake_sub_file), \
                _Patch(R, "_find_rooms_detail", _boom):
            rc = R.main(["rooms", "--brand", "b", "--avatar", "a", "--sub", "thin", "--dry-run"])
        check("`rooms --dry-run` returns cleanly and pulls nothing", rc == 0, str(rc))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 6. --pick-thinnest on a temp tree

def test_pick_thinnest_on_temp_tree():
    section("6. pick_thinnest picks the smallest by count on a temp tree")
    tmp = Path(tempfile.mkdtemp())
    try:
        core = tmp / "brands" / "testbrand" / "core-avatars" / "testavatar"
        subs = core / "sub-avatars"
        subs.mkdir(parents=True)
        (subs / "sub-01-thin.md").write_text("---\nid: thin\n---\n\n### sub-01-thin\n")
        (subs / "sub-02-fat.md").write_text("---\nid: fat\n---\n\n### sub-02-fat\n")
        lang = core / "language"
        lang.mkdir()
        (lang / "prospects.json").write_text(json.dumps({
            "schema": 1, "avatar": "testavatar", "entries": [
                {"id": "1", "text": "a", "sub": "fat"},
                {"id": "2", "text": "b", "sub": "fat"},
                {"id": "3", "text": "c", "sub": "fat"},
            ]}))

        picked, ranked = R.pick_thinnest(root=tmp)
        check("a candidate was found", picked is not None)
        check("the thin one (0 rows) was picked over the fat one (3 rows)",
             picked and picked["sub"] == "thin", str(picked))
        check("both candidates were ranked", len(ranked) == 2, str(len(ranked)))
        check("counts are correct", {c["sub"]: c["rows"] for c in ranked} == {"thin": 0, "fat": 3})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 7 & 8. regression + mechanics

def test_parse_rooms_does_not_swallow_the_rest_of_the_file():
    section("7. parse_rooms stops at the next heading (regression: DOTALL swallow)")
    text = ("### sub-x — X\n\n- **Core desire:** \"fix it\"\n\n"
           "### rooms — Where they talk (curated 2026-09-18)\n\n"
           "- r/one — a room\n- r/two — another room\n\n"
           "### language-delta\n\n- this line must NOT show up as a room\n")
    rooms = R.parse_rooms(text)
    check("both rooms are found", rooms == ["r/one", "r/two"], str(rooms))

    empty = R.parse_rooms("### sub-x — X\n\nno rooms heading anywhere here\n")
    check("no rooms heading -> empty list, never a guess", empty == [])


def test_platform_detection_and_query_seeding():
    section("8. platform detection and per-question query seeding")
    check("tiktok url detected", R.platform_of("https://www.tiktok.com/@x/video/1") == "tiktok")
    check("instagram url detected", R.platform_of("https://www.instagram.com/p/abc/") == "instagram")
    check("youtube url detected", R.platform_of("https://youtu.be/abc") == "youtube")
    check("unknown platform is None", R.platform_of("https://example.com/x") is None)
    check("no source_url is None", R.platform_of(None) is None)

    plan = R.build_queries_per_question(["word1", "word2"], R.FALLBACK_QUESTIONS)
    check("one query per question", len(plan) == len(R.FALLBACK_QUESTIONS))
    check("every query carries the desire words", all("word1" in p["query"] for p in plan))
    ids = {p["question"]["id"] for p in plan}
    check("fallback questions are all present", ids == {q["id"] for q in R.FALLBACK_QUESTIONS})


# ---------------------------------------------------------------- 9. the video-teardown shim is a re-export

def test_video_teardown_shim_is_a_reexport():
    section("9. the video-teardown shim re-exports this engine (LL-1 precedent)")
    ws = Path.home() / "Projects" / "workspace"
    machine = ws / "components" / "video-teardown" / "machine"
    shim_path = machine / "research.py"
    if not shim_path.is_file():
        check("video-teardown shim exists", False, str(shim_path))
        return
    sys.path.insert(0, str(machine))
    try:
        import importlib
        if "research" in sys.modules:
            del sys.modules["research"]
        shim = importlib.import_module("research")
        check("shim exposes a plain inputs(st)", callable(getattr(shim, "inputs", None)))
        check("shim's deep_for IS the engine's object, not a copy",
             shim.deep_for is R.deep_for)
        check("shim's pick_thinnest IS the engine's object, not a copy",
             shim.pick_thinnest is R.pick_thinnest)
        check("shim declares a chain_profile with language_stages",
             "depth" in (shim.CHAIN_PROFILE.get("language_stages") or []))
        check("shim's chain_profile names a language_for_stage callable",
             callable(shim.CHAIN_PROFILE.get("language_for_stage")))

        # inputs(st) with no avatar decided must short-circuit identically
        # whether called on the shim or the engine directly — same object,
        # same behaviour, no second implementation to drift.
        st = {"brand": None}
        out_shim = shim.inputs(st)
        out_engine = R.inputs(st, chain_profile=shim.CHAIN_PROFILE)
        check("shim and engine agree on the no-avatar-yet path",
             out_shim == out_engine, str(out_shim)[:120])
    finally:
        sys.path.remove(str(machine))


# ---------------------------------------------------------------- 10. the tally is weighted by score

def test_tally_rooms_weights_by_score():
    section("10. tally_rooms ranks by TOTAL SCORE, not by post count")
    posts = [
        # the busiest room, but quiet: 3 posts, 6 score
        {"communityName": "r/busy", "title": "b1", "ups": 2, "url": "u1"},
        {"communityName": "busy", "title": "b2", "ups": 2, "url": "u2"},
        {"communityName": "r/busy", "title": "b3", "ups": 2, "url": "u3"},
        # the loudest room: 1 post, 100 score
        {"communityName": "r/loud", "title": "the loud one", "ups": 100, "url": "u4"},
        # a room whose rows carry no score at all -> 0, never a crash
        {"communityName": "r/silent", "title": "s1", "url": "u5"},
        {"subreddit": "silent", "title": "s2", "url": "u6"},
        # no room name at all -> never tallied, never invented
        {"title": "orphan", "ups": 999, "url": "u7"},
    ]
    ranked = R.tally_rooms(posts, top=5, score_fn=lambda r: r.get("ups"))
    names = [r["room"] for r in ranked]
    check("the loudest room outranks the busiest", names[:2] == ["loud", "busy"], str(names))
    check("the `r/` prefix is normalised away once", "r/busy" not in names and "busy" in names,
         str(names))
    check("posts counted per room", {r["room"]: r["posts"] for r in ranked}
         == {"loud": 1, "busy": 3, "silent": 2}, str(ranked))
    check("scores summed per room", {r["room"]: r["score"] for r in ranked}
         == {"loud": 100, "busy": 6, "silent": 0}, str(ranked))
    check("a row with no room name is never tallied", "?" not in names and len(ranked) == 3,
         str(names))
    check("every kept room carries a sample title",
         all(r["sample_title"] for r in ranked), str(ranked))
    check("the sample is the room's loudest post",
         next(r for r in ranked if r["room"] == "loud")["sample_title"] == "the loud one")

    top2 = R.tally_rooms(posts, top=2, score_fn=lambda r: r.get("ups"))
    check("top=N keeps exactly N rooms", len(top2) == 2, str(len(top2)))
    check("an empty pull tallies to nothing", R.tally_rooms([], score_fn=lambda r: 0) == [])


# ---------------------------------------------------------------- 11. seeded vs confirmed

SEEDED = ("### sub-x — X\n\n- **Core desire:** \"fix it\"\n\n"
         "### rooms — Where they talk (curated 2026-09-18, Builder C — correct or extend)\n\n"
         "- r/one — a room\n- r/two — another\n\n"
         "### language-delta\n\n- keep me\n")


def test_seeded_vs_confirmed():
    section("11. a rooms block is locked by `confirmed by:`, never by its heading")
    check("an agent-curated block reads as seeded", R.rooms_block_state(SEEDED)[0] == "seeded",
         R.rooms_block_state(SEEDED)[0])
    check("...so rooms_are_confirmed says no", R.rooms_are_confirmed(SEEDED) is False)

    gatherer = SEEDED.replace(
        "### rooms — Where they talk (curated 2026-09-18, Builder C — correct or extend)",
        '### rooms — found 2026-09-18 by the gatherer (edit freely; add "confirmed by: '
        '<your name>" to lock)')
    check("a gatherer block reads as seeded", R.rooms_block_state(gatherer)[0] == "seeded")

    # A person locks it by adding the line — and the gatherer's own heading,
    # which literally contains the words "found ... by the gatherer", must not
    # stop that from counting.
    locked = gatherer.replace("- r/one — a room", "confirmed by: the owner\n- r/one — a room")
    check("adding `confirmed by:` locks a gatherer block",
         R.rooms_block_state(locked)[0] == "confirmed", R.rooms_block_state(locked)[0])
    bulleted = SEEDED.replace("- r/one — a room", "- confirmed by: the owner\n- r/one — a room")
    check("a bulleted `- confirmed by:` locks it too",
         R.rooms_block_state(bulleted)[0] == "confirmed")
    check("a confirmed block's rooms still parse", R.parse_rooms(locked) == ["r/one", "r/two"],
         str(R.parse_rooms(locked)))

    check("no rooms block at all reads as none",
         R.rooms_block_state("### sub-x\n\nnothing here\n")[0] == "none")
    check("empty text reads as none", R.rooms_block_state("")[0] == "none")
    check("the heading is readable for a report",
         "curated 2026-09-18" in R.rooms_block_heading(SEEDED), R.rooms_block_heading(SEEDED))


# ---------------------------------------------------------------- 12. write-back is surgical

def test_write_back_replaces_only_the_seeded_block():
    section("12. the write-back replaces the seeded block and nothing else")
    tmp = Path(tempfile.mkdtemp())
    try:
        f = tmp / "sub-01-x.md"
        f.write_text(SEEDED)
        before = f.read_text()
        m = R.ROOMS_RE.search(before)
        head, tail = before[:m.start()], before[m.end():]

        found = [dict(room="NewRoom", posts=4, score=120, sample_title="t", sample_url="u"),
                 dict(room="Other", posts=2, score=9, sample_title="t2", sample_url="u2")]
        changed = R.write_rooms_block(f, found, when="2026-09-18")
        after = f.read_text()
        check("the file changed", changed is True)
        check("everything BEFORE the block is byte-identical", after.startswith(head), repr(head[-40:]))
        check("everything AFTER the block is byte-identical", after.endswith(tail), repr(tail[:40]))
        check("the old rooms are gone", "r/one" not in after and "r/two" not in after)
        check("the old heading is gone", "curated 2026-09-18, Builder C" not in after)
        check("the new rooms are in", "r/NewRoom" in after and "r/Other" in after)
        check("the heading says found-by-the-gatherer, dated",
             "### rooms — found 2026-09-18 by the gatherer" in after)
        check("the heading tells a person how to lock it",
             'add "confirmed by: <your name>" to lock' in after)
        check("the new block parses back as rooms",
             R.parse_rooms(after) == ["r/NewRoom", "r/Other"], str(R.parse_rooms(after)))
        check("the new block reads as seeded, not confirmed",
             R.rooms_block_state(after)[0] == "seeded")
        check("the sections around it survived", "### language-delta" in after and "keep me" in after)
        check("the section above it survived", "Core desire" in after)

        # Locked: a confirmed block is never overwritten.
        locked = f.read_text().replace("- r/NewRoom", "confirmed by: the owner\n- r/NewRoom")
        f.write_text(locked)
        changed2 = R.write_rooms_block(f, [dict(room="Nope", posts=1, score=1,
                                                sample_title="", sample_url="")])
        check("a confirmed block is never overwritten", changed2 is False)
        check("...and the file is untouched", f.read_text() == locked)

        # A file with no rooms block at all gets one appended, rest intact.
        g = tmp / "sub-02-y.md"
        g.write_text("### sub-y\n\n- **Core desire:** \"x\"\n")
        R.write_rooms_block(g, found, when="2026-09-18")
        out = g.read_text()
        check("a file with no block gets one appended",
             out.startswith('### sub-y\n\n- **Core desire:** "x"\n') and "r/NewRoom" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 13. resolve_rooms: confirmed wins, else discover

def test_resolve_rooms_confirmed_wins_else_discovers():
    section("13. resolve_rooms — a confirmed block wins; otherwise discovery runs")
    tmp = Path(tempfile.mkdtemp())
    try:
        subs = tmp / "brands" / "b" / "core-avatars" / "a" / "sub-avatars"
        subs.mkdir(parents=True)
        f = subs / "sub-01-x.md"
        f.write_text(SEEDED.replace('"fix it"', '"I want my dark spots to fade for good"'))

        def _fake_sub_file(brand, avatar, sub, root=None):
            return f if (brand, avatar, sub) == ("b", "a", "x") else None

        found = [dict(room="Discovered", posts=3, score=50, sample_title="t", sample_url="u")]

        def _fake_detail(brand, avatar, sub, **kw):
            return dict(ok=True, rooms=found, spend=0.16, cached=False,
                       words=kw.get("words") or [], query="q", cap=40, posts_read=40)

        with _Patch(R, "sub_file", _fake_sub_file), _Patch(R, "_find_rooms_detail", _fake_detail):
            rooms, words, disc = R.resolve_rooms("b", "a", "x")
        check("a seeded block triggers discovery", disc and disc.get("source") == "discovery")
        check("the found rooms are what gets used", rooms == ["r/Discovered"], str(rooms))
        check("the discovery is written back into the avatar's own file",
             disc.get("written_to") == str(f), str(disc.get("written_to")))
        check("...and the file now carries the gatherer block",
             "r/Discovered" in f.read_text())
        check("the desire words came from the avatar's own file", "spots" in words, str(words))

        # Now a person confirms it — discovery must not run at all.
        f.write_text(f.read_text().replace("- r/Discovered", "confirmed by: the owner\n- r/Discovered"))
        with _Patch(R, "sub_file", _fake_sub_file), _Patch(R, "_find_rooms_detail", _boom):
            rooms2, _w2, disc2 = R.resolve_rooms("b", "a", "x")
        check("a confirmed block skips discovery entirely", disc2.get("source") == "confirmed")
        check("the confirmed rooms are used as written", rooms2 == ["r/Discovered"], str(rooms2))

        # Discovery that comes back empty falls back to what the file said.
        f.write_text(SEEDED)

        def _empty(brand, avatar, sub, **kw):
            return dict(ok=False, rooms=[], spend=0.0, cached=False, words=[], query="q",
                       why="[UNFILLED: no key]")

        with _Patch(R, "sub_file", _fake_sub_file), _Patch(R, "_find_rooms_detail", _empty):
            rooms3, _w3, disc3 = R.resolve_rooms("b", "a", "x")
        check("empty discovery falls back to the seeded rooms", rooms3 == ["r/one", "r/two"],
             str(rooms3))
        check("...and says so in the record", disc3.get("source") == "discovery-empty")
        check("...and the file was NOT rewritten with nothing", "r/one" in f.read_text())

        # discover=False is the no-spend path the dry run uses.
        with _Patch(R, "sub_file", _fake_sub_file), _Patch(R, "_find_rooms_detail", _boom):
            rooms4, _w4, disc4 = R.resolve_rooms("b", "a", "x", discover=False)
        check("discover=False never pulls", rooms4 == ["r/one", "r/two"] and disc4 is None)

        # rooms_and_words keeps its old signature and its old return shape.
        with _Patch(R, "sub_file", _fake_sub_file), _Patch(R, "_find_rooms_detail", _empty):
            pair = R.rooms_and_words("b", "a", "x")
        check("rooms_and_words still returns exactly (rooms, words)",
             isinstance(pair, tuple) and len(pair) == 2, str(type(pair)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 14. discovery searches no room

def test_discovery_search_is_unrestricted_top_year():
    section("14. discovery fires ONE unrestricted search, sort top, window year")
    calls = []

    def _spy(rooms, queries, cap, out_dir, sort=None, time_window=None, no_comments=False):
        calls.append(dict(rooms=rooms, queries=list(queries), cap=cap, sort=sort,
                         time_window=time_window, no_comments=no_comments))
        return ([{"communityName": "r/found", "title": "t", "ups": 5, "url": "u"}], "", 0.16)

    tmp = Path(tempfile.mkdtemp())
    try:
        with _Patch(R, "_run_reddit", _spy), _Patch(R, "_cache_root", lambda: tmp):
            det = R._find_rooms_detail("b", "a", "x", cap=40, words=["dark", "spots", "fade", "stay", "hands"])
        check("exactly one search fired", len(calls) == 1, str(len(calls)))
        check("NO subreddit was named — that is the point", calls[0]["rooms"] == [],
             str(calls[0]["rooms"]))
        want_sort, want_window, want_posts_only, want_keep = R._discovery_cfg()
        check("sort is what research.json declares", calls[0]["sort"] == want_sort,
             str(calls[0]["sort"]))
        check("window is what research.json declares", calls[0]["time_window"] == want_window,
             str(calls[0]["time_window"]))
        # The second thing the first live pull taught: sorting an UNRESTRICTED
        # search by score ranks the loudest posts on Reddit that share a word,
        # not the posts about the topic. Relevance finds the topical rooms and
        # the score weighting then picks the loudest of those.
        check("the declared sort is relevance, not top", want_sort == "relevance", want_sort)
        check("posts_only is declared on", want_posts_only is True)
        check("five rooms are kept", want_keep == 5, str(want_keep))
        check("the cap is the small discovery cap", calls[0]["cap"] == 40, str(calls[0]["cap"]))
        # The regression that cost the first live pull: the door's default
        # maxComments let ONE viral thread's comments eat the whole cap, so
        # discovery came back with one room and it was the wrong one.
        check("posts only — a comment thread is one room repeated",
             calls[0]["no_comments"] is True, str(calls[0]["no_comments"]))
        check("one query, in the avatar's own words", len(calls[0]["queries"]) == 1
             and "dark spots fade stay" == calls[0]["queries"][0], str(calls[0]["queries"]))
        check("the room came back tallied", det["rooms"][0]["room"] == "found", str(det["rooms"]))
        check("the spend is reported", det["spend"] == 0.16, str(det["spend"]))

        # Second call, same key -> cache hit, no second search.
        with _Patch(R, "_run_reddit", _boom), _Patch(R, "_cache_root", lambda: tmp):
            det2 = R._find_rooms_detail("b", "a", "x", cap=40,
                                        words=["dark", "spots", "fade", "stay", "hands"])
        check("a repeat discovery comes from cache", det2.get("cached") is True)
        check("a cached discovery costs nothing", det2["spend"] == 0.0)

        # No desire words at all -> no search, no guess.
        with _Patch(R, "_run_reddit", _boom), _Patch(R, "_cache_root", lambda: tmp):
            det3 = R._find_rooms_detail("b", "a", "nowords", cap=40, words=[])
        check("no desire words -> no search and no invented room",
             det3["rooms"] == [] and "[UNFILLED" in (det3.get("why") or ""), str(det3))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 15. demographic fit

CORE_PROFILE = """# A core avatar

**Who (demographics in plain terms):** a woman, mid-fifties to seventy.

### demographics

age: ~55–70 — UNMEASURED working band
gender: female
skin tone / ethnicity: light, sun-damaged, freckling — a lighter-skinned customer
region: US Sun Belt
language: unknown — this file states none

## 1. Desire — start here

**Core desire:** "I want my dark spots to fade for good"
"""

SUB_OVERRIDE = """### sub-01-x — a narrower who

- **Core desire (inherited):** "I want my dark spots to fade for good"

### demographics

age: 30–39
region: the United Kingdom

### rooms — seeded

- r/one
"""

BLANK_PROFILE = """# An avatar nobody has filled in

### demographics

age: unknown
gender: unknown
skin tone / ethnicity: unknown
region: unknown
language: unknown

## 1. Desire

**Core desire:** "I want it fixed"
"""


def test_demographic_fit():
    section("15. demographic fit — the marker table, the slots, and what gets dropped")

    # --- the marker table itself, pure and offline
    table = {m["id"]: m for m in R.markers_table()}
    check("the marker table lives in research.json, not in code", len(table) >= 10, str(len(table)))
    check("no room of ours is named in the table (workspace rule 7)",
          all("skincare" not in w.lower() and "yappers" not in w.lower()
              for m in table.values() for w in m["match"]),
          str([w for m in table.values() for w in m["match"] if "skincare" in w.lower()]))

    demo = R.parse_demographics(CORE_PROFILE)
    check("the five slots parse off the block",
          set(demo) == {"age", "gender", "skin tone / ethnicity", "region", "language"}, str(demo))
    check("an `unknown` slot reads as unknown, not as a value",
          R._slot(demo, "language") is None, str(demo.get("language")))

    # THE RULING'S OWN THREE — the rooms that started this.
    for room, marker in (("r/Blackskincare", "black"), ("r/skincare_ph", "philippines"),
                         ("r/indianbeautyyappers", "south-asian")):
        f = R.room_fit(room, demo)
        check(f"{room} is a mismatch for this avatar", f["fit"] == "no", str(f))
        check(f"{room} names the marker that caught it", marker in f["marker"], f["marker"])
        check(f"{room} says why", len(f["why"]) > 20)

    # Kept: a general room, an age-band room that overlaps, a room in the right region.
    for room in ("r/Sunscreenreddit", "r/SkincareAddicts", "r/Melasmaskincare"):
        f = R.room_fit(room, demo)
        check(f"{room} carries no marker and is kept", f["fit"] == "unknown" and f["marker"] == "general",
              str(f))
    check("a 50+ room overlaps a 55–70 avatar and is kept",
          R.room_fit("r/50PlusSkinCare", demo)["fit"] == "yes")
    check("a 30+ room is open upward, so it overlaps too",
          R.room_fit("r/30PlusSkinCare", demo)["fit"] == "yes")
    check("a teen room does NOT overlap a 55–70 avatar",
          R.room_fit("r/teenagers", demo)["fit"] == "no")
    check("a men's room is a mismatch for a female avatar",
          R.room_fit("r/MensHealth", demo)["fit"] == "no")
    check("`men` never fires inside `women`",
          "male" not in R.room_fit("r/AskWomenOver30", demo)["markers"],
          str(R.room_fit("r/AskWomenOver30", demo)["markers"]))
    check("a 2-letter marker must be a whole segment — `ph` finds skincare_ph",
          R.room_fit("r/skincare_ph", demo)["fit"] == "no")
    check("...and never fires inside a longer word",
          R.room_fit("r/phimosis", demo)["marker"] == "general",
          R.room_fit("r/phimosis", demo)["marker"])

    # --- an UNKNOWN profile never drops anything
    blank = R.parse_demographics(BLANK_PROFILE)
    for room in ("r/Blackskincare", "r/skincare_ph", "r/indianbeautyyappers", "r/teenagers",
                 "r/MensHealth"):
        f = R.room_fit(room, blank)
        check(f"an unknown profile never drops {room}", f["fit"] == "unknown", str(f))
    check("no block at all never drops anything either",
          all(R.room_fit(r, {})["fit"] != "no"
              for r in ("r/Blackskincare", "r/skincare_ph", "r/teenagers")))

    # --- a sub-avatar inherits the core and overrides line for line
    tmp = Path(tempfile.mkdtemp())
    try:
        av = tmp / "brands" / "b" / "core-avatars" / "a"
        (av / "sub-avatars").mkdir(parents=True)
        (av / "profile.md").write_text(CORE_PROFILE)
        sub = av / "sub-avatars" / "sub-01-x.md"
        sub.write_text(SUB_OVERRIDE)

        core_only = R.demographics("b", "a", None, root=tmp)
        check("the core's own block is read", core_only.get("region") == "US Sun Belt",
              str(core_only))

        merged = R.demographics("b", "a", "x", root=tmp, sub_path=sub)
        check("the sub overrides the lines it carries",
              merged["age"] == "30–39" and merged["region"] == "the United Kingdom", str(merged))
        check("...and inherits the ones it does not",
              merged["gender"] == "female" and "lighter-skinned" in merged["skin tone / ethnicity"],
              str(merged))
        check("a UK room fits the sub but not the core",
              R.room_fit("r/CasualUK", merged)["fit"] == "yes"
              and R.room_fit("r/CasualUK", core_only)["fit"] == "no")
        check("a teen room still misses a 30–39 sub",
              R.room_fit("r/teenagers", merged)["fit"] == "no")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- split_by_fit keeps and drops the right rows, and says why
    found = [dict(room="Sunscreenreddit", posts=3, score=90),
             dict(room="Blackskincare", posts=1, score=30),
             dict(room="skincare_ph", posts=2, score=40),
             dict(room="50PlusSkinCare", posts=1, score=12)]
    kept, dropped = R.split_by_fit(found, demo)
    check("the mismatched rooms are dropped", sorted(d["room"] for d in dropped)
          == ["Blackskincare", "skincare_ph"], str([d["room"] for d in dropped]))
    check("the rest are kept", sorted(k["room"] for k in kept)
          == ["50PlusSkinCare", "Sunscreenreddit"], str([k["room"] for k in kept]))
    check("every dropped row carries its own reason",
          all(d["fit"]["why"] for d in dropped))
    check("the kept rows carry their verdict too",
          all(k["fit"]["fit"] in ("yes", "unknown") for k in kept))
    md = R.render_dropped_md(dropped)
    check("the dropped section names each room and its reason",
          "r/Blackskincare" in md and "r/skincare_ph" in md and "—" in md, md[:120])
    check("nothing dropped renders as a plain 'None'", R.render_dropped_md([]).startswith("None"))

    # --- the write-back lists only the kept rooms, and names the dropped ones
    tmp2 = Path(tempfile.mkdtemp())
    try:
        f = tmp2 / "sub.md"
        f.write_text(SEEDED)
        R.write_rooms_block(f, kept, when="2026-09-18", dropped=dropped)
        text = f.read_text()
        check("the block lists the kept rooms", "r/Sunscreenreddit" in text and "r/50PlusSkinCare" in text)
        check("a dropped room is never listed as a room to pull from",
              "- r/Blackskincare" not in text and "- r/skincare_ph" not in text)
        check("...but the file says they were found and thrown out",
              "Dropped as a demographic mismatch" in text and "r/Blackskincare" in text)
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    # --- every filed row is tagged, and a `no` room never files one
    posts = {
        "https://reddit.com/r/Sunscreenreddit/1": {
            "row": {"title": "kept", "body": "b", "communityName": "Sunscreenreddit", "ups": 5},
            "tags": {"mechanism"}},
        "https://reddit.com/r/Blackskincare/2": {
            "row": {"title": "dropped", "body": "b", "communityName": "r/Blackskincare", "ups": 9},
            "tags": {"objection"}},
    }
    thrown = []
    entries = R.build_bank_rows("b", "a", "x", posts, {}, demo=demo, dropped_out=thrown)
    check("one row filed, one thrown away", len(entries) == 1 and len(thrown) == 1,
          f"{len(entries)}/{len(thrown)}")
    check("the filed row is the one from the matching room",
          entries[0]["source"]["name"].endswith("Sunscreenreddit"), entries[0]["source"]["name"])
    check("every filed row carries a fit record",
          {"room", "verdict", "why"} <= set(entries[0]["fit"]), str(entries[0].get("fit")))
    check("a filed row's verdict is never `no`", entries[0]["fit"]["verdict"] in ("yes", "unknown"))
    check("the thrown-away row keeps its reason for the run record",
          thrown[0]["fit"]["fit"] == "no" and thrown[0]["room"] == "Blackskincare", str(thrown[0]))

    # ...and with no demographics on file, nothing is thrown away at all
    thrown2 = []
    entries2 = R.build_bank_rows("b", "a", "x", posts, {}, demo={}, dropped_out=thrown2)
    check("an unknown profile files every row and drops none",
          len(entries2) == 2 and thrown2 == [], f"{len(entries2)}/{len(thrown2)}")

    # --- the header line a run prints
    check("the demographics line names what was checked against",
          "female" in R.demographics_line(demo) and "·" in R.demographics_line(demo))
    check("no block at all says so rather than printing nothing",
          "[UNFILLED" in R.demographics_line({}))


def main():
    test_no_key_never_raises()
    test_bank_row_schema_and_permalink_drop()
    test_cache_hit_skips_pull()
    test_dry_run_spends_nothing()
    test_pick_thinnest_on_temp_tree()
    test_parse_rooms_does_not_swallow_the_rest_of_the_file()
    test_platform_detection_and_query_seeding()
    test_video_teardown_shim_is_a_reexport()
    test_tally_rooms_weights_by_score()
    test_seeded_vs_confirmed()
    test_write_back_replaces_only_the_seeded_block()
    test_resolve_rooms_confirmed_wins_else_discovers()
    test_discovery_search_is_unrestricted_top_year()
    test_demographic_fit()

    section("voiceprint — the spoken profile off a creator's own audio (2026-09-19)")
    import research_gatherer.voiceprint as V  # noqa: E402
    tr = {"text": "[music] Okay, so I'm gonna show you. It's not the sunscreen. Right? Huge.",
          "words": [
              {"text": "[music]", "start": 0.0, "end": 1.0, "type": "audio_event"},
              {"text": "Okay,", "start": 1.0, "end": 1.3, "type": "word"},
              {"text": " ", "start": 1.3, "end": 1.35, "type": "spacing"},
              {"text": "so", "start": 1.35, "end": 1.5, "type": "word"},
              {"text": "I'm", "start": 1.55, "end": 1.7, "type": "word"},
              {"text": "gonna", "start": 1.7, "end": 1.9, "type": "word"},
              {"text": "show", "start": 1.9, "end": 2.1, "type": "word"},
              {"text": "you.", "start": 2.1, "end": 2.4, "type": "word"},
              {"text": "It's", "start": 3.0, "end": 3.2, "type": "word"},
              {"text": "not", "start": 3.2, "end": 3.4, "type": "word"},
              {"text": "the", "start": 3.4, "end": 3.5, "type": "word"},
              {"text": "sunscreen.", "start": 3.5, "end": 4.0, "type": "word"},
              {"text": "Right?", "start": 4.5, "end": 4.9, "type": "word"},
              {"text": "Huge.", "start": 5.5, "end": 6.0, "type": "word"}]}
    words = V.words_of(tr)
    check("audio events and spacing rows are not words", len(words) == 12 and words[0]["text"] == "Okay,")
    m = V.measure_post({"id": "T-01", "name": "t", "post": "u"}, tr, {})
    check("the text is built from the word rows, so the [music] tag is not speech",
          not m["text"].startswith("[") and m["words"] == 12)
    check("sentences split on . ? ! and fragments are counted by the heuristic",
          m["sentences"] == 4 and m["fragments"] == 2, "%s / %s" % (m["sentences"], m["fragments"]))
    check("contractions count I'm, It's and gonna", m["contractions"] == 3, str(m["contractions"]))
    check("markers count okay, so and right", m["markers"].get("okay") == 1 and m["markers"].get("so") == 1
          and m["markers"].get("right") == 1, str(m["markers"]))
    check("a pause is a gap of 0.3 s or more between words: three here",
          m["pauses"]["count"] == 3 and m["pauses"]["max_s"] == 0.6, str(m["pauses"]))
    check("questions per post", m["questions"] == 1)
    check("opener and sign-off are the first and last five words",
          m["opener"] == "Okay, so I'm gonna show" and m["signoff"] == "not the sunscreen. Right? Huge.")
    check("every phrase carries a receipt of post @ seconds",
          all(v["receipt"].startswith("T-01 @ ") for v in m["bigrams"].values()))
    vp = V.roll_up("someone", [m])
    check("the roll-up carries its denominators and totals",
          vp["denominators"]["words"] == 12 and vp["totals"]["fragments"] == 2 and vp["thin"] is True)
    check("wpm is words over the speech span", vp["wpm"] == round(12 / (5.0 / 60), 1), str(vp["wpm"]))
    md = V.render_md(vp, {"core": None, "sub": None, "line": ""})
    check("the markdown names its denominators", "12 words" in md and "4 sentences" in md)
    check("no drive, no selected file, no rows — never a crash",
          V.selected_posts("nobody", Path(tempfile.mkdtemp())) == {})
    check("a missing key is None, never a crash", V.key_of() is None or isinstance(V.key_of(), str))
    check("the gatherer CLI routes the voiceprint mode",
          "voiceprint" in (HERE / "gather.py").read_text())

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
