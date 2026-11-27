"""Tests for style_chain.py — the swipe's style is the one setting; any element in another style is a variant to make.

    python3 -m pytest components/video-production/styles/test_style_chain.py -q
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
COMP = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


SC = load("t_style_chain", HERE / "style_chain.py")
STYLED = next(r["id"] for r in SC.rows() if r.get("family") == "3d")             # any non-photoreal row
OTHER = next(r["id"] for r in SC.rows() if r.get("family") == "handmade")
REAL = next(r["id"] for r in SC.rows() if r.get("family") == "photoreal")


@pytest.fixture
def ws(tmp_path, monkeypatch):
    (tmp_path / "runs").mkdir()
    monkeypatch.setenv("AI_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("VIDEO_STUDIO_DATA", str(tmp_path / "studio"))
    monkeypatch.setenv("VIDEO_STUDIO_WRITING", str(tmp_path / "writing"))
    return tmp_path


def jdump(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d))


def person(ws, brand="b", pid="p1", style=None, variant=None):
    home = ws / "runs" / "ai-elements" / brand / "casting" / pid
    (home / "reference").mkdir(parents=True)
    (home / "reference" / "real.jpg").write_bytes(b"x")
    (home / "master.jpg").write_bytes(b"m")
    spec = {"id": pid, "brand": brand, "who": "a person", "adjustments": ["ours"], "base": "tee", "details": "hands",
            "looks": {"look-1": {"outfit": "shirt", "refs": ["reference/real.jpg"]}}, "texture": {"skin": {}},
            "real_references": [{"file": "reference/real.jpg", "kind": "real video frame", "from": "x", "use": "face"}]}
    if style:
        spec["style_id"] = style
    jdump(home / "spec.json", spec)
    if variant:
        v = home / "styles" / variant
        (v / "sheets").mkdir(parents=True)
        (v / "master.jpg").write_bytes(b"v")
        (v / "provenance.json").write_text("{}")
    return home


# ── the bank ──

def test_photoreal_family_and_no_style_need_no_variant():
    assert SC.is_photoreal(None) and SC.is_photoreal(REAL)
    assert not SC.is_photoreal(STYLED)
    assert SC.same_look(None, REAL) and not SC.same_look(None, STYLED) and not SC.same_look(STYLED, OTHER)


def test_unknown_style_is_refused_by_name():
    with pytest.raises(SystemExit) as e:
        SC.canonical("no-such-style")
    assert "no-such-style" in str(e.value)


def test_footage_only_in_photoreal():
    assert SC.footage_allowed(None) and SC.footage_allowed(REAL) and not SC.footage_allowed(STYLED)


# ── the one setting ──

def test_style_comes_from_brief_then_writing_run_then_teardown(ws):
    jdump(ws / "writing" / "teardown-1" / "run.json", {"style_id": STYLED})
    jdump(ws / "writing" / "writing-1" / "run.json", {"teardown": "teardown-1"})
    jdump(ws / "studio" / "briefs" / "idea-1" / "brief.json", {"brief": "writing-1"})
    assert SC.ad_style("idea-1")["id"] == STYLED                      # carried from the teardown, through the run
    jdump(ws / "writing" / "writing-1" / "run.json", {"style_id": OTHER, "teardown": "teardown-1"})
    assert SC.ad_style("idea-1")["id"] == OTHER                       # the writing run's own wins over its teardown
    jdump(ws / "studio" / "briefs" / "idea-1" / "brief.json", {"brief": "writing-1", "style": {"id": REAL}})
    assert SC.ad_style("idea-1")["id"] == REAL                        # the production's setting wins over both


def test_changing_the_style_is_one_setting(ws):
    jdump(ws / "studio" / "briefs" / "idea-1" / "brief.json", {"brief": "w", "style": {"id": STYLED}})
    SC.set_ad_style("idea-1", OTHER, "test")
    b = json.loads((ws / "studio" / "briefs" / "idea-1" / "brief.json").read_text())
    assert b["style"]["id"] == OTHER and b["style_history"][0]["id"] == STYLED
    assert SC.ad_style("idea-1")["id"] == OTHER


# ── one element in one style ──

def test_banked_person_in_another_style_is_a_variant_to_make_never_a_gap(ws):
    person(ws)
    r = SC.resolve("b", "person", "p1", STYLED)
    assert r["state"] == "make" and r["dir"].endswith(f"styles/{STYLED}") and "ensure-one" in r["next"]
    assert SC.resolve("b", "person", "p1", None)["state"] == "master"
    assert SC.resolve("b", "person", "p1", REAL)["state"] == "master"


def test_variant_on_file_is_reused(ws):
    home = person(ws, variant=STYLED)
    r = SC.resolve("b", "person", "p1", STYLED)
    assert r["state"] == "have"
    assert SC.element_ref("p1", STYLED, home) == f"p1/styles/{STYLED}"
    assert SC.element_file("b", "person", "p1", STYLED, "sheets/look-1.jpg") == home / "styles" / STYLED / "sheets" / "look-1.jpg"


def test_master_born_in_the_style_serves_itself(ws):
    home = person(ws, style=STYLED)
    assert SC.resolve("b", "person", "p1", STYLED)["state"] == "master"
    assert SC.resolve("b", "person", "p1", None)["state"] == "make"     # the photoreal look of a styled master: a variant
    assert SC.element_ref("p1", STYLED, home) == "p1"


def test_unbanked_element_is_no_master(ws):
    assert SC.resolve("b", "person", "nobody", STYLED)["state"] == "no-master"


# ── the look reference ──

def test_face_free_frames_skip_every_shot_with_a_face(ws):
    run = ws / "writing" / "td"
    shots = run / "framemap" / "shots"
    shots.mkdir(parents=True)
    for k in ("K01", "K02", "K03"):
        (shots / f"{k}-mid.jpg").write_bytes(b"f")
    jdump(run / "framemap" / "framemap.json", {"shots": [
        {"id": "K01", "stills": {"mid": "K01-mid.jpg"}, "map": {"who": ["Creator (head, torso)"]}},
        {"id": "K02", "stills": {"mid": "K02-mid.jpg"}, "map": {"who": ["Creator (left hand)"]}},
        {"id": "K03", "stills": {"mid": "K03-mid.jpg"}, "map": {"who": []}}]})
    assert [p.name for p in SC.face_free_frames(run)] == ["K02-mid.jpg", "K03-mid.jpg"]
    jdump(run / "run.json", {"style_id": STYLED})
    sw = SC.swatch
    SC.swatch = lambda sid, ws=None: None          # no swatch on this machine: the swipe's face-free frame
    try:
        lk = SC.look_reference(STYLED, run="td")
    finally:
        SC.swatch = sw
    assert lk["kind"] == "face-free swipe frame" and lk["file"].endswith("-mid.jpg")
    # the swipe is in another style: its frames are not this style's look
    other = SC.look_reference(OTHER, run="td")
    assert other is None or other["kind"] == "style swatch"
    assert SC.look_reference(None, run="td") is None
    swatch = ws / "sw.jpg"
    swatch.write_bytes(b"s")
    SC.swatch = lambda sid, ws=None: swatch        # the swatch is always in the style: it wins over the swipe's frames
    try:
        assert SC.look_reference(STYLED, run="td")["kind"] == "style swatch"
    finally:
        SC.swatch = sw


# ── making it ──

def test_person_variant_spec_keeps_identity_and_adds_the_look(ws, tmp_path):
    home = person(ws)
    out = home / "styles" / STYLED
    out.mkdir(parents=True)
    look = tmp_path / "look.jpg"
    look.write_bytes(b"l")
    spec = SC.person_variant_spec(home, STYLED, {"file": str(look), "kind": "style swatch", "use": "the look only"}, out)
    assert spec["style_id"] == STYLED and spec["variant_of"] == "../.."
    assert spec["who"] == "a person" and spec["looks"]["look-1"]["outfit"] == "shirt"
    assert (out / spec["looks"]["look-1"]["refs"][0]).resolve() == (home / "reference" / "real.jpg").resolve()
    assert (out / spec["real_references"][0]["file"]).resolve() == (home / "reference" / "real.jpg").resolve()
    assert (out / spec["production_references"][0]["file"]).resolve() == (home / "master.jpg").resolve()
    assert spec["production_references"][-1]["use"] == "the look only"
    assert "texture" not in spec and spec["set"] == f"cast-p1-{STYLED}"
    assert STYLED in spec["adjustments"][0] and "identity" in spec["adjustments"][1]


class FakeGate:
    def __init__(self, kept=None):
        self.kept = kept

    def kept_print(self, brand, name):
        return self.kept


class FakeQueue:
    def __init__(self, tmp):
        self.tmp, self.filed = tmp, []

    def file(self, brand, what, **kw):
        self.filed.append(dict(kw, what=what))
        f = self.tmp / f"{kw['name']}.json"
        f.write_text("{}")
        return f


def test_ensure_dry_run_spends_and_writes_nothing(ws, monkeypatch):
    home = person(ws)
    monkeypatch.setattr(SC, "_set_queue", lambda: pytest.fail("a dry run never touches the queue"))
    r = SC.ensure_one("b", "person", "p1", STYLED, dry_run=True)
    assert r["request"]["style"] == STYLED and r["request"]["cast"] == ["p1"]
    assert not (home / "styles").exists()


def test_ensure_files_the_styled_print_first(ws, monkeypatch, tmp_path):
    person(ws)
    q = FakeQueue(tmp_path)
    monkeypatch.setattr(SC, "_set_queue", lambda: (FakeGate(None), q))
    r = SC.ensure_one("b", "person", "p1", STYLED)
    assert r["state"] == "queued"
    f = q.filed[0]
    assert f["style"] == STYLED and f["style_formula"] == SC.formula(STYLED) and f["resume"]["tool"] == "style_chain"
    assert f["identity_reference"].endswith("master.jpg")
    assert "a person" in f["what"] and "never younger" in f["what"] and "no props" in f["what"]      # the print words carry who they are


def test_ensure_adopts_a_kept_print_for_a_product(ws, monkeypatch, tmp_path):
    kit = ws / "runs" / "ai-elements" / "b" / "products" / "kit1"
    (kit / "model").mkdir(parents=True)
    (kit / "model" / "product-sheet.png").write_bytes(b"s")
    kp = tmp_path / "print-v1.png"
    kp.write_bytes(b"printed")
    monkeypatch.setattr(SC, "_set_queue", lambda: (FakeGate(kp), FakeQueue(tmp_path)))
    r = SC.ensure_one("b", "product", "kit1", STYLED)
    v = kit / "styles" / STYLED
    assert r["state"] == "have" and (v / "picture.png").read_bytes() == b"printed"
    prov = json.loads((v / "provenance.json").read_text())
    assert prov["style"] == STYLED and prov["identity_from"].endswith("product-sheet.png")
    assert SC.resolve("b", "product", "kit1", STYLED)["state"] == "have"


def test_needs_maps_take_cast_to_the_bank(ws):
    person(ws, pid="lead")
    jdump(ws / "studio" / "briefs" / "idea-1" / "brief.json", {"brief": "w", "style": {"id": STYLED},
                                                                   "shot_fill": {"brand": "b"}})
    jdump(ws / "studio" / "briefs" / "idea-1" / "scenes" / "S1" / "take.json", {"cast": {"LEAD": {}, "NEW GUY": {}}})
    n = SC.needs("idea-1")
    st = {e["name"]: e["state"] for e in n["elements"]}
    assert st == {"LEAD": "make", "NEW GUY": "no-master"}
    # the writing brief's cast comes first; a take's longer name for the same person is the same person
    stages = ws / "writing" / "w" / "stages"
    stages.mkdir(parents=True)
    (stages / "5-brief.md").write_text('```json\n{"cast": [{"name": "LEAD", "bank_id": "lead"}, '
                                       '{"name": "GUY", "bank_id": "NEW"}, {"name": "MAID", "bank_id": "NEW"}]}\n```')
    st = {e["name"]: e["state"] for e in SC.needs("idea-1")["elements"]}
    assert st == {"LEAD": "make", "GUY": "no-master", "MAID": "no-master"}


# ── downstream steps read it ──

def test_print_words_render_in_the_style():
    ps = load("t_picture_sets", COMP / "image-production" / "picture_sets.py")
    plain = ps.print_prompt({"shot": "a room", "light": "soft"})
    styled = ps.print_prompt({"shot": "a room", "light": "soft", "style_formula": SC.formula(STYLED)})
    assert "real, unretouched photograph" in plain
    assert "real, unretouched photograph" not in styled and SC.formula(STYLED) in styled and "Never photoreal" in styled


def test_make_character_styled_person_skips_real_skin_deslop():
    mc = load("t_make_character", COMP / "video-production" / "machine" / "make_character.py")
    assert mc.style_lock(STYLED) and mc.style_lock(None) is None
    P = {k: "{real} {who}" for k in ("master", "turnaround", "angles-expressions", "light-test", "details", "look")}
    P["deslop"] = "deslop"
    spec = {"who": "w", "adjustments": ["a"], "base": "b", "details": "d", "looks": {}, "style_id": STYLED,
            "texture": {"skin": {"file": "/nope/skin.jpg", "shows": "s"}, "hair": {"file": "/nope/h.jpg", "shows": "h", "on": "o"}}}
    names = [j[0] for j in mc.jobs(spec, P, [], [], Path("/tmp/x"), Path("/tmp"))]
    assert "deslop" not in names and names[0] == "master"


def test_casting_takes_the_video_style():
    sys.path.append(str(COMP / "casting"))
    from casting import gates
    r = gates.resolve_elements({"style": STYLED})
    assert not r["problems"] and r["rows"]["style"]["id"] == STYLED


def test_a_new_person_is_cast_straight_in_the_ads_style(ws, monkeypatch, tmp_path):
    run = ws / "writing" / "w"
    (run / "framemap" / "shots").mkdir(parents=True)
    for k in ("K01", "K07"):
        (run / "framemap" / "shots" / f"{k}-mid.jpg").write_bytes(b"f")
    jdump(run / "framemap" / "framemap.json", {"shots": [
        {"id": "K01", "start": 0.0, "stills": {"mid": "K01-mid.jpg"}, "map": {"who": ["Creator (head)"]}},
        {"id": "K07", "start": 9.5, "stills": {"mid": "K07-mid.jpg"}, "map": {"who": ["Night Porter (face, torso)"]}},
        {"id": "K02", "start": 1.0, "stills": {"mid": "K01-mid.jpg"}, "map": {"who": ["Porter (head, shoulders)"]}}]})
    (run / "stages").mkdir()
    (run / "stages" / "5-brief.md").write_text("**PORTER** is the porter.\n- **Looks:** NEW: a navy coat. Used in S1.\n\n## THE WORLD\n")
    row = {"name": "PORTER", "identity_block": "about 50", "adjustments": ["a rounder face"], "real_reference": ""}
    r = SC.new_person("b", row, STYLED, "w", dry_run=True)
    sp = r["spec"]
    assert r["state"] == "make" and sp["style_id"] == STYLED                    # born in the style: no variant needed
    assert "K07" in sp["real_references"][0]["from"] and sp["looks"]["look-1"]["outfit"] == "a navy coat"
    assert STYLED in sp["adjustments"][0] and "resembling no real person" in sp["adjustments"][-1]
    assert {"title", "role", "why", "age"} <= set(sp["character"]) and sp["character"]["age"] == "50"   # the sheet record's fields
    q = FakeQueue(tmp_path)
    monkeypatch.setattr(SC, "_set_queue", lambda: (FakeGate(None), q))
    r = SC.new_person("b", row, STYLED, "w")
    assert r["state"] == "queued" and q.filed[0]["style"] == STYLED and q.filed[0]["identity_reference"].endswith("K07-mid.jpg")
    assert q.filed[0]["people_in_it"] is True          # the print's words never say "no people" for a person


def test_a_code_only_copy_finds_the_bank_through_the_writing_runs(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_WORKSPACE", raising=False)
    (tmp_path / "runs" / "ai-elements").mkdir(parents=True)
    (tmp_path / "runs" / "video-teardown" / "_work").mkdir(parents=True)
    monkeypatch.setenv("VIDEO_STUDIO_WRITING", str(tmp_path / "runs" / "video-teardown" / "_work"))
    assert SC.workspace() == tmp_path


def test_styled_print_plan_says_what_the_board_holds():
    ps = load("t_picture_sets2", COMP / "image-production" / "picture_sets.py")
    w = ps.print_prompt({"shot": "a man", "light": "soft", "style_formula": "F", "people_none": False,
                         "reference_says": "the second is the reference board: people first, last the style picture"})
    assert "reference board" in w and "photo quality" not in w and "No people" not in w


def test_a_styled_print_on_its_plan_board_files_as_kept(tmp_path, monkeypatch):
    ps = load("t_picture_sets3", COMP / "image-production" / "picture_sets.py")
    monkeypatch.setattr(ps, "home", lambda brand, name: tmp_path / name)
    rec = {"print": {"reference": "runs/x/set-requests/cast-a-s-reference.png"}, "prints": [], "renders": []}
    monkeypatch.setattr(ps, "record", lambda brand, name: rec)
    pr = tmp_path / "p.png"
    pr.write_bytes(b"p")
    try:
        ps.put("b", "cast-a-s", printed=str(pr), note="kept: right", trail={"reference": "runs/x/set-requests/cast-a-s-reference.png"})
    except ValueError as e:
        pytest.fail(f"a plan board is a valid reference: {e}")
    except Exception:
        pass                                    # filing details past the guard are not this test's subject
    rec["print"]["reference"] = "runs/x/crop.png"
    with pytest.raises(ValueError):
        ps.put("b", "cast-a-s", printed=str(pr), note="kept: right", trail={"reference": "runs/x/crop.png"})


def test_an_element_is_found_in_whichever_bank_holds_it(tmp_path, monkeypatch):
    data, code = tmp_path / "data", tmp_path / "code"
    (data / "runs" / "ai-elements" / "b" / "casting" / "a").mkdir(parents=True)
    (code / "runs" / "ai-elements" / "b" / "casting" / "z").mkdir(parents=True)
    monkeypatch.setattr(SC, "workspace", lambda: data)
    monkeypatch.setattr(SC, "HERE", code / "components" / "video-production" / "styles")
    assert SC.element_home("b", "person", "a") == data / "runs" / "ai-elements" / "b" / "casting" / "a"
    assert SC.element_home("b", "person", "z") == code / "runs" / "ai-elements" / "b" / "casting" / "z"
    assert SC.element_home("b", "person", "new") == data / "runs" / "ai-elements" / "b" / "casting" / "new"


def test_a_half_made_person_is_still_to_make(ws):
    home = person(ws)
    v = home / "styles" / STYLED
    (v / "full").mkdir(parents=True)
    (v / "full" / "master.png").write_bytes(b"raw")              # master made, sheets not finished, no record yet
    assert SC.resolve("b", "person", "p1", STYLED)["state"] == "make"


def test_a_variant_is_drawn_from_its_print_and_the_look_never_from_photoreal_pictures():
    mc = load("t_make_character2", COMP / "video-production" / "machine" / "make_character.py")
    P = {k: "{real} {who}" for k in ("master", "headshot", "turnaround", "angles-expressions", "light-test", "details", "look")}
    spec = {"who": "w", "adjustments": ["a"], "base": "b", "details": "d", "style_id": STYLED, "variant_of": "../..",
            "looks": {"look-1": {"outfit": "o", "refs": ["/photo/of/her.jpg"]}},
            "production_references": [{"file": "/master/photoreal.jpg", "use": "identity"},
                                      {"file": "/style/swatch.jpg", "use": "the look only"}]}
    real, prod = [Path("/real/photo.jpg")], [Path("/master/photoreal.jpg"), Path("/style/swatch.jpg")]
    jobs = {j[0]: [str(r) for r in j[2]] for j in mc.jobs(spec, P, real, prod, Path("/out"), Path("/"))}
    assert jobs["master"] == ["/style/swatch.jpg"]                         # the kept print goes in first at build time
    assert all("/real/" not in r and "photoreal" not in r and "/photo/of/" not in r for v in jobs.values() for r in v)


def test_a_cast_row_is_a_character_by_its_kind_or_by_personified_words_with_no_age():
    assert SC.is_character({"kind": "creature", "identity_block": "a man, 40"})          # the row's word wins
    assert not SC.is_character({"kind": "person", "identity_block": "a cartoon mascot"})
    assert SC.is_character({"identity_block": "his hands as a pair of white four-finger cartoon gloves"})
    assert SC.is_character({"identity_block": "PERSONIFIED PROBLEM: a family of tiny bumps, uncles and kids"})
    assert not SC.is_character({"identity_block": "28, muscular, a cartoon tee"})          # a person always has an age
    assert not SC.is_character({"identity_block": "mid 20s, curly ponytail"})
    assert not SC.is_character({"identity_block": "four women in bridesmaid dresses"})


def test_a_character_is_printed_once_and_its_kept_print_is_its_master(ws, monkeypatch, tmp_path):
    (ws / "writing" / "w" / "stages").mkdir(parents=True)
    (ws / "writing" / "w" / "stages" / "5-brief.md").write_text("**THE MITTENS** are mittens.\n")
    row = {"name": "THE MITTENS", "identity_block": "his hands as two cartoon mittens", "adjustments": ["made ours"],
           "real_reference": "a search for cartoon mittens"}
    home = ws / "runs" / "ai-elements" / "b" / "casting" / "the-mittens"
    q = FakeQueue(tmp_path)
    monkeypatch.setattr(SC, "_set_queue", lambda: (FakeGate(None), q))
    r = SC.new_person("b", row, STYLED, "w")                       # no real photo yet: say where it goes, spend nothing
    assert r["state"] == "no-master" and "reference" in r["next"] and not q.filed
    (home / "reference").mkdir(parents=True)
    (home / "reference" / "real.jpg").write_bytes(b"photo")
    (home / "reference" / "real.source.json").write_text(json.dumps({"source_url": "https://example.test/p"}))
    r = SC.new_person("b", row, STYLED, "w")
    f = q.filed[0]
    assert r["state"] == "queued" and r["character"] and f["people_in_it"] is False
    assert f["identity_reference"].endswith("real.jpg") and f["style"] == STYLED and "never as a person" in f["scene"]
    spec = json.loads((home / "spec.json").read_text())
    assert spec["shown"] == "character" and spec["real_references"][0]["from"] == "https://example.test/p"
    kp = tmp_path / "print-v1.png"
    from PIL import Image
    Image.new("RGB", (40, 70), "white").save(kp)
    monkeypatch.setattr(SC, "_set_queue", lambda: (FakeGate(kp), q))
    r = SC.new_person("b", row, STYLED, "w")
    assert r["state"] == "master" and r["picture"].endswith("master.jpg") and len(q.filed) == 1   # printed once
    assert (home / "picture.png").read_bytes() == kp.read_bytes() and (home / SC.CHARACTER_SHEET).is_file()
    assert not (home / "sheets" / "headshot.jpg").exists()          # no person sheets
    assert SC.look_sheet(home, "S1") == SC.CHARACTER_SHEET
    prov = json.loads((home / "provenance.json").read_text())
    assert prov["shown"] == "character" and prov["rights"] and prov["made_with"] and "runs/ai-elements" in prov["drive"]
    assert SC.resolve("b", "person", "the-mittens", STYLED)["state"] == "master"


def test_the_elements_standard_holds_a_character_without_face_sheets():
    std = json.loads((HERE.parent / "elements-standard.json").read_text())
    names = {r["name"] for r in std["person_character"]["requires"]}
    assert "master picture" in names and "real reference" in names and "angles and expressions" not in names


def test_room_words_props_out_surfaces_bare_fixtures_kept():
    """A set's print words carry the room only: the brief's props go in at the shot, a surface they stood on is said
    bare, the room's own fixtures stay."""
    got = SC.room_words("one wide white sink under one mirror, one shared ledge with one face-wash bottle, "
                        "white door with a brass knob and a keypad lock, chrome toaster on the counter",
                        ["keypad lock", "chrome toaster", "compact mirror"])
    assert "one wide white sink under one mirror" in got
    assert "one shared ledge, bare and clear" in got
    assert "white door" in got
    assert "bottle" not in got and "keypad" not in got and "toaster" not in got


def test_room_words_leave_a_room_with_no_props_unchanged():
    assert SC.room_words("narrow hallway, white walls, tile floor") == "narrow hallway, white walls, tile floor."
