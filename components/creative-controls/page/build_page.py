"""Build the Creative Controls page from a scores run.

    python3 components/creative-controls/page/build_page.py <brand> <label> <thumb-dir> [example asset id]

Reads runs/creative-controls/<brand>/<label>/scores.json, writes
runs/creative-controls/<brand>/<label>/creative-controls.html (published over
(private page)) and the team's Markdown
mirror. Thumbnails are cached in <thumb-dir>, a temp folder of the caller's.
"""
import base64, json, subprocess, sys, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CCD = HERE.parent
REPO = CCD.parents[1]
BRAND, LABEL = sys.argv[1], sys.argv[2]
T = Path(sys.argv[3]); T.mkdir(parents=True, exist_ok=True)
RUN = REPO / 'runs/creative-controls' / BRAND / LABEL
sys.path.insert(0, str(CCD))
import creative_controls as CC
C = CC.load()
GL = json.loads((CCD / 'glossary.json').read_text())['terms']
SC = json.loads((RUN / 'scores.json').read_text())


def _teardown_run(repo, run, brand=None):
    """A picture run's folder on the image-teardown plane: runs/image-teardown/<brand>/<run>/, its one home since
    2026-10-28 (components/naming/WHERE-EVERYTHING-GOES-owner.md item 4). The old lane folder
    tools/image-teardown/runs/<run>/ is read for one release, for a checkout that has not moved its runs."""
    root = Path(repo) / "runs" / "image-teardown"
    run = Path(str(run)).name
    hits = ([root / str(brand).lower() / run] if brand else []) + sorted(root.glob(f"*/{run}"))
    work = [d for d in hits if (d / "out").is_dir() or (d / "vars").is_dir()]
    old = Path(repo) / "tools" / "image-teardown" / "runs" / run
    if work:
        return work[0]
    if old.is_dir():
        return old
    return next((d for d in hits if d.is_dir()), hits[0] if hits else root / "_unfiled" / run)


def thumb(p, i):
    o = T / (re.sub(r'[^\w-]', '_', i) + '.jpg')
    if not o.exists():
        subprocess.run(['sips', '-Z', '320', '-s', 'format', 'jpeg', '-s', 'formatOptions', '62', str(p), '--out', str(o)], capture_output=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(o.read_bytes()).decode() if o.exists() else ''


assets = []
for i, v in SC.items():
    r = v.get('read')
    if not r or v.get('problems'):
        continue
    a = v['asset']
    assets.append({'id': i, 'group': a['group'], 'note': a.get('note', ''), 'img': thumb(a['path'], i),
                   'lv': {k: x['level'] for k, x in r['dials'].items()},
                   'why': {k: x['why'] for k, x in r['dials'].items()},
                   'emo': r.get('emotion') or {}, 'tech': r.get('techniques') or [],
                   'standout': r.get('standout') or '', 'swap': r.get('swap') or '', 'notes': r.get('notes') or ''})

# the worked example: a swipe he picked, the one the chain has to turn up the most
_, target = CC.target('maxed', BRAND, 'image')
picked = [a for a in assets if a['group'] == 'swipe-picked']
EXAMPLE = sys.argv[4] if len(sys.argv) > 4 else None   # the asset id to walk through the chain
ex = next((a for a in picked if a['id'] == EXAMPLE), None) or (max(picked, key=lambda a: a['lv']['stopping_power']) if picked else None)
if ex:
    inj = _teardown_run(REPO, BRAND + '-batch-pick-' + ex['id'][len('picked-'):], BRAND) / 'out/03-injection.md'
    m = re.search(r'\*\*SWAPS:\*\*\s*(.+)', inj.read_text()) if inj.exists() else None
    ex['swapline'] = m.group(1).strip() if m else ''
    w = re.search(r'\*\*WHY IT STILL READS:\*\*\s*(.+)', inj.read_text()) if inj.exists() else None
    ex['readsline'] = w.group(1).strip() if w else ''

say = [
 {'say': 'Make this (in the Swipe Bank)', 'does': 'The next time you message this work, the swipe is opened, read on every dial, and briefed at Maxed: our objects swapped in by rhyme, every dial at or above the swipe.', 'shows': 'the BRAND-A Image Queue board, under its awareness level'},
 {'say': 'Run brief 229 at native', 'does': 'The brand step and the brief run again on the Native preset: no offer, no call to action, the post look, everything else maxed. Also: "at problem aware", "at proof".', 'shows': 'the same card on the board, new brief'},
 {'say': 'Absurdity down to 2 on 229', 'does': 'One dial changed for that brief, everything else kept. Any dial by its name: "edge up", "more rhyme", "less words on it" (anchorage).', 'shows': 'the same card on the board, new brief'},
 {'say': 'Move the sliders here, press Save', 'does': 'Those levels become the preset for every brief from the next run. They are picked up the next time you message this work.', 'shows': 'this page keeps them; every new brief carries them'},
 {'say': 'Score these (with links or pictures)', 'does': 'The reader scores each one on every dial and adds it to this page, so you can see where it sits against what we make.', 'shows': 'Every asset, the gap, and the slider matches'},
 {'say': 'Add a dial for …  /  add the name …', 'does': 'It goes into the creative-controls home once, and every chain that reads it (pictures now; video and copy next) gets it on its next run.', 'shows': 'this page, Each dial and The real names'},
]

data = {'dials': [{'id': d['id'], 'name': d['name'], 'aka': d['aka'], 'what': d['what'], 'scale': d['scale'],
                   'copy': d['copy'], 'video': d['video'], 'image': d['image'], 'media': d['media'],
                   'default': d['default'], 'risk': d['risk']} for d in C['dials']],
        'presets': C['presets'], 'emotions': C['emotions'], 'techniques': C['techniques'], 'guards': C['guards'],
        'assets': assets, 'gloss': GL, 'example': ex, 'target': target, 'say': say}
page = (HERE / 'template.html').read_text().replace('/*DATA*/null', json.dumps(data, ensure_ascii=False))
(RUN / 'creative-controls.html').write_text(page)
print(len(assets), 'assets', round(len(page) / 1e6, 2), 'MB', 'example', ex and ex['id'])

# the team's Markdown mirror
G = {'ours-approved': 'Our ads the owner kept', 'ours-pulled': 'Our ads the owner pulled', 'swipe-picked': 'Swipes the owner picked',
     'swipe-organic': 'Popular organic posts', 'swipe-competitor': 'Competitor statics'}
pic = [d for d in C['dials'] if 'image' in d['media']]
md = ['# Creative controls (the owner)', '',
      'Page: (private page) · home: `components/creative-controls/` '
      '(dials `controls.json`, names `glossary.json`, rendered `slices/controls.md` and `GLOSSARY.md`, reader `read.py`)', '',
      'One set of dials for copy, video and pictures. A reader measures the level an asset is at; a chain sets the level it should be at. '
      'Default stance: absurd, maxed out, hyper-specific, native at the top of the funnel.', '',
      '## How it runs', '',
      '1. A swipe comes in (picked in the Swipe Bank, or a link).',
      '2. The reader scores it on every dial, with the reason for each level.',
      '3. The image chain\'s brand step (stage 3 v4) sets ours: the preset\'s level (Maxed unless the order says otherwise), never below the swipe, one line per dial naming what in the picture puts it there.',
      '4. The brief (stage 6 v9) turns each dial into a picture direction and ends section 3 with a Dials line the picture check holds the draft to.', '',
      '## How to start it', ''] + ['- **%s**: %s' % (s['say'], s['does']) for s in say] + ['',
      '## The gap (average level, by where the picture came from)', '',
      '| Where it came from | n | ' + ' | '.join(d['name'] for d in pic) + ' |', '|---|---|' + '---|' * len(pic)]
for g, label in G.items():
    xs = [a for a in assets if a['group'] == g]
    if xs:
        md.append('| %s | %d | ' % (label, len(xs)) + ' | '.join(
            ('%.1f' % (sum(a['lv'][d['id']] for a in xs if d['id'] in a['lv']) / max(1, sum(1 for a in xs if d['id'] in a['lv']))))
            for d in pic) + ' |')
md += ['', '## The dials', '', '| Dial | Also called | Scale, low to high | Default | Medium |', '|---|---|---|---|---|']
md += ['| %s | %s | %s | %s | %s |' % (d['name'], ', '.join(d['aka']), ' · '.join('%s %s' % (s['level'], s['name']) for s in d['scale']),
                                       d['default']['level'], ', '.join(d['media'])) for d in C['dials']]
md += ['', '## Guards (always on)', ''] + ['- **%s**: %s' % (g['name'], g['what']) for g in C['guards']]
md += ['', '## Presets', ''] + ['- **%s** (%s): %s ' % (p['name'], p['id'], p['what']) + ', '.join('%s %s' % kv for kv in p['levels'].items()) for p in C['presets']]
md += ['', 'The full glossary (%d real names) is `components/creative-controls/GLOSSARY.md`.' % len(GL)]
(REPO / 'tools/image-teardown/context/CREATIVE-CONTROLS-owner.md').write_text('\n'.join(md) + '\n')
print('mirror written')
