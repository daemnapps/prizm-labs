"""The page chain's shared plumbing: where a run lives, how a stage is run and kept.

Every stage is one prompt file (`prompts/<stage>-v<N>-owner.md`, highest N wins) with {fields} filled from the run.
The prompt AS SENT and the output are both written into the run folder, word for word, so the owner page shows exactly
what ran. Models are called through components/run-kit (claude_door: any account, the next one when one runs out).

    runs/page-chain/<brand>/<label>/
        run.json                    what was declared, every stage's prompt name, hash, model, time
        source/page.txt|page.html   the captured page (page-teardown)
        <stage>--sent.md            the prompt exactly as sent
        <stage>.md / <stage>.json   the stage's output exactly as returned (json pulled out when the stage returns one)

Used by page-teardown, page-writing and page-production. Agnostic: no brand, person or machine path in here.

A run starts from its PAGE BRIEF (2026-11-14): `open_page_brief` numbers it in the brief register, reserves the
version on the page list (components/naming/page_list.py) and names the run `<place>_<page>_<vN>`; `file_build`
files the finished build as that version of the page.
"""
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def workspace():
    if os.environ.get("AI_WORKSPACE"):
        return Path(os.environ["AI_WORKSPACE"]).expanduser()
    p = Path(__file__).resolve()
    for up in p.parents:
        if (up / "components").is_dir() and (up / "brands").is_dir():
            return up
    raise SystemExit("cannot find the workspace (a folder holding components/ and brands/); set AI_WORKSPACE")


WS = workspace()
sys.path.append(str(WS / "components" / "run-kit"))
from run_kit import model as KIT  # noqa: E402

UsageLimit = KIT.UsageLimit


def run_dir(brand, label):
    d = WS / "runs" / "page-chain" / brand / label
    d.mkdir(parents=True, exist_ok=True)
    return d


def latest_prompt(prompts_dir, stage):
    hits = []
    for p in Path(prompts_dir).glob(f"{stage}-v*-owner.md"):
        m = re.search(r"-v(\d+)-owner\.md$", p.name)
        if m:
            hits.append((int(m.group(1)), p))
    if not hits:
        raise SystemExit(f"no prompt for stage `{stage}` in {prompts_dir}")
    return sorted(hits)[-1][1]


def fill(template, fields):
    wanted = set(re.findall(r"\{([a-z_]+)\}", template))
    missing = sorted(wanted - set(fields))
    if missing:
        raise SystemExit(f"prompt fields not supplied: {missing}")
    out = template
    for k, v in fields.items():
        out = out.replace("{" + k + "}", v if (v is not None and str(v).strip()) else "(none supplied)")
    return out


def pull_json(text):
    """The JSON a stage returned: the last ```json block, else the whole reply."""
    blocks = re.findall(r"```json\s*(.*?)```", text, re.S)
    raw = blocks[-1] if blocks else text
    raw = raw.strip()
    if not raw.startswith(("{", "[")):
        i = min([x for x in (raw.find("{"), raw.find("[")) if x >= 0] or [0])
        raw = raw[i:]
    return json.loads(raw)


JOBS = ("new-page", "new-control", "variant")


def _load(name, path):
    """A sibling component's public tool, loaded from its file under its own name (no clash with any other
    module of the same name on the path)."""
    import importlib.util
    d = str(Path(path).parent)
    if d not in sys.path:
        sys.path.append(d)
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def page_tools():
    """(page list, brief register) — naming's page_list.py and image-teardown's briefs.py, their public tools."""
    pl = _load("page_list", WS / "components" / "naming" / "page_list.py")
    br = _load("brief_register", WS / "components" / "image-teardown" / "tools" / "briefs.py")
    return pl, br


def open_page_brief(brand, page, job, product=None, title=None):
    """Number the page brief before anything runs. -> (run label, brief key, version)."""
    import fcntl
    import tempfile
    pl, br = page_tools()
    with open(os.path.join(tempfile.gettempdir(), "brief-register.lock"), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)           # the same lock every brief-numbering caller holds
        bid, rec = br.open_page_brief(brand, page, job, product=product, title=title)
        label = pl.run_label(page, rec["version"])
        reg = br.load()
        reg["briefs"][bid]["run"] = f"runs/page-chain/{brand}/{label}"
        br.save(reg)
    return label, bid, rec["version"]


def open_from_hypothesis(path):
    """The testing loop's hand-off: a hypothesis record → a variant page brief. -> (label, brief, version, record)."""
    import fcntl
    import tempfile
    pl, br = page_tools()
    with open(os.path.join(tempfile.gettempdir(), "brief-register.lock"), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        bid, rec = br.open_page_brief_from_hypothesis(path)
        label = pl.run_label(rec["page"], rec["version"])
        reg = br.load()
        reg["briefs"][bid]["run"] = f"runs/page-chain/{pl.parse_page_id(rec['page'])['brand']}/{label}"
        br.save(reg)
    return label, bid, rec["version"], rec


def control_url(page):
    """The address of the version holding the page's control mark (what a variant is built from)."""
    pl, _ = page_tools()
    _, e = pl.find(page)
    c = pl.control(e) if e else None
    return (c or {}).get("url") or (e or {}).get("url")


def file_build(run):
    """The finished build, filed on the page list as the run's version. None for a run with no page brief."""
    page, version = run.state.get("page"), run.state.get("version")
    if not page:
        return None
    pl, _ = page_tools()
    rel = f"runs/page-chain/{run.brand}/{run.label}"
    return pl.file_build(page, version, rel, rel + "/site/index.html")


class Run:
    def __init__(self, brand, label):
        self.brand, self.label = brand, label
        self.dir = run_dir(brand, label)
        self.state_path = self.dir / "run.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {
            "brand": brand, "label": label, "stages": {},
            "started": datetime.datetime.now().isoformat(timespec="seconds")}

    def save(self, **extra):
        self.state.update(extra)
        self.state["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
        self.state_path.write_text(json.dumps(self.state, indent=1, ensure_ascii=False))

    def stage(self, name, prompts_dir, fields, tier="designs", as_json=True, resume=False, order=None,
              component=None, title=None):
        """Run one stage (or keep it on resume while its prompt and inputs are unchanged). Returns the parsed
        JSON (as_json) or the text."""
        pf = latest_prompt(prompts_dir, name.split("@")[0])
        sent = fill(pf.read_text(), fields)
        h = hashlib.sha256(sent.encode()).hexdigest()[:12]
        out_md = self.dir / f"{name}.md"
        prev = self.state["stages"].get(name, {})
        if resume and out_md.exists() and prev.get("sent_sha") == h:
            print(f"  == {name} kept (same prompt, same inputs)")
            text = out_md.read_text()
        else:
            (self.dir / f"{name}--sent.md").write_text(sent)
            model, why = KIT.pick(tier, len(sent))
            print(f"  -> {name}  {pf.name} · {model} · {len(sent):,} chars in", flush=True)
            t0 = datetime.datetime.now()
            text = KIT.call(sent, model, label=name, timeout=1800)
            out_md.write_text(text.strip() + "\n")
            self.state["stages"][name] = dict(
                prompt=str(pf.relative_to(WS)), prompt_sha=hashlib.sha256(pf.read_bytes()).hexdigest()[:12],
                sent_sha=h, model=model, chars_in=len(sent), chars_out=len(text),
                seconds=round((datetime.datetime.now() - t0).total_seconds(), 1),
                sent=f"{name}--sent.md", out=out_md.name, component=component, title=title or name,
                order=order if order is not None else len(self.state["stages"]))
            self.save()
            print(f"     done in {self.state['stages'][name]['seconds']}s, {len(text):,} chars", flush=True)
        if not as_json:
            return text
        data = pull_json(text)
        (self.dir / f"{name}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
        return data


def read_ws(rel):
    p = WS / rel
    return p.read_text().strip() if p.is_file() else f"[UNFILLED: {rel} is not on file]"
