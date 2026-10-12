#!/usr/bin/env python3
"""One ad drop, handed over — assembled, verified, and refused if it is short.

    handoff.py --brand <brand> --drop <drop> --for <person@example.com>
    handoff.py --brand <brand> --drop <drop> --check        # verify, change nothing
    handoff.py --dir runs/image-teardown/<brand>/<drop>/deliverable --for …

the owner, 2026-09-24, after a handoff reached the person without the pictures:
*"stop these types of issues from happening. Make sure these things are
clean, consolidated, and systemized so that when I just do ad handoffs,
everything is ready to go. There should be no question. You're wasting my
time."*

**Every check below is a failure that actually happened**, not a precaution
somebody imagined:

| # | Check | The day it bit |
|---|---|---|
| 1 | the handoff document carries its own Drive link | the document travelled on its own and the pictures were unreachable |
| 2 | every picture is on DRIVE with bytes, matched by name through the API | Drive for Desktop went offline mid-copy and the server got filenames with no bytes |
| 3 | every ad has at least one picture | a brief whose rolls all failed shipped an empty folder |
| 4 | every ad has copy, and the copy names no ad that has no pictures | the copy and the pictures were built to two different labels |
| 5 | every ad name parses to the naming convention | a name that does not parse cannot join spend back to the creative |
| 6 | every funnel link answers 200 | two of three destinations were on a branch that was never deployed |
| 7 | the person it is for can open the folder | the one thing nobody can check from inside the folder |

A failing check **refuses the handoff and names what is missing**. It never
prints a link to something incomplete, because a link that half-works costs
more time than no link at all. Exit 0 READY (all seven ran and passed),
1 REFUSED, 2 PARTIAL — nothing failed but `--offline` or no `--for` left
checks unrun, so no link either (SI-149).

The drop is not built here — `image-edit` makes the pictures, `copywriter`
writes the copy, `naming` names them. This is the gate they all pass through
on the way to a person.
"""
import argparse, csv, json, os, re, sys, urllib.error, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this gate
from run_kit.paths import repo  # noqa: E402  the one workspace locator (triage page 12)

try:
    WS = repo(HERE)
except FileNotFoundError:
    raise SystemExit("no workspace root above this file")
sys.path.insert(0, str(WS / "components/naming"))
RUNS = WS / "runs" / "ad-handoff"     # every verdict's record, for the runs filer (SI-103)


def drop_dir(brand, drop):
    """A drop's deliverable/: runs/image-teardown/<brand>/<drop>/deliverable/,
    else the legacy runs/image-edit/<brand>/<drop>/deliverable/ for a drop filed
    before 2026-10-07. The new home when neither exists."""
    for machine in ("image-teardown", "image-edit"):
        d = WS / "runs" / machine / brand / drop / "deliverable"
        if d.is_dir():
            return d
    return WS / "runs" / "image-teardown" / brand / drop / "deliverable"


# ---- the pieces the checks read ---------------------------------------
def ad_folders(d: Path):
    return sorted(x for x in d.iterdir() if x.is_dir() and not x.name.startswith("."))


MEDIA = (".png", ".jpg", ".jpeg", ".mp4", ".mov")   # finished videos ship in a drop like pictures (1 Oct 2026)


def pictures(folder: Path):
    """Every finished picture or video in one ad's folder."""
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in MEDIA)


def copy_rows(d: Path):
    f = d / "copy.csv"
    if not f.is_file():
        return []
    with f.open(newline="") as fh:
        return list(csv.DictReader(fh))


def links(d: Path):
    """The funnel links this drop's ads point at, if it declares any."""
    f = d / "links.json"
    if f.is_file():
        return json.loads(f.read_text())
    out, doc = {}, d / "HANDOFF.md"
    if doc.is_file():                      # fall back to the table in the page
        page = doc.read_text()
        for name, url in re.findall(r"\|\s*\*\*(.+?)\*\*[^|]*\|\s*`?(https?://\S+?)`?\s*\|",
                                    page):
            out[name.strip()] = url
        # … and to its [text](https://…) links (SI-149); not pictures, and not the
        # folder's own Drive address, which is check 1's, not a funnel destination
        for name, url in re.findall(r"(?<!!)\[([^\]]+)\]\((https?://[^)\s]+)\)", page):
            name = name.strip()
            if "drive.google.com/" in url or url in out.values():
                continue
            out[name if name not in out else f"{name} · {url}"] = url
    return out


class NotOnDrive(Exception):
    """A segment of the drop's Drive path is not there — the path so far."""


def drive_folder(brand, drop, engine, svc, parts):
    """The drop's folder on Shared Assets, found READ-ONLY (SI-149): per segment
    gdrive-creator's two looks — the name search, then the parent listing —
    and never `engine.folder`, which creates what it does not find. A missing
    segment raises NotOnDrive naming the path; nothing is made on Drive."""
    node = engine.shared_drive_id("Shared Assets", svc)
    if not node:
        raise SystemExit("no 'Shared Assets' shared drive reachable by this account")
    for i, p in enumerate(parts):
        node = engine._folder_by_name(svc, p, node) or engine._folder_listed(svc, p, node)
        if not node:
            raise NotOnDrive("Shared Assets/" + "/".join(parts[:i + 1]))
    return node


def drive_service():
    """The same door every other tool opens Drive through — the keys module
    beside video-teardown loads this machine's vault into the environment."""
    sys.path.insert(0, str(WS / "components/gdrive-creator"))
    sys.path.insert(0, str(WS / "tools/video-teardown/machine"))
    import keys
    for k, v in (keys.all_keys() or {}).items():
        os.environ.setdefault(k, v)
    from gdrive_creator import engine
    return engine, engine.service()


def resolves(url, timeout=20):
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": "Mozilla/5.0 (ad-handoff check)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.reason
    except Exception as e:                              # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


# ---- the seven checks --------------------------------------------------
def run_checks(d: Path, brand, drop, for_whom, online=True, checked=None):
    """(problems, notes, folder_id). `checked`, when given, is a set this fills
    with the numbers of the checks that actually ran in full — fewer than seven
    is a PARTIAL run, never READY (SI-149)."""
    problems, notes = [], []
    checked = set() if checked is None else checked
    ads = ad_folders(d)
    rows = copy_rows(d)

    # 3 · every ad has at least one picture
    empty = [a.name for a in ads if not pictures(a)]
    if empty:
        problems.append(f"{len(empty)} ad folder(s) hold no picture: " + ", ".join(empty[:4]))
    here = {f"{a.name}/{p.name}" for a in ads for p in pictures(a)}
    npics = len(here)
    notes.append(f"{len(ads)} ads · {npics} pictures")
    checked.add(3)

    # 4 · copy for every ad, and no copy row pointing at an ad that is not here
    if not rows:
        problems.append("no copy.csv — the ads have no copy to go with them")
    else:
        named = {a.name for a in ads}
        have = {r.get("ad_name", "").strip() for r in rows}
        missing = sorted(named - have)
        orphan = sorted(x for x in have - named if x)
        blank = [r.get("ad_name", "?") for r in rows if not (r.get("primary_text") or "").strip()]
        if missing:
            problems.append(f"{len(missing)} ad(s) have pictures but no copy row: "
                            + ", ".join(x[-24:] for x in missing[:4]))
        if orphan:
            problems.append(f"{len(orphan)} copy row(s) name an ad with no pictures here: "
                            + ", ".join(x[-24:] for x in orphan[:4]))
        if blank:
            problems.append(f"{len(blank)} ad(s) have an empty primary text")
        notes.append(f"{len(rows)} copy rows")
    checked.add(4)

    # 5 · every ad name parses to the convention — a check that cannot run refuses
    try:
        import names as N
    except Exception as e:                              # noqa: BLE001
        problems.append(f"name check could not run — {type(e).__name__}")
    else:
        bad = []
        for a in ads:
            try:
                # either form parses to one dict; None is a name that is not ours
                if N.parse_any(a.name) is None:
                    bad.append(f"{a.name[-28:]} (not 13/14 values in either form)")
            except Exception as e:                      # noqa: BLE001
                bad.append(f"{a.name[-28:]} ({e})")
        if bad:
            problems.append(f"{len(bad)} ad name(s) do not parse: " + "; ".join(bad[:3]))
        checked.add(5)

    # 6 · every funnel link answers — offline, nothing is resolved and it is not counted
    funnel = links(d) or {}
    if online:
        for name, url in funnel.items():
            code, why = resolves(url)
            if code != 200:
                problems.append(f"funnel link '{name}' answers {code or why} — {url}")
    if funnel:
        notes.append(f"{len(funnel)} funnel link(s)" + ("" if online else " — not resolved, offline"))
    if online or not funnel:
        checked.add(6)

    # 2 and 7 · Drive: the bytes are there, and the person can open it
    folder_id = None
    if online:
        try:
            engine, svc = drive_service()
            folder_id = drive_folder(brand, drop, engine, svc,
                                     ["runs", d.parents[2].name if len(d.parents) > 3 and d.parents[3].name == "runs"
                                      else "image-teardown", brand, drop, "deliverable"])
            kids = svc.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id,name,mimeType)", pageSize=500,
                supportsAllDrives=True, includeItemsFromAllDrives=True).execute()["files"]
            dfolders = [f for f in kids if f["mimeType"].endswith("folder")]
            there, empty_bytes = set(), []
            for fo in dfolders:
                got = svc.files().list(
                    q=f"'{fo['id']}' in parents and trashed=false",
                    fields="files(name,size)", pageSize=500,
                    supportsAllDrives=True, includeItemsFromAllDrives=True).execute()["files"]
                pics = [g for g in got if g["name"].lower().endswith(MEDIA)]
                there |= {f"{fo['name']}/{g['name']}" for g in pics}
                empty_bytes += [f"{fo['name']}/{g['name']}" for g in pics
                                if not int(g.get("size") or 0)]
            # the same <ad>/<file> names on both sides, not just the same count
            short, extra = sorted(here - there), sorted(there - here)
            if short:
                problems.append(f"{len(short)} picture(s) here are not on Drive — the mirror "
                                "is short: " + ", ".join(x[-40:] for x in short[:3]))
            if extra:
                problems.append(f"{len(extra)} picture(s) on Drive are not in this folder: "
                                + ", ".join(x[-40:] for x in extra[:3]))
            if empty_bytes:
                problems.append(f"{len(empty_bytes)} picture(s) on Drive have no bytes "
                                "(a sync that stopped half way): "
                                + ", ".join(x[-40:] for x in empty_bytes[:3]))
            docs = {f["name"] for f in kids if not f["mimeType"].endswith("folder")}
            for must in ("HANDOFF.md", "copy.csv"):
                if must not in docs:
                    problems.append(f"{must} is not on Drive")
            notes.append(f"{len(there & here)} of {npics} pictures matched on Drive by name")
            checked.add(2)

            if for_whom:
                perms = svc.permissions().list(
                    fileId=folder_id, supportsAllDrives=True,
                    fields="permissions(type,role,emailAddress)").execute()["permissions"]
                who = {p.get("emailAddress", "").lower() for p in perms}
                if for_whom.lower() not in who:
                    # emails only (SI-132 (handoff group honesty)): say what was not checked
                    miss = (f"{for_whom} is not on this folder by email — group or domain "
                            "access is not checked; if they reach Shared Assets through a "
                            "group, share the folder with them directly")
                    if any(p.get("type") in ("group", "domain") for p in perms):
                        miss += (" (this folder has group/domain grants, which this check "
                                 "cannot see into)")
                    problems.append(miss)
                else:
                    notes.append(f"{for_whom} can open it")
                checked.add(7)
        except SystemExit:
            raise
        except NotOnDrive as e:
            problems.append(f"not on Drive yet: {e}")
        except Exception as e:                          # noqa: BLE001
            problems.append(f"could not verify against Drive — {type(e).__name__}: {e}")

    # 1 · the document carries its own Drive link — online, THIS folder's link
    doc = d / "HANDOFF.md"
    linked = re.findall(r"https://drive\.google\.com/drive/folders/([A-Za-z0-9_-]+)",
                        doc.read_text()) if doc.is_file() else []
    if not doc.is_file():
        problems.append("no HANDOFF.md — nothing tells the person what this is")
    elif not linked:
        problems.append("HANDOFF.md does not carry the Drive link to this folder — "
                        "the moment it travels on its own the pictures are unreachable")
    elif folder_id:
        if folder_id in linked:
            checked.add(1)
        else:
            problems.append(f"HANDOFF.md links Drive folder {', '.join(linked[:2])}, but this "
                            f"drop's folder on Drive is {folder_id} — the page points elsewhere")

    return problems, notes, folder_id


def stamp_link(d: Path, folder_id):
    """Put this folder's own address at the top of its handoff page."""
    doc = d / "HANDOFF.md"
    if not doc.is_file() or not folder_id:
        return False
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    s = doc.read_text()
    if url in s:
        return False
    s = re.sub(r"https://drive\.google\.com/drive/folders/\S+", url, s) if \
        re.search(r"https://drive\.google\.com/drive/folders/\S+", s) else \
        s.replace("\n", f"\n\n### 📁 {url}\n", 1)
    doc.write_text(s)
    return True


def write_verdict(brand, drop, problems, folder_id, d, check_only, runs=None, partial=False):
    """File this verdict at runs/ad-handoff/<brand>/<drop>/ — run.json + check.json,
    the shape the runs filer reads (SI-103 (handoff verdict record)). A write that
    fails says so on stderr and changes nothing else: the verdict still stands.
    A run that skipped a check is `partial`, with no link (SI-149)."""
    out = Path(runs or RUNS) / brand / drop
    try:
        rel = str(Path(d).resolve().relative_to(WS))
    except ValueError:
        rel = str(d)
    link = None if problems or partial or not folder_id else \
        f"https://drive.google.com/drive/folders/{folder_id}"
    state = "refused" if problems else "partial" if partial else "ready"
    run = {"tool": "ad-handoff", "brand": brand, "drop": drop,
           "state": state, "check_only": bool(check_only),
           "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "drop_dir": rel, "link": link}
    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "run.json").write_text(json.dumps(run, indent=2) + "\n")
        (out / "check.json").write_text(
            json.dumps({"held": bool(problems), "problems": list(problems)}, indent=2) + "\n")
    except OSError as e:
        print(f"ad-handoff: verdict record not written to {out} — {e}", file=sys.stderr)


def dir_names(d: Path, brand=None, drop=None):
    """(brand, drop) read off a --dir that ends <brand>/<drop>/deliverable, or a
    refusal naming the path — the Drive walk and the verdict record are both
    named by them, so neither may be None (SI-149)."""
    if d.name != "deliverable" or not d.parent.name or not d.parent.parent.name:
        raise SystemExit(f"--dir must end <brand>/<drop>/deliverable — cannot tell "
                         f"the brand and drop from {d}")
    got = (d.parent.parent.name, d.parent.name)
    if (brand or got[0], drop or got[1]) != got:
        raise SystemExit(f"--dir {d} is {got[0]}/{got[1]}, not --brand {brand} --drop {drop}")
    return got


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand"); ap.add_argument("--drop")
    ap.add_argument("--dir", help="the deliverable folder, if it is not at the standard path")
    ap.add_argument("--for", dest="for_whom", help="who it is being handed to, by email")
    ap.add_argument("--check", action="store_true", help="verify only; change nothing")
    ap.add_argument("--offline", action="store_true", help="skip every check that needs the network")
    a = ap.parse_args()

    if a.dir:
        d = Path(a.dir) if Path(a.dir).is_absolute() else WS / a.dir
        brand, drop = dir_names(d, a.brand, a.drop)
    else:
        if not (a.brand and a.drop):
            raise SystemExit("--brand and --drop, or --dir")
        d = drop_dir(a.brand, a.drop)
        brand, drop = a.brand, a.drop
    if not d.is_dir():
        raise SystemExit(f"no drop at {d}")

    print(f"ad handoff · {brand} · {drop}\n")
    checked = set()
    problems, notes, folder_id = run_checks(d, brand, drop, a.for_whom,
                                            online=not a.offline, checked=checked)
    for n in notes:
        print(f"  · {n}")
    print()
    partial = len(checked) < 7
    write_verdict(brand, drop, problems, folder_id, d, a.check, partial=partial)
    if problems:
        print(f"REFUSED — {len(problems)} thing(s) to fix before this goes to anyone:\n")
        for p in problems:
            print(f"  ✗ {p}")
        print("\nNo link printed. A link to an incomplete handoff costs more time "
              "than no link.")
        sys.exit(1)

    if partial:
        # nothing failed, but not everything was looked at — that is not READY (SI-149)
        skipped = ", ".join(str(n) for n in range(1, 8) if n not in checked)
        why = "--offline skips Drive and the funnel links" if a.offline else \
            "no --for, so nobody's access was checked"
        print(f"PARTIAL — {len(checked)} of 7 checked (not checked: {skipped}; {why}).\n")
        print("No link printed. Run it online with --for <email> for a verdict.")
        sys.exit(2)

    if not a.check and stamp_link(d, folder_id):
        print("  · wrote this folder's own address into HANDOFF.md")
    print("READY — every check passed.\n")
    print(f"  {'https://drive.google.com/drive/folders/' + folder_id if folder_id else d}")
    print("\nSend that. It carries the pictures, the copy, the lists and the page "
          "that explains them.")


if __name__ == "__main__":
    main()
