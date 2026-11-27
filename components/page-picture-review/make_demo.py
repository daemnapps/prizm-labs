#!/usr/bin/env python3
"""Build the numbered picture demo from the page kit's own build output.

    python3 make_demo.py <project> --state <page-dir> [--slug S] [--page P] [--out D] [--no-build]

The demo is the **built** page with a numbering overlay added — not a
reconstruction of it. campaign-build renders the page exactly as it deploys
(layout, includes, header and footer, the kit's own CSS and JS), and this
script then rewrites the built page's absolute asset URLs so the file works
from anywhere, and appends the overlay. What you look at is the real page.

Requires node_modules in the project (npm ci). --no-build reuses _site as-is.
--out inside the workspace must sit under runs/; anything else there is refused.
"""
import json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def _workspace():
    """The folder holding components/ and brands/ above this file (AI_WORKSPACE wins when
    it names one) — None when this file runs outside a workspace."""
    def is_ws(d):
        return os.path.isdir(os.path.join(d, 'brands')) and os.path.isdir(os.path.join(d, 'components'))
    env = os.environ.get('AI_WORKSPACE')
    if env and is_ws(env):
        return os.path.realpath(env)
    d = os.path.realpath(HERE)
    while True:
        if is_ws(d):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


WORKSPACE = _workspace()


def refuse_out(out_dir, workspace=None):
    """None when a demo may be written to out_dir, else the refusal.
    Inside the workspace a machine writes only under runs/ (K2 (brands write wall) brands write wall);
    outside it (the page kit's own repo, a temp folder) is not this workspace's to police."""
    if not (workspace or WORKSPACE):
        return None
    ws = os.path.realpath(workspace or WORKSPACE)
    out = os.path.realpath(out_dir)
    if os.path.commonpath([ws, out]) != ws:
        return None
    runs = os.path.join(ws, 'runs')
    if os.path.commonpath([runs, out]) == runs:
        return None
    return (f'refused: --out {out} is inside the workspace but outside its runs/ folder — '
            'a machine writes only under runs/ (brands/ is read-only to machines)')

OVERLAY = 'pic-index.js'                    # the engine's own
MARKS   = 'pic-marks.js'                    # optional layer: decide from the page
                                            # itself when it is a published artifact;
                                            # inert anywhere else
STATE_FILES = ['slots.json', 'pic-state.json', 'notes.json']   # the page's

# GTM and the Meta Pixel are stripped from the review copy: a picture review
# should not fire pageviews into the live property. Nothing visible changes.
ANALYTICS = [
    re.compile(r'<!--\s*Google Tag Manager.*?<!--\s*End Google Tag Manager[^>]*-->', re.S | re.I),
    re.compile(r'<script[^>]*>[^<]*?(?:googletagmanager\.com|fbevents\.js)[^<]*?</script>', re.S | re.I),
    re.compile(r'<noscript>\s*<iframe[^>]*googletagmanager[^>]*>.*?</noscript>', re.S | re.I),
]

def build(project, state_dir, slug=None, page=None, out_dir=None, run_build=True):
    import json as _json
    cfg = _json.load(open(os.path.join(state_dir, 'page.json')))
    slug = slug or cfg['slug']; page = page or cfg['page']
    project = os.path.abspath(project)
    if run_build:
        subprocess.run(['npx', 'campaign-build'], cwd=project, check=True,
                       stdout=subprocess.DEVNULL)
    built = os.path.join(project, '_site', slug, page, 'index.html')
    if not os.path.exists(built):
        sys.exit(f'no built page at {built} — run npm ci, then campaign-build')
    html = open(built, encoding='utf-8').read()

    out_dir = os.path.abspath(out_dir or os.path.dirname(built))
    why = refuse_out(out_dir)
    if why:
        sys.exit(why)
    # the build serves assets at /<slug>/<path>; they are src/<slug>/assets/<path> on disk
    src_assets = os.path.join(project, 'src', slug, 'assets')
    rel = os.path.relpath(src_assets, out_dir).replace(os.sep, '/')
    # the build writes the asset root in several quotings — plain, single, and
    # &quot; inside inline styles, plus bare in srcset — so rewrite every one
    n = html.count(f'/{slug}/')
    html = html.replace(f'/{slug}/', f'{rel}/')
    # version every local asset: a replaced picture keeps its filename, so without
    # this the browser shows the previous one and you review a stale page
    stamp = str(int(time.time()))
    esc = re.escape(rel)
    html = re.sub(rf'({esc}/[^"\'&\s)]+\.(?:jpg|jpeg|png|webp|svg|gif|css|js))',
                  rf'\1?b={stamp}', html)
    print(f'asset URLs rewritten: {n}, versioned b={stamp}')

    for pattern in ANALYTICS:
        html = pattern.sub('', html)

    slots = open(os.path.join(state_dir, 'slots.json'), encoding='utf-8').read()
    state = open(os.path.join(state_dir, 'pic-state.json'), encoding='utf-8').read()
    notes_path = os.path.join(state_dir, 'notes.json')
    notes = open(notes_path, encoding='utf-8').read() if os.path.exists(notes_path) else '{}'
    chip = ('<span style="background:%s;color:%s;padding:1px 6px;border-radius:3px">%s</span>')
    bar = ('<div style="position:fixed;z-index:100000;top:0;left:0;right:0;background:#111;color:#fff;'
           'font:600 12px/1.6 system-ui;padding:6px 12px;text-align:center">PICTURE INDEX &mdash; the built page, '
           'numbered &middot; ' + chip % ('#ffd600', '#111', 'D#') + ' desktop '
           + chip % ('#ffd600', '#111', 'M#') + ' mobile &middot; '
           + chip % ('#e53935', '#fff', 'replace') + ' '
           + chip % ('#e8730c', '#fff', 'redo') + ' '
           + chip % ('#55606b', '#fff', 'updated') + ' '
           + chip % ('#2e7d32', '#fff', 'keep / accepted') + ' &middot; '
           '<span id="pic-count">0 decided</span></div><div style="height:30px"></div>')
    overlay = (f'{bar}<script>window.PIC_SLOTS_INLINE={slots};'
               f'window.PIC_STATE_INLINE={state};window.PIC_NOTES_INLINE={notes};</script>'
               f'<script src="pic-index.js?b={stamp}"></script>'
               f'<script src="pic-marks.js?b={stamp}"></script>')
    assert '</body>' in html, 'built page has no </body>'
    html = html.replace('</body>', overlay + '</body>', 1)

    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, '_preview-landing.html')
    open(out, 'w', encoding='utf-8').write(html)
    for f in (OVERLAY, MARKS):
        shutil.copy(os.path.join(HERE, f), os.path.join(out_dir, f))
    placed = []
    same_dir = os.path.realpath(out_dir) == os.path.realpath(state_dir)
    for f in STATE_FILES:
        src = os.path.abspath(os.path.join(state_dir, f))
        dst = os.path.join(out_dir, f)
        if not os.path.isfile(src):          # notes.json is optional on read
            continue
        if same_dir:                         # the state IS the demo's folder
            placed.append(f)
            continue
        if os.path.lexists(dst):
            os.remove(dst)
        if f == 'pic-state.json':
            # the page polls this every 2 s; a link makes that poll read the
            # authoritative decisions, where a copy would freeze them at build time
            try:
                os.symlink(src, dst)
                placed.append(f + ' (link)')
                continue
            except OSError as e:
                print(f'pic-state.json copied, not linked ({e}) — the open page will '
                      f'NOT see live edits to {src}; regenerate after each change')
        shutil.copy(src, dst)
        placed.append(f)
    print('built page :', built)
    print('demo       :', out)
    print('assets via :', rel)
    print('kit copied :', ', '.join([OVERLAY, MARKS] + placed))

if __name__ == '__main__':
    a = sys.argv[1:]
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    no_build = '--no-build' in a
    if no_build: a.remove('--no-build')
    slug = opt('--slug'); page = opt('--page'); out = opt('--out')
    state = opt('--state')
    if not a or not state:
        sys.exit(__doc__)
    build(a[0], state, slug, page, out, run_build=not no_build)
