"""Storyboard idea -> Video Studio brief (the owner, 2026-11-08: one video workflow tool).
Reads the writing run's stage-5 production brief and the board's owner edits, writes one scene workflow per scene:
the AI voice read of its line, then one generation step per shot (start picture, angle, move, action).
    python3 seed_from_brief.py <board idea key, e.g. brief7>
Never overwrites a take that exists; prints the canvas link."""
import json, os, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402
BRIEFS = ST.BRIEFS
ROOM = Path(os.environ.get('VIDEO_STUDIO_BOARD_DATA') or HERE.parents[1] / 'runs' / 'storyboard')   # the storyboard board's data (matrix.json, owner-edits/)
WORK = ST.WORK if hasattr(ST, 'WORK') else ST.WRITING
STUDIO = os.environ.get('VIDEO_STUDIO_STUDIO') or 'http://127.0.0.1:8922'


def brief_json(run):
    """The run's production brief, its scenes folded into sequences first: one moment is one scene, its shots in
    order (BRIEF-SPEC "Scenes and shots"; components/video-writing/machine/scene_shots.py)."""
    b = (WORK / run / 'stages' / '5-brief.md').read_text()
    return json.loads(re.findall(r'```json\s*\n(.*?)\n```', b, re.S)[-1])


def with_edits(doc, edits):
    """The owner's board edits laid on each scene as the board shows it, then the scenes folded into sequences, so
    an edit made on one line of a back-and-forth stays on that line."""
    for sc in doc.get('scenes') or []:
        ov = edits.get(sc.get('id')) or {}
        if ov.get('voice'):
            sc['voice'] = ov['voice']
            shots = sc.get('shots') or []
            if len(shots) == 1:
                shots[0]['lines'] = [{'say': ov['voice'], 'speaker': sc.get('speaker')}]
        if ov.get('happens'):
            sc['happens'] = ov['happens']
    sys.path.insert(0, str(ST.part('video-writing') / 'machine'))
    try:
        import scene_shots as SS
        doc['scenes'] = SS.fold(doc.get('scenes') or [])
    except ImportError:
        pass
    return doc


def frame_prompt(ff):
    return '. '.join(str(ff.get(k)) for k in ('subject', 'action', 'composition', 'location', 'lighting', 'camera', 'style') if ff.get(k))


def made_already(idea):
    """A canvas brief already made from this storyboard idea (brief.json "idea"), e.g. brief1 -> 0322."""
    for bp in sorted(BRIEFS.glob('*/brief.json')):
        try:
            if json.loads(bp.read_text()).get('idea') == idea:
                return bp.parent.name
        except (OSError, ValueError):
            continue
    return None


def main(idea):
    have = made_already(idea)
    if have:                                     # the production exists: open it, never seed a second one
        order = json.loads((BRIEFS / have / 'brief.json').read_text()).get('order') or []
        print(json.dumps({'brief': have, 'scenes': len(order), 'url': STUDIO + '/?brief=' + have}))
        return
    m = re.fullmatch(r'brief(\d+)', idea)
    item = next(a for a in json.loads((ROOM / 'matrix.json').read_text())['ads'] if str(a['n']) == m[1])
    run = item['line']; doc = brief_json(run)
    edits = {}
    for f in (ROOM / 'owner-edits').glob(idea + '*.json'):
        try: edits.update(json.loads(f.read_text()).get('scene_edits') or {})
        except (OSError, ValueError): pass
    doc = with_edits(doc, edits)
    edits = {}                                   # laid on above, before the fold
    num = 'P%02d' % int(m[1])
    bd = BRIEFS / num; order = []
    for sc in doc['scenes']:
        sid = sc['id']; order.append(sid)
        d = bd / 'scenes' / sid; d.mkdir(parents=True, exist_ok=True); p = d / 'take-1.json'
        if p.exists(): continue
        ov = edits.get(sid) or {}
        words = ov.get('voice', sc.get('voice') or '')
        steps = []
        # one read per line, each in its speaker's voice, laid down in the scene's order (a scene may hold several speakers)
        script = sc.get('script') or ([{'speaker': sc.get('speaker'), 'say': words}] if words else [])
        if ov.get('voice'):
            script = [{'speaker': sc.get('speaker'), 'say': ov['voice']}]
        for k, ln in enumerate(script, 1):
            steps.append({'id': 'voice' if len(script) == 1 else 'voice-%d' % k, 'tool': 'voice.ai', 'model': None,
                          'prompt': ln.get('say'), 'seed': None, 'inputs': {},
                          'params': {'speaker': ln.get('speaker'), 'delivery': sc.get('delivery'), 'emotion': sc.get('emotion'), 'order': k},
                          'note': 'AI voice read of %s line %d' % (ln.get('speaker') or 'the', k)})
        ff = sc.get('first_frame') or {}
        shots = sc.get('shots') or [{}]
        if sc.get('take') == 'continuous':      # the swipe holds one take: ONE clip carries every line (BRIEF-SPEC 6-8; take.py)
            steps.append({'id': 'take', 'tool': 'gen.take', 'model': None, 'prompt': frame_prompt(ff), 'seed': None,
                          'inputs': {'refs': ff.get('refs') or []},
                          'params': {'script': [{'speaker': ln.get('speaker'), 'say': ln.get('say')} for ln in script],
                                     'staging': ov.get('happens') or sc.get('happens'), 'motion': sc.get('motion'),
                                     'beats': [{'shot': sh.get('id'), 'face': sh.get('face'), 'do': sh.get('action') or (sh.get('gestures') or [None])[0]}
                                               for sh in shots]},
                          'note': 'one continuous take: start picture from the swipe frame, a voice sample per speaker, the swipe seconds as motion'})
            shots = []
        for i, sh in enumerate(shots):
            start = frame_prompt(ff) if sh.get('start_picture', 'first_frame') == 'first_frame' else str(sh.get('start_picture'))
            params = {'copies': sh.get('copies'), 'lines': sh.get('lines') or [], 'speaker': sh.get('speaker')}
            if i > 0:                    # a scene is a sequence: the same people in the same place as its first shot
                params['scene_master'] = 'shot-1'
                if sh.get('hands_off') == 'continuous' or shots[i - 1].get('hands_off') == 'continuous':
                    params['continue_from'] = 'shot-%d' % i
            steps.append({'id': 'shot-%d' % (i + 1), 'tool': 'gen.shot', 'model': None,
                          'prompt': ' | '.join(x for x in [start, sh.get('angle'), sh.get('camera_move'), sh.get('face'), ov.get('happens') or sc.get('happens')] if x),
                          'seed': None, 'inputs': {'refs': ff.get('refs') or []}, 'params': params,
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
