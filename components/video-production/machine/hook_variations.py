"""Prepare isolated scroll-stopper runs against an existing approved control.

The first spoken scene may share a generated clip with later body scenes. The
replacement boundary comes from the approved edit's voice clock, never the
whole clip's duration. Preparing openings does not rewrite the control run.

Public surface: prepare(run, edit, root), openings(run), make_voice(opening).
CLI: hook_variations.py prepare RUN --edit EDIT | voice OPENING

HELD FOR REVIEW (2026-11-18, machine/held.json `hooks-from-the-body`): body_openings(plan) reads the body's own
on-camera lines for ones that can open the ad and proposes them as openings; `from-body RUN` prints them. Nothing
calls it and `--apply` is refused until the owner's review turns it on.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def replacement_boundary(edit_map, scene):
    lines = sorted(edit_map.get('voice') or [], key=lambda x: x['a'])
    if not lines or lines[0].get('scene') != scene:
        raise ValueError('The hook must replace the first spoken scene of the approved cut')
    first = [x for x in lines if x.get('scene') == scene]
    body = [x for x in lines if x.get('scene') != scene]
    if not body:
        raise ValueError('The approved cut has no body after its opening')
    end = max(float(x['b']) for x in first)
    start = float(body[0]['a'])
    if start < end - 0.001:
        raise ValueError('Opening speech overlaps the body; resolve the join before generation')
    return {'scene': scene, 'body_starts_at': start,
            'opening_ends_at': end, 'next_scene': body[0]['scene']}


def specifications(plan, edit_map, matrix=None):
    hooks = plan.get('hooks') or []
    controls = [h for h in hooks if str(h.get('take', '')).lower() == 'control']
    if len(controls) != 1:
        raise ValueError('Exactly one control hook must identify the approved opening')
    control = controls[0]
    scene = control.get('opener_scene')
    if not scene:
        raise ValueError('The control hook has no opener_scene')
    boundary = replacement_boundary(edit_map, scene)
    source = next((s for s in plan.get('scenes') or [] if s['id'] == scene), None)
    speaker = (source or {}).get('speaker') or next(
        (x.get('who') for x in edit_map.get('voice', []) if x.get('scene') == scene), None)
    if not source or not speaker:
        raise ValueError('The opening scene needs a named speaker')
    rows = []
    for n, hook in enumerate(hooks, 1):
        if hook is control:
            continue
        if not hook.get('text') or not hook.get('thumb'):
            raise ValueError('Every opening needs its written line and visual concept')
        if hook.get('opener_scene') not in (None, scene):
            raise ValueError('An opening targets a different scene; resolve it explicitly')
        matched = next((r for r in (matrix or {}).get('openings', []) if r['id'] == 'V%d' % (n - 1)), None)
        if matrix and not matched:
            raise ValueError('The hook matrix is missing opening V%d' % (n - 1))
        # A thumbnail is a cover, not a description of the moving opening.
        visual = matched['scroll'] if matched else hook.get('scroll')
        if not visual:
            raise ValueError('The hook needs its full scroll event; thumbnail-only generation is refused')
        rows.append({'id': 'h%02d' % n, 'title': hook['id'], 'text': matched['line'] if matched else hook['text'],
                     'visual': visual, 'thumbnail': matched['thumb'] if matched else hook['thumb'], 'card': hook.get('card'),
                     'matrix_row': matched, 'format_contract': (matrix or {}).get('format_contract'),
                     'speaker': speaker, 'source_hook': copy.deepcopy(hook),
                     'replacement': copy.deepcopy(boundary), 'state': 'prepared'})
    return rows, source


def prepare(run, edit, root, matrix=None, batch='hooks'):
    run, edit, root = Path(run).resolve(), Path(edit).resolve(), Path(root).resolve()
    parent = read(run / 'plan.json')
    if not re.fullmatch(r'[a-z0-9-]+', batch):
        raise ValueError('Invalid batch folder')
    rows, source = specifications(parent, read(edit / 'edit-map.json'), matrix)
    control = edit / 'renders' / 'control.mp4'
    if not control.is_file():
        raise ValueError('No approved control render exists')
    provenance = {'control': str(control.relative_to(root)), 'control_sha256': sha(control),
                  'edit_map_sha256': sha(edit / 'edit-map.json'),
                  'decisions_sha256': sha(edit / 'decisions.json'),
                  'source_run': str(run.relative_to(root))}
    existing = run / batch / 'index.json'
    if existing.is_file():
        old = read(existing)
        if old.get('source') != provenance or [(x['source_hook'], x.get('matrix_row')) for x in old['openings']] != [(x['source_hook'], x.get('matrix_row')) for x in rows]:
            raise ValueError('Control or hooks changed; existing opening work is preserved for review')
        return old
    rec = read(run / 'run.json')
    elements = read(run / 'elements.json')
    for row in rows:
        out = run / batch / row['id']
        if out.exists():
            raise ValueError('An opening folder already exists without its index: ' + row['id'])
        # No stale control gestures, words, props or outfit descriptions survive.
        sc = {'id': 'S1', 'speaker': row['speaker'], 'who': row['speaker'],
              'voice': row['text'], 'to_camera': True, 'kind': 'presenter',
              'opens': True, 'section': source.get('section'), 'priority': 1,
              'first_frame': {'subject': row['visual'],
                              'continuity': 'Use the approved control picture for outfit, room and light'},
              'hands_off': 'cut'}
        plan = {'shape': 'scenes', 'brand': rec['brand'], 'cast': copy.deepcopy(parent['cast']),
                'piece': copy.deepcopy(parent.get('piece') or {}), 'scenes': [sc],
                'hooks': [], 'layers': {}, 'sfx': [], 'music': None}
        out.mkdir(parents=True)
        write(out / 'plan.json', plan)
        write(out / 'run.json', {'machine': 'video-production-hook', 'brand': rec['brand'],
              'label': rec['label'] + '-' + row['id'], 'format': rec.get('format'),
              'parent_run': str(run.relative_to(root)), 'hook': row['id']})
        write(out / 'lines.json', {'S1': row['text']})
        write(out / 'elements.json', elements)
        cast = [{'id': i['id'], 'bank_id': i['bank_id']} for i in elements.get('items', [])
                if i.get('kind') == 'person']
        doc = dict(plan, cast=cast)
        (out / 'brief.md').write_text('# ' + row['title'] + '\n\nOpening variation of the approved control.\n\n```json\n'
                                     + json.dumps(doc, indent=2, ensure_ascii=False) + '\n```\n')
        write(out / 'opening.json', dict(row, source=provenance))
    index = {'source': provenance, 'openings': rows}
    write(existing, index)
    return index


def openings(run):
    index = Path(run) / 'hooks' / 'index.json'
    return read(index) if index.is_file() else {'openings': []}


def keep_parent_voice(opening):
    """A variation is read with the previous run's exact voice settings and delivery tag, never defaults."""
    root = Path(__file__).resolve().parents[3]
    parent = root / read(opening / 'opening.json')['source']['source_run']
    timing = parent / 'vo/timing.json'
    was = (read(timing).get('scenes') or {}).get('S1') or {} if timing.is_file() else {}
    plan = read(opening / 'plan.json')
    scene = plan['scenes'][0]
    if was.get('voice_settings'):
        scene['voice_settings'] = was['voice_settings']
    tag = was.get('delivery_tag') or (re.match(r'\[[^\]]+\]', was.get('sent_text', '')) or [None])[0]
    if tag:
        scene['delivery_tag'] = tag
    (opening / 'plan.json').write_text(json.dumps(plan, indent=2, ensure_ascii=False) + '\n')


def make_voice(opening):
    opening = Path(opening)
    if (opening / 'vo' / 'S1.mp3').is_file():
        return {'state': 'already_made', 'file': 'vo/S1.mp3'}
    keep_parent_voice(opening)
    path = Path(__file__).with_name('voice.py')
    spec = importlib.util.spec_from_file_location('hook_voice', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_for(opening, per_line=False)


def module(name):
    spec = importlib.util.spec_from_file_location('hook_' + name, Path(__file__).with_name(name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def plan_clip(opening, root):
    """Use the existing clip prompt builder and the parent's route and movement reference."""
    opening, root = Path(opening), Path(root)
    record = read(opening / 'opening.json')
    parent = root / record['source']['source_run']
    if sha(root / record['source']['control']) != record['source']['control_sha256']:
        raise ValueError('The control changed; review the replacement boundary first')
    plan = read(opening / 'plan.json')
    motion = read(opening / 'motion.json')
    scene = dict(plan['scenes'][0], **motion)
    scene['shots'] = [{k: motion[k] for k in
                      ('face', 'gestures', 'camera_move', 'emotion', 'no') if k in motion}]
    plan['scenes'] = [scene]
    runner = module('clips_run')
    people, problems = runner.people_of(opening)
    if problems:
        raise ValueError('; '.join(problems))
    who = record['speaker']
    if who not in people:
        raise ValueError('The hook speaker is absent from the cast')
    voice = opening / 'vo/S1.mp3'
    if not voice.is_file():
        raise ValueError('The opening needs its locked voice read first')
    seconds = module('voice').audio_seconds(voice)
    old = read(parent / 'clips/plan.json')
    template = next(c for c in old['calls'] if not c.get('hook') and
                    record['replacement']['scene'] in c.get('scenes', []))
    call = copy.deepcopy(template)
    # A model-specific demonstration may need to drop a conflicting parent
    # gesture reference while retaining the same start frame and voice route.
    if motion.get('use_movement_reference') is False:
        call['refs'] = [r for r in call.get('refs', []) if r.get('kind') != 'movement']
    for stale in ('params', 'kling', 'seedance', 'acting', 'prompt', 'swipe_elements', 'take_round', 'final'):
        call.pop(stale, None)
    call.update(id='G01-C1', clip='G01-C1', section_id='G01', section='Section 1', n=1,
                scenes=['S1'], start_frame='S1-F1', face_ref='S1-F1', end_frame=None, after=None,
                seconds=seconds, duration=module('seedance').span(seconds), window=[0, seconds], at=0,
                people=[who], talking=True, hands_off='cut', camera=motion.get('camera_move', 'still'),
                lines=[{'scene': 'S1', 'speaker': who, 'text': record['text'], 'on_camera': True,
                        'at': 0, 'until': seconds}],
                voice_parts=[{'scene': 'S1', 'person': who, 'line': record['text'],
                              'voice_id': people[who]['voice_id']}])
    call['image_refs'] = module('clip_refs').for_call(opening, call, root)
    call['ref_notes'] = module('clip_refs').notes(opening, call, root)
    call['seedance'] = module('seedance_prompt').build(
        call, {'S1': scene}, people, {}, plan.get('piece', {}).get('style', ''), who)
    call['prompt'] = call['seedance']['prompt']
    write(opening / 'plan.json', plan)
    write(opening / 'clips/plan.json', {'calls': [call], 'tts': [], 'problems': []})
    (opening / 'clips/PROMPTS.md').write_text('# ' + record['title'] + '\n\n' + call['prompt'] + '\n')
    # A single independent opening has no swipe effects or old body scenes.
    write(opening / 'storyboard.json', {'sections': [{'id': 'G01', 'scenes': ['S1'],
          'maker': 'lip-sync', 'seconds': seconds, 'starts': 0, 'voice': {'S1': seconds},
          'clips': [{'scenes': ['S1'], 'seconds': seconds,
                     'starts_from': "the section's start picture"}],
          'elements': ['person · ' + who],
          'frames': [{'what': 'start frame', 'from': 'S1'}],
          'voice_from': {'S1': 'recorded'},
          'start_frame': {'from_scene': 'S1'}, 'effects': []}],
          'people_map': {'lead': [who]}, 'layers': {}})
    return call


def make_opening(opening, root):
    opening = Path(opening)
    module('hook_workflow').require_clip(opening, root)
    index = opening.parent / 'index.json'
    if index.is_file() and 'held' in str(read(index).get('state', read(index).get('status', ''))):
        raise ValueError('This batch is held for format review')
    result_file = opening / 'clip-result.json'
    if result_file.is_file():
        result = read(result_file)
        state = module('hook_workflow').inspect(opening, root)
        if result.get('file') and Path(result['file']).is_file() and state.get('can_check_clip'):
            return result
    picture = opening / 'media/S1-F1.png'
    if not picture.is_file():
        raise ValueError('The opening has no starting picture')
    body = module('body_check').check(opening, picture)
    write(opening / 'body-check.json', body)
    if not body.get('ok'):
        raise ValueError('Starting picture body check: ' + '; '.join(body.get('problems') or []))
    call = plan_clip(opening, root)
    runner = module('clips_run')
    result = runner.make_clip(opening, call)
    write(result_file, result)
    return result


# ---------------------------------------------------------------- openings from the body (HELD, 2026-11-18)
# The decision this fills: "More openings from what exists" had no rule. A line already filmed in the body can open the
# ad when it stands on its own; moving it to the front is a re-cut of footage that exists, never a new clip. Written
# and not live: machine/held.json `hooks-from-the-body` is off, so nothing calls this and `--apply` is refused.

LEANS_BACK = re.compile(r"^(and|but|so|because|then|also|which|plus|or|well|anyway|that's why|that is why|"
                        r"it|this|that|these|those|they|them|he|she|there)\b", re.I)
SIGNALS = (("asks a question", re.compile(r"\?")),
           ("speaks to the viewer", re.compile(r"\b(you|your|you're|yours)\b", re.I)),
           ("carries a figure", re.compile(r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|twice|half|years?)\b", re.I)),
           ("turns on a contrast", re.compile(r"\b(never|stop|don't|doesn't|didn't|nobody|nothing|wrong|until|instead|actually)\b", re.I)),
           ("is an admission", re.compile(r"\b(i|i'd|i've|my|me)\b", re.I)))
NOT_A_LINE = {'card', 'endcard', 'screen', 'split'}


def body_openings(plan, limit=3, max_words=16, min_words=4):
    """Lines already in the body that could open the ad, as opening rows (the same shape every opening has: id, text,
    opener_scene, take), best first. A line qualifies when it is spoken on camera in a scene after the control's
    opening, is between `min_words` and `max_words` long, does not lean on the line before it, and carries at least
    one hook signal. Each row says why. Reads the plan only; makes and changes nothing."""
    hooks = plan.get('hooks') or []
    control = next((h for h in hooks if str(h.get('take', '')).lower() == 'control'), None)
    opener = (control or {}).get('opener_scene') or next((s.get('id') for s in plan.get('scenes') or [] if s.get('opens')), None)
    have = {re.sub(r'[^a-z0-9 ]', '', str(h.get('text') or '').lower()).strip() for h in hooks}
    rows, past_opening = [], opener is None
    for n, s in enumerate(plan.get('scenes') or []):
        if s.get('id') == opener:
            past_opening = True
            continue
        if not past_opening or not s.get('to_camera') or (s.get('kind') or '') in NOT_A_LINE:
            continue
        line = str(s.get('voice') or s.get('line') or '').strip()
        if not line or re.match(r'(?i)^none\b', line):
            continue
        first = re.split(r'(?<=[.!?])\s+', line)[0].strip()
        words = first.split()
        if not (min_words <= len(words) <= max_words) or LEANS_BACK.match(first):
            continue
        if re.sub(r'[^a-z0-9 ]', '', first.lower()).strip() in have:
            continue
        why = [name for name, rx in SIGNALS if rx.search(first)]
        if not why:
            continue
        rows.append((-len(why), n, {'text': first, 'opener_scene': s.get('id'), 'from_body': True,
                                    'take': 'a line already in the body, moved to the front',
                                    'why': '%d words, stands on its own, %s' % (len(words), ', '.join(why))}))
    out = [r for _, _, r in sorted(rows, key=lambda x: (x[0], x[1]))[:limit]]
    for i, r in enumerate(out, 1):
        r['id'] = 'Body opening %d' % i
    return out


def apply_body_openings(run):
    """Add the proposed body openings to the run's plan. REFUSED while the change is held for review."""
    held = module('held')
    if not held.on('hooks-from-the-body'):
        raise ValueError('Openings from the body are held for review (machine/held.json hooks-from-the-body is off): '
                         'nothing was written')
    run = Path(run)
    plan = read(run / 'plan.json')
    new = body_openings(plan)
    plan['hooks'] = list(plan.get('hooks') or []) + new
    write(run / 'plan.json', plan)
    return new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('from-body'); b.add_argument('run'); b.add_argument('--apply', action='store_true')
    p = sub.add_parser('prepare'); p.add_argument('run'); p.add_argument('--edit', required=True)
    p.add_argument('--matrix'); p.add_argument('--batch', default='hooks')
    v = sub.add_parser('voice'); v.add_argument('opening')
    for command in ('plan-clip', 'make'):
        v = sub.add_parser(command); v.add_argument('opening')
    a = parser.parse_args()
    if a.command == 'from-body':
        rows = apply_body_openings(a.run) if a.apply else body_openings(read(Path(a.run) / 'plan.json'))
        print(json.dumps({'openings': rows, 'state': 'written' if a.apply else 'proposed, nothing written (held for review)'},
                         indent=1, ensure_ascii=False))
        return
    if a.command == 'prepare':
        # Shared path finder, not a machine-specific checkout path.
        spec = importlib.util.spec_from_file_location('hook_paths', Path(__file__).parents[2] / 'run-kit' / 'run_kit' / 'paths.py')
        paths = importlib.util.module_from_spec(spec); spec.loader.exec_module(paths)
        result = prepare(a.run, a.edit, paths.repo(), read(a.matrix) if a.matrix else None, a.batch)
        print(json.dumps({'openings': len(result['openings']), 'state': 'prepared'}))
    elif a.command == 'voice':
        print(json.dumps(make_voice(a.opening), default=str))
    else:
        spec = importlib.util.spec_from_file_location('hook_paths', Path(__file__).parents[2] / 'run-kit' / 'run_kit' / 'paths.py')
        paths = importlib.util.module_from_spec(spec); spec.loader.exec_module(paths)
        fn = plan_clip if a.command == 'plan-clip' else make_opening
        result = fn(a.opening, paths.repo())
        print(json.dumps({'file': result.get('file'), 'id': result.get('id'),
                          'below_criteria': result.get('below_criteria')}, default=str))


if __name__ == '__main__':
    main()
