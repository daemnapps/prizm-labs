"""A brand's email look, read from brands/<brand>/email-sms/design-system.json.

Everything that makes a designed email look like one brand lives in that file: colours, the two type
faces and their files, the logo, the ornaments (optional), the moment themes, the sign-off and footer,
the guarantee word for word, the prices the product check accepts, the words it refuses, the names that
never appear. The engine (engine.py) names no brand.

A file reference is one of:
    brand:<path>    under brands/<brand>/
    drive:<path>    under the Shared Assets drive (found by brandpath's drive_index.mount())
    repo:<path>     under the workspace root
    run:<path>      under the send's own run folder (pictures made for that send)
    product:<name>  one of the brand's real product pictures, named in the look's `products`
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent.parent / "brandpath"))   # the sibling component, through its public surface
import brandpath  # noqa: E402

REPO = Path(brandpath.repo(HERE))


def reach():
    """gdrive-creator's Drive reach (LD-14 (shared Drive reach)), imported at call time. Found as
    image-production's drive_reach.py finds it — the nearest parent holding gdrive-creator/gdrive_creator,
    appended to sys.path — not through ../drive_reach.py, whose `from paths import component` meets
    marketing-calendar's paths.py once line.py has put that folder first on the path."""
    home = next((d / "gdrive-creator" for d in HERE.parents if (d / "gdrive-creator" / "gdrive_creator").is_dir()), None)
    if home is not None and str(home) not in sys.path:
        sys.path.append(str(home))   # appended, never ahead of the caller
    from gdrive_creator import reach as R
    return R

TOKENS = ("canvas", "deep", "surface", "ink", "muted", "dim", "button", "button_ink", "glow", "glow_rgb",
          "orn_hi", "orn_mid", "orn_lo", "line", "eyebrow", "accent",
          "band", "band_ink", "alt", "panel", "panel_ink")


class Look(dict):
    """The look as a dict, plus `path()` to resolve a file reference and `brand`."""

    def __init__(self, brand, data, run_dir=None):
        super().__init__(data)
        self.brand = brand
        self.run_dir = Path(run_dir) if run_dir else None

    def path(self, ref):
        if not ref:
            return None
        if isinstance(ref, dict):
            ref = ref.get("file")
        kind, _, rest = ref.partition(":")
        if kind == "product":
            if rest not in self.get("products", {}):
                raise KeyError("%s: no product picture %r in %s's look (have: %s)" % (ref, rest, self.brand, ", ".join(self.get("products", {}))))
            return self.path(self["products"][rest])
        if kind == "brand":
            return Path(brandpath.brand_root(self.brand, REPO / "brands")) / rest
        if kind == "repo":
            return REPO / rest
        if kind == "run":
            if not self.run_dir:
                raise ValueError("%s: a run: picture needs the send's run folder" % ref)
            local = self.run_dir / rest
            if local.is_file():
                return local            # a file on disk always wins
            # LD-34 (run pictures from Drive): media/ is gitignored, so on another machine the
            # picture is fetched from the run's Drive mirror, by name, as drive: is (LD-16 (email design by API))
            R = reach()
            try:
                return R.readable("Shared Assets/runs/email-production/%s/%s/%s" % (self.brand, self.run_dir.name, rest))
            except (R.NoDrive, SystemExit):
                return local            # as before: the caller's open fails, naming it
        if kind == "drive":
            import drive_index
            m = drive_index.mount()
            if m:
                try:
                    with open(str(Path(m) / rest), "rb"):
                        return Path(m) / rest
                except OSError:
                    pass                # not there, or the mount does not read here (launchd: no Full Disk Access)
            # LD-16 (email design by API): the one file, fetched by name through the Drive API
            R = reach()
            try:
                return R.readable("Shared Assets/" + rest)
            except (R.NoDrive, SystemExit):
                if m:
                    return Path(m) / rest   # as before with a mount: the caller checks it
                raise FileNotFoundError("%s: the Shared Assets drive is not mounted on this computer" % ref)
        return Path(ref)

    def tokens(self, theme=None):
        t = dict(self["tokens"])
        if theme:
            t.update((self.get("themes", {}).get(theme) or {}).get("tokens", {}))
        return t

    def ornament(self, name, theme=None):
        if theme:
            o = ((self.get("themes", {}).get(theme) or {}).get("ornaments") or {}).get(name)
            if o:
                return o
        return (self.get("ornaments") or {}).get(name)


def load(brand, run_dir=None):
    f = Path(brandpath.brand_root(brand, REPO / "brands")) / "email-sms" / "design-system.json"
    if not f.exists():
        raise SystemExit("%s has no email look yet: brands/%s/email-sms/design-system.json "
                         "(copy another brand's, then change every value to this brand's own)" % (brand, brand))
    data = json.loads(f.read_text())
    missing = [k for k in TOKENS if k not in data.get("tokens", {})]
    if missing:
        raise SystemExit("%s: design-system.json is missing tokens %s" % (f, ", ".join(missing)))
    spec = Path(run_dir) / "design" / "email.json" if run_dir else None
    if spec and spec.exists():    # this email only: its own "tokens" (e.g. {"muted": "#FFFFFF"}) replace the brand's for this send
        _mine = json.loads(spec.read_text())
        data["tokens"].update(_mine.get("tokens") or {})
        if _mine.get("layout"):    # this email only: e.g. {"button_radius": "0", "button_wide": true}
            data["layout"] = dict(data.get("layout") or {}, **_mine["layout"])
    return Look(brand, data, run_dir)
