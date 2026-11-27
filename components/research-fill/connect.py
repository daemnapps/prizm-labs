#!/usr/bin/env python3
"""Connect a brand's own customer-word sources, prove each one works, and keep them pulling daily.

    python3 components/research-fill/connect.py reviews     --brand B --platform judgeme|junip --key KEY_NAME [--shop-domain D]
    python3 components/research-fill/connect.py surveys     --brand B --sheet SHEET_ID --name "Post-purchase" --relationship ordered|refund|lead
    python3 components/research-fill/connect.py interviews  --brand B [--inbox core-avatars/<a>/language/evidence/inbox] [--speaker "Our Name"]
    python3 components/research-fill/connect.py helpdesk    --brand B --helpdesk gorgias
    python3 components/research-fill/connect.py ad-comments --brand B --meta-account act_123
    python3 components/research-fill/connect.py feedback    --brand B --key KLAVIYO_KEY_NAME
    python3 components/research-fill/connect.py test        --brand B [--source reviews]   a dry run of each connected source: pulls and counts, files nothing
    python3 components/research-fill/connect.py daily       --brand B [--dry-run]          the daily pull for this brand, in this copy
    python3 components/research-fill/connect.py schedule    [--hour 5] [--minute 30] [--print]  the daily pull at 05:30 on this Mac

Every connect writes only the brand's own operations/language-pulls.json or operations/brand.json
(inside brands/<brand>/, which git ignores) and then runs that source's dry run, so you see at once
whether it works. Key values never go in these files: only the key's NAME. The value goes in .env
through the setup page. The daily pull and the dry runs reach only free sources; the gatherer
fails closed if anything tries a paid scrape. Standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GATHER = REPO / "components" / "research-gatherer" / "gather.py"
DAILY = REPO / "components" / "research-gatherer" / "daily.py"
KEY_NAME = re.compile(r"[A-Z][A-Z0-9_]{2,63}\Z")
MODE = {"reviews": "reviews", "surveys": "surveys", "interviews": "interviews", "feedback": "feedback",
        "helpdesk": "ownvoice", "ad-comments": "ownvoice"}
LABEL = "co.prizm.research-daily"


def _read(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _placeholder(value):
    return isinstance(value, str) and ("<" in value or "YYYY" in value)


class Sources:
    def __init__(self, brand, root=REPO):
        self.brand = brand
        self.root = Path(root)
        self.folder = self.root / "brands" / brand
        if not self.folder.is_dir():
            raise SystemExit(f"No brand folder brands/{brand}/. Pull or link it first (components/brand-sync).")
        self.pulls_path = self.folder / "operations" / "language-pulls.json"
        self.brand_path = self.folder / "operations" / "brand.json"

    def pulls(self):
        data = _read(self.pulls_path, {})
        if _placeholder(data.get("language_avatar")):
            avatars = [a.get("id") for a in _read(self.folder / "core-avatars" / "avatars.json", {}).get("avatars", [])
                       if a.get("id") and not _placeholder(a.get("id"))]
            data["language_avatar"] = avatars[0] if avatars else data.get("language_avatar")
        return data

    def _key(self, name):
        if not KEY_NAME.fullmatch(name or ""):
            raise SystemExit("Give the key's NAME (capitals, digits, _), never its value. The value goes in .env.")
        return name

    def reviews(self, platform, key, shop_domain=None, since=None):
        if platform not in ("junip", "judgeme"):
            raise SystemExit("Reviews: the platform is junip or judgeme.")
        if platform == "judgeme" and not shop_domain:
            raise SystemExit("Judge.me also needs --shop-domain (the shop's domain as Judge.me knows it).")
        data = self.pulls()
        block = {"platform": platform, "key": self._key(key), "note": ""}
        if shop_domain:
            block["shop_domain"] = shop_domain
        if since:
            block["since"] = since
        data["reviews"] = block
        _write(self.pulls_path, data)

    def surveys(self, sheet, name, relationship, survey=None, since=None):
        if relationship not in ("ordered", "refund", "lead"):
            raise SystemExit("Surveys: --relationship is ordered, refund or lead.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", sheet or ""):
            raise SystemExit("Surveys: --sheet is the Google Sheet's file id (the long part of its link).")
        data = self.pulls()
        rows = [s for s in data.get("surveys", []) if not _placeholder(s.get("survey")) and s.get("sheet") != sheet]
        sid = survey or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "survey"
        row = {"survey": sid, "name": name, "sheet": sheet, "relationship": relationship, "note": ""}
        if since:
            row["since"] = since
        data["surveys"] = rows + [row]
        _write(self.pulls_path, data)

    def interviews(self, inbox=None, speakers=None):
        data = self.pulls()
        avatar = data.get("language_avatar")
        inbox = inbox or f"core-avatars/{avatar or '<avatar>'}/language/evidence/inbox"
        if _placeholder(inbox):
            raise SystemExit("Interviews: name the avatar first (core-avatars/avatars.json) or give --inbox.")
        if ".." in Path(inbox).parts or Path(inbox).is_absolute():
            raise SystemExit("Interviews: --inbox is a folder inside the brand folder.")
        (self.folder / inbox).mkdir(parents=True, exist_ok=True)
        data["interviews"] = {"inbox": inbox, "company_speakers": speakers or [], "note": ""}
        _write(self.pulls_path, data)

    def feedback(self, key, since=None):
        data = self.pulls()
        block = {"enabled": True, "key": self._key(key), "metric": "Submitted Feedback", "note": ""}
        if since:
            block["since"] = since
        data["feedback"] = block
        _write(self.pulls_path, data)

    def _brand_json(self):
        data = _read(self.brand_path, {})
        if "_example_keys" in data and "brand" not in data:      # still the empty template
            data = {"brand": self.brand, "label": self.brand}
        return data

    def helpdesk(self, helpdesk):
        if helpdesk != "gorgias":
            raise SystemExit("Support inbox: only Gorgias is read today (through the brand's ads database).")
        data = self._brand_json()
        data.setdefault("accounts", {})["helpdesk"] = helpdesk
        _write(self.brand_path, data)
        if not self.pulls_path.exists():
            _write(self.pulls_path, self.pulls())

    def ad_comments(self, account):
        if not re.fullmatch(r"act_\d{5,20}", account or ""):
            raise SystemExit("Ad comments: --meta-account is the ad account id, like act_1234567890.")
        data = self._brand_json()
        accounts = [a for a in data.get("ad_accounts", []) if a.get("account") and a.get("account") != account]
        data["ad_accounts"] = accounts + [{"network": "meta", "account": account, "note": ""}]
        _write(self.brand_path, data)
        if not self.pulls_path.exists():
            _write(self.pulls_path, self.pulls())

    def connected(self):
        data = _read(self.pulls_path, {})
        out = []
        if (data.get("reviews") or {}).get("platform") in ("junip", "judgeme"):
            out.append("reviews")
        if any(not _placeholder(s.get("sheet", "<")) for s in data.get("surveys", [])):
            out.append("surveys")
        if data.get("interviews") and not _placeholder(data["interviews"].get("inbox", "<")):
            out.append("interviews")
        if (data.get("feedback") or {}).get("enabled"):
            out.append("feedback")
        b = _read(self.brand_path, {})
        if (b.get("accounts") or {}).get("helpdesk") or any(a.get("account") for a in b.get("ad_accounts", [])):
            out.append("ad-comments")
        return out


def dry_run(brand, source, root=REPO, runner=subprocess.run):
    mode = MODE[source]
    argv = [sys.executable, str(Path(root) / GATHER.relative_to(REPO)), mode, "--brand", brand, "--dry-run"]
    if mode == "ownvoice":
        argv.append("--no-scrape")
    r = runner(argv, capture_output=True, text=True, timeout=600)
    tail = "\n".join((r.stdout or "").strip().splitlines()[-6:] + (r.stderr or "").strip().splitlines()[-3:])
    return r.returncode, tail


def plist(hour, minute, root=REPO):
    py = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable
    logs = Path.home() / "Library" / "Logs" / "prizm"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array><string>{py}</string><string>{root / DAILY.relative_to(REPO)}</string><string>--inside</string></array>
  <key>EnvironmentVariables</key><dict><key>AI_WORKSPACE</key><string>{root}</string></dict>
  <key>WorkingDirectory</key><string>{root}</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>{hour}</integer><key>Minute</key><integer>{minute}</integer></dict>
  <key>StandardOutPath</key><string>{logs}/research-daily.out</string>
  <key>StandardErrorPath</key><string>{logs}/research-daily.err</string>
</dict></plist>
"""


def main(argv=None, out=sys.stdout, root=REPO, runner=subprocess.run):
    ap = argparse.ArgumentParser(description="Connect a brand's own customer-word sources.")
    ap.add_argument("cmd", choices=["reviews", "surveys", "interviews", "helpdesk", "ad-comments", "feedback", "test", "daily", "schedule"])
    ap.add_argument("--brand")
    ap.add_argument("--platform")
    ap.add_argument("--key")
    ap.add_argument("--shop-domain")
    ap.add_argument("--since")
    ap.add_argument("--sheet")
    ap.add_argument("--name")
    ap.add_argument("--relationship")
    ap.add_argument("--survey")
    ap.add_argument("--inbox")
    ap.add_argument("--speaker", action="append")
    ap.add_argument("--helpdesk")
    ap.add_argument("--meta-account")
    ap.add_argument("--source")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-test", action="store_true", help="write the connection, skip its dry run")
    ap.add_argument("--hour", type=int, default=5)
    ap.add_argument("--minute", type=int, default=30)
    ap.add_argument("--print", action="store_true", help="schedule: show the job, install nothing")
    a = ap.parse_args(argv)

    if a.cmd == "schedule":
        text = plist(a.hour, a.minute, Path(root))
        if a.print or sys.platform != "darwin":
            out.write(text)
            if sys.platform != "darwin":
                out.write("Not a Mac: run `connect.py daily --brand <b>` once a day with the system's own scheduler.\n")
            return 0
        target = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        (Path.home() / "Library" / "Logs" / "prizm").mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        subprocess.run(["launchctl", "unload", str(target)], capture_output=True)
        r = subprocess.run(["launchctl", "load", str(target)], capture_output=True, text=True)
        out.write(f"Daily pull scheduled at {a.hour:02d}:{a.minute:02d} for every brand in this copy.\n" if r.returncode == 0
                  else f"Couldn't load the schedule: {r.stderr.strip()}\n")
        return r.returncode

    if not a.brand:
        out.write("Name the brand: --brand <brand>.\n")
        return 2
    try:
        s = Sources(a.brand, root=root)
        if a.cmd == "daily":
            argv2 = [sys.executable, str(Path(root) / DAILY.relative_to(REPO)), "--inside", "--brand", a.brand] + (["--dry-run"] if a.dry_run else [])
            r = runner(argv2, capture_output=True, text=True, timeout=1800, env=dict(os.environ, AI_WORKSPACE=str(root)))
            out.write((r.stdout or "")[-3000:] + (r.stderr or "")[-1000:])
            return r.returncode
        if a.cmd == "test":
            sources = [a.source] if a.source else s.connected()
            if not sources:
                out.write("Nothing connected yet. Connect reviews, surveys, interviews, helpdesk or ad comments first.\n")
                return 1
            worst = 0
            for src in dict.fromkeys(MODE[x] for x in sources):
                name = next(k for k in sources if MODE[k] == src)
                code, tail = dry_run(a.brand, name, root, runner)
                out.write(f"{'✓' if code == 0 else '✗'} {name}\n{tail}\n")
                worst = worst or code
            return worst
        if a.cmd == "reviews":
            s.reviews(a.platform, a.key, a.shop_domain, a.since)
        elif a.cmd == "surveys":
            if not a.name:
                raise SystemExit("Surveys: give --name for the survey.")
            s.surveys(a.sheet, a.name, a.relationship, a.survey, a.since)
        elif a.cmd == "interviews":
            s.interviews(a.inbox, a.speaker)
        elif a.cmd == "helpdesk":
            s.helpdesk(a.helpdesk)
        elif a.cmd == "ad-comments":
            s.ad_comments(a.meta_account)
        elif a.cmd == "feedback":
            s.feedback(a.key, a.since)
    except SystemExit as err:
        out.write(f"{err}\n")
        return 2
    out.write(f"Connected {a.cmd} for {a.brand}.\n")
    if a.no_test:
        return 0
    code, tail = dry_run(a.brand, a.cmd, root, runner)
    out.write(f"{'✓ it pulls' if code == 0 else '✗ the dry run failed'}:\n{tail}\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
