#!/usr/bin/env python3
"""SI-194 (readers use loader), email-production: every key read goes through
ep_keys -> components/keys/loader.py, and no key value rides on a command line.

    python3 test_si194_ep_keys.py

No network, no model, no real key. HOME is a temp folder from before the
first import, so the real ~/.workflow-worker.env, ~/.daemn, ~/.gemini.env,
~/.apify.env and the Keychain are never looked at; the brand config lives in a
temp workspace (AI_WORKSPACE). The Keychain helper is a FAKE daemn_keys.py
written into the temp ~/.daemn that records every name it is asked for.
subprocess.run is replaced by a recorder that keeps argv and stdin. Every
name and value below is made up.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="email-production-si194-"))
WS = TMP / "ws"
BRAND = "testbrand"            # config overrides every key name
PLAIN = "plainbrand"           # config names only the store: default names
os.environ["HOME"] = str(TMP / "home-at-import")   # before anything reads Path.home()
os.environ["AI_WORKSPACE"] = str(WS)                # before anything imports paths.py
os.environ.pop("KEYS_NO_FALLBACK", None)

NAMES = {
    "client": "FAKE_SHOP_CLIENT_NAME", "app": "FAKE_SHOP_APP_NAME",
    "token": "FAKE_SHOP_TOKEN_NAME", "loop": "FAKE_LOOP_NAME",
    "klaviyo": "FAKE_KLAVIYO_NAME",
    "store": f"{BRAND.upper()}_NEXTCOMMERCE_STORE",
    "next": f"{BRAND.upper()}_NEXTCOMMERCE_ACCESS_TOKEN",
    "openai": "OPENAI_API_KEY",
}
PLAIN_DEFAULTS = [f"SHOPIFY_{PLAIN.upper()}_CLIENT_ID", f"SHOPIFY_{PLAIN.upper()}_APP",
                  f"SHOPIFY_{PLAIN.upper()}_TOKEN", f"LOOP_{PLAIN.upper()}_KEY"]
ENV_VALUES = {k: f"fake-env-{k}-value" for k in NAMES}
KC_VALUES = {k: f"fake-keychain-{k}-value" for k in NAMES}
ALL_FAKES = list(ENV_VALUES.values()) + list(KC_VALUES.values())
# The store NAME is the 29 Next subdomain: it is in the URL by design, not a secret.
SECRET_FAKES = [v for v in ALL_FAKES if "-store-" not in v] + ["fake-minted-token"]

HELPER = '''
import json, os
_D = os.path.dirname(os.path.abspath(__file__))
def key(name, required=False):
    with open(os.path.join(_D, "calls.log"), "a") as f:
        f.write(str(name) + "\\n")
    with open(os.path.join(_D, "vault.json")) as f:
        v = json.load(f).get(name)
    if v is None and required:
        raise KeyError(name)
    return v
'''


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


write(WS / "brands" / BRAND / "email-sms" / "machine.json", json.dumps({
    "shopify": {"shop": "fake-store.example", "client_id_key": NAMES["client"],
                "app_key": NAMES["app"], "token_key": NAMES["token"]},
    "loop_key": NAMES["loop"]}))
write(WS / "brands" / PLAIN / "email-sms" / "machine.json",
      json.dumps({"shopify": {"shop": "plain-store.example"}}))

sys.path.insert(0, str(HERE))
import ep_keys                      # noqa: E402
import shopify                      # noqa: E402
import loop                         # noqa: E402
import offer_bank_build             # noqa: E402
import run_month                    # noqa: E402
import simple_email as S            # noqa: E402  (last: it takes this folder off sys.path)
sys.path.insert(0, str(HERE))


class Recorder:
    """Stands in for subprocess.run: keeps (argv, stdin), answers with `reply(argv)`."""

    def __init__(self, reply=lambda argv: "{}"):
        self.calls = []
        self.reply = reply

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw.get("input")))
        return subprocess.CompletedProcess(argv, 0, self.reply(argv), "")

    def curls(self):
        return [c for c in self.calls if c[0] and c[0][0] == "curl"]


def shop_reply(argv):
    if argv[0] == "curl" and argv[-1] == S.KLAVIYO + "/accounts":   # the right-account check (2026-10-22)
        return json.dumps({"data": [{"attributes": {"contact_information": {"website_url": "https://example.test"}}}]})
    if argv[0] == "curl" and argv[-1].startswith(S.KLAVIYO):
        return "{}"
    if argv[0] == "curl" and any("oauth/access_token" in a for a in argv):
        return json.dumps({"access_token": "fake-minted-token", "expires_in": 3600})
    if argv[0] == "curl":
        return 'HTTP/1.1 200 OK\r\nlink: <https://fake-store.example/next>; rel="next"\r\n\r\n{"ok": 1}'
    return ""


class Base(unittest.TestCase):

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="home-", dir=TMP))
        env = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        for n in list(NAMES.values()) + PLAIN_DEFAULTS + ["KEYS_NO_FALLBACK"]:
            os.environ.pop(n, None)
        self._forget_helper()
        self.addCleanup(self._forget_helper)
        self.out, self.err = io.StringIO(), io.StringIO()
        for cm in (contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err)):
            cm.__enter__()
            self.addCleanup(cm.__exit__, None, None, None)

    def tearDown(self):
        printed = self.out.getvalue() + self.err.getvalue()
        for v in ALL_FAKES:
            self.assertNotIn(v, printed)

    @staticmethod
    def _forget_helper():
        sys.modules.pop("daemn_keys", None)
        sys.path[:] = [p for p in sys.path if not p.endswith(".daemn")]

    def helper(self, values):
        d = self.home / ".daemn"
        write(d / "daemn_keys.py", HELPER)
        write(d / "vault.json", json.dumps({NAMES[k]: v for k, v in values.items()}))

    def helper_calls(self):
        f = self.home / ".daemn" / "calls.log"
        return f.read_text().split() if f.is_file() else []

    def env(self, values):
        for k, v in values.items():
            os.environ[NAMES[k]] = v

    def run_all(self, values):
        """Every reader once; returns what each one used, read off the recorder."""
        got = {}
        shopify.use(BRAND)
        rec = Recorder(shop_reply)
        with mock.patch.object(subprocess, "run", rec):
            got["klaviyo"] = S.kl_key({"klaviyo_key": NAMES["klaviyo"], "from": {"email": "hi@example.test"}})
            shopify._mint()
            mint = [c for c in rec.curls() if any("oauth" in a for a in c[0])][-1]
            body = json.loads(mint[1])
            got["client"], got["app"] = body["client_id"], body["client_secret"]
            got["token"] = shopify.token()
        rec2 = Recorder(lambda argv: json.dumps({"data": []}))
        with mock.patch.object(subprocess, "run", rec2):
            loop.pull(BRAND, pages=1)
        got["loop"] = rec2.curls()[0][1].split(": ", 1)[1].strip()
        rec3 = Recorder(lambda argv: json.dumps({"results": []}))
        with mock.patch.object(subprocess, "run", rec3):
            self.assertEqual(offer_bank_build.from_next(BRAND), [])
        self.assertIn(values["store"], rec3.curls()[0][0][-1])
        got["store"] = values["store"]
        got["next"] = rec3.curls()[0][1].split("Bearer ", 1)[1].strip()
        got["openai"] = run_month.have_picture_key()
        for r in (rec, rec2, rec3):
            self.assert_no_value_on_argv(r)
        return got

    def assert_no_value_on_argv(self, rec):
        for argv, _ in rec.curls():
            for v in SECRET_FAKES:
                self.assertFalse(any(v in a for a in argv), f"{v!r} on argv {argv[:3]}")


class EnvFirst(Base):

    def test_env_beats_the_keychain(self):
        self.helper(dict(KC_VALUES, token=json.dumps({"t": "fake-keychain-token-value",
                                                      "exp": int(time.time()) + 9999})))
        env = dict(ENV_VALUES, token=json.dumps({"t": "fake-env-token-value",
                                                 "exp": int(time.time()) + 9999}))
        self.env(env)
        got = self.run_all(env)
        for k in ("klaviyo", "client", "app", "loop", "store", "next"):
            self.assertEqual(got[k], ENV_VALUES[k], k)
        self.assertEqual(got["token"], "fake-env-token-value")
        self.assertIs(got["openai"], True)
        self.assertEqual(self.helper_calls(), [])      # env found it: the helper was never asked

    def test_keychain_found_when_env_empty(self):
        kc = dict(KC_VALUES, token=json.dumps({"t": "fake-keychain-token-value",
                                               "exp": int(time.time()) + 9999}))
        self.helper(kc)
        got = self.run_all(kc)
        for k in ("klaviyo", "client", "app", "loop", "store", "next"):
            self.assertEqual(got[k], KC_VALUES[k], k)
        self.assertEqual(got["token"], "fake-keychain-token-value")
        self.assertIs(got["openai"], True)
        self.assertIn(NAMES["openai"], self.helper_calls())


class MiniSkipsOldPlaces(Base):

    def test_managed_file_present_reads_no_old_place(self):
        write(self.home / ".workflow-worker.env", f"{NAMES['openai']}=fake-managed-value\n")
        self.helper(KC_VALUES)
        lines = "".join(f"{n}=fake-file-value\n" for n in NAMES.values())
        for f in (".daemn/keys.env", ".apify.env", ".gemini.env"):
            write(self.home / f, lines)
        self.assertIs(run_month.have_picture_key(), False)
        for n in NAMES.values():
            self.assertIsNone(ep_keys.key(n), n)
        shopify.use(BRAND)
        rec = Recorder(shop_reply)
        with mock.patch.object(subprocess, "run", rec):
            with self.assertRaises(SystemExit):
                S.kl_key({"klaviyo_key": NAMES["klaviyo"], "from": {"email": "hi@example.test"}})
            with self.assertRaises(SystemExit):
                loop.pull(BRAND, pages=1)
            with self.assertRaises(SystemExit):
                shopify._mint()
            self.assertEqual(offer_bank_build.from_next(BRAND), [])
        self.assertEqual(rec.calls, [])
        self.assertEqual(self.helper_calls(), [])      # the helper was never called
        self.assertIn("old locations skipped", ep_keys.missing(NAMES["loop"]))


class Imports(unittest.TestCase):

    def test_import_and_brand_exit_with_no_daemn(self):
        home = Path(tempfile.mkdtemp(prefix="bare-home-", dir=TMP))
        env = dict(os.environ, HOME=str(home), AI_WORKSPACE=str(WS))
        r = subprocess.run([sys.executable, "-c", "import shopify, loop, offer_bank_build"],
                           cwd=HERE, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        for script in ("shopify.py", "loop.py"):
            r = subprocess.run([sys.executable, script], cwd=HERE, env=env,
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0, script)
            self.assertIn("--brand", r.stderr, script)
            self.assertNotIn("daemn_keys", r.stderr, script)


class Names(Base):

    def test_config_overrides_choose_the_name(self):
        shopify.use(BRAND)
        self.assertEqual((shopify.CFG["client_id_key"], shopify.CFG["app_key"],
                          shopify.CFG["token_key"]),
                         (NAMES["client"], NAMES["app"], NAMES["token"]))
        self.assertEqual(loop.key_name(BRAND), NAMES["loop"])

    def test_defaults_when_config_names_none(self):
        shopify.use(PLAIN)
        self.assertEqual([shopify.CFG["client_id_key"], shopify.CFG["app_key"],
                          shopify.CFG["token_key"], loop.key_name(PLAIN)], PLAIN_DEFAULTS)

    def test_reads_ask_key_by_name(self):
        asked = []

        def fake_key(name):
            asked.append(name)
            return "fake-asked-value"
        shopify.use(BRAND)
        rec = Recorder(shop_reply)
        with mock.patch.object(ep_keys, "key", fake_key), mock.patch.object(subprocess, "run", rec):
            S.kl_key({"klaviyo_key": NAMES["klaviyo"], "from": {"email": "hi@example.test"}})
            shopify._mint()
            shopify.token()
            loop.pull(BRAND, pages=1)
            offer_bank_build.from_next(BRAND)
            run_month.have_picture_key()
        for n in NAMES.values():
            self.assertIn(n, asked)


class NoValueOnArgv(Base):

    def test_headers_ride_on_stdin(self):
        key = ENV_VALUES["klaviyo"]
        tok = ENV_VALUES["token"]
        shopify.use(BRAND)
        rec = Recorder(shop_reply)
        with mock.patch.object(subprocess, "run", rec):
            S.kl("GET", "lists", key)
            S.kl("POST", "campaigns", key, payload={"data": {"type": "campaign"}})
            S.kl("POST", "image-upload", key, form={"file": "@/tmp/fake.png", "name": "x"})
            shopify.get("/shop.json", tok=tok)
            shopify.page("https://fake-store.example/next", tok=tok)
            loop.get("/subscription", ENV_VALUES["loop"])
        self.assert_no_value_on_argv(rec)
        want = [f"Authorization: Klaviyo-API-Key {key}\n"] * 3 + \
               [f"X-Shopify-Access-Token: {tok}\n"] * 2 + [f"X-Loop-Token: {ENV_VALUES['loop']}\n"]
        self.assertEqual([c[1] for c in rec.curls()], want)
        for argv, _ in rec.curls():
            i = argv.index("@-")
            self.assertEqual(argv[i - 1], "-H")
            self.assertEqual(argv.count("@-"), 1)
        kl_get, kl_post, kl_form, sh_get, sh_page, lp = [c[0] for c in rec.curls()]
        self.assertIn("revision: " + S.REVISION, kl_get)
        self.assertIn("accept: application/vnd.api+json", kl_get)
        self.assertEqual(kl_post[kl_post.index("-d") + 1], json.dumps({"data": {"type": "campaign"}}))
        self.assertIn("Content-Type: application/vnd.api+json", kl_post)
        self.assertIn("file=@/tmp/fake.png", kl_form)
        self.assertIn("name=x", kl_form)
        for argv in (sh_get, sh_page):
            self.assertEqual(argv[argv.index("-D") + 1], "-")
            self.assertIn("Accept: application/json", argv)
        self.assertEqual(sh_page[-1], "https://fake-store.example/next")
        self.assertIn("-f", lp[1])
        self.assertIn("Accept: application/json", lp)
        self.assertTrue(lp[-1].startswith(loop.BASE + "/subscription"))

    def test_mint_body_on_stdin(self):
        self.env(ENV_VALUES)
        shopify.use(BRAND)
        rec = Recorder(shop_reply)
        with mock.patch.object(subprocess, "run", rec):
            self.assertEqual(shopify._mint(), "fake-minted-token")
        argv, body = rec.curls()[0]
        self.assertEqual(argv[argv.index("--data-binary") + 1], "@-")
        self.assertNotIn("-d", argv)
        self.assertEqual(body, json.dumps({"client_id": ENV_VALUES["client"],
                                           "client_secret": ENV_VALUES["app"],
                                           "grant_type": "client_credentials"}))
        self.assert_no_value_on_argv(rec)
        sec = [c[0] for c in rec.calls if c[0][0] == "security"]
        self.assertEqual(len(sec), 1)                   # the Keychain write-back is unchanged
        self.assertFalse(any(ENV_VALUES["client"] in a or ENV_VALUES["app"] in a for a in sec[0]))


class Missing(Base):

    def test_kl_key_missing_names_the_key_and_places(self):
        with self.assertRaises(SystemExit) as cm:
            S.kl_key({"klaviyo_key": NAMES["klaviyo"], "from": {"email": "hi@example.test"}})
        msg = str(cm.exception.code)
        self.assertIn(NAMES["klaviyo"], msg)
        self.assertIn("looked in", msg)
        self.assertIn("built but not pushed", msg)
        self.assertNotIn("in the Keychain", msg)
        with self.assertRaises(SystemExit) as cm:
            S.kl_key({})
        self.assertIn("built but not pushed", str(cm.exception.code))

    def test_loop_and_mint_missing_exit_without_curl(self):
        shopify.use(BRAND)
        rec = Recorder(shop_reply)
        with mock.patch.object(subprocess, "run", rec):
            with self.assertRaises(SystemExit) as cm:
                loop.pull(BRAND, pages=1)
            self.assertIn(NAMES["loop"], str(cm.exception.code))
            with self.assertRaises(SystemExit) as cm:
                shopify._mint()
            self.assertIn(NAMES["client"], str(cm.exception.code))
            self.env({"client": ENV_VALUES["client"]})
            with self.assertRaises(SystemExit) as cm:
                shopify._mint()
            self.assertIn(NAMES["app"], str(cm.exception.code))
            self.assertNotIn(ENV_VALUES["client"], str(cm.exception.code))
        self.assertEqual(rec.calls, [])

    def test_from_next_either_missing_is_empty(self):
        for present in ({"store": ENV_VALUES["store"]}, {"next": ENV_VALUES["next"]}, {}):
            for k in ("store", "next"):
                os.environ.pop(NAMES[k], None)
            self.env(present)
            rec = Recorder()
            with mock.patch.object(subprocess, "run", rec):
                self.assertEqual(offer_bank_build.from_next(BRAND), [])
            self.assertEqual(rec.calls, [])

    def test_have_picture_key_false_without_key(self):
        self.assertIs(run_month.have_picture_key(), False)


class Token(Base):

    def _token(self, stored):
        if stored is not None:
            os.environ[NAMES["token"]] = stored
        self.env({"client": ENV_VALUES["client"], "app": ENV_VALUES["app"]})
        shopify.use(BRAND)
        rec = Recorder(shop_reply)
        with mock.patch.object(subprocess, "run", rec):
            t = shopify.token()
        return t, [c for c in rec.curls() if any("oauth" in a for a in c[0])]

    def test_live_stored_token_is_used(self):
        t, mints = self._token(json.dumps({"t": "fake-live-token", "exp": int(time.time()) + 9999}))
        self.assertEqual((t, mints), ("fake-live-token", []))

    def test_expired_or_absent_mints(self):
        for stored in (json.dumps({"t": "fake-old-token", "exp": int(time.time()) - 10}), None):
            os.environ.pop(NAMES["token"], None)
            t, mints = self._token(stored)
            self.assertEqual(t, "fake-minted-token")
            self.assertEqual(len(mints), 1)


class EpKeys(Base):

    def test_empty_names_and_never_raises(self):
        self.assertIsNone(ep_keys.key(None))
        self.assertIsNone(ep_keys.key(""))
        os.environ[NAMES["loop"]] = "  "
        self.assertIsNone(ep_keys.key(NAMES["loop"]))
        os.environ[NAMES["loop"]] = " fake-padded-value "
        self.assertEqual(ep_keys.key(NAMES["loop"]), "fake-padded-value")
        with mock.patch.object(ep_keys, "_load_loader", side_effect=RuntimeError("no loader")):
            self.assertIsNone(ep_keys.key(NAMES["loop"]))
            self.assertIn(NAMES["loop"], ep_keys.missing(NAMES["loop"]))
        msg = ep_keys.missing(NAMES["klaviyo"])
        self.assertIn(NAMES["klaviyo"], msg)
        self.assertIn("environment", msg)

    def test_loader_by_path_under_its_own_name(self):
        ep_keys.key(NAMES["loop"])
        mod = sys.modules["upright_keys_loader"]
        self.assertEqual(Path(mod.__file__).resolve(),
                         (HERE.parents[1] / "components" / "keys" / "loader.py").resolve())
        src = (HERE / "ep_keys.py").read_text()
        self.assertNotIn("import email", src)
        self.assertNotIn("daemn_keys.key", src)


if __name__ == "__main__":
    unittest.main()
