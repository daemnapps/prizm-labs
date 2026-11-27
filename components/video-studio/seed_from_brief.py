"""Storyboard idea -> Video Studio brief (the owner, 2026-11-08: one video workflow tool).
Reads the writing run's stage-5 production brief and the board's owner edits, writes one scene workflow per scene:
the AI voice read of its line, then one generation step per shot (start picture, angle, move, action).
    python3 seed_from_brief.py <board idea key, e.g. idea-7>
Never overwrites a take that exists; prints the canvas link."""
import json, os, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402
import script_lines as SL  # noqa: E402
BRIEFS = ST.BRIEFS
ROOM = Path(os.environ.get('VIDEO_STUDIO_BOARD_DATA') or HERE.parents[1] / 'runs' / 'storyboard')   # the storyboard board's data (matrix.json, owner-edits/)
WORK = ST.WORK if hasattr(ST, 'WORK') else ST.WRITING
STUDIO = os.environ.get('VIDEO_STUDIO_STUDIO') or 'http://127.0.0.1:8922'


def run_style(run):
    """The writing run's style as the production brief carries it: {id, from}; id None = photoreal."""
    import importlib.util
    f = ST.part('video-production') / 'styles' / 'style_chain.py'
    if not f.is_file():
        return {'id': None, 'from': 'style chain not installed'}
    sp = importlib.util.spec_from_file_location('seed_style_chain', f)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    st = m.run_style(run, WORK)
    return dict(st, rule="the ad is made in the swipe's style; every element is pulled or made in it")


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
        if ov.get('voice'):             # one script: "NAME: line" per spoken line (script_lines.py)
            rows = SL.lines(ov['voice'], sc.get('script') or [], sc.get('speaker') or '')
            sc['voice'] = ' '.join(r['say'] for r in rows)
            if sc.get('script') or len(rows) > 1:
                sc['script'] = rows
            shots = sc.get('shots') or []
            if len(shots) == 1:
                shots[0]['lines'] = [{'say': r['say'], 'speaker': r['speaker'] or sc.get('speaker')} for r in rows]
        if ov.get('happens'):
            sc['happens'] = ov['happens']
    sys.path.insert(0, str(ST.part('video-writing') / 'machine'))
    try:
        import scene_shots as SS
        # the storyboard's own join (scenes with the same section tag, 2026-11-16) is the production's scene list;
        # a brief joined at writing is unchanged by it, so production gets exactly the scenes the storyboard shows
        doc['scenes'] = (SS.join_sections if hasattr(SS, 'join_sections') else SS.fold)(doc.get('scenes') or [])
    except ImportError:
        pass
    return doc


def k_ids(source):
    """Every swipe shot a source names: "K05-K10, K42" -> [K05 … K10, K42]."""
    out = []
    for a, b in re.findall(r'K(\d{2,3})(?:\s*[–-]\s*K(\d{2,3}))?', str(source or '')):
        out += ['K%02d' % i for i in range(int(a), int(b or a) + 1)]
    return out


def picture_of(ks, pics):
    """One picture type for a run of swipe shots (BRIEF-SPEC rule 9): talking if anyone speaks on screen in it, else a
    mimed line, else the voice over the picture (lips off)."""
    kinds = [pics[k]['picture'] for k in ks if k in pics]
    for kind in ('talking', 'mime'):
        if kind in kinds:
            return kind, next(pics[k] for k in ks if k in pics and pics[k]['picture'] == kind)
    return (max(set(kinds), key=kinds.count), None) if kinds else (None, None)


def lips_of(kind, default='on'):
    """on, mime or off for a picture type; a line with no swipe shot behind it follows the ad's own mode (`default`)."""
    return {'talking': 'on', 'mime': 'mime'}.get(kind, 'off' if kind else default)


def ad_mode(pics):
    """How this ad uses the voice: 'on' when people speak on screen in at least a fifth of the voiced shots, else 'off'
    (a narrated ad: the voice runs over the picture)."""
    voiced = [p['picture'] for p in pics.values() if p['picture'] != 'silent']
    return 'on' if not voiced or voiced.count('talking') / len(voiced) >= 0.2 else 'off'


def subject_words(subjects):
    """A shot's subjects as the brief defines them (storyboard, 2026-11-16), in words a model reads: who each person
    is and wears, the product line written for the shot, the place and its light, each prop with its size and look."""
    s = subjects or {}
    parts = []
    for p in s.get('people') or []:
        parts.append('%s: %s%s' % (p.get('id'), p.get('is') or '', ('; wearing ' + p['look']) if p.get('look') else ''))
    pr = s.get('product')
    if isinstance(pr, dict):                 # the product from the bank (2026-11-16): one product, the same in every shot
        bits = [pr.get('name') or pr.get('id'), pr.get('what'), ('real size ' + pr['size_reads']) if isinstance(pr.get('size_reads'), str) else '']
        parts.append('product: ' + ', '.join(b for b in bits if b) + ''.join('; in this shot: ' + str(x) for x in pr.get('in_shot') or []))
    else:
        for ln in pr or []:
            parts.append('product: ' + str(ln))
    if s.get('place'):
        pl = s['place']
        parts.append('place %s: %s%s' % (pl.get('id'), pl.get('is') or '', ('; ' + pl['light']) if pl.get('light') else ''))
    for x in s.get('props') or []:
        parts.append('prop %s: %s' % (x.get('name'), '; '.join(v for v in (x.get('size'), x.get('look')) if v)))
    return ('Subjects: ' + ' · '.join(parts)) if parts else ''


def scene_subjects(shots):
    """Every subject the scene's shots name, once each: people and props by name, the product lines in shot order."""
    out = {'people': [], 'product': [], 'place': [], 'props': []}
    seen = set()
    for sh in shots:
        s = sh.get('subjects') or {}
        for k, key in (('people', 'id'), ('props', 'name')):
            for x in s.get(k) or []:
                if (k, x.get(key)) not in seen:
                    seen.add((k, x.get(key))); out[k].append(x)
        pr = s.get('product')
        if isinstance(pr, dict):
            have = next((x for x in out['product'] if isinstance(x, dict) and x.get('id') == pr.get('id')), None)
            if have is None:
                out['product'].append(dict(pr, in_shot=list(pr.get('in_shot') or [])))
            else:
                have['in_shot'] += [x for x in pr.get('in_shot') or [] if x not in have['in_shot']]
        else:
            for ln in pr or []:
                if ln not in out['product']:
                    out['product'].append(ln)
        if s.get('place') and ('place', s['place'].get('id')) not in seen:
            seen.add(('place', s['place'].get('id'))); out['place'].append(s['place'])
    return {k: v for k, v in out.items() if v}


def frame_prompt(ff):
    return '. '.join(str(ff.get(k)) for k in ('subject', 'action', 'composition', 'location', 'lighting', 'camera', 'style') if ff.get(k))


def made_already(idea):
    """A canvas brief already made from this storyboard idea (brief.json "idea"), e.g. idea-1 -> 0322. A folder kept
    under its old name as a link (P02 -> idea-2) is not a second production."""
    for bp in sorted(BRIEFS.glob('*/brief.json')):
        if bp.parent.is_symlink():
            continue
        try:
            if json.loads(bp.read_text()).get('idea') == idea:
                return bp.parent.name
        except (OSError, ValueError):
            continue
    return None


def cast_picks(doc, picked):
    """The cast picked at Produce (owner, 16 Nov 2026): {role: cast bank id, or "new"}, kept to the brief's own roles."""
    roles = [c.get('id') for c in doc.get('cast') or [] if isinstance(c, dict) and c.get('id')]
    out = {}
    for role in roles:
        v = (picked or {}).get(role)
        if isinstance(v, str) and (v == 'new' or re.fullmatch(r'[a-z0-9-]+', v)):
            out[role] = v
    return out


def footage_cut(sh, lane):
    """The clip of ours a shot is cut from in this lane, or None (generate). `mix`: the chain's own cut (the footage pass
    passed it); `real`: our closest clip, passed or not; `ai`: never."""
    f = sh.get('footage') or {}
    if lane == 'mix':
        return f.get('clip') if f.get('plan') == 'cut' else None
    if lane == 'real':
        return f.get('clip') or f.get('nearest')
    return None


def drive_root():
    """The folder that holds the Shared Assets drive on this machine, found and never named (builder card rules 3-4):
    VIDEO_STUDIO_DRIVE when set, else brandpath's own finder (the first Drive account that has Shared Assets)."""
    if os.environ.get('VIDEO_STUDIO_DRIVE'):
        return Path(os.environ['VIDEO_STUDIO_DRIVE']).parent
    try:
        import importlib.util as iu
        sp = iu.spec_from_file_location('seed_drive_index', str(ST.part('brandpath') / 'drive_index.py'))
        di = iu.module_from_spec(sp); sp.loader.exec_module(di)
        m = di.mount()
        return m.parent if m else None
    except Exception:  # noqa: BLE001 -- no Drive here: the footage step says so itself
        return None


def library_settings(doc, brand):
    """The ad's footage settings, set by the chain (owner, 16 Nov: "this should be the chain, not me"): the brand, whose
    hands may play a shot (the one demographic band the storyboard's footage pass chose, from our creators' folders), the
    product as the bank names it and how footage shows it, and the library on this machine."""
    band = (doc.get('footage_band') or {}).get('band')
    prod = next(((sh.get('subjects') or {}).get('product') for sc in doc.get('scenes') or [] for sh in sc.get('shots') or []
                 if isinstance(sh, dict) and isinstance((sh.get('subjects') or {}).get('product'), dict)), None) or {}
    root = drive_root()
    out = {'brand': brand, 'bar': 0.4, 'library_roots': [str(root)] if root else [],
           'why': 'Set by the chain at production set-up: the demographic band from the storyboard footage pass, the product from the product bank.'}
    if band:
        out['hands_like'] = ['/' + band.strip('/') + '/']
    if prod.get('name'):
        out['product'] = prod['name']
    if prod.get('what'):
        out['product_seen'] = prod['what']
    return out


def _lane_mod():
    """The chain's lane rule (components/video-production/machine/lane.py): the workspace the writing runs live in
    first, else the one this Studio sits in (a test's own writing folder)."""
    import importlib.util
    f = next((x for x in (ST.part('video-production', Path(WORK).resolve().parents[2]) / 'machine' / 'lane.py',
                          ST.part('video-production') / 'machine' / 'lane.py') if x.is_file()))
    sp = importlib.util.spec_from_file_location('seed_chain_lane', str(f))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def lane_call(run, lane=None, why=None, by=None):
    """How this production is made: {lane, why, by}. A lane handed in (picked at Produce, or the chain's call the Studio
    already asked for) is kept with its reason; none handed in = the chain's own call for this brief
    (components/video-production/machine/lane.py). Never an assumed lane (the logic layer, 2026-11-18)."""
    m = _lane_mod()
    if lane in m.lanes() and why:
        return {'lane': lane, 'why': why, 'by': by or m.PICKED}
    got = m.chosen(lane, WORK / run)
    return {k: got[k] for k in ('lane', 'why', 'by')}


def trail_rows(decision, choice, why, by):
    """A production's first rows on the decision trail (run-kit `trail.add`, kept as `trail` on the production's own
    brief.json, the same shape every stage writes). A workspace without the module keeps the same row."""
    st = {}
    try:
        rk = str(ST.part('run-kit', Path(WORK).resolve().parents[2]))
        if rk not in sys.path:
            sys.path.append(rk)
        from run_kit import trail
        trail.add(st, 'production', decision, choice, why, by)
    except Exception:  # noqa: BLE001 -- a note never stops a production being set up
        import datetime
        st = {'trail': [{'at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
                         'stage': 'production', 'decision': decision, 'choice': choice, 'why': why, 'by': by}]}
    return st.get('trail') or []


def waiting_real(p, lane):
    """A take seeded in the Real lane that still waits on footage (a footage.find step), while the ad's lane is now one
    that makes those shots (AI or AI + Real): Produce again sets it up the new lane's way (owner, 16 Nov 2026: a lane
    picked at Produce must carry through without a hand step). Takes already cut or made are never touched."""
    if lane == 'real' or not p.exists():
        return False
    try:
        return any(st.get('tool') == 'footage.find' for st in json.loads(p.read_text()).get('steps') or [])
    except (OSError, ValueError):
        return False


def main(idea, picked=None, lane=None, lane_why=None, lane_by=None):
    idea = re.sub(r'^brief(\d+)$', r'idea-\1', idea)
    have = made_already(idea)
    if have:                                     # the production exists: open it, never seed a second one
        hb = json.loads((BRIEFS / have / 'brief.json').read_text())
        order = hb.get('order') or []
        if lane not in ('ai', 'mix', 'real'):    # none picked: a missing scene is seeded in the production's own lane
            own = _lane_mod().of(hb)
            lane, lane_why, lane_by = own['lane'], own['why'], own['by']
        cur = lane
        missing = [s for s in order if not (BRIEFS / have / 'scenes' / s / ((hb.get('picks') or {}).get(s, 'take-1') + '.json')).exists()
                   or waiting_real(BRIEFS / have / 'scenes' / s / ((hb.get('picks') or {}).get(s, 'take-1') + '.json'), cur)]
        if not missing or have != re.sub(r'^brief(\d+)$', r'idea-\1', idea):
            print(json.dumps({'brief': have, 'scenes': len(order), 'url': STUDIO + '/?brief=' + have}))
            return
        # ...except a scene it is missing (set aside, or new on the storyboard): seeded below, the rest untouched
    m = re.fullmatch(r'(?:idea-|brief)(\d+)', idea)
    idea = 'idea-' + m[1]                        # an idea's key (Video Names, 9 Nov); the old briefN still works
    item = next(a for a in json.loads((ROOM / 'matrix.json').read_text())['ads'] if str(a['n']) == m[1])
    run = item['line']; doc = brief_json(run)
    made = lane_call(run, lane, lane_why, lane_by)
    if made['lane'] not in ('ai', 'mix', 'real'):            # a creator piece is never seeded here: said, not hidden
        made = {'lane': 'ai', 'by': made['by'],
                'why': 'a production was asked for here although ' + made['why'] + '; every shot is made'}
    lane = made['lane']
    brand = json.loads((WORK / run / 'run.json').read_text()).get('brand')
    edits = {}
    for f in (ROOM / 'owner-edits').glob(idea + '*.json'):
        try: edits.update(json.loads(f.read_text()).get('scene_edits') or {})
        except (OSError, ValueError): pass
    doc = with_edits(doc, edits)
    edits = {}                                   # laid on above, before the fold
    picks = cast_picks(doc, picked)
    sys.path.insert(0, str(HERE))
    import lips as LP
    pics = LP.labels(WORK / run)                 # every swipe shot's picture type, measured (BRIEF-SPEC rule 9)
    mode = ad_mode(pics)
    num = 'idea-%d' % int(m[1])                 # an idea's production folder until its brief number is given
    bd = BRIEFS / num; order = []
    try:                                         # the dial levels the writing aimed for, read off its own prompt
        import take_sheet as TS
        controls = TS.controls_target(WORK / run, json.loads((WORK / run / 'run.json').read_text()).get('brand'))
    except Exception:  # noqa: BLE001 -- a production with no target carries none; production never invents one
        controls = None
    for sc in doc['scenes']:
        sid = sc['id']; order.append(sid)
        d = bd / 'scenes' / sid; d.mkdir(parents=True, exist_ok=True); p = d / 'take-1.json'
        if p.exists() and not waiting_real(p, lane): continue
        if p.exists():                           # a Real-lane take still waiting on footage, now in a lane that makes it
            p.replace(d / 'take-1.real-lane.json')   # kept beside the new take, never deleted
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
        shots = sc.get('shots') or [{'footage': sc['footage']} if sc.get('footage') else {}]   # a shotless scene (end card): its own footage
        scene_ks = list(dict.fromkeys(k_ids(sc.get('source')) + [k for x in shots for k in k_ids(x.get('copies'))]))
        scene_kind, _ = picture_of(scene_ks, pics)
        line_lips = []                          # each line: on (spoken on screen), mime, or off (voice over the picture)
        for ln in script:
            sh = next((x for x in shots if any((l.get('say') or '') and (l.get('say') or '')[:40] in (ln.get('say') or '')
                                               for l in x.get('lines') or [])), None)
            kind, row = picture_of(k_ids(sh.get('copies')) if sh else k_ids(sc.get('source')), pics)
            line_lips.append((lips_of(kind, mode), (row or {}).get('who', [''])[0].split(' (')[0].title() if kind == 'mime' else None))
        cuts = [footage_cut(x, lane) for x in shots]
        if lane in ('mix', 'real') and any(cuts):   # a shot cut from our footage is never folded into a generated take
            sc = dict(sc, take=None)
        if sc.get('take') == 'continuous':      # the swipe holds one take: ONE clip carries every line (BRIEF-SPEC 6-8; take.py)
            steps.append({'id': 'take', 'tool': 'gen.take', 'model': None, 'prompt': frame_prompt(ff), 'seed': None,
                          'inputs': {'refs': ff.get('refs') or []},
                          'params': {'script': [dict({'speaker': ln.get('speaker'), 'say': ln.get('say'), 'lips': lp[0]},
                                                     **({'mouthed_by': lp[1]} if lp[1] else {}))
                                                for ln, lp in zip(script, line_lips)],
                                     'staging': ov.get('happens') or sc.get('happens'), 'motion': sc.get('motion'),
                                     # the writing's creative dials, carried as set (production adds none): the target
                                     # the writing aimed for, and this scene's delivery, emotion and doctrine
                                     **({'controls': controls} if controls else {}),
                                     **{k: sc[k] for k in ('delivery', 'emotion') if sc.get(k)},
                                     **({'doctrine': sc['doctrine']} if isinstance(sc.get('doctrine'), dict) else {}),
                                     'subjects': scene_subjects(sc.get('shots') or []),
                                     # the brief's beats, field by field (2026-11-15): who, action, prop, target, where
                                     # are carried apart into the take (take.py builds its words from them, take_beats
                                     # reads the made take against them); a brief without beats falls back to its shots
                                     'beats': [{'shot': b.get('shot'), 'who': b.get('who') or sc.get('who') or '',
                                                'action': b.get('do') or '', 'prop': b.get('prop') or '',
                                                'target': b.get('target') or '',
                                                'where': b.get('where') or b.get('setting_id') or sc.get('setting_id') or '',
                                                'camera': b.get('camera') if b.get('camera') not in (None, '', 'held') else '',
                                                'over': b.get('over') or ''}
                                               for b in sc.get('beats') or []] or
                                              [{'shot': sh.get('id'), 'face': sh.get('face'), 'do': sh.get('action') or (sh.get('gestures') or [None])[0]}
                                               for sh in shots]},
                          'note': 'one continuous take: start picture from the swipe frame, a voice sample per speaker, the swipe seconds as motion'})
            shots = []
        sources = {}
        for i, sh in enumerate(shots):
            cut = footage_cut(sh, lane)
            if cut and cut.get('shared_path'):     # our own footage: the clip, at its times (the Studio cuts it like any clip)
                sid_ = 'shot-%d' % (i + 1)
                sources[sid_] = {'file': os.path.basename(cut['shared_path']), 'drive_location': cut['shared_path'],
                                 'clip_id': cut.get('clip_id'), 'creator': cut.get('creator')}
                # the shot plays its action and no more (owner, 16 Nov: clean edits, clear usage, no awkward pauses): the
                # chain's shot_timing rule, at most 2.5 s (the end card 3 s), from the busiest unbroken stretch near where
                # the chain matched it
                import swipe_cut as SWC
                c_in, c_out = float(cut.get('in') or 0), float(cut.get('out') or 0)
                need = SWC.TIMING.shot_seconds(c_out - c_in, sc.get('kind'))
                at = SWC.busiest_in(brand, cut['shared_path'], c_in, need, before=0.0, after=max(0.0, c_out - c_in - need) + 1.0)
                c_in = at if at is not None else c_in
                steps.append({'id': sid_, 'tool': 'ffmpeg.trim', 'model': None, 'prompt': None, 'seed': None,
                              'inputs': {'source': 'slot:' + sid_, 'in': c_in, 'out': round(c_in + need, 3)},
                              'params': {'copies': sh.get('copies'), 'lines': sh.get('lines') or []},
                              'note': '%s · our footage: %s %s–%s s' % (sh.get('id') or '', cut.get('creator') or 'brand footage', cut.get('in'), cut.get('out'))})
                continue
            if lane == 'real':                     # 100% real: a shot with no clip of ours waits for footage, never generated
                steps.append({'id': 'shot-%d' % (i + 1), 'tool': 'footage.find', 'model': None, 'prompt': (ov.get('happens') or sc.get('happens') or ''),
                              'seed': None, 'inputs': {}, 'params': {'copies': sh.get('copies')},
                              'note': (sh.get('id') or '') + ' · no clip of ours yet: find or film it'})
                continue
            start = frame_prompt(ff) if sh.get('start_picture', 'first_frame') == 'first_frame' else str(sh.get('start_picture'))
            kind, _ = picture_of(k_ids(sh.get('copies')), pics)
            params = {'copies': sh.get('copies'), 'lines': sh.get('lines') or [], 'speaker': sh.get('speaker'),
                      'picture': kind, 'lips': lips_of(kind, 'off' if sc.get('kind') in ('card', 'endcard', 'screen') else mode)}
            if i > 0:                    # a scene is a sequence: the same people in the same place as its first shot
                params['scene_master'] = 'shot-1'
                if sh.get('hands_off') == 'continuous' or shots[i - 1].get('hands_off') == 'continuous':
                    params['continue_from'] = 'shot-%d' % i
            steps.append({'id': 'shot-%d' % (i + 1), 'tool': 'gen.shot', 'model': None,
                          'prompt': ' | '.join(x for x in [start, sh.get('angle'), sh.get('camera_move'), sh.get('face'), ov.get('happens') or sc.get('happens'), subject_words(sh.get('subjects'))] if x),
                          'seed': None, 'inputs': {'refs': ff.get('refs') or []}, 'params': params,
                          'note': sh.get('id') or ''})
        json.dump({'schema': 'scene-workflow/v1', 'brief': run, 'scene': sid, 'take': 'take-1',
                   'title': (sc.get('section') or sid).replace('-', ' '), 'lane': 'ai',
                   # A only where someone speaks on screen; the voice over a picture is B (BRIEF-SPEC rule 9)
                   'roll': {'greenscreen': 'G', 'card': 'C', 'endcard': 'E', 'screen': 'S'}.get(sc.get('kind'))
                           or ('A' if any(lp[0] == 'on' for lp in line_lips) and (scene_kind or pics == {}) else 'B'),
                   'pictures': dict(__import__('collections').Counter(pics[k]['picture'] for k in scene_ks if k in pics)),
                   'clock': {'locked': False}, 'words': words, 'steps': steps, 'sources': sources if lane in ('mix', 'real') else {},
                   'subjects': scene_subjects(sc.get('shots') or []),   # the storyboard's defined subjects, for injection and the take
                   'from': 'storyboard ' + idea + ' · ai-workspace runs/video-teardown/_work/' + run + '/stages/5-brief.md'},
                  open(p, 'w'), indent=1, ensure_ascii=False)
    bp = bd / 'brief.json'
    if not bp.exists():
        json.dump({'schema': 'scene-canvas-brief/v1', 'brief': run, 'number': num, 'title': item['name'],
                   'order': order, 'picks': {s: 'take-1' for s in order}, 'idea': idea,
                   'deliver': {'width': 1080, 'height': 1920, 'video': 'h264', 'audio': 'aac 48 kHz'},
                   # the ad's style: the ONE setting every element is made in (owner ruling, 12 Nov 2026), from the
                   # writing run, which carries the teardown's style_id (video-production styles/style_chain.py)
                   'style': run_style(run),
                   # the cast picked at Produce: role -> cast bank id ("new" = to cast); the bank ids in one list as before
                   'cast_roles': picks, 'cast': [v for v in dict.fromkeys(picks.values()) if v != 'new'],
                   'shot_fill': library_settings(doc, json.loads((WORK / run / 'run.json').read_text()).get('brand')),
                   # how the ad is made: ai | mix (AI + real) | real, with why and who chose (a person at Produce, else
                   # the chain's call from the maker route, the format, the style and the footage decision)
                   'lane': lane, 'lane_why': made['why'], 'lane_by': made['by'],
                   'trail': trail_rows('how the ad is made', lane, made['why'], made['by'])},
                  open(bp, 'w'), indent=1, ensure_ascii=False)
    # every continuous take gets its take sheet (take.json) from the chain, so the scene chain (take.py scene: direction,
    # rehearsal, start picture, review, take, checks) runs on it; nothing is written by hand (owner, 16 Nov 2026)
    try:
        import take_sheet as TS
        for sid in order:
            TS.write(bd, sid)
    except Exception as e:  # noqa: BLE001 -- the Studio shows a scene with no sheet as not directed yet
        print('take sheets not written: %s' % e, file=sys.stderr)
    print(json.dumps({'brief': num, 'scenes': len(order), 'url': STUDIO + '/?brief=' + num}))


if __name__ == '__main__':
    _cast = json.loads(sys.argv[sys.argv.index('--cast') + 1]) if '--cast' in sys.argv else None
    _arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None  # noqa: E731
    _lane = _arg('--lane')
    main(sys.argv[1], _cast, _lane if _lane in ('ai', 'mix', 'real') else None, _arg('--lane-why'), _arg('--lane-by'))
