#!/usr/bin/env python3
"""SI-183's declared test — the creators root is one function again.

    cd tools/video-teardown/machine && python3 test_damon2_creators_root.py

Offline: no network, no real Drive mount, nothing written outside a temp
directory. library.py is loaded by path with chain.drive_root() pointed at a
temp dir, so every path below resolves into the fixture and nowhere else.

    (a) creators_root() is root()/"creators" — where creator_dir() already wrote
    (b) creator_dir(h, make=False) sits directly under creators_root()
    (c) dashboard.py and doctor.py build no `/ "creators"` path by hand — read
        as tokens, so comments and the text inside strings never count
"""

import ast, importlib.util, io, sys, tempfile, tokenize
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
sys.path.insert(0, str(MACHINE))

import chain as C          # noqa: E402

FAILS = []


def check(label, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAILS.append(label)


class fake_drive:
    """chain.drive_root() pointed at a temp dir for the length of the block —
    the same seam test_library_root.py's fake_drive gives through $HOME."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prev = C.drive_root
        mount = Path(self.tmp.name) / "Team Drive"
        mount.mkdir()
        C.drive_root = lambda: mount
        return mount

    def __exit__(self, *exc):
        C.drive_root = self.prev
        self.tmp.cleanup()
        return False


def load_library():
    spec = importlib.util.spec_from_file_location("library", MACHINE / "library.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hand_built_creators(path):
    """Every `/ "creators"` in the CODE of one file. Tokenized, so a comment is
    a COMMENT token and a JS or HTML blob is one STRING token — neither can
    match; only a real `/` operator followed by the literal "creators" does."""
    toks = [t for t in tokenize.generate_tokens(io.StringIO(path.read_text()).readline)
            if t.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE)]
    hits = []
    for a, b in zip(toks, toks[1:]):
        if a.type == tokenize.OP and a.string == "/" and b.type == tokenize.STRING:
            try:
                val = ast.literal_eval(b.string)
            except Exception:
                continue
            if val == "creators":
                hits.append(f"{path.name}:{a.start[0]}")
    return hits


L = load_library()

print("(a) creators_root() is where creator_dir() writes")
with fake_drive() as mount:
    check("creators_root() == root() / 'creators'",
          L.creators_root() == L.root() / "creators", str(L.creators_root()))
    check("creators_root() resolves inside the stubbed drive",
          mount in L.creators_root().parents, str(L.creators_root()))

print("(b) a creator's folder sits directly under creators_root()")
with fake_drive() as mount:
    d = L.creator_dir("Mara Creator", make=False)
    check("creator_dir(h, make=False).parent == creators_root()",
          d.parent == L.creators_root(), str(d))
    check("make=False creates nothing", not any(mount.iterdir()), str(d))
    made = L.creator_dir("Mara Creator")
    check("make=True creates it in the same place",
          made == d and (made / "posts").is_dir(), str(made))

print("(c) no caller builds the creators path by hand")
for name in ("dashboard.py", "doctor.py"):
    hits = hand_built_creators(MACHINE / name)
    check(f"{name} names no `/ \"creators\"` literal", not hits, ", ".join(hits))
# The reader itself must FIRE on the shape it hunts, or (c) proves nothing.
with tempfile.TemporaryDirectory() as t:
    probe = Path(t) / "probe.py"
    probe.write_text('# L.root() / "creators"\nx = "a / \\"creators\\""\n')
    quiet = hand_built_creators(probe)
    probe.write_text('r = L.root() / "creators"\n')
    loud = hand_built_creators(probe)
check("the reader ignores comments and strings, and fires on real code",
      not quiet and loud == ["probe.py:1"], f"{quiet} · {loud}")

print()
if FAILS:
    print(f"FAILED {len(FAILS)}: " + "; ".join(FAILS))
    sys.exit(1)
print("all green")
