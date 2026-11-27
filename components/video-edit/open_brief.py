#!/usr/bin/env python3
"""Video editing briefs, for the editor: list a brand's briefs and open one in HyperFrames or Premiere.

    python open_brief.py list <brand>
    python open_brief.py open <brief number> <hyperframes|premiere> [--brand <brand>]

Works on Mac and Windows. Finds the shared drive by itself (or SHARED_ASSETS=<path to Shared Assets>). Copies the brief to
~/VideoBriefs/<brief key>/ (the editor's own working copy; the shared folder is never edited), then:
  hyperframes  opens the HyperFrames project (hyperframes/edit/, or hyperframes/ in a Studio pack) in the HyperFrames app
  premiere     sets up the Premiere bridge once (prpr), builds the ready project (premiere/build.py) and opens it;
               a Studio pack's timeline (edit/<key>.premiere.xml) opens straight in Premiere
"""
import glob, json, os, platform, re, shutil, string, subprocess, sys
from pathlib import Path

WIN = platform.system() == "Windows"
ROLE = Path("runs") / "handoffs" / "video-editor"

def shared_assets() -> Path:
    env = os.environ.get("SHARED_ASSETS")
    cands = [Path(env)] if env else []
    home = Path.home()
    cands += [Path(p) for p in glob.glob(str(home / "Library/CloudStorage/GoogleDrive-*/Shared drives/Shared Assets"))]
    cands += [home / "Google Drive/Shared drives/Shared Assets", home / "My Drive/Shared drives/Shared Assets"]
    if WIN:
        cands += [Path(f"{d}:/Shared drives/Shared Assets") for d in string.ascii_uppercase]
    for c in cands:
        if (c / ROLE).is_dir():
            return c
    sys.exit("Can't find the shared drive 'Shared Assets'. Open Google Drive for desktop and sign in, "
             "or set SHARED_ASSETS to the folder's path.")

def brief_dirs(brand=None):
    root = shared_assets() / ROLE
    brands = [brand.lower()] if brand else sorted(p.name for p in root.iterdir() if p.is_dir())
    for b in brands:
        d = root / b
        if not d.is_dir():
            sys.exit(f"No video editing briefs for '{b}'. Brands: {', '.join(sorted(p.name for p in root.iterdir() if p.is_dir()))}")
        for k in sorted(d.iterdir(), key=lambda p: p.name):
            if k.is_dir() and not k.name.startswith(("_", ".")):
                yield b, k

def number(key):
    m = re.search(r"brief-(\d+)", key)
    return m.group(1) if m else key

def title_of(folder: Path):
    """The ad's name: BRIEF.md's first heading, else RUN.md's run-sheet line without its labels and key."""
    brief = folder / "BRIEF.md"
    if brief.exists():
        for line in brief.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    run = folder / "RUN.md"
    if run.exists():
        first = (run.read_text(encoding="utf-8", errors="ignore").splitlines() or [""])[0]
        parts = [x.strip() for x in re.sub(r"^#\s*", "", first).split("·")]
        parts = [x for x in parts if x and x.upper() != "RUN SHEET" and x != folder.name]
        if len(parts) > 1 and parts[0].isupper():
            parts = parts[1:]                          # the brand label
        return " · ".join(parts)
    try:                                               # a Studio pack without a run sheet: its clip list carries the title
        return json.loads((folder / "clips.json").read_text(encoding="utf-8")).get("title") or ""
    except (OSError, ValueError, AttributeError):
        return ""

def hyperframes_dir(folder: Path):
    """Where the HyperFrames project sits: hyperframes/edit/ (edit-line packs) or hyperframes/ (Studio packs)."""
    for d in (folder / "hyperframes" / "edit", folder / "hyperframes"):
        if (d / "index.html").exists():
            return d
    return None

def premiere_xml(folder: Path):
    """A Studio pack's Premiere timeline (edit/<key>.premiere.xml), or None."""
    hits = sorted((folder / "edit").glob("*.premiere.xml")) if (folder / "edit").is_dir() else []
    return hits[-1] if hits else None

def info(folder: Path):
    hf = hyperframes_dir(folder) is not None
    pr = any((folder / "premiere").glob("brief-*.xml")) or premiere_xml(folder) is not None
    back = [p.name for p in (folder / "returned").glob("*") if p.is_file() and not p.name.startswith(".")]
    return {"title": title_of(folder), "hyperframes": hf, "premiere": pr, "returned": bool(back)}

def approved_keys():
    """The briefs the owner approved (components/briefs/approved.py, beside this file's component)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "briefs"))
    import approved
    return approved.keys()

def cmd_list(brand):
    rows, ok = [], approved_keys()
    for b, k in brief_dirs(brand):
        if not re.search(r"brief-\d+", k.name):
            continue                                   # a hand-off goes out once the brief is numbered; anything else is a draft
        i = info(k)
        if k.name not in ok and not i["returned"]:
            continue                                   # only a brief the owner approved is the editor's to read (2026-11-25)
        opens = " + ".join(x for x in ("hyperframes", "premiere") if i[x]) or "—"
        delivery = json.loads((k / "delivery-state.json").read_text()) if (k / "delivery-state.json").is_file() else {}
        state = (delivery.get("state", "") + " · " + delivery.get("revision_id", "")) if delivery else ("back" if i["returned"] else "open")
        rows.append((number(k.name), i["title"][:60], opens, state, b))
    rows.sort(key=lambda r: r[0], reverse=True)
    ready = [r for r in rows if r[2] != "—"]
    print(f"{len(ready)} ready to edit ({len(rows)} briefs in all)\n")
    print(f"{'Brief':<7} {'Opens in':<24} {'State':<6} What")
    for r in rows:
        print(f"{r[0]:<7} {r[2]:<24} {r[3]:<6} {r[1]}")
    print("\nSay: open brief <number> in hyperframes   (or: in premiere)")

def find(num, brand=None):
    hits = [(b, k) for b, k in brief_dirs(brand) if number(k.name) == str(num).lstrip("#").zfill(4) or number(k.name) == str(num)]
    if not hits:
        sys.exit(f"No brief {num}" + (f" for {brand}" if brand else "") + ".")
    return hits[-1]

def local_copy(src: Path) -> Path:
    dst = Path.home() / "VideoBriefs" / src.name
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if rel.parts and rel.parts[0] == "returned":
            continue
        if p.suffix in (".prproj", ".prin") or any(x in ("Adobe Premiere Pro Auto-Save", "Motion Graphics Template Media") for x in rel.parts):
            continue                                   # another machine's Premiere files never come along
        q = dst / rel
        if p.is_dir():
            q.mkdir(parents=True, exist_ok=True)
        elif not q.exists() or q.stat().st_size != p.stat().st_size or q.stat().st_mtime < p.stat().st_mtime:
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)
    (dst / "returned").mkdir(exist_ok=True)
    return dst

def launch(path: Path, app=None):
    if WIN:
        os.startfile(str(path))
    else:
        subprocess.run(["open"] + (["-a", app] if app else []) + [str(path)])

def premiere_app():
    if WIN:
        return None
    apps = sorted(glob.glob("/Applications/Adobe Premiere Pro */Adobe Premiere Pro *.app"))
    return apps[-1] if apps else None

VENV = Path.home() / ".video-briefs" / "venv"           # the bridge lives in its own space: no system installs

def venv_python():
    return VENV / ("Scripts/python.exe" if WIN else "bin/python")

def prpr_bin():
    b = VENV / ("Scripts/prpr.exe" if WIN else "bin/prpr")
    return str(b) if b.exists() else None

def ensure_prpr():
    if not prpr_bin():
        print("Setting up the Premiere bridge (once)...")
        if not venv_python().exists():
            subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(venv_python()), "-m", "pip", "install", "--quiet", "--upgrade", "pip", "prpr"], check=True)
    b = prpr_bin()
    st = subprocess.run([b, "-f", "json", "plugin", "status"], capture_output=True, text=True)
    if '"installed": true' not in (st.stdout or ""):
        subprocess.run([b, "plugin", "install"], check=True)
        return b, True
    return b, False

ADDON = Path(__file__).resolve().parent / "premiere"   # captions-bridge.zxp + make_captions.jsx
UPIA = ("C:/Program Files/Common Files/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.exe" if WIN else
        "/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent")

def captions_addon():
    """The small Premiere add-on that turns captions.srt into a real, retypable caption track. True if just installed."""
    if not Path(UPIA).exists():
        return None
    listed = subprocess.run([UPIA, "--list", "all"], capture_output=True, text=True).stdout or ""
    if "Video Briefs Captions" in listed:
        return False
    subprocess.run([UPIA, "--install", str(ADDON / "captions-bridge.zxp")], capture_output=True, text=True)
    return True

def make_captions(srt: Path):
    import urllib.request
    jsx = (ADDON / "make_captions.jsx").read_text(encoding="utf-8").replace("__SRT__", srt.as_posix())
    try:
        with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8875/jsx", data=jsx.encode("utf-8"), method="POST"), timeout=90) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return None

def cmd_open(num, app, brand=None):
    b, src = find(num, brand)
    if src.name not in approved_keys() and not info(src)["returned"]:
        sys.exit(f"Brief {number(src.name)} is not approved yet, so it is not ready to edit.")
    i = info(src)
    app = app.lower()
    if app not in ("hyperframes", "premiere"):
        sys.exit("Say which: hyperframes or premiere.")
    if not i[app]:
        sys.exit(f"Brief {number(src.name)} isn't packed for {app} yet.")
    print(f"Copying brief {number(src.name)} to your machine...")
    dst = local_copy(src)
    if app == "hyperframes":
        hf = shutil.which("hyperframes")
        if not hf:
            subprocess.run(["npm", "i", "-g", "hyperframes"], check=True, shell=WIN)
            hf = shutil.which("hyperframes")
        subprocess.run([hf, "open", str(hyperframes_dir(dst))], shell=WIN)
        print(f"Brief {number(src.name)} is open in HyperFrames. Finished master goes in {dst / 'returned'}")
        return
    xml = premiere_xml(dst)
    if xml and not (dst / "premiere" / "build.py").exists():
        launch(xml, premiere_app())                    # a Studio pack: its timeline opens straight in Premiere
        print(f"Brief {number(src.name)} is open in Premiere: the timeline with made scenes in place and a named placeholder "
              f"for every clip to make (CLIPS.md has each one's recipe).\nFinished master goes in {dst / 'returned'}")
        return
    b, fresh = ensure_prpr()
    fresh = (captions_addon() is True) or fresh
    ping = subprocess.run([b, "--timeout", "40", "ping"], capture_output=True, text=True)
    if ping.returncode:
        if fresh:
            sys.exit("The Premiere bridge is installed. Quit Premiere, open it again, then say the same thing once more.")
        sys.exit("Premiere didn't answer. Open Premiere, then say the same thing once more.")
    r = subprocess.run([str(venv_python()), str(dst / "premiere" / "build.py")], capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.strip()[-400:])
    if r.returncode:
        sys.exit(r.stderr[-800:] or "The Premiere build stopped.")
    said = make_captions(dst / "premiere" / "captions.srt")
    caps = ("captions are a real caption track: click any caption to retype it, restyle them all at once"
            if said and "createCaptionTrack true" in said else "captions are on as clips (restart Premiere once for retypable captions)")
    print(f"Brief {number(src.name)} is open in Premiere: the rough cut assembled, every piece its own clip; {caps}.\n"
          f"Finished master goes in {dst / 'returned'}")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("list", "open"):
        sys.exit(__doc__)
    if a[0] == "list":
        cmd_list(a[1] if len(a) > 1 else None)
    else:
        brand = a[a.index("--brand") + 1] if "--brand" in a else None
        cmd_open(a[1], a[2] if len(a) > 2 else "hyperframes", brand)
