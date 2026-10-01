#!/usr/bin/env python3
"""One zip a brand's briefs go to the graphic designer in.

    pack.py --brand <brand>                 build <brand>-brief-pack.zip
    pack.py --brand <brand> --upload        and put it on Drive, link recorded

The zip and its README land at runs/image-teardown/<brand>/brief-pack-<date>/
deliverable/ (the zip is gitignored there); on Drive the zip sits at the
mirrored path, Shared Assets/runs/image-teardown/<brand>/brief-pack-<date>/.

Damon, 2026-09-17: *"create a download pack to give to our graphic designer
so she can just plug it into Higgsfield and start to generate the variations
the brief calls for. All the work has already been done."*

It has. Every brief already has a Drive folder (`deliver.py`) holding the
swipe, our draft, the brief, the work order and its prompts. What it did not
have was **one thing to hand over** — twenty-one folder links is a scavenger
hunt, one zip is a job. So this reads the same files `deliver.py` ships, never
a second rendering of them, and folds them into:

    <brand>-brief-pack/
        README.md            the batch at a glance, the settings, the order
        p143/
            source.jpg       the swipe — the target
            draft.png        our first pass, for comparison
            work-order.md    what to make, the settings, the Elements, the job
            brief.md         the argument behind it
            prompts/*.txt    paste-ready, one control + variations
            refs/            the reference images, numbered as the prompt names them
        p144/ ...

The README repeats nothing a work order says better; it lists the briefs so
she can see the whole batch and tick them off, and names the two settings
that are the same for every one so she sets them once.
"""
import argparse, json, re, shutil, sys, tempfile, zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import paths as _P
WS = _P.REPO                      # the workspace, found by walking up — not counted
import briefs as B
import deliver as D

# Where a machine's output lands (CLAUDE.md, 2026-09-17): the
# record in git at runs/<machine>/<brand>/<run-label>/, media on Drive at the
# mirrored path. The zip is media; the README is its record.
MACHINE = "image-teardown"


def what_it_is(brief_md):
    # Some briefs put the sentence on the same line as the label, some on
    # the next; both are the brief's own first sentence.
    m = re.search(r"(?:\*\*What this is[.:]?\*\*|## What this is)\s*(.+?)(?=\n\n)",
                  brief_md, re.S)
    if not m:
        return ""
    s = re.sub(r"\s+", " ", m.group(1)).strip()
    return re.split(r"(?<=[.]) ", s)[0]


def elements(work_order):
    """The Higgsfield Elements a work order attaches, in its own words."""
    out = []
    for row in re.findall(r"^\| (the \w+) \| `([0-9a-f-]{36})` \| (.+?) \|$",
                          work_order, re.M):
        out.append(row)
    return out


def settings(work_order):
    m = re.search(r"## The settings.*?\n(\|.*?)(?=\n###|\n## )", work_order, re.S)
    return m.group(1).strip() if m else ""


def build(brand, out_dir, product=None):
    reg = B.load()
    base = json.loads((HERE / "drafts" / brand / "baseline.json").read_text()) \
        if (HERE / "drafts" / brand / "baseline.json").is_file() else {}
    product = product or base.get("product")
    # One pack per product line (2026-09-18): the designer works one product's
    # briefs as a batch, and the Elements and offer differ per product.
    ids = [b for b, r in sorted(reg["briefs"].items())
           if r.get("brand") == brand and r.get("run")
           and (r.get("product") or base.get("product")) == product
           and (HERE / "runs" / r["run"] / "out/06-brief.md").is_file()
           and (HERE / "worksheets" / brand / b / "work-order.md").is_file()]
    if not ids:
        sys.exit(f"no finished briefs for {brand}")

    # The tree is staged in a temp dir and only the zip and README survive:
    # the pack's pictures are gitignored and its text is already committed
    # once at the run, so a second copy in git would be a copy to drift.
    stage = Path(tempfile.mkdtemp(prefix="brief-pack-"))
    root = stage / f"{brand}-{product}-brief-pack"
    root.mkdir(parents=True)

    rows, first_wo, nprompts = [], None, 0
    for bid in ids:
        rec = reg["briefs"][bid]
        run = HERE / "runs" / rec["run"]
        ws = HERE / "worksheets" / brand / bid
        d = root / bid
        (d / "prompts").mkdir(parents=True)
        shutil.copy(run / "assets/source.jpg", d / "source.jpg")
        drf = D.newest_draft(brand, bid)
        if drf:
            shutil.copy(drf, d / "draft.png")
        shutil.copy(run / "out/06-brief.md", d / "brief.md")
        # a product with no banked Element ships its picture in the folder
        clean = HERE / "drafts" / brand / "products" / f"{product}-tube.png"
        if product != base.get("product") and clean.is_file():
            shutil.copy(clean, d / "product.png")
        wo = (ws / "work-order.md").read_text()
        (d / "work-order.md").write_text(wo)
        ps = sorted((ws / "prompts").glob("*.txt"))
        for p in ps:
            shutil.copy(p, d / "prompts" / p.name)
        if (ws / "refs").is_dir():
            shutil.copytree(ws / "refs", d / "refs")
        nprompts += len(ps)
        first_wo = first_wo or wo
        bm = (run / "out/06-brief.md").read_text()
        dec = rec.get("declares") or {}
        person = next((e for e in elements(wo) if e[0] == "the person"), None)
        rows.append((bid, what_it_is(bm), dec.get("concept") or "",
                     len(ps), person[2] if person else "",
                     (rec.get("drive") or {}).get("folder", "")))

    # A product Element is the same across the brand; read it off the first
    # work order rather than restating it here.
    prod = next((e for e in elements(first_wo) if e[0] == "the product"), None)
    people = {r[4] for r in rows}
    one_person = rows[0][4] if len(people) == 1 and rows[0][4] else None
    # The same woman sits for every brief in the batch, so her Element is
    # set once with the product's rather than repeated twenty-one times.
    person_row = ""
    if one_person:
        pe = next((e for e in elements(first_wo) if e[0] == "the person"), None)
        person_row = f"| the person | `{pe[1]}` | {pe[2]} |" if pe else ""
    lines = [
        f"# {brand} · {product} — brief pack",
        "",
        f"{len(ids)} briefs · {nprompts} pictures to make · packed {date.today()}",
        "",
        "Each folder is one brief. Open its `work-order.md` first — it says what "
        "to make, the settings, the Elements to attach, and the five-step job. "
        "Everything in the folder is there to match `source.jpg`; nothing is to "
        "be improved on.",
        "",
        "## Set these once — they are the same for every brief",
        "",
        settings(first_wo),
        "",
        "Attach these Higgsfield Elements to every generation, so every brief "
        "is the same woman and the same product:",
        "",
        "| | Element | Reads as |",
        "|---|---|---|",
        person_row,
        f"| the product | `{prod[1]}` | {prod[2]} |" if prod else "| the product | see work order | |",
        "",
        "" if one_person else ("The **person** Element changes per brief — it "
                               "is in each work order and in the table below."),
        "",
        "## The briefs",
        "",
        "| Brief | What it is | Concept | Pictures |"
        + ("" if one_person else " The person (Element) |") + " Drive |",
        "|---|---|---|---|" + ("" if one_person else "---|") + "---|",
    ]
    for bid, what, concept, n, person, drive in rows:
        link = f"[folder]({drive})" if drive else ""
        who = "" if one_person else f" {person} |"
        lines.append(f"| `{bid}` | {what} | {concept} | {n} |{who} {link} |")
    lines += [
        "",
        "## What goes back",
        "",
        "In each brief's folder, a `finals/` folder holding your one keeper per "
        "prompt, named after the prompt file (`00-control.png`, "
        "`01-<name>.png`, …). If a prompt would not land after two or three "
        "re-rolls, one line in `finals/notes.txt` saying which and what it kept "
        "doing — do not rewrite the prompt.",
        "",
        "Every brief's Drive folder is in the table above; drop `finals/` there.",
        "",
    ]
    readme = "\n".join(l for l in lines if l is not None)
    (root / "README.md").write_text(readme)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "README.md").write_text(readme)
    zp = out_dir / f"{brand}-{product}-brief-pack.zip"
    if zp.exists():
        zp.unlink()
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(root.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(stage))
    shutil.rmtree(stage)
    return zp, ids, nprompts, product


def upload_big(svc, path, parent):
    """deliver.upload sends a file in one write, which a 150 MB zip times out
    on. Same update-in-place and anyone-with-the-link rules, sent in chunks."""
    import socket
    from googleapiclient.http import MediaFileUpload
    socket.setdefaulttimeout(600)
    q = f"'{parent}' in parents and name='{path.name}' and trashed=false"
    hit = svc.files().list(q=q, fields="files(id)", supportsAllDrives=True,
                           includeItemsFromAllDrives=True).execute()["files"]
    media = MediaFileUpload(str(path), resumable=True, chunksize=8 * 1024 * 1024)
    req = (svc.files().update(fileId=hit[0]["id"], media_body=media,
                              supportsAllDrives=True, fields="id") if hit else
           svc.files().create(body={"name": path.name, "parents": [parent]},
                              media_body=media, fields="id",
                              supportsAllDrives=True))
    done = None
    while done is None:
        status, done = req.next_chunk(num_retries=5)
        if status:
            print(f"  {int(status.progress() * 100)}%", end="\r", flush=True)
    fid = done["id"]
    svc.permissions().create(fileId=fid, body={"role": "reader", "type": "anyone"},
                             supportsAllDrives=True).execute()
    return fid


def upload(brand, label, zp):
    """Drive, at the mirrored runs path: Shared Assets/runs/<machine>/<brand>/<label>/."""
    engine, svc = D.service()
    d = svc.drives().list(fields="drives(id,name)").execute()["drives"]
    shared = next((x for x in d if x["name"] == "Shared Assets"), None)
    if not shared:
        sys.exit("no 'Shared Assets' shared drive reachable by this account")
    node = shared["id"]
    for part in ("runs", MACHINE, brand, label):
        node = D.folder(engine, svc, part, node)
    fid = upload_big(svc, zp, node)
    # A link already handed out must stay current: a pack that used to be
    # named <brand>-brief-pack.zip (before packs were per product,
    # 2026-09-18) is refreshed under that name too, same file id.
    legacy = f"{brand}-brief-pack.zip"
    q = f"'{node}' in parents and name='{legacy}' and trashed=false"
    if svc.files().list(q=q, fields="files(id)", supportsAllDrives=True,
                        includeItemsFromAllDrives=True).execute()["files"]:
        tmp = zp.with_name(legacy)
        import shutil as _sh; _sh.copy(zp, tmp)
        upload_big(svc, tmp, node); tmp.unlink()
    return (f"https://drive.google.com/file/d/{fid}/view",
            f"https://drive.google.com/drive/folders/{node}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label")
    ap.add_argument("--product")
    ap.add_argument("--upload", action="store_true")
    a = ap.parse_args()
    base = json.loads((HERE / "drafts" / a.brand / "baseline.json").read_text()) \
        if (HERE / "drafts" / a.brand / "baseline.json").is_file() else {}
    product = a.product or base.get("product")
    # the baseline product keeps the label it has had since the first pack
    label = a.label or (f"brief-pack-{date.today()}" if product == base.get("product")
                        else f"brief-pack-{product}-{date.today()}")
    if not a.label and product == base.get("product"):
        # reuse the existing run label for the baseline product, if any
        prev = (B.load().get("packs") or {}).get(f"{a.brand}--{product}") or \
               (B.load().get("packs") or {}).get(a.brand)
        label = prev.get("label", label) if prev else label
    run_dir = WS / "runs" / MACHINE / a.brand / label
    out = run_dir / "deliverable"
    zp, ids, n, product = build(a.brand, out, product)
    a.label = label
    rec = {"machine": MACHINE, "brand": a.brand, "product": product, "label": a.label,
           "packed": str(date.today()), "briefs": ids, "prompts": n,
           "zip": zp.name, "zip_mb": round(zp.stat().st_size / 1_000_000)}
    print(f"{zp.relative_to(WS)}  ·  {len(ids)} briefs  ·  {n} prompts  ·  "
          f"{rec['zip_mb']} MB")
    if a.upload:
        url, folder = upload(a.brand, a.label, zp)
        rec["drive"] = {"zip": url, "folder": folder}
        reg = B.load()
        packs = reg.setdefault("packs", {})
        packs.pop(a.brand, None)          # the old brand-only key, pre 2026-09-18
        packs[f"{a.brand}--{product}"] = {
            "brand": a.brand, "product": product, "url": url, "label": a.label,
            "briefs": ids, "packed": rec["packed"]}
        B.save(reg)
        print(f"on Drive: {url}  ·  recorded in briefs.json")
    (run_dir / "run.json").write_text(json.dumps(rec, indent=1) + "\n")
