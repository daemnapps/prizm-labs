import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import identity as I  # noqa: E402

SRC = """## Treat Bumps: Expert Tips in Springfield
[BUTTON: Book Appointment -> /book]
[NAV] [LINK: Our Team -> /team]
Bumps happen when hair curls back into the skin. Acme Skin Clinic, led by Dr. Jane Roe, serves Springfield.
We offer a 30-day money-back guarantee on every visit. ingrown hairs are common.
## Ingrown Hairs"""
ITEMS = I.from_capture(SRC) + [{"text": "Acme Skin Clinic", "kind": "brand"}, {"text": "Springfield", "kind": "place"},
                               {"text": "30-day money-back guarantee", "kind": "guarantee"}]


def test_clean_page_passes():
    assert I.check("Shaving bumps start under the skin. Our brush lifts the hair out.", SRC, ITEMS)["pass"]


def test_each_kind_is_caught():
    for leak in ("Book Appointment today", "near Springfield", "the Acme Skin Clinic way", "Dr. Jane Roe says",
                 "a 30-day money-back guarantee", "Our Team"):
        assert not I.check(f"Read this. {leak}. Done.", SRC, ITEMS)["pass"], leak


def test_eight_word_run_is_caught():
    r = I.check("Bumps happen when hair curls back into the skin. Acme always.", SRC, ITEMS)
    assert any(h["test"] == "run" for h in r["hits"])


def test_topic_phrase_used_in_lowercase_is_not_a_name():
    assert I.check("Ingrown Hairs and what to do.", SRC, [])["pass"]
