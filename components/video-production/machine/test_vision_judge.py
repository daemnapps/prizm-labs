"""The vision judge door — fake judges only, no network, no model, no CLI."""
import base64, os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_judge as vj  # noqa: E402

PNG = base64.b64decode(  # a 1x1 picture
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def fake(answer=None, error=None, seen=None):
    def fn(prompt, images, want_json, cfg, **kw):
        if seen is not None:
            seen.append({"prompt": prompt, "images": list(images), "cfg": cfg})
        if error:
            raise error
        return answer, "fake-model"
    return fn


class Door(unittest.TestCase):
    def setUp(self):
        os.environ.pop("VISION_JUDGE_ORDER", None)

    def test_first_judge_that_answers_wins_and_says_so(self):
        a = vj.ask("q", [], want_json=True, order_=["a", "b"],
                   backends={"a": fake('{"verdict": "SAME"}'), "b": fake('{"verdict": "DIFFERENT"}')})
        self.assertEqual(vj.json_of(a)["verdict"], "SAME")
        self.assertEqual(a.backend, "a")
        self.assertEqual(a.by(), "a (fake-model)")

    def test_an_out_of_credit_judge_falls_through(self):
        a = vj.ask("q", [], want_json=True, order_=["claude", "local", "gemini"],
                   backends={"claude": fake(error=vj.VisionJudgeError("claude failed")),
                             "local": fake(error=TimeoutError("slow")),
                             "gemini": fake('{"verdict": "SAME"}')})
        self.assertEqual(a.backend, "gemini")
        self.assertEqual([t["backend"] for t in a.tried], ["claude", "local", "gemini"])
        self.assertIn("error", a.tried[0])

    def test_unreadable_json_falls_through(self):
        a = vj.ask("q", [], want_json=True, order_=["a", "b"],
                   backends={"a": fake("I think it is fine"), "b": fake('{"subjects": []}')})
        self.assertEqual(a.backend, "b")
        self.assertEqual(a.tried[0]["error"], "unreadable answer")

    def test_plain_text_is_fine_when_json_is_not_wanted(self):
        a = vj.ask("q", [], order_=["a"], backends={"a": fake("MATCH — same place")})
        self.assertEqual(str(a), "MATCH — same place")

    def test_every_judge_failing_raises_never_passes(self):
        with self.assertRaises(vj.VisionJudgeError):
            vj.ask("q", [], want_json=True, order_=["a", "b"],
                   backends={"a": fake(error=RuntimeError("402")), "b": fake("")})

    def test_order_comes_from_config_and_env_overrides_it(self):
        self.assertTrue(vj.order({"order": ["local", "claude"]}) == ["local", "claude"])
        os.environ["VISION_JUDGE_ORDER"] = "claude, gemini"
        try:
            self.assertEqual(vj.order({"order": ["local"]}), ["claude", "gemini"])
        finally:
            os.environ.pop("VISION_JUDGE_ORDER")

    def test_providers_json_declares_the_order(self):
        cfg = vj.config()
        self.assertTrue(cfg.get("order"))
        for name in cfg["order"]:
            self.assertIn(name, vj.BACKENDS)

    def test_role_reaches_the_judge(self):
        seen = []
        vj.ask("q", [], order_=["a"], role="review", backends={"a": fake("ok", seen=seen)})
        self.assertEqual(seen[0]["cfg"]["role"], "review")

    def test_parts_become_files_in_order(self):
        seen = []
        parts = [{"text": "Image 1 is the reference."},
                 {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(PNG).decode()}},
                 {"text": "Image 2 is ours."},
                 {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(PNG).decode()}}]
        a = vj.ask_parts(parts, want_json=True, order_=["a"],
                         backends={"a": fake('{"verdict": "SAME"}', seen=seen)})
        self.assertEqual(a.backend, "a")
        self.assertEqual(len(seen[0]["images"]), 2)
        self.assertIn("[Image 1]", seen[0]["prompt"])
        self.assertLess(seen[0]["prompt"].index("reference"), seen[0]["prompt"].index("[Image 1]"))

    def test_gemini_gets_the_parts_unchanged(self):
        got = {}
        def g(prompt, images, want_json, cfg, parts=None):
            got["parts"] = parts
            return '{"verdict": "SAME"}', "g"
        g_backends = {"gemini": g}
        orig = vj.gemini_backend
        vj.gemini_backend = g                        # ask_parts recognises the gemini judge by identity
        try:
            parts = [{"text": "t"}]
            vj.ask_parts(parts, want_json=True, order_=["gemini"], backends=g_backends)
        finally:
            vj.gemini_backend = orig
        self.assertEqual(got["parts"], [{"text": "t"}])

    def test_a_picture_is_shrunk_for_the_judge(self):
        from PIL import Image
        d = Path(tempfile.mkdtemp())
        Image.new("RGB", (3000, 2000)).save(d / "big.png")
        out = vj._small(d / "big.png", d, 1)
        with Image.open(out) as im:
            self.assertLessEqual(max(im.size), vj.MAX_SIDE)


if __name__ == "__main__":
    unittest.main()
