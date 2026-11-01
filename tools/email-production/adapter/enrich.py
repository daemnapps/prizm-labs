"""Make each picture on the team's page say where it lives, in words the team uses, with a link to open it in Drive.

adapter/sync.py list gives every real picture `how.from` as a raw reference ("drive:brands/…", a proof id,
or nothing for a product cut-out). This reads the same email.json the rows came from, walks the pictures in the
same order sync.py does, and rewrites each picture's `source` and `how` for the page:

    source   "Real product photo, cut out" / "Real product photo" / "Real customer or brand photo" /
             "Made by the picture machine" / "Not made yet"
    how      {"made": false, "from": "Shared Assets › brands › brand-b › …", "link": "https://drive.google.com/…"}
             {"made": false, "todo": true} for a picture still to make

The Drive link comes from the proof index (runs/asset-index/<brand>/proof/proof.json, drive_url) or, for a file on
the Shared Assets drive, from the Drive for desktop mount (the file's item id). A person's run on a laptop; with no
mount the path is still shown, without a link.

    python3 tools/email-production/adapter/enrich.py rows.json > rows-enriched.json
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.append(str(REPO / "components" / "brandpath"))
import drive_index  # noqa: E402

RUNS = REPO / "runs" / "email-production"
LABEL = {"cut": "Real product photo, cut out", "photo": "Real product photo", "proof": "Real customer or brand photo",
         "made": "Made by the picture machine"}


def pretty(rel):
    return "Shared Assets › " + " › ".join(p for p in rel.split("/") if p)


def drive_link(mount, rel):
    if not mount:
        return None
    f = Path(mount) / rel
    try:
        out = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", str(f)], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    fid = out.stdout.strip()
    return "https://drive.google.com/file/d/%s/view" % fid if out.returncode == 0 and fid else None


def raw_pictures(sec):
    out = []

    def walk(x):
        if isinstance(x, dict):
            if "alt" in x and ("photo" in x or "proof" in x or "source" in x or "todo" in x):
                out.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(sec)
    return out


def where(x, brand, label, look, proofs, mount):
    if "todo" in x or x.get("source") == "make":
        return "Not made yet", {"made": False, "todo": True}
    ref = x.get("photo") or x.get("stage") or ""
    if "proof" in x:
        p = proofs.get(x["proof"]) or {}
        rel = "brands/%s/%s" % (brand, p["rel"]) if p.get("rel") else ""
        return LABEL["proof"], {"made": False, "from": pretty(rel) if rel else x["proof"], "link": p.get("drive_url")}
    if ref.startswith("product:"):
        ref = (look.get("products") or {}).get(ref.split(":", 1)[1], "")
        src = LABEL["cut"]
    else:
        src = LABEL.get(x.get("source"), x.get("source") or LABEL["photo"])
    if ref.startswith("drive:"):
        rel = ref.split(":", 1)[1]
        return src, {"made": False, "from": pretty(rel), "link": drive_link(mount, rel)}
    if ref.startswith("run:"):
        rel = "runs/email-production/%s/%s/%s" % (brand, label, ref.split(":", 1)[1])
        return LABEL["made"], {"made": True, "record": None, "note": "Made for this email: " + pretty(rel),
                               "link": drive_link(mount, rel)}
    return src, None


def main(rows_file):
    rows = json.load(open(rows_file))
    mount = drive_index.mount()
    for r in rows:
        brand, label = r["brand"], r["label"]
        spec = json.load(open(RUNS / brand / label / "design" / "email.json"))
        look = json.load(open(REPO / "brands" / brand / "email-sms" / "design-system.json"))
        pj = REPO / "runs" / "asset-index" / brand / "proof" / "proof.json"
        proofs = {i["id"]: i for i in (json.load(open(pj)).get("items") or [])} if pj.is_file() else {}
        for s in r["sections"]:
            raw = raw_pictures(spec["sections"][s["i"]])
            for k, p in enumerate(s.get("pictures") or []):
                if k >= len(raw) or (p.get("how") or {}).get("record"):
                    continue
                src, how = where(raw[k], brand, label, look, proofs, mount)
                p["source"] = src
                if how is not None:
                    p["how"] = how
    json.dump(rows, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])
