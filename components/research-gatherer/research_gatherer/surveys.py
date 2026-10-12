"""Surveys — new form answers into the avatar's bank.

    python3 components/research-gatherer/gather.py surveys --brand B [--dry-run] [--since D] [--avatar A]

Built 2026-09-29 (free sources run on a trigger). The surveys are the brand's
own config — `operations/language-pulls.json` › `surveys`, one entry per response
sheet:

    {"survey": "customers", "name": "Brand Improvement (Customers)",
     "sheet": "<Google Sheet file id>", "relationship": "ordered",
     "lane": "churned" (optional), "since": "2026-08-25"}

Read free, through the Google Drive API as the workspace's service account
(`GDRIVE_SA_KEY`): the sheet's first tab exported as CSV. The Sheets API is
not used (not switched on for that project). A sheet the service account
cannot open is named in the run's notes, never guessed around.

One row per answer: question = the form question (`q-<nn>_<slug>`, reusing
the number the bank already gave that question), item = the response id (a
hash of the timestamp and the respondent's email — the email is never
stored), source id `survey_<brand>_<survey>`. Email, name and phone columns
are never read into a row. Cursor: runs/research/<brand>/surveys-state.json,
the newest response timestamp per survey, moved only when nothing is held.
"""
import argparse
import csv
import datetime as dt
import io
import json
import re
from pathlib import Path

from . import annotate as A
from . import voicepull as V

say = V.say
SKIP_COL = re.compile(r"(e-?mail|name|phone|address|zip|order (number|#)|^timestamp$|^d$)", re.I)
EMPTY = {"", "n/a", "na", "no", "none", "nope", "nothing", "-", ".", "no comment", "no comments", "nothing else", "not at all"}
TS_FORMATS = ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y")


def parse_ts(s):
    s = (s or "").strip()
    for f in TS_FORMATS:
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            continue
    return None


def parse_since(s):
    """`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS` (a cursor) -> datetime, else None."""
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "")[:19]) if s else None
    except ValueError:
        return None


def qslug(q, n=60):
    s = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (q or "").lower())).strip("-")
    return s[:n].rstrip("-")


def bank_questions(ldir, source_id):
    """{question slug: q-id} the bank already uses for this survey."""
    out = {}
    for f in ldir.parent.rglob("*.json"):
        if "/used/" in str(f):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for e in d.get("entries", []) if isinstance(d, dict) else []:
            s = e.get("source") or {}
            q = s.get("question")
            if s.get("id") == source_id and isinstance(q, str) and re.match(r"^q-\d+_", q):
                out.setdefault(q.split("_", 1)[1], q)
    return out


def question_ids(headers, known):
    """q-id per question column: the bank's own when the slug matches (a
    prefix either way — older ids were cut at 60 characters), else the next
    free number."""
    used = {int(q[2:q.index("_")]) for q in known.values()}
    nxt = max(used or {0}) + 1
    out = {}
    for i, h in enumerate(headers):
        s = qslug(h)
        hit = next((q for k, q in known.items() if s and (s.startswith(k) or k.startswith(s))), None)
        if not hit:
            hit = f"q-{nxt:02d}_{s}"
            nxt += 1
        out[i] = hit
    return out


def rows_from_csv(text, survey, brand, label, today, since=None, known=None):
    """CSV text -> (rows, newest timestamp seen). Pure — the tests call it."""
    table = list(csv.reader(io.StringIO(text)))
    if not table:
        return [], None
    head = table[0]
    qcols = [i for i, h in enumerate(head) if i > 0 and h.strip() and not SKIP_COL.search(h.strip())]
    email_col = next((i for i, h in enumerate(head) if re.search(r"e-?mail", h, re.I)), None)
    sid = f"survey_{brand}_{survey['survey']}"
    qids = question_ids([head[i] for i in qcols], known or {})
    since_ts = parse_since(since)
    newest, out = None, []
    rel = survey.get("relationship") or "survey respondent, relationship unknown"
    rel = "ordered" if rel in ("ordered", "customer") else rel
    url = f"https://docs.google.com/spreadsheets/d/{survey.get('sheet', '')}"
    for line in table[1:]:
        ts = parse_ts(line[0] if line else "")
        if ts is None:
            continue
        newest = max(newest, ts) if newest else ts
        if since_ts and ts <= since_ts:
            continue
        resp = V.rid(line[0], line[email_col] if email_col is not None and email_col < len(line) else "")
        for k, i in enumerate(qcols):
            ans = (line[i] if i < len(line) else "").strip()
            if len(ans) < 3 or re.sub(r"[^a-z ]", "", ans.lower()).strip() in EMPTY:
                continue
            q = qids[k]
            out.append(dict(kind="survey", text=A.clean(ans), said=ts.strftime("%Y-%m-%d"), pulled=today,
                            ref=f"{url}#response-{resp}·{q.split('_')[0]}", item=resp,
                            source_name=f"{survey.get('name') or survey['survey']} survey — Q: {head[i].strip()}",
                            source_type="survey", source_id=sid, source_kind="survey", property=brand,
                            question=q, relationship=rel,
                            force_lane=survey.get("lane")))
    return out, newest


def export_csv(file_id):
    """The sheet's first tab as CSV, through the Drive API as the service
    account. (text, None) or (None, why)."""
    raw = V.key("GDRIVE_SA_KEY")
    if not raw:
        return None, "GDRIVE_SA_KEY not found (environment or Keychain)"
    try:
        p = Path(raw).expanduser()
        info = json.loads(p.read_text()) if p.is_file() else json.loads(raw)
    except Exception as e:
        return None, f"GDRIVE_SA_KEY could not be read as a service-account key ({str(e)[:60]})"
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as e:
        return None, f"the Google client library is not installed for this python ({str(e)[:60]})"
    try:
        cr = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive.readonly"])
        d = build("drive", "v3", credentials=cr, cache_discovery=False)
        return d.files().export(fileId=file_id, mimeType="text/csv").execute().decode("utf-8", "replace"), None
    except Exception as e:
        msg = str(e)
        if "404" in msg or "403" in msg:
            return None, (f"the service account {info.get('client_email', '?')} cannot open this sheet — "
                          "share it with that address (Viewer)")
        return None, msg[:160]


def main(argv=None, fetch=None, labeller=None, claude=None):
    ap = argparse.ArgumentParser(prog="gather.py surveys")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar")
    ap.add_argument("--since", help="YYYY-MM-DD; default = each survey's cursor, else its `since` in language-pulls.json")
    ap.add_argument("--dry-run", action="store_true", help="pull and count; read and file nothing")
    a = ap.parse_args(argv)
    fetch = fetch or export_csv
    c = V.cfg("surveys")
    bj = V.brand_json(a.brand)
    label = bj.get("label") or a.brand
    surveys = bj.get("surveys") or []
    now, today, run_label = V.now_labels()
    say(f"surveys · {a.brand}{' · DRY RUN' if a.dry_run else ''}")
    if not surveys:
        say("  no surveys in language-pulls.json — nothing to pull")
        return 0
    avatar = V.avatar_for(a.brand, bj, a.avatar)
    if not avatar:
        say("  name the avatar (--avatar, or language_avatar in language-pulls.json)")
        return 2
    ldir = A.lang_dir(a.brand, avatar)
    state = V.load_state(a.brand, "surveys")
    notes, rows, newest, counts = [], [], {}, {}
    for s in surveys:
        sid = f"survey_{a.brand}_{s['survey']}"
        since = a.since or (state.get(s["survey"]) or {}).get("last_response") or s.get("since") or c.get("first_run_since")
        text, why = fetch(s.get("sheet"))
        if text is None:
            notes.append(f"{s.get('name') or s['survey']}: {why}")
            say(f"  {s['survey']}: MISSING — {why}")
            continue
        got, nw = rows_from_csv(text, s, a.brand, label, today, since, bank_questions(ldir, sid))
        old = V.bank_texts(ldir, sid)   # the hand import of 2026-08-25 carries no response ref
        got = [r for r in got if len(r["text"]) < 25 or V.norm(r["text"]) not in old]
        counts[s["survey"]] = len(got)
        if nw:
            newest[s["survey"]] = nw.strftime("%Y-%m-%dT%H:%M:%S")
        say(f"  {s['survey']}: {len(got)} new answers since {since}")
        rows += got
    fresh, filed, dropped, held = V.file_rows(a.brand, avatar, label, rows, "survey answers", c, run_label,
                                              a.dry_run, labeller=labeller, claude=claude)
    if filed is None:
        say("  dry run — nothing read, nothing filed" if a.dry_run else "  nothing new")
        if not a.dry_run:
            for k, v in newest.items():
                state.setdefault(k, {})["last_response"] = v
            V.save_state(a.brand, "surveys", state)
        return 0
    V.write_run(a.brand, "surveys", label, run_label, a.since or "each survey's cursor", filed, dropped, held, notes,
                extra={"avatar": avatar, "answers": counts},
                intro="New answers to the brand's own surveys since the last run. Every row below is now in the "
                      "brand's language bank, with its lane, awareness level and sophistication signal.")
    if not held:
        for k, v in newest.items():
            state.setdefault(k, {})["last_response"] = v
        V.save_state(a.brand, "surveys", state)
    return 0
