#!/usr/bin/env python3
"""Stage the demo as a self-contained bundle, and prove the bundle is complete.

    python3 bundle.py stage   <demo.html> <assets-dir> --out <dir> [--state <page-dir>]
    python3 bundle.py check   <dir> [--state <page-dir>]
    python3 bundle.py compare <a.json> <b.json>

Why this exists. `make_demo.py` writes a demo that reaches its pictures with a
relative path into the funnel's own `assets/`, which works inside a clone and
nowhere else. Publishing the demo means copying every file it can ask for into
one folder — and the set of those files is a GRAPH, not a list: the page names
a design stylesheet, which `@import`s a fonts stylesheet, which names four
`.woff2` faces the page never mentions. A regex over the HTML finds none of
them, the page publishes clean, and every line of type silently falls back to a
system sans. That happened on 2026-09-18; this module is the answer to it.

Three layers, and only the third is proof:

  stage    walk the reference graph transitively, so the bundle is closed
  check    assert statically that every local URL resolves — refuse otherwise
  compare  diff two rendered fingerprints (see fingerprint.js) so the published
           copy is shown to match the original, rather than assumed to

`check` exits non-zero when a local reference is missing. Wire it before the
publish call and a missing asset can never reach a reviewer.
"""
import json, os, posixpath, re, shutil, sys

# Text formats that can themselves reference further files. Anything else is a
# leaf — we copy it and stop.
#
# .js is deliberately NOT here. A script builds URLs at runtime, so no static
# reader can tell a real reference from a fragment of code — scanning the
# overlay's own `[style*="url("]` selector yields the "path" `]`. Scripts are
# covered by the render fingerprint instead, which sees what the browser
# actually fetched.
FOLLOW = {'.css', '.svg'}

def load_known_missing(state_dir):
    """References this page's kit makes and does not ship, with a reason each.

    Kit content, not engine content: the engine has no opinion about which 404 is
    acceptable. Absent a state dir, nothing is tolerated and every unresolved
    reference fails the gate.
    """
    if not state_dir:
        return {}
    p = os.path.join(state_dir, 'known-missing.json')
    if not os.path.isfile(p):
        return {}
    return {k: v for k, v in json.load(open(p)).items() if not k.startswith('_')}


ASSET_RE = r'[^"\'&\s)]+\.(?:jpg|jpeg|png|webp|svg|gif|css|js|woff2?|ttf|eot|mp4|webm)'

# What the artifact viewer's CSP admits. Anything external and not on this list
# is blocked in a published artifact and will render blank or unstyled.
CSP_OK = ('https://fonts.googleapis.com/', 'https://fonts.gstatic.com/',
          'https://cdnjs.cloudflare.com/', 'https://cdn.jsdelivr.net/npm/')


def refs_in(text, ext):
    """Every reference a text asset makes, by the rules of ITS OWN format.

    Applying HTML's src=/href= to a .js file finds fragments of code; applying
    CSS's url() to everything is safe. So the patterns are chosen per format.
    HTML is entity-decoded first: the kit writes inline styles as
    `url(&quot;assets/img/x.jpg&quot;)`, and the raw text would otherwise yield
    a path with `&quot;` glued to both ends.
    """
    if ext == '.html':
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&amp;', '&')
    out = re.findall(r'url\(\s*[\'"]?([^)\'"]+)', text)          # every format
    if ext == '.css':
        out += re.findall(r'@import\s+[\'"]([^\'"]+)', text)
    if ext in ('.html', '.svg'):
        out += re.findall(r'(?:src|href|poster)\s*=\s*[\'"]([^\'"]+)', text)
        # srcset is a comma list of "<url> [descriptor]" candidates; every one is
        # a file the browser may fetch, so every one must resolve
        for s in re.findall(r'srcset\s*=\s*[\'"]([^\'"]+)', text):
            out += [c.split()[0] for c in s.split(',') if c.strip()]
    return [r.strip() for r in out]


def is_local(u):
    return not u.startswith(('data:', 'http://', 'https://', '//', '#', 'mailto:'))


def is_hint(u):
    """A bare origin is a preconnect/dns-prefetch hint, not a loaded resource.

    It costs a DNS lookup that never happens under the artifact CSP and renders
    nothing, so counting it as blocked is noise that hides the real blocks.
    """
    return re.fullmatch(r'(?:https?:)?//[^/]+/?', u) is not None


def inside(path, root):
    """True when `path`, symlinks resolved, is `root` or lies beneath it."""
    p, r = os.path.realpath(path), os.path.realpath(root)
    return p == r or p.startswith(r.rstrip(os.sep) + os.sep)


def stage(demo, assets_dir, out, prefix='assets'):
    """Copy the demo and the transitive closure of its assets into `out`."""
    html = open(demo, encoding='utf-8').read()
    here = os.path.dirname(os.path.abspath(demo))

    # the demo addresses assets by a relative path into the funnel; find it and
    # flatten it to <prefix>/ so the bundle stands on its own
    rel_prefix = re.search(rf'((?:\.\./)+[^"\'&\s)]*?/assets/)', html)
    if not rel_prefix:
        sys.exit(f'{demo}: no relative assets prefix found — was this made by make_demo.py?')
    rel_prefix = rel_prefix.group(1)

    seeds = {m.split('/assets/', 1)[1].split('?')[0]
             for m in re.findall(re.escape(rel_prefix) + ASSET_RE, html)}

    staged, missing, refused, queue = set(), [], set(), sorted(seeds)
    while queue:
        rel = queue.pop(0)
        if rel in staged or rel in refused:
            continue
        src = os.path.join(assets_dir, rel)
        dst = os.path.join(out, prefix, rel)
        # a reference like `@import "../../x.css"` climbs out of the assets dir
        # and, flattened under <prefix>/, out of the bundle too — never read or
        # write outside either root (realpath, so a symlink cannot smuggle it)
        if not inside(src, assets_dir) or not inside(dst, out):
            refused.add(rel)
            continue
        if not os.path.isfile(src):
            missing.append(rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
        staged.add(rel)
        # follow the graph: a staged text asset's own references, resolved
        # relative to ITS folder, not the page's
        ext = os.path.splitext(rel)[1].lower()
        if ext in FOLLOW:
            body = open(src, encoding='utf-8', errors='replace').read()
            for r in refs_in(body, ext):
                if not is_local(r) or r.endswith('/'):
                    continue
                queue.append(posixpath.normpath(
                    posixpath.join(posixpath.dirname(rel), r.split('?')[0])))

    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(
        html.replace(rel_prefix, prefix + '/'))

    # the overlay's own kit sits beside the demo and is fetched by name
    kit = []
    for f in ('pic-index.js', 'pic-marks.js', 'slots.json', 'pic-state.json', 'notes.json'):
        p = os.path.join(here, f)
        if os.path.isfile(p):
            shutil.copy(p, os.path.join(out, f))
            kit.append(f)

    manifest = {'demo': os.path.abspath(demo), 'assets_dir': os.path.abspath(assets_dir),
                'prefix': prefix, 'seeds': len(seeds), 'staged': sorted(staged),
                'kit': kit, 'missing_at_stage': sorted(missing),
                'refused_outside': sorted(refused)}
    json.dump(manifest, open(os.path.join(out, 'bundle-manifest.json'), 'w'), indent=1)

    print(f'seeds from the page : {len(seeds)}')
    print(f'staged (closure)    : {len(staged)}  (+{len(staged) - len(seeds)} found by following text assets)')
    print(f'kit copied          : {", ".join(kit) or "none"}')
    if missing:
        print(f'NOT FOUND in source : {len(missing)} — {", ".join(missing)}')
    if refused:
        print(f'REFUSED, outside    : {len(refused)} — {", ".join(sorted(refused))}'
              f'  (resolves outside {assets_dir} or {out}; not copied)')
    print(f'bundle              : {out}')
    return missing


def check(bundle, state_dir=None):
    """Assert every local reference in the bundle resolves. Exit 1 if not."""
    known_missing = load_known_missing(state_dir)
    broken, external, hints, known = [], {}, set(), set()
    n_files = n_refs = 0
    for root, _dirs, files in os.walk(bundle):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in FOLLOW | {'.html'}:
                continue
            path = os.path.join(root, name)
            text = open(path, encoding='utf-8', errors='replace').read()
            n_files += 1
            for r in refs_in(text, ext):
                n_refs += 1
                if not is_local(r):
                    if r.startswith(('http://', 'https://', '//')):
                        if is_hint(r):
                            hints.add(r)
                        else:
                            external.setdefault(r.split('?')[0],
                                                any(r.startswith(p) for p in CSP_OK))
                    continue
                if r.endswith('/'):          # a directory link, not a file request
                    continue
                target = posixpath.normpath(posixpath.join(
                    os.path.relpath(root, bundle).replace(os.sep, '/').lstrip('.').lstrip('/'),
                    r.split('?')[0].split('#')[0]))
                if not target or target.endswith('/'):
                    continue
                if not os.path.isfile(os.path.join(bundle, target)):
                    stripped = target.split('/', 1)[1] if target.startswith('assets/') else target
                    if stripped in known_missing:
                        known.add(stripped)
                    else:
                        broken.append((os.path.relpath(path, bundle), r))

    print(f'scanned {n_files} text files, {n_refs} references')
    if hints:
        print(f'connection hints (no resource) : {len(hints)}')
    blocked = [u for u, ok in external.items() if not ok]
    allowed = [u for u, ok in external.items() if ok]
    print(f'external, CSP-allowed : {len(allowed)}')
    for u in sorted(allowed):
        print(f'    ok      {u}')
    print(f'external, CSP-BLOCKED : {len(blocked)}   (these render blank when published)')
    for u in sorted(blocked):
        print(f'    BLOCKED {u}')
    if known:
        print(f'known-absent, acknowledged   : {len(known)}')
        for k in sorted(known):
            print(f'    (ok)    {k} — {known_missing[k]}')
    if broken:
        print(f'\nMISSING LOCAL FILES: {len(broken)} — the bundle is NOT closed')
        for where, ref in broken:
            print(f'    {where}  ->  {ref}')
        return 1
    print('\nclosed: every local reference resolves')
    return 0


def invalid_fields(fp):
    """The fields a fingerprint must carry to be compared, and does not."""
    if not isinstance(fp, dict):
        return ['viewport', 'sampleCount', 'digest']
    gaps = []
    if not fp.get('viewport'):
        gaps.append('viewport')
    n = fp.get('sampleCount')
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        gaps.append('sampleCount')
    d = fp.get('digest')
    if not isinstance(d, str) or not d:
        gaps.append('digest')
    return gaps


def compare(a_path, b_path):
    """Diff two fingerprints from fingerprint.js. Exit 1 on any difference.

    `a` is the original demo, `b` the bundle that would be published. The
    element digest is the headline: equal digests mean the two pages share the
    same structure, fonts and image names — every sampled box, font and picture
    name and size — not the same pixels. fingerprint.js never reads image bytes,
    so a different picture under the same name and size still matches.
    """
    a, b = json.load(open(a_path)), json.load(open(b_path))
    # two empty or truncated files agree on every .get() below, so a side that
    # is not a real fingerprint is refused before anything is compared
    invalid = False
    for side, fp in (('a', a), ('b', b)):
        gaps = invalid_fields(fp)
        if gaps:
            print(f"INVALID FINGERPRINT — {side}: missing {', '.join(gaps)}")
            invalid = True
    if invalid:
        return 1
    problems = []

    if a.get('viewport') != b.get('viewport'):
        problems.append(f"viewport differs — {a.get('viewport')} vs {b.get('viewport')}; "
                        f"the comparison is only meaningful at one size")

    for key in ('imgTotal', 'imgBroken', 'badges', 'sampleCount', 'fontsStatus'):
        if a.get(key) != b.get(key):
            problems.append(f'{key}: {a.get(key)!r} vs {b.get(key)!r}')

    if b.get('imgBroken'):
        problems.append(f"bundle has {b['imgBroken']} broken image(s): "
                        f"{', '.join(b.get('brokenList', []))}")

    fa, fb = set(a.get('fontsLoaded', [])), set(b.get('fontsLoaded', []))
    if fa != fb:
        problems.append(f'font families loaded differ — missing from bundle: '
                        f'{sorted(fa - fb) or "none"}; extra: {sorted(fb - fa) or "none"}')

    ha, hb = a.get('hashes', []), b.get('hashes', [])
    if a.get('digest') != b.get('digest'):
        diff = [i for i, (x, y) in enumerate(zip(ha, hb)) if x != y]
        problems.append(f'element digest differs — {len(diff)} of {min(len(ha), len(hb))} '
                        f'elements render differently; indices {diff[:20]}'
                        + (' ...' if len(diff) > 20 else ''))
        problems.append('  rerun fingerprint.js with window.FP_DETAIL = '
                        f'{diff[:5]} on both pages to see what changed')

    if problems:
        print(f'DIFFERENT — {len(problems)} finding(s)')
        for p in problems:
            print('   ', p)
        return 1
    print(f"STRUCTURE MATCHES at {a.get('viewport')} — {a.get('sampleCount')} elements "
          f"(digest {a.get('digest')}), {len(fa)} font families, "
          f"{a.get('imgTotal')} images, 0 broken")
    return 0


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a.pop(0)
    if cmd == 'stage':
        def opt(name, default=None):
            if name in a:
                i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
            return default
        out = opt('--out'); prefix = opt('--prefix', 'assets'); state = opt('--state')
        if len(a) != 2 or not out:
            sys.exit('usage: bundle.py stage <demo.html> <assets-dir> --out <dir>')
        stage(a[0], a[1], out, prefix)
        rc = check(out, state)
        refused = json.load(open(os.path.join(out, 'bundle-manifest.json'))).get('refused_outside')
        if refused:
            print(f'\nREFUSED: {len(refused)} reference(s) resolve outside the assets dir or '
                  f'--out — the bundle is NOT closed')
            rc = 1
        sys.exit(rc)
    elif cmd == 'check':
        state = None
        if '--state' in a:
            i = a.index('--state'); state = a[i + 1]; del a[i:i + 2]
        sys.exit(check(a[0], state))
    elif cmd == 'compare':
        sys.exit(compare(a[0], a[1]))
    else:
        sys.exit(__doc__)
