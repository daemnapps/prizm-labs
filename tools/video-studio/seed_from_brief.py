"""Storyboard idea -> Video Studio brief (the owner, 2026-11-08: one video workflow tool).
Reads the writing run's stage-5 production brief and the board's owner edits, writes one scene workflow per scene:
the AI voice read of its line, then one generation step per shot (start picture, angle, move, action).
    python3 seed_from_brief.py <board idea key, e.g. brief7>
Never overwrites a take that exists; prints the canvas link."""
import json, os, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOM = Path(os.environ.get('VIDEO_STUDIO_BOARD_DATA') or HERE.parents[1] / 'runs' / 'storyboard')   # the storyboard board's data (matrix.json, owner-edits/)
WORK = HERE.parents[1] / 'runs' / 'video-teardown' / '_work'
STUDIO = os.environ.get('VIDEO_STUDIO_STUDIO') or 'http://127.0.0.1:8922'


def brief_json(run):
    b = (WORK / run / 'stages' / '5-brief.md').read_text()
    return json.loads(re.findall(r'```json\s*\n(.*?)\n```', b, re.S)[-1])


def frame_prompt(ff):
    return '. '.join(str(ff.get(k)) for k in ('subject', 'action', 'composition', 'location', 'lighting', 'camera', 'style') if ff.get(k))


def made_already(idea):
    """A canvas brief already made from this storyboard idea (brief.json "idea"), e.g. brief1 -> 0322."""
    for bp in sorted((HERE / 'briefs').glob('*/brief.json')):
        try:
            if json.loads(bp.read_text()).get('idea') == idea:
                return bp.parent.name
        except (OSError, ValueError):
            continue
    return None


def main(idea):
    have = made_already(idea)
    if have:                                     # the production exists: open it, never seed a second one
        order = json.loads((HERE / 'briefs' / have / 'brief.json').read_text()).get('order') or []
        print(json.dumps({'brief': have, 'scenes': len(order), 'url': STUDIO + '/?brief=' + have}))
        return
    m = re.fullmatch(r'brief(\d+)', idea)
    item = next(a for a in json.loads((ROOM / 'matrix.json').read_text())['ads'] if str(a['n']) == m[1])
    run = item['line']; doc = brief_json(run)
    edits = {}
    for f in (ROOM / 'owner-edits').glob(idea + '*.json'):
        try: edits.update(json.loads(f.read_text()).get('scene_edits') or {})
        except (OSError, ValueError): pass
    num = 'P%02d' % int(m[1])
    bd = HERE / 'briefs' / num; order = []
    for sc in doc['scenes']:
        sid = sc['id']; order.append(sid)
        d = bd / 'scenes' / sid; d.mkdir(parents=True, exist_ok=True); p = d / 'take-1.json'
        if p.exists(): continue
        ov = edits.get(sid) or {}
        words = ov.get('voice', sc.get('voice') or '')
        steps = []
        if words:
            steps.append({'id': 'voice', 'tool': 'voice.ai', 'model': None, 'prompt': words, 'seed': None, 'inputs': {},
                          'params': {'speaker': sc.get('speaker'), 'delivery': sc.get('delivery'), 'emotion': sc.get('emotion')},
                          'note': 'AI voice read of this line'})
        ff = sc.get('first_frame') or {}
        for i, sh in enumerate(sc.get('shots') or [{}]):
            start = frame_prompt(ff) if sh.get('start_picture', 'first_frame') == 'first_frame' else str(sh.get('start_picture'))
            steps.append({'id': 'shot-%d' % (i + 1), 'tool': 'gen.shot', 'model': None,
                          'prompt': ' | '.join(x for x in [start, sh.get('angle'), sh.get('camera_move'), sh.get('face'), ov.get('happens') or sc.get('happens')] if x),
                          'seed': None, 'inputs': {'refs': ff.get('refs') or []}, 'params': {'copies': sh.get('copies')},
                          'note': sh.get('id') or ''})
        json.dump({'schema': 'scene-workflow/v1', 'brief': run, 'scene': sid, 'take': 'take-1',
                   'title': (sc.get('section') or sid).replace('-', ' '), 'lane': 'ai',
                   'roll': {'greenscreen': 'G', 'card': 'C', 'endcard': 'E'}.get(sc.get('kind'), 'A'),
                   'clock': {'locked': False}, 'words': words, 'steps': steps, 'sources': {},
                   'from': 'storyboard ' + idea + ' · ai-workspace runs/video-teardown/_work/' + run + '/stages/5-brief.md'},
                  open(p, 'w'), indent=1, ensure_ascii=False)
    bp = bd / 'brief.json'
    if not bp.exists():
        json.dump({'schema': 'scene-canvas-brief/v1', 'brief': run, 'number': num, 'title': item['name'] + ' · from storyboard ' + idea,
                   'order': order, 'picks': {s: 'take-1' for s in order}, 'idea': idea,
                   'deliver': {'width': 1080, 'height': 1920, 'video': 'h264', 'audio': 'aac 48 kHz'}}, open(bp, 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({'brief': num, 'scenes': len(order), 'url': STUDIO + '/?brief=' + num}))


if __name__ == '__main__':
    main(sys.argv[1])
