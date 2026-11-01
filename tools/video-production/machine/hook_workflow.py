"""Opening workflow contract shared by the board and unattended chains.

The board renders these stages and dispatches actions. Checks, dependencies and
byte-bound approvals live here. Public: inspect, act, require_clip, require_edit.
No generation is performed by a status read.
"""
import hashlib
import importlib.util
import json
import shutil
import time
from pathlib import Path


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def digest(path, algorithm='sha256'):
    if not path or not Path(path).is_file():
        return ''
    h = hashlib.new(algorithm)
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load(root, relative):
    spec = importlib.util.spec_from_file_location('workflow_' + Path(relative).stem, Path(root) / relative)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def file_at(root, value):
    p = Path(value) if value else None
    return (p if p.is_absolute() else Path(root) / p) if p else None


def clip_of(run, root):
    rec = read(Path(run) / 'clips/ledger.json').get('G01-C1') or {}
    return file_at(root, rec.get('file')), rec


def inspect(run, root):
    run, root = Path(run), Path(root)
    opening = read(run / 'opening.json')
    if not opening:
        return {}
    errors = []
    index = read(run.parent / 'index.json')
    if 'held' in str(index.get('state', index.get('status', ''))):
        errors.append('This opening batch is held for review.')
    matrix = read(run.parent / 'hook-matrix.json')
    hm = load(root, 'tools/video-writing/machine/hook_matrix.py')
    errors += hm.check(matrix, read(run / 'run.json').get('brand'))
    row = opening.get('matrix_row') or {}
    current = next((r for r in matrix.get('openings', []) if r.get('id') == row.get('id')), {})
    if row != current or row.get('line') != opening.get('text'):
        errors.append('The opening differs from its current hook matrix; reconcile it first.')
    source = opening.get('source') or {}
    if digest(file_at(root, source.get('control'))) != source.get('control_sha256'):
        errors.append('The approved control changed; review the opening boundary.')
    stages = [{'id': 'matrix', 'name': 'Hook, format and creative dials', 'complete': not errors, 'issues': errors}]
    refs, ref_errors = [], []
    recipe = read(run / 'picture-recipe.json')
    try:
        if not recipe:
            raise ValueError('The start-picture recipe is missing.')
        pv = load(root, 'components/model-inputs/preview.py')
        result = pv.preview('pictures.generate', recipe, quote=False)
        refs = result.get('inputs') or []
        ref_errors += [f['say'] for f in result.get('findings', []) if f.get('level') == 'error']
        for ref in refs:
            path = file_at(root, ref.get('path'))
            if not path or not path.is_file():
                ref_errors.append('Missing reference: ' + str(ref.get('role')))
        if not refs:
            ref_errors.append('The recipe supplies no reference pictures.')
    except (ValueError, KeyError, OSError) as e:
        ref_errors.append(str(e))
    stages.append({'id': 'references', 'name': 'References and swaps', 'complete': not ref_errors,
                   'issues': ref_errors, 'count': len(refs)})
    # Picture dependencies exclude the spoken line and motion instructions.
    # A copy-only revision must keep a reviewed still and all its references.
    signature = hashlib.sha256(json.dumps({'recipe': recipe,
        'references': [(r.get('path'), digest(file_at(root, r.get('path')))) for r in refs]},
        sort_keys=True).encode()).hexdigest()
    clip_signature = hashlib.sha256(json.dumps({'line': opening.get('text'),
        'motion': read(run / 'motion.json'), 'inputs': read(run / 'clip-inputs.json'),
        'voice': digest(run / 'vo/S1.mp3')}, sort_keys=True).encode()).hexdigest()
    voice_binding = read(run / 'voice-binding.json')
    changes = read(run / 'hook-changes.json').get('changes') or []
    voice_current = bool((run / 'vo/S1.mp3').is_file() and
        ((voice_binding.get('line') == opening.get('text') and voice_binding.get('sha256') == digest(run / 'vo/S1.mp3'))
         if voice_binding else not any(c.get('part') == 'spoken_line' for c in changes)))
    pic = run / 'media/S1-F1.png'
    pic_sha = digest(pic)
    fc = read(run / 'hook-frame-check.json')
    frame_checked = bool(pic_sha and fc.get('sha256') == pic_sha and fc.get('setup_signature') == signature
                         and (fc.get('body') or {}).get('ok'))
    approval = read(run / 'shot-approvals.json').get('G01') or {}
    frame_approved = frame_checked and approval.get('sha') == digest(pic, 'sha1')[:16] and approval.get('setup_signature') == signature
    stages.append({'id': 'frame', 'name': 'Start frame checked and approved', 'complete': frame_approved,
                   'issues': [] if frame_approved else ((fc.get('body') or {}).get('problems') or ['Check and approve the current start frame.'])})
    clip, ledger = clip_of(run, root)
    clip_sha = digest(clip)
    binding = read(run / 'clip-binding.json')
    stale_clip = bool(clip_sha and ((changes and changes[-1].get('clip_before') == clip_sha) or
        binding.get('sha256') != clip_sha or binding.get('frame_sha256') != pic_sha or
        binding.get('setup_signature') != signature or binding.get('clip_signature') != clip_signature))
    review = read(run / 'hook-clip-review.json')
    clip_checked = bool(clip_sha and review.get('sha256') == clip_sha and review.get('checks_ok')
                        and review.get('frame_sha256') == pic_sha and review.get('setup_signature') == signature
                        and review.get('clip_signature') == clip_signature)
    clip_approved = clip_checked and not stale_clip and review.get('approved_sha256') == clip_sha
    stages.append({'id': 'clip', 'name': 'Finished clip checked and approved', 'complete': clip_approved,
                   'issues': [] if clip_approved else (['The saved change needs a new opening clip; all unaffected assets are reused.'] if stale_clip
                        else (review.get('issues') if review.get('sha256') == clip_sha else []) or ['Review the finished motion, anatomy and spoken line.'])})
    edit = read(run / 'hook-edit.json')
    cut = file_at(root, edit.get('file'))
    edit_current = bool(cut and cut.is_file() and edit.get('clip_sha256') == clip_sha
                        and edit.get('control_sha256') == source.get('control_sha256') and clip_approved)
    stages.append({'id': 'edit', 'name': 'Opening joined to the approved body', 'complete': edit_current,
                   'issues': [] if edit_current else ['Make the full cut after approving the clip.']})
    setup_ok = not errors and not ref_errors
    return {'run': str(run.relative_to(root / 'runs/video-production')), 'stages': stages,
            'line': opening.get('text'), 'scroll': row.get('scroll'), 'controls': row.get('controls') or {},
            'format': matrix.get('format_contract') or {}, 'body_join': row.get('body_join'),
            'base': str(file_at(root, recipe.get('brief', {}).get('base')) or ''),
            'can_reuse_control_frame': setup_ok and bool(digest(file_at(root, recipe.get('brief', {}).get('base')))),
            'can_check_frame': setup_ok and pic.is_file(), 'can_approve_frame': setup_ok and frame_checked,
            'can_make_clip': setup_ok and frame_approved and voice_current, 'can_check_clip': setup_ok and frame_approved and bool(clip_sha) and not stale_clip,
            'can_make_voice': setup_ok and not voice_current, 'voice_current': voice_current,
            'can_approve_clip': setup_ok and frame_approved and clip_checked and not stale_clip, 'can_edit': setup_ok and frame_approved and clip_approved,
            'clip': str(clip) if clip_sha else '', 'cut': str(cut) if edit_current else '',
            'frame_checked': frame_checked, 'clip_checked': clip_checked, 'setup_signature': signature,
            'clip_signature': clip_signature, 'motion': read(run / 'motion.json').get('happens') or '',
            'movement_id': read(run / 'clip-inputs.json').get('movement_id', 'none' if read(run / 'motion.json').get('use_movement_reference') is False else ''),
            'movements': [{'id': e['id'], 'does': e.get('does') or []} for e in
                          load(root, 'tools/video-production/machine/movement.py').bank()],
            'change_impacts': {p: change_impact(p) for p in ('spoken_line', 'motion', 'motion_reference')}}
    


def require_clip(run, root):
    state = inspect(run, root)
    if state and not state['can_make_clip']:
        issues = [i for s in state['stages'][:3] if not s['complete'] for i in s['issues']]
        if not state.get('voice_current'):
            issues.append('Make the voice for the revised line; the existing frame and references are reused.')
        raise ValueError('Opening workflow: ' + ' '.join(issues))


def require_edit(run, root):
    state = inspect(run, root)
    if not state.get('can_edit'):
        raise ValueError('Check and approve the current opening clip before making its full cut.')


def act(run, root, action):
    run, root = Path(run), Path(root)
    state = inspect(run, root)
    if not state or not state.get('can_' + action):
        raise ValueError('Complete the preceding workflow checks before ' + action.replace('_', ' ') + '.')
    if action == 'reuse_control_frame':
        recipe = read(run / 'picture-recipe.json')
        base = file_at(root, recipe['brief']['base'])
        pic = run / 'media/S1-F1.png'
        archive = run / 'versions' / ('frame-' + digest(pic))
        archive.mkdir(parents=True, exist_ok=True)
        if pic.is_file():
            shutil.copy2(pic, archive / pic.name)
        write(archive / 'picture-recipe.json', recipe)
        shutil.copy2(base, pic)
        keep = 'Reuse the approved control picture exactly, including its existing person, props and hand pose. No picture generation or pose change.'
        recipe['brief']['swaps'] = keep
        recipe['brief']['shot_direction'] = {'face': 'Exactly as the approved control picture.', 'gesture': keep}
        for row in (recipe['brief'].get('swap_list') or {}).get('swaps', []):
            if row.get('kind') == 'cast':
                row['to'] = keep
        recipe['reused_frame'] = {'source': str(base.relative_to(root)), 'sha256': digest(base)}
        write(run / 'picture-recipe.json', recipe)
        opening = read(run / 'opening.json')
        opening['thumbnail'] = opening['matrix_row']['thumb'] = keep
        opening['matrix_row']['watch_payoff'] = 'The contrast between the approved teaching models supports the spoken comparison.'
        write(run / 'opening.json', opening)
        matrix = read(run.parent / 'hook-matrix.json')
        matrix['openings'] = [opening['matrix_row'] if r.get('id') == opening['matrix_row']['id'] else r for r in matrix['openings']]
        write(run.parent / 'hook-matrix.json', matrix)
    elif action == 'check_frame':
        pic = run / 'media/S1-F1.png'
        old = read(run / 'hook-frame-check.json')
        body = old.get('body') if old.get('sha256') == digest(pic) else None
        existing = read(run / 'body-checks.json').get(pic.name) or {}
        body = body or (existing if existing.get('sha') == digest(pic, 'sha1')[:16] else None)
        if body and body.get('checker_sha256') != digest(root / 'tools/video-production/prompts/v2/body-check-v1-damon.md'):
            body = None
        body = body or load(root, 'tools/video-production/machine/body_check.py').check(run, pic, 'hook-frame-body')
        write(run / 'hook-frame-check.json', {'sha256': digest(pic), 'body': body, 'setup_signature': state['setup_signature']})
        checks = read(run / 'body-checks.json')
        checks[pic.name] = dict(body, sha=digest(pic, 'sha1')[:16])
        write(run / 'body-checks.json', checks)
    elif action == 'approve_frame':
        pic = run / 'media/S1-F1.png'
        approvals = read(run / 'shot-approvals.json')
        approvals['G01'] = {'picture': str(pic.relative_to(root)), 'sha': digest(pic, 'sha1')[:16],
                            'setup_signature': state['setup_signature'], 'by': 'board review'}
        write(run / 'shot-approvals.json', approvals)
    elif action == 'check_clip':
        clip, ledger = clip_of(run, root)
        old = read(run / 'hook-clip-review.json')
        body = old.get('body') if old.get('sha256') == digest(clip) else None
        checker = load(root, 'tools/video-production/machine/body_check.py')
        if body and body.get('checker_sha256') != digest(root / 'tools/video-production/prompts/v2/body-check-v1-damon.md'):
            body = None
        body = body or checker.check(run, clip, 'hook-video-body')
        issues = list(body.get('problems') or [])
        if not body.get('ok'):
            issues.append('The finished-video body check did not pass.')
        if (ledger.get('line_check') or {}).get('verdict') != 'PASS':
            issues.append('The spoken-line check did not pass.')
        parity = load(root, 'tools/video-production/machine/lineparity.py')
        if parity.compare(parity.say_numbers((ledger.get('line_check') or {}).get('heard', '')),
                          parity.say_numbers(state.get('line', ''))) < parity.threshold_of():
            issues.append('This clip says an earlier version of the hook; regenerate only its voice and clip.')
        if not ((ledger.get('qc') or {}).get('lips') or {}).get('ok'):
            issues.append('The lip-sync check did not pass.')
        write(run / 'hook-clip-review.json', {'sha256': digest(clip), 'body': body, 'issues': issues, 'checks_ok': not issues,
              'frame_sha256': digest(run / 'media/S1-F1.png'), 'setup_signature': state['setup_signature']})
        review = read(run / 'hook-clip-review.json')
        review['clip_signature'] = state['clip_signature']
        write(run / 'hook-clip-review.json', review)
    elif action == 'approve_clip':
        clip, _ = clip_of(run, root)
        review = read(run / 'hook-clip-review.json')
        review.update(approved_sha256=digest(clip), reviewed_by='board review')
        write(run / 'hook-clip-review.json', review)
    elif action == 'make_voice':
        voice = run / 'vo'
        if voice.is_dir():
            versions = run / 'versions'
            versions.mkdir(exist_ok=True)
            voice.rename(versions / ('voice-' + str(time.time_ns())))
        load(root, 'tools/video-production/machine/hook_variations.py').make_voice(run)
        write(run / 'voice-binding.json', {'line': state['line'], 'sha256': digest(run / 'vo/S1.mp3')})
        load(root, 'tools/video-production/machine/hook_variations.py').plan_clip(run, root)
    return {'workflow': inspect(run, root)}


def change_impact(part):
    impacts = {
        'spoken_line': {'reuse': ['approved start frame', 'cast, props and room references', 'motion reference', 'body'],
                        'rebuild': ['this opening voice', 'this opening clip', 'joined cut']},
        'motion': {'reuse': ['approved start frame', 'voice', 'cast, props and room references', 'body'],
                   'rebuild': ['this opening clip', 'joined cut']},
        'motion_reference': {'reuse': ['approved start frame', 'voice', 'cast, props and room references', 'body'],
                             'rebuild': ['prepared motion reference (local cache)', 'this opening clip', 'joined cut']}}
    if part not in impacts:
        raise ValueError('Unknown isolated change')
    return impacts[part]


def revise(run, root, part, value):
    """Save one change, preserve every asset, spend nothing. Dependent stages reopen."""
    run, root = Path(run), Path(root)
    impact = change_impact(part)
    value = str(value).strip()
    if not value and part != 'motion_reference':
        raise ValueError('Write the replacement value first.')
    opening = read(run / 'opening.json')
    row = opening['matrix_row']
    previous = (opening['text'] if part == 'spoken_line' else
                read(run / 'motion.json').get('happens') if part == 'motion' else
                read(run / 'clip-inputs.json').get('movement_id', 'none' if read(run / 'motion.json').get('use_movement_reference') is False else ''))
    if value == previous:
        return {'unchanged': True, 'impact': {'reuse': ['all current assets'], 'rebuild': []}}
    clip_before = digest(clip_of(run, root)[0])
    if part == 'motion_reference':
        choices = {e['id'] for e in load(root, 'tools/video-production/machine/movement.py').bank()}
        if value not in choices | {'', 'none'}:
            raise ValueError('Choose an active motion reference from the bank.')
        inputs = read(run / 'clip-inputs.json'); previous = inputs.get('movement_id', '')
        inputs['movement_id'] = value; write(run / 'clip-inputs.json', inputs)
    else:
        previous = opening['text'] if part == 'spoken_line' else read(run / 'motion.json').get('happens')
        plan = read(run / 'plan.json')
        if part == 'spoken_line':
            opening['text'] = row['line'] = value
            plan['scenes'][0]['voice'] = value
            plan['scenes'][0]['beats'] = []
            motion = read(run / 'motion.json')
            if motion.get('beats'):
                motion['beats'] = []
                write(run / 'motion.json', motion)
            write(run / 'lines.json', {'S1': value})
        else:
            opening['visual'] = row['scroll'] = value
            for control in (row.get('controls') or {}).values():
                if control.get('evidence') == previous:
                    control['evidence'] = value
            motion = read(run / 'motion.json'); motion['happens'] = value
            # Old timed gestures must not survive an explicit replacement action.
            motion['beats'] = []; motion['gestures'] = value
            write(run / 'motion.json', motion)
            plan['scenes'][0].update(happens=value, beats=[], gestures=value)
            for shot in plan['scenes'][0].get('shots') or []:
                shot['gestures'] = value
        write(run / 'plan.json', plan)
        write(run / 'opening.json', opening)
        matrix = read(run.parent / 'hook-matrix.json')
        matrix['openings'] = [row if r['id'] == row['id'] else r for r in matrix['openings']]
        write(run.parent / 'hook-matrix.json', matrix)
        index = read(run.parent / 'index.json')
        for r in index.get('openings') or []:
            if r['id'] == run.name:
                r.update(text=opening['text'], visual=opening.get('visual', row.get('scroll', '')), matrix_row=row)
        write(run.parent / 'index.json', index)
    changes = read(run / 'hook-changes.json').get('changes') or []
    changes.append({'part': part, 'before': previous, 'after': value, 'impact': impact, 'at': time.time(), 'clip_before': clip_before})
    write(run / 'hook-changes.json', {'changes': changes})
    return {'impact': impact, 'workflow': inspect(run, root)}
