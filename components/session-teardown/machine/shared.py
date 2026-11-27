"""The shared pieces this machine runs on, loaded from their own components (never copied here).

    run-kit           Chain (stages, tiers, depends, dry run, reuse, prompt as sent, run.json), filing, prompts
    marketing-chain-checks   the gates: hold() writes check.json and stops failing work
    page-teardown     the structure prompt (prompts/structure-vN-owner.md), capture.py (any page as text) and
                      chain_io.pull_json (the JSON a stage returned)
    naming            page_list.page_context — which page-chain run built a page's control (the page system's reader)
    page-production   chain_page.CSS — the page chain's run page look, so every teardown page reads the same

A sibling's module is loaded from its file under its own name (page-teardown chain_io's `_load` pattern), so
nothing here can shadow or be shadowed by a module of the same name.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENTS = HERE.parents[1]
WS = COMPONENTS.parent
for p in (COMPONENTS / "run-kit", COMPONENTS / "marketing-chain-checks"):
    if str(p) not in sys.path:
        sys.path.append(str(p))

PAGE_TEARDOWN = COMPONENTS / "page-teardown"
PAGE_TEARDOWN_PROMPTS = PAGE_TEARDOWN / "prompts"
PAGE_CHAIN_RUNS = WS / "runs" / "page-chain"


def load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    d = str(Path(path).parent)
    if d not in sys.path:
        sys.path.append(d)                       # appended: our own modules always win a name clash
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def chain_io():
    return load("chain_io", PAGE_TEARDOWN / "machine" / "chain_io.py")


def page_context(page_id):
    """The page system's reader (components/naming/page_list.py page_context): the page's entry, control, the brief
    and page-chain run that built it. None for a page it does not know, or if it cannot answer."""
    try:
        return load("page_list", COMPONENTS / "naming" / "page_list.py").page_context(page_id)
    except Exception:                            # noqa: BLE001 — the teardown falls back to its own scan
        return None


def capture():
    """page-teardown's capture (needs bs4; only a live run without a page-chain teardown on file calls it)."""
    return load("page_teardown_capture", PAGE_TEARDOWN / "machine" / "capture.py").capture


def page_css():
    try:
        return load("chain_page", COMPONENTS / "page-production" / "machine" / "chain_page.py").CSS
    except Exception:                            # the page still renders, plainer, if that file ever moves
        return ("body{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:0 auto;padding:20px 16px;"
                "background:#fbfaf7;color:#17181a}pre{white-space:pre-wrap}")
