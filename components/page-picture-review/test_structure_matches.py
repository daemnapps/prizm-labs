#!/usr/bin/env python3
"""SI-180 (proof says structure matches): `bundle.py compare` says STRUCTURE
MATCHES, never IDENTICAL, when two fingerprints agree — it compares boxes,
fonts and image names and sizes, never pixels.

    python3 test_structure_matches.py

Stdlib only, no network; every case works in its own temp dir. Runs under
python3 and /usr/bin/python3 (3.9). Exit 0 only if every case passes.
"""
import contextlib, io, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bundle  # noqa: E402


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb' if isinstance(data, bytes) else 'w') as f:
        f.write(data)


def run_compare(a_path, b_path):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = bundle.compare(a_path, b_path)
    return rc, buf.getvalue()


def fingerprint():
    """One page as fingerprint.js reports it: a single 1200-wide hero.jpg."""
    return {"viewport": "1280x800", "imgTotal": 1, "imgBroken": 0, "brokenList": [],
            "fontsStatus": "loaded", "fontsLoaded": ["Serif"], "badges": 0,
            "sampleCount": 2, "volatileSkipped": 0, "digest": "d1", "hashes": [11, 22]}


def case_a():
    with tempfile.TemporaryDirectory() as t:
        # the two copies ship a different picture under the same name and size;
        # fingerprint.js records only the name and naturalWidth, so the two
        # fingerprints come out equal
        pa, pb = os.path.join(t, 'a', 'hero.jpg'), os.path.join(t, 'b', 'hero.jpg')
        write(pa, b'\xff\xd8' + b'\x01' * 64)
        write(pb, b'\xff\xd8' + b'\x02' * 64)
        assert os.path.getsize(pa) == os.path.getsize(pb)
        assert open(pa, 'rb').read() != open(pb, 'rb').read(), 'image bytes should differ'
        fa, fb = os.path.join(t, 'a', 'fp.json'), os.path.join(t, 'b', 'fp.json')
        write(fa, json.dumps(fingerprint()))
        write(fb, json.dumps(fingerprint()))
        rc, out = run_compare(fa, fb)
        assert rc == 0, f'equal structure returned {rc}, want 0\n{out}'
        assert out.startswith('STRUCTURE MATCHES'), f'output does not start STRUCTURE MATCHES:\n{out}'
        assert 'IDENTICAL' not in out.upper(), f'output claims IDENTICAL:\n{out}'
        assert '2 elements' in out and '1 font families' in out and '1 images' in out, \
            f'counts missing from output:\n{out}'


def case_b():
    with tempfile.TemporaryDirectory() as t:
        other = fingerprint()
        other['digest'], other['hashes'] = 'd2', [11, 33]
        fa, fb = os.path.join(t, 'a.json'), os.path.join(t, 'b.json')
        write(fa, json.dumps(fingerprint()))
        write(fb, json.dumps(other))
        rc, out = run_compare(fa, fb)
        assert rc == 1, f'differing digest returned {rc}, want 1\n{out}'
        assert out.startswith('DIFFERENT'), f'output does not start DIFFERENT:\n{out}'
        assert 'STRUCTURE MATCHES' not in out, f'differing digest says STRUCTURE MATCHES:\n{out}'


CASES = [
    ('a', 'equal structure, different image bytes: STRUCTURE MATCHES, never IDENTICAL', case_a),
    ('b', 'a differing digest still prints DIFFERENT and returns 1', case_b),
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
    print(f'\n{len(CASES) - failed}/{len(CASES)} passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
