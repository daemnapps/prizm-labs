"""The start picture moves to the scene's rehearsal: the motion chain's, never a stale programmed blocking beside it.

    python3 -m pytest components/motion/test_first_frame_style.py -q
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motion_program as MP  # noqa: E402


def test_a_scene_with_both_picks_the_chains_rehearsal(tmp_path):
    (tmp_path / "rehearsal").mkdir()
    (tmp_path / "rehearsal" / "blocking.mp4").write_bytes(b"r")
    (tmp_path / "blocking.mp4").write_bytes(b"old")
    (tmp_path / "chain.json").write_text(json.dumps({"stages": {"rehearse": {"ok": True, "file": "rehearsal/blocking.mp4"}}}))
    assert MP.rehearsal(tmp_path) == tmp_path / "rehearsal" / "blocking.mp4"


def test_the_rehearsal_is_found_without_a_chain_record(tmp_path):
    (tmp_path / "rehearsal").mkdir()
    (tmp_path / "rehearsal" / "blocking.mp4").write_bytes(b"r")
    (tmp_path / "blocking.mp4").write_bytes(b"old")
    assert MP.rehearsal(tmp_path) == tmp_path / "rehearsal" / "blocking.mp4"


def test_the_programmed_blocking_only_when_there_is_no_rehearsal(tmp_path):
    (tmp_path / "blocking.mp4").write_bytes(b"p")
    assert MP.rehearsal(tmp_path) == tmp_path / "blocking.mp4"
    (tmp_path / "blocking.mp4").unlink()
    with pytest.raises(SystemExit):
        MP.rehearsal(tmp_path)


# The start picture is written from the rehearsal's first frame and checked against it (2026-11-12): framing words go
# ahead of the look, and a take whose picture fails the check is held before anything is paid for.
import motion_chain as MC  # noqa: E402


def test_no_rehearsal_pose_means_no_framing_words(tmp_path):
    assert MP.framing(tmp_path) == ""


def _scene(tmp_path):
    md = tmp_path / "motion"
    (md / "rehearsal").mkdir(parents=True)
    (md / "rehearsal" / "pose.json").write_text("{}")
    pic = md / "first-frame.png"
    pic.write_bytes(b"p")
    return pic


def test_a_failed_picture_holds_the_take(tmp_path, monkeypatch):
    pic = _scene(tmp_path)
    bad = {"picture": str(pic), "failed": 1, "rows": [{"name": "start picture · creator framing", "short": "42% of the rehearsal's size", "ok": False}]}
    monkeypatch.setattr(MC, "start_check", lambda d, p=None: bad)
    held = MC.picture_held(tmp_path, pic)
    assert "creator framing" in held and "remake" in held


def test_a_passing_picture_is_not_rechecked(tmp_path, monkeypatch):
    pic = _scene(tmp_path)
    (tmp_path / "motion" / "match-start-picture.json").write_text(json.dumps({"picture": str(pic), "failed": 0, "rows": []}))
    monkeypatch.setattr(MC, "start_check", lambda d, p=None: pytest.fail("the saved check should be reused"))
    assert MC.picture_held(tmp_path, pic) == ""


def test_a_picture_without_a_rehearsal_is_not_held(tmp_path):
    pic = tmp_path / "x.png"
    pic.write_bytes(b"p")
    assert MC.picture_held(tmp_path, pic) == ""
