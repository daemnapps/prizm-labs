"""Consistency tests: one setting, one look, one variant per person and location, made once, and the measured checks.

    python3 -m pytest components/video-production/styles/test_consistency.py -q

Each test name says the rule it holds. The picture checks (face likeness, set colour) run where opencv is installed
(the face reader's own Python); the verdict lines are checked everywhere on known inputs.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


CO = load("t_consistency", HERE / "consistency.py")
SC = CO.SC
STYLED = next(r["id"] for r in SC.rows() if r.get("family") == "3d")
OTHER = next(r["id"] for r in SC.rows() if r.get("family") == "handmade")


@pytest.fixture
def ad(tmp_path, monkeypatch):
    """A production in STYLED: two banked people (one photoreal master, one born in the style), one location."""
    (tmp_path / "runs").mkdir()
    monkeypatch.setenv("AI_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("VIDEO_STUDIO_DATA", str(tmp_path / "studio"))
    monkeypatch.setenv("VIDEO_STUDIO_WRITING", str(tmp_path / "writing"))
    cast = tmp_path / "runs" / "ai-elements" / "b" / "casting"
    for pid, style in (("lead", None), ("guest", STYLED)):
        (cast / pid / "reference").mkdir(parents=True)
        (cast / pid / "reference" / "r.jpg").write_bytes(b"r")
        (cast / pid / "master.jpg").write_bytes(b"m")
        spec = {"id": pid, "brand": "b", "who": pid, "adjustments": ["ours"], "base": "tee", "details": "hands",
                "looks": {}, "real_references": [{"file": "reference/r.jpg", "kind": "real video frame", "from": "x"}]}
        if style:
            spec["style_id"] = style
        (cast / pid / "spec.json").write_text(json.dumps(spec))
    look = tmp_path / "look.jpg"
    look.write_bytes(b"l")
    monkeypatch.setattr(SC, "swatch", lambda sid, ws=None: look)
    stages = tmp_path / "writing" / "w" / "stages"
    stages.mkdir(parents=True)
    (stages / "5-brief.md").write_text("```json\n" + json.dumps({
        "cast": [{"name": "LEAD", "bank_id": "lead"}, {"name": "GUEST", "bank_id": "guest"}],
        "world": [{"id": "HOTEL ROOM", "bank_id": "NEW", "description": "a room", "real_reference": ""}]}) + "\n```")
    b = tmp_path / "studio" / "briefs" / "idea-1"
    b.mkdir(parents=True)
    (b / "brief.json").write_text(json.dumps({"brief": "w", "style": {"id": STYLED}, "shot_fill": {"brand": "b"}}))
    return tmp_path


class Gate:
    def __init__(self, kept=None):
        self.kept = kept

    def kept_print(self, brand, name):
        return self.kept(name) if callable(self.kept) else self.kept


class Queue:
    def __init__(self, tmp):
        self.tmp, self.filed = tmp, []

    def file(self, brand, what, **kw):
        self.filed.append(dict(kw, what=what))
        f = self.tmp / f"{kw['name']}.json"
        f.write_text("{}")
        return f


# ── 1. the style is read from one setting and every element resolves to that style ──

def test_every_element_resolves_to_the_one_setting(ad):
    n = SC.needs("idea-1")
    got = {e.get("name") or e["id"]: (e["state"], (e.get("dir") or "").split("/casting/")[-1]) for e in n["elements"]}
    assert got["LEAD"] == ("make", f"lead/styles/{STYLED}")       # photoreal master: a variant in the ad's style
    assert got["GUEST"] == ("master", "guest")                     # born in the ad's style: the master itself
    assert got["HOTEL ROOM"][0] == "no-master"                     # a new location: made once, in the style


def test_changing_the_setting_moves_every_element_to_the_new_style(ad):
    SC.set_ad_style("idea-1", OTHER, "test")
    n = SC.needs("idea-1")
    dirs = {e.get("name"): e.get("dir") or "" for e in n["elements"] if e["kind"] == "person"}
    assert dirs["LEAD"].endswith(f"lead/styles/{OTHER}") and dirs["GUEST"].endswith(f"guest/styles/{OTHER}")


# ── 2. one look per ad ──

def test_one_look_is_pinned_and_every_element_is_made_with_it(ad, monkeypatch, tmp_path):
    q = Queue(tmp_path)
    monkeypatch.setattr(SC, "_set_queue", lambda: (Gate(None), q))
    SC.ensure("idea-1")
    pinned = json.loads((ad / "studio" / "briefs" / "idea-1" / "brief.json").read_text())["style"]["look"]
    assert pinned["file"].endswith("look.jpg") and pinned["style"] == STYLED
    assert len(q.filed) == 2                                        # LEAD's variant and the HOTEL ROOM set
    assert {f["look_reference"] for f in q.filed} == {pinned["file"]}
    assert {f["style"] for f in q.filed} == {STYLED}


def test_the_pinned_look_is_kept_when_a_new_swatch_appears(ad, monkeypatch, tmp_path):
    first = SC.ad_look("idea-1")
    other = tmp_path / "other.jpg"
    other.write_bytes(b"o")
    monkeypatch.setattr(SC, "swatch", lambda sid, ws=None: other)
    assert SC.ad_look("idea-1")["file"] == first["file"]          # the ad keeps its one look


# ── 3. a missing variant is made once and reused, never made twice ──

def test_a_variant_is_made_once_and_reused(ad, monkeypatch, tmp_path):
    kept = tmp_path / "print.png"
    kept.write_bytes(b"p")
    builds = []

    class MC:
        @staticmethod
        def build(spec_path, out):
            builds.append(out)
            (out / "sheets").mkdir(exist_ok=True)
            (out / "master.jpg").write_bytes(b"v")
            (out / "provenance.json").write_text("{}")

    monkeypatch.setattr(SC, "_set_queue", lambda: (Gate(kept), Queue(tmp_path)))
    monkeypatch.setattr(SC, "_make_character", lambda: MC)
    a = SC.ensure_one("b", "person", "lead", STYLED)
    b = SC.ensure_one("b", "person", "lead", STYLED)
    assert a["state"] == b["state"] == "have" and len(builds) == 1


def test_a_waiting_variant_files_the_same_request_never_a_second(ad, monkeypatch, tmp_path):
    q = Queue(tmp_path)
    monkeypatch.setattr(SC, "_set_queue", lambda: (Gate(None), q))
    SC.ensure_one("b", "person", "lead", STYLED)
    SC.ensure_one("b", "person", "lead", STYLED)
    assert len({f["name"] for f in q.filed}) == 1                   # one request (refreshed), so one print


def test_a_location_is_made_once_then_is_the_set_for_every_shot(ad, monkeypatch, tmp_path):
    kept = tmp_path / "set-print.png"
    kept.write_bytes(b"s")
    monkeypatch.setattr(SC, "_set_queue", lambda: (Gate(kept), Queue(tmp_path)))
    row = SC.writing_world("w")[0]
    r = SC.new_location("b", row, STYLED, "w")
    assert r["state"] == "master" and r["dir"].endswith("sets/hotel-room")
    el = json.loads((Path(r["dir"]) / "element.json").read_text())
    assert el["style_id"] == STYLED and "every surface bare" in el["what"]
    again = [e for e in SC.needs("idea-1")["elements"] if e["kind"] == "set"][0]
    assert again["state"] == "master" and again["dir"] == r["dir"]  # reused, never redrawn


# ── 4. every person and location resolves to exactly one variant ──

def test_one_variant_each(ad):
    v = CO.one_verdict(SC.needs("idea-1")["elements"])
    assert v["verdict"] == "NOT YET" and "LEAD" in v["why"] and "HOTEL ROOM" in v["why"]
    two = [{"kind": "person", "name": "A", "id": "a", "dir": "/x/a", "state": "have"},
           {"kind": "person", "name": "A", "id": "a", "dir": "/x/a2", "state": "have"}]
    assert CO.one_verdict(two)["verdict"] == "FAIL"
    one = [{"kind": "person", "name": "A", "id": "a", "dir": "/x/a", "state": "have"},
           {"kind": "set", "name": "R", "id": "r", "dir": "/x/r", "state": "master"}]
    assert CO.one_verdict(one)["verdict"] == "PASS"


# ── 5. the pass / fail lines, on known inputs ──

def test_same_person_passes_only_over_the_line_and_nearest_to_themselves():
    good = CO.person_verdict("A", {"s1": 0.62, "s2": 0.55}, {"s1": ("B", 0.20), "s2": ("B", 0.30)})
    assert good["verdict"] == "PASS" and "0.55" in good["why"]
    low = CO.person_verdict("A", {"s1": 0.62, "s2": 0.21}, {})
    assert low["verdict"] == "FAIL" and "s2" in low["why"]
    swapped = CO.person_verdict("A", {"s1": 0.45}, {"s1": ("B", 0.50)})
    assert swapped["verdict"] == "FAIL" and "B" in swapped["why"]
    # each picture is judged on its own: a weak picture that is still nearest its own person passes
    fair = CO.person_verdict("A", {"s1": 0.95, "s2": 0.45}, {"s1": ("B", 0.60), "s2": ("B", 0.40)})
    assert fair["verdict"] == "PASS"
    assert CO.person_verdict("A", {"s1": None}, {})["verdict"] == "NOT YET"


def test_same_place_passes_only_on_the_sets_colour():
    assert CO.place_verdict("R", {"k1": (0.9, 4.0)})["verdict"] == "PASS"
    assert CO.place_verdict("R", {"k1": (0.9, 4.0), "k2": (0.2, 30.0)})["verdict"] == "FAIL"
    assert CO.place_verdict("R", {})["verdict"] == "NOT YET"


def test_one_look_fails_on_another_style_or_another_look_picture():
    pin = {"file": "/a/look.jpg"}
    assert CO.look_verdict("s", pin, {"A": {"style": "s", "look": "/b/look.jpg"}})["verdict"] == "PASS"
    assert CO.look_verdict("s", pin, {"A": {"style": "t", "look": "/a/look.jpg"}})["verdict"] == "FAIL"
    assert CO.look_verdict("s", pin, {"A": {"style": "s", "look": "/a/frame.jpg"}})["verdict"] == "FAIL"


# ── 6. the measures themselves (where opencv is installed) ──

def test_the_set_colour_measure_tells_the_same_room_from_another(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    warm = np.full((64, 64, 3), (60, 120, 200), np.uint8)
    cool = np.full((64, 64, 3), (200, 120, 60), np.uint8)
    for n, a in (("ref", warm), ("same", warm.copy()), ("other", cool)):
        cv2.imwrite(str(tmp_path / f"{n}.png"), a)
    c, de = CO.place_score(tmp_path / "ref.png", tmp_path / "same.png")
    assert c >= CO.PLACE_CORR and de <= CO.PLACE_DE
    c, de = CO.place_score(tmp_path / "ref.png", tmp_path / "other.png")
    assert c < CO.PLACE_CORR or de > CO.PLACE_DE


def test_refiling_a_request_keeps_its_print_in_flight(tmp_path, monkeypatch):
    sys.path.append(str(HERE.parents[1] / "image-production"))
    from image_production import set_queue
    monkeypatch.setattr(set_queue, "home", lambda brand: tmp_path)
    f = set_queue.file("b", "a room", name="set-a-s")
    r = json.loads(f.read_text())
    r["printing"] = {"generation": "g1"}
    f.write_text(json.dumps(r))
    set_queue.file("b", "a room", name="set-a-s")
    assert json.loads(f.read_text())["printing"] == {"generation": "g1"}   # never printed twice


def test_one_style_across_the_cast_fails_a_half_stylised_person():
    # idea-12 as measured on 12 Nov: three people drawn in the style sit ~0.6 apart, a half-stylised one at ~0.2
    v = CO.cast_style_verdict({"HUSBAND": 0.52, "MANAGER": 0.47, "HOUSEKEEPER": 0.50, "creator": 0.23})
    assert v["verdict"] == "FAIL" and "creator" in v["why"]
    assert CO.cast_style_verdict({"A": 0.55, "B": 0.48, "C": 0.51, "D": 0.44})["verdict"] == "PASS"
    assert CO.cast_style_verdict({"A": 0.5, "B": 0.5})["verdict"] == "NOT YET"


def test_a_styled_variant_drops_the_photoreal_words_and_keeps_every_mark():
    who = ("64; sleek chin-length silver-grey bob, blue-grey eyes, soft rounded jaw, warm fair skin with visible pores, "
           "fine lines and freckling, small gold hoop earrings. Natural skin, no beauty-filter look.")
    out = SC.unreal(who)
    for keep in ("silver-grey bob", "blue-grey eyes", "rounded jaw", "freckling", "gold hoop"):
        assert keep in out
    assert "pores" not in out and "beauty-filter" not in out


# ── a scene's start picture is made from the ad's variants, and the check reads it ──

def _scene(ad, look_from="the brief (S1)"):
    stages = ad / "writing" / "w" / "stages"
    (stages / "5-brief.md").write_text("```json\n" + json.dumps({
        "cast": [{"name": "LEAD", "bank_id": "lead"}],
        "world": [{"id": "HOTEL ROOM", "bank_id": "NEW", "description": "a room"}],
        "scenes": [{"id": "S1", "setting_id": "HOTEL ROOM", "looks": {"LEAD": "a blue dress"}, "props": ["COLLAR"],
                    "shots": [{"gestures": ["finger on the collar rim"], "face": "eyes down"}]},
                   {"id": "S2", "setting_id": "HOTEL ROOM"}],
        "props": [{"name": "COLLAR", "size": "5 cm ring", "look": "brushed metal"}],
        "product_lock": ["S1: S1.1, cap down in the collar · LABEL · laid on"]}) + "\n```")
    kit = ad / "runs" / "ai-elements" / "b" / "products" / "kit1"
    (kit / "styles" / STYLED).mkdir(parents=True)
    (kit / "model").mkdir()
    (kit / "model" / "product-sheet.png").write_bytes(b"s")
    (kit / "styles" / STYLED / "picture.png").write_bytes(b"v")
    run = ad / "writing" / "w" / "run.json"
    run.write_text(json.dumps({"product": "kit1"}))
    v = ad / "runs" / "ai-elements" / "b" / "casting" / "lead" / "styles" / STYLED
    (v / "sheets").mkdir(parents=True)
    for f in ("master.jpg", "sheets/headshot.jpg", "sheets/look-2-blue.jpg"):
        (v / f).write_bytes(b"x")
    (v / "provenance.json").write_text("{}")
    (v / "looks.json").write_text(json.dumps({"looks": {
        "look-1-white": {"outfit": "a white shirt", "from": "elsewhere", "sheet": "sheets/headshot.jpg"},
        "look-2-blue": {"outfit": "a long blue dress", "from": look_from, "sheet": "sheets/look-2-blue.jpg"}}}))
    room = ad / "runs" / "ai-elements" / "b" / "sets" / "hotel-room"
    room.mkdir(parents=True)
    (room / "picture.png").write_bytes(b"p")
    (room / "element.json").write_text(json.dumps({"style_id": STYLED, "print": "set-hotel-room-" + STYLED}))
    sc = ad / "studio" / "briefs" / "idea-1" / "scenes" / "S1"
    sc.mkdir(parents=True)
    (sc / "take.json").write_text(json.dumps({"cast": {"LEAD": {}}}))
    return sc


def test_a_scene_start_picture_takes_the_place_people_and_look_in_the_ads_style(ad, monkeypatch, tmp_path):
    _scene(ad)
    kept = tmp_path / "print-v1.png"
    kept.write_bytes(b"k")
    monkeypatch.setattr(SC, "_set_queue", lambda: (Gate(kept), Queue(tmp_path)))
    r = SC.scene_refs("idea-1", "S1")
    assert r["style"] == STYLED and r["formula"] == SC.formula(STYLED) and not r["missing"]
    assert r["set_print"] == str(kept) and r["set"]["id"] == "hotel-room"           # the gate's kept print, first
    assert r["people"] == [{"name": "LEAD", "element": f"lead/styles/{STYLED}", "file": "sheets/look-2-blue.jpg",
                            "path": str(ad / "runs" / "ai-elements" / "b" / "casting" / "lead" / "styles" / STYLED
                                        / "sheets" / "look-2-blue.jpg")}]
    assert r["look"]["file"].endswith("look.jpg")                                   # the ad's one look picture


def test_the_scene_look_is_found_by_its_words_when_no_record_names_the_scene(ad):
    _scene(ad, look_from="elsewhere")
    r = SC.scene_refs("idea-1", "S1")
    assert r["people"][0]["file"] == "sheets/look-2-blue.jpg"


def test_a_scene_with_a_person_not_yet_in_the_style_is_held(ad):
    sc = _scene(ad)
    (sc / "take.json").write_text(json.dumps({"cast": {"LEAD": {}, "GUEST": {}}}))
    SC.set_ad_style("idea-1", OTHER, "test")                                         # nobody is banked in OTHER
    r = SC.scene_refs("idea-1", "S1")
    assert any("LEAD" in m for m in r["missing"]) and any("location" in m for m in r["missing"])


def test_the_consistency_check_reads_start_pictures(ad):
    sc = _scene(ad)
    (sc / "motion").mkdir()
    (sc / "motion" / "first-frame.png").write_bytes(b"f")
    (sc / "motion" / "first-frame.json").write_text(json.dumps({
        "picture": "first-frame.png", "set": "hotel-room", "style": STYLED,
        "picture_from": [{"element": f"lead/styles/{STYLED}", "file": "sheets/look-2-blue.jpg"}]}))
    bdir = ad / "studio" / "briefs" / "idea-1"
    assert CO.production_stills(bdir, {"id": "lead"}, "person") == [sc / "motion" / "first-frame.png"]
    assert CO.production_stills(bdir, {"id": "hotel-room"}, "set") == [sc / "motion" / "first-frame.png"]


def test_the_product_goes_in_only_where_the_brief_puts_it_in_the_scene(ad):
    sc = _scene(ad)
    r = SC.scene_refs("idea-1", "S1")
    assert r["product"]["id"] == "kit1" and r["product"]["where"] == "cap down in the collar"
    assert r["product"]["picture"].endswith(f"kit1/styles/{STYLED}/picture.png")      # the product in the ad's style
    assert r["props"] == ["collar: brushed metal, 5 cm ring"]
    assert r["moment"] == "finger on the collar rim; face: eyes down"      # the hands go where the brief says
    (sc.parent / "S2").mkdir()
    (sc.parent / "S2" / "take.json").write_text(json.dumps({"cast": {}}))
    assert SC.scene_refs("idea-1", "S2")["product"] is None
