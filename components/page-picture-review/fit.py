#!/usr/bin/env python3
"""Fit a generated master into a slot, encode it, and say what it cost.

    python3 fit.py <master> --slot 59 [--mobile] --repo <cpk> --state <page-dir> [--dry-run]
    python3 fit.py --batch <dir> --slots 59-70 --repo <cpk> --state <page-dir> [--dry-run]
    python3 fit.py --selftest

The crop reproduces what the BROWSER does with `background-size: cover` and
`background-position: X% Y%`: the picture is scaled until it covers the box, and
the overflow is distributed by the position percentage. Getting this subtly
wrong makes pictures that look right alone and wrong on the page, which is the
worst failure mode because nothing errors — so `--selftest` checks the maths
against the one placement already recorded in placements.json.

Geometry is per SLOT, not per picture: measured once off the built page (see
GEOM below), then every candidate for that slot reuses it.

Encoding is mozjpeg via cjpeg at q82 progressive, matching the hero already on
the page. Never run `campaign-compress` on this output — it palettises PNGs and
made the hero 10 KB bigger.
"""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

def page_config(state_dir):
    """kit / slug / page for the page this state describes. Never hard-coded."""
    return json.load(open(os.path.join(state_dir, 'page.json')))


def load_state(state_dir):
    """A page's own geometry and slot table. The engine holds neither.

    Geometry is per SLOT, measured once off the built page, then every candidate
    for that slot reuses it — so this file is a page's property, not the tool's.
    """
    g = json.load(open(os.path.join(state_dir, 'geometry.json')))
    # keep every field an entry carries: a `mode: native` slot has `min` and no
    # target/anchor, and fit_one routes on `mode` — dropping it cover-crops it
    desktop = {}
    for k, v in g['desktop'].items():
        e = dict(v)
        for f in ('target', 'anchor'):
            if f in e:
                e[f] = tuple(e[f])
        e.setdefault('note', '')
        desktop[int(k)] = e
    mobile = {int(k): v for k, v in g['mobile'].items()}
    slots = json.load(open(os.path.join(state_dir, 'slots.json')))
    return desktop, mobile, slots


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                          '-show_entries', 'stream=width,height', '-of', 'csv=p=0', path],
                         capture_output=True, text=True).stdout.strip()
    w, h = out.split(',')[:2]
    return int(w), int(h)


def cover_crop(sw, sh, tw, th, ax, ay):
    """The source rect the browser would show. Returns (cw, ch, x, y)."""
    want = tw / th
    have = sw / sh
    if have > want:                       # source too wide — trim the sides
        cw, ch = round(sh * want), sh
        return cw, ch, round((sw - cw) * ax), 0
    cw, ch = sw, round(sw / want)         # source too tall — trim top/bottom
    return cw, ch, 0, round((sh - ch) * ay)


def luminance(path, rect):
    """Mean and peak luminance over a rect given as (x, y, w, h) fractions."""
    w, h = probe(path)
    x, y, rw, rh = int(rect[0] * w), int(rect[1] * h), int(rect[2] * w), int(rect[3] * h)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'crop={rw}:{rh}:{x}:{y}',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True).stdout
    tot = peak = 0
    n = len(raw) // 3
    for i in range(0, len(raw), 3):
        l = 0.299 * raw[i] + 0.587 * raw[i + 1] + 0.114 * raw[i + 2]
        tot += l
        peak = max(peak, l)
    return tot / n, peak


def fit_one(master, slot, repo, state_dir, dry=False, mobile=False):
    desktop_geom, mobile_geom, slots = load_state(state_dir)
    cfg = page_config(state_dir)
    g = (mobile_geom if mobile else desktop_geom).get(slot)
    if not g:
        tree = 'M' if mobile else 'D'
        return print(f'{tree}{slot}: not in geometry.json — measure it off the '
                     f'built page first') or False
    dest_name = slots[str(slot)][('mobile' if mobile else 'desktop')]

    if g.get('mode') == 'native':
        return _native(master, slot, g, repo, cfg, dest_name, dry, mobile)

    tw, th = g['target']; ax, ay = g['anchor']
    dest = os.path.join(repo, cfg['kit'], 'src', cfg['slug'], cfg['assets_subdir'], dest_name)

    sw, sh = probe(master)
    cw, ch, x, y = cover_crop(sw, sh, tw, th, ax, ay)
    scale = tw / cw
    # how the recorded placements express it: pixels lost in TARGET space
    lost_w = round(sw * (th / ch) - tw) if cw < sw else 0
    lost_h = round(sh * (tw / cw) - th) if ch < sh else 0

    print(f'#{slot:<3} {os.path.basename(master):<26} {sw}x{sh} -> {tw}x{th}')
    print(f'      crop {cw}x{ch} at +{x}+{y}   scale {scale*100:.1f}%'
          f'{"  UPSCALE" if scale > 1.001 else ""}'
          + (f'   ({lost_w or lost_h}px lost in target space)' if (lost_w or lost_h) else '   (no crop)'))
    if dry:
        return True

    # one stage file per call, so two fits at once never share a frame
    fd = tempfile.NamedTemporaryFile(suffix='.ppm', delete=False); tmp = fd.name; fd.close()
    try:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', master,
                            '-vf', f'crop={cw}:{ch}:{x}:{y},scale={tw}:{th}:flags=lanczos',
                            tmp], capture_output=True, text=True)
        if r.returncode:
            return print(f'      ffmpeg failed: {r.stderr.strip()[:200]}') or False
        r = subprocess.run(['cjpeg', '-quality', '82', '-progressive', '-outfile', dest, tmp],
                           capture_output=True, text=True)
        if r.returncode:
            return print(f'      cjpeg failed: {r.stderr.strip()[:200]}') or False
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    size = os.path.getsize(dest)
    print(f'      wrote {dest_name}  {size/1024:.0f} KB')
    return True


def _native(master, slot, g, repo, cfg, dest_name, dry, mobile):
    """Encode as generated. No crop, no scale — the slot sizes it in CSS."""
    sw, sh = probe(master)
    mw, mh = g['min']
    print(f'#{"M" if mobile else "D"}{slot:<2} {os.path.basename(master):<26} {sw}x{sh} -> as generated')
    short = sw < mw or sh < mh
    print(f'      native fit, no crop   needs at least {mw}x{mh}'
          + ('   TOO SMALL — will be upscaled by the browser' if short else '   ok'))
    if dry:
        return True
    dest = os.path.join(repo, cfg['kit'], 'src', cfg['slug'], cfg['assets_subdir'], dest_name)
    fd = tempfile.NamedTemporaryFile(suffix='.ppm', delete=False); tmp = fd.name; fd.close()
    try:
        if subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', master, tmp],
                          capture_output=True).returncode:
            return print('      ffmpeg failed') or False
        if subprocess.run(['cjpeg', '-quality', '82', '-progressive', '-outfile', dest, tmp],
                          capture_output=True).returncode:
            return print('      cjpeg failed') or False
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(f'      wrote {dest_name}  {os.path.getsize(dest)/1024:.0f} KB')
    return True


def selftest():
    """The hero already on the page is the only recorded placement; match it.

    placements.json: source 3120x1328 -> 2850x1410, "6.2% upscale, 463px of
    width cropped". That 463 is measured after scaling to the target height,
    which is the accounting the original used.
    """
    sw, sh, tw, th = 3120, 1328, 2850, 1410
    cw, ch, x, y = cover_crop(sw, sh, tw, th, 0.5, 0.89)
    upscale = (tw / cw - 1) * 100
    lost = round(sw * (th / ch) - tw)
    ok = abs(upscale - 6.2) < 0.15 and abs(lost - 463) < 2
    print(f'D1 replay: crop {cw}x{ch}+{x}+{y}, upscale {upscale:.1f}% (recorded 6.2%), '
          f'{lost}px lost in target space (recorded 463px)')
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--selftest' in a:
        sys.exit(selftest())

    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    dry = '--dry-run' in a and not a.remove('--dry-run')
    mobile = '--mobile' in a and not a.remove('--mobile')
    repo = opt('--repo'); batch = opt('--batch'); rng = opt('--slots'); one = opt('--slot')
    state = opt('--state')
    if not repo or not state:
        sys.exit(__doc__)

    if batch:
        lo, hi = (int(v) for v in rng.split('-'))
        files = sorted(f for f in os.listdir(batch) if re.search(r'\.(png|jpg|jpeg|webp)$', f, re.I))
        want = hi - lo + 1
        if len(files) != want:
            sys.exit(f'{len(files)} files in {batch} but slots {lo}-{hi} need {want} — '
                     f'name them in slot order, or place them one at a time')
        print(f'{len(files)} masters -> slots {lo}..{hi}\n')
        ok = all(fit_one(os.path.join(batch, f), lo + i, repo, state, dry=dry)
                 for i, f in enumerate(files))
        print('\nall placed' if ok else '\nSOME FAILED')
        sys.exit(0 if ok else 1)

    if one:
        sys.exit(0 if fit_one(a[0], int(one), repo, state, dry=dry, mobile=mobile) else 1)
    sys.exit(__doc__)
