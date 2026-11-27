#!/usr/bin/env python3
"""PPR-1 (picture bundle gate honest): the publish gate and the copy proof say
PASS or STRUCTURE MATCHES only when it is true.

    python3 test_ppr1.py

Stdlib only, no network, no ffmpeg/ffprobe/npx; every case works in its own temp
dir. Runs under python3 and /usr/bin/python3 (3.9). Exit 0 only if every case
passes.
"""
import contextlib, io, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bundle, fit, make_demo  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


def files_under(root, skip=()):
    found = set()
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if os.path.join(d, x) not in skip]
        found.update(os.path.join(d, n) for n in names)
    return found


def case_a():
    got = bundle.refs_in('<img srcset="a.jpg 1x, b.jpg 2x"><img srcset="c.jpg 480w,d.jpg 800w">'
                         '<video poster="p.png">', '.html')
    want = {'a.jpg', 'b.jpg', 'c.jpg', 'd.jpg', 'p.png'}
    assert want <= set(got), f'missing {sorted(want - set(got))} from {got}'


def case_b():
    with tempfile.TemporaryDirectory() as t:
        write(os.path.join(t, 'index.html'),
              '<img srcset="absent.jpg 2x"><video poster="absent.png"></video>')
        rc = quiet(bundle.check, t)
        assert rc == 1, f'both absent: check returned {rc}, want 1'
        write(os.path.join(t, 'absent.jpg'), 'x')
        write(os.path.join(t, 'absent.png'), 'x')
        rc = quiet(bundle.check, t)
        assert rc == 0, f'both present: check returned {rc}, want 0'


def case_c():
    with tempfile.TemporaryDirectory() as t:
        assets = os.path.join(t, 'funnel', 'assets')
        write(os.path.join(assets, 'a.css'), '@import "../../x.css";\n')
        write(os.path.join(t, 'x.css'), 'body{}')          # where the import resolves
        demo = os.path.join(t, 'demo', 'demo.html')
        write(demo, '<link rel="stylesheet" href="../funnel/assets/a.css"></head><body></body>')
        out = os.path.join(t, 'build', 'out')              # dst would be build/x.css
        out2 = os.path.join(t, 'build', 'out2')
        before = files_under(t)

        missing = quiet(bundle.stage, demo, assets, out)
        assert missing == [], f'stage returned missing={missing}'
        new = files_under(t, skip=(out,)) - before
        assert not new, f'written outside --out: {sorted(new)}'
        man = json.load(open(os.path.join(out, 'bundle-manifest.json')))
        assert '../../x.css' in man.get('refused_outside', []), \
            f"refused_outside = {man.get('refused_outside')}"
        assert os.path.isfile(os.path.join(out, 'assets', 'a.css')), 'a.css was not staged'

        r = subprocess.run([sys.executable, os.path.join(HERE, 'bundle.py'), 'stage',
                            demo, assets, '--out', out2],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        assert r.returncode == 1, f'CLI stage exit {r.returncode}, want 1\n{r.stdout}'
        new = files_under(t, skip=(out, out2)) - before
        assert not new, f'CLI wrote outside --out: {sorted(new)}'


def case_d():
    good = {"viewport": "1280x800", "sampleCount": 3, "digest": "abc", "hashes": [1, 2, 3],
            "imgTotal": 0, "imgBroken": 0, "badges": 0, "fontsStatus": "loaded",
            "fontsLoaded": []}
    no_digest = dict(good)
    del no_digest['digest']
    with tempfile.TemporaryDirectory() as t:
        def fp(name, obj):
            p = os.path.join(t, name)
            write(p, json.dumps(obj))
            return p
        e1, e2 = fp('e1.json', {}), fp('e2.json', {})
        g1, g2, nd = fp('g1.json', good), fp('g2.json', good), fp('nd.json', no_digest)
        rc = quiet(bundle.compare, e1, e2)
        assert rc == 1, f'{{}} vs {{}} returned {rc}, want 1'
        rc = quiet(bundle.compare, g1, nd)
        assert rc == 1, f'valid vs no-digest returned {rc}, want 1'
        rc = quiet(bundle.compare, g1, g2)
        assert rc == 0, f'structure-matching valid returned {rc}, want 0'


def case_e():
    with tempfile.TemporaryDirectory() as t:
        write(os.path.join(t, 'geometry.json'), json.dumps({
            'desktop': {'1': {'mode': 'native', 'min': [100, 100]},
                        '2': {'target': [10, 10], 'anchor': [0.5, 0.5]}},
            'mobile': {}}))
        write(os.path.join(t, 'slots.json'), '{}')
        desktop, _mobile, _slots = fit.load_state(t)
        assert desktop[1]['mode'] == 'native', desktop[1]
        assert list(desktop[1]['min']) == [100, 100], desktop[1]
        assert desktop[2]['target'] == (10, 10), desktop[2]


class Demo(object):
    """The (f) build, kept alive so (g) can edit its state afterwards."""
    tmp = state = out = None


def case_f():
    Demo.tmp = tempfile.TemporaryDirectory()
    t = Demo.tmp.name
    project, state, out = (os.path.join(t, n) for n in ('project', 'state', 'out'))
    write(os.path.join(project, '_site', 's', 'p', 'index.html'),
          '<html><body><img src="/s/img/a.jpg"></body></html>')
    os.makedirs(os.path.join(project, 'src', 's', 'assets'))
    write(os.path.join(state, 'page.json'), json.dumps({'slug': 's', 'page': 'p', 'kit': 'k'}))
    write(os.path.join(state, 'slots.json'), '{}')
    write(os.path.join(state, 'pic-state.json'), '{}')
    Demo.state, Demo.out = state, out
    quiet(make_demo.build, project, state, out_dir=out, run_build=False)
    for f in ('_preview-landing.html', 'pic-index.js', 'pic-marks.js', 'slots.json',
              'pic-state.json'):
        assert os.path.isfile(os.path.join(out, f)), f'{f} missing from out'
    assert not os.path.lexists(os.path.join(out, 'notes.json')), 'notes.json appeared in out'


def case_g():
    assert Demo.out, '(f) did not run'
    link = os.path.join(Demo.out, 'pic-state.json')
    assert os.path.islink(link), 'out/pic-state.json is not a symlink'
    write(os.path.join(Demo.state, 'pic-state.json'), json.dumps({'1': 'keep'}))
    got = json.load(open(link))
    assert got == {'1': 'keep'}, f'out/pic-state.json reads {got}'


def case_h():
    rc = quiet(fit.selftest)
    assert rc == 0, f'fit.selftest returned {rc}'


CASES = [
    ('a', 'refs_in finds srcset candidates and poster', case_a),
    ('b', 'check fails a page with absent srcset/poster targets', case_b),
    ('c', 'stage refuses an @import outside --out and writes nothing there', case_c),
    ('d', 'compare refuses an empty or digest-less fingerprint', case_d),
    ('e', 'load_state keeps a native desktop entry', case_e),
    ('f', 'build with no notes.json runs clean', case_f),
    ('g', 'the demo pic-state.json is a live link to --state', case_g),
    ('h', 'fit selftest', case_h),
]


def main():
    failed = 0
    for key, name, fn in CASES:
        try:
            fn()
            print(f'PASS ({key}) {name}')
        except Exception as e:                      # noqa: BLE001 — report and go on
            failed += 1
            print(f'FAIL ({key}) {name}: {type(e).__name__}: {e}')
    if Demo.tmp:
        Demo.tmp.cleanup()
    print(f'\n{len(CASES) - failed}/{len(CASES)} passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
