"""Public delivery contract: pack, validate, gate, request_revision and submit.

A handoff owns required deliverable slots and acceptance criteria. Makers may
change creative execution, but a submission must fill every slot, attest every
criterion, and match the current revision and exact file hashes. No network on
check; submit uses the existing approval-card writer, never an uploader.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import sys
import fcntl
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'run-kit'))
from run_kit.paths import repo as workspace_root
REPO = Path(os.environ.get('DELIVERY_WORKSPACE_ROOT') or workspace_root(HERE)).resolve()
ROLES = ('graphic-designer', 'video-editor')
CONTRACT = 'DELIVERY-REQUIREMENTS.json'
STATE = 'delivery-state.json'
SUBMISSION = 'submission.json'


class Incomplete(ValueError):
    pass


def read(path, default=None):
    path = Path(path)
    if not path.is_file():
        return {} if default is None else default
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '.tmp-' + str(os.getpid()))
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def role_of(folder):
    return next((p for p in Path(folder).parts if p in ROLES), None)


def brief_text(folder):
    paths = [folder / 'BRIEF.md'] + sorted((folder / 'briefs').glob('*/brief.md'))
    for path in paths:
        if path.is_file():
            return path.read_text(encoding='utf-8').split('<!-- video-delivery-instructions:start -->')[0].split('<!-- delivery-contract:start -->')[0]
    return ''


def pack(folder, role=None, record=None, slots=None):
    """Freeze requirements once. Unresolved scope is held, never assumed control-only."""
    folder = Path(folder)
    role = role or role_of(folder)
    if role not in ROLES:
        return None
    if read(folder / 'run.json').get('packet_kind') == 'filming-assignment':
        return None  # raw takes have their own existing filming acceptance contract
    if (folder / CONTRACT).is_file() and not (read(folder / CONTRACT).get('state') == 'needs-scope' and (record or slots)):
        req = read(folder / CONTRACT)
    else:
        rec = record or read(folder / 'handoff.json') or read(folder / 'manifest.json') or read(folder / 'run.json')
        text = brief_text(folder)
        names = re.findall(r'^\*\*(Opening\s+\d+[^*\n]*)\*\*', text, re.M)
        if slots is None:
            if role == 'video-editor':
                named = names or [str(x.get('id') or x.get('name') or '') for x in rec.get('hooks', []) if isinstance(x, dict)]
                if not named and isinstance(rec.get('deliver'), list):
                    named = [str(x) for x in rec['deliver'] if str(x).lower().endswith(('.mp4', '.mov', '.m4v'))]
            else:
                named = [str(x.get('id') or x.get('name') or '') for x in rec.get('variations', []) if isinstance(x, dict)]
                if not named and rec.get('kind') in ('sequence', 'carousel'):
                    named = [str(x.get('asset') or '') for x in rec.get('steps', [])]
            slots = [{'id': 'slot-%02d' % (i + 1), 'label': n, 'kind': 'video' if role == 'video-editor' else 'image',
                      'cover_required': role == 'video-editor'} for i, n in enumerate(dict.fromkeys(n for n in named if n))]
        criteria = [
            {'id': 'complete-set', 'text': 'Every required deliverable slot is filled; each variation is a distinct creative, not another export of the control.'},
            {'id': 'creative-review', 'text': 'All final files were reviewed in full for finished visual quality, readable words and intentional creative execution. Creative changes are recorded per slot.'},
            {'id': 'facts', 'text': 'Product identity, factual claims, offer and required destination remain accurate.'},
            {'id': 'technical-review', 'text': 'Required format, dimensions, safe zones and export quality are checked; video sound, captions and sync are checked where applicable.'},
            {'id': 'brief-criteria', 'text': 'Every additional acceptance criterion in the brief has been checked; no missing requirement is hidden by a creative substitution.'},
        ]
        # AI-made work brings its making back with it (owner, 28 Nov 2026): every generation tried and kept, the exact
        # prompt for each, and what was changed between tries, so the brief's own prompts can be tightened and the cost
        # per brief brought down. Read from the brief or its record: an AI route or a generation tool named.
        ai = (str(rec.get('production_route') or rec.get('route') or '').lower() == 'ai'
              or re.search(r'\b(higgsfield|seedance|kling|veo|wan \d|generat(ed|ion)s?|ai route)\b', text, re.I))
        if ai:
            criteria.append({'id': 'generation-record', 'text': 'GENERATIONS.json is returned beside the files: every generation tried and every one kept, '
                             'each with its tool, its job or generation id (or link), the exact prompt used, the credits it cost when shown, '
                             'and for each retry one line on what was changed in the prompt and why.'})
        if role == 'video-editor':
            criteria.append({'id': 'cover-review', 'text': 'Every final video has its own distinct finished cover, source-video record and successful image-production checks.'})
        # Carry structured checks and explicit acceptance/checklist sections without treating scene wording as a fixed script.
        extra = rec.get('acceptance_criteria') or rec.get('checks') or []
        if isinstance(extra, dict):
            extra = [str(k) + ': ' + str(v) for k, v in extra.items()]
        if not isinstance(extra, list):
            extra = []
        in_checks = False
        for line in text.splitlines():
            if re.match(r'^#{1,6} ', line):
                in_checks = bool(re.search(r'checks before|acceptance criteria|delivery checklist|quality checks', line, re.I))
            elif in_checks and re.match(r'^\s*(?:[-*]|\d+\.)\s+', line):
                extra.append(re.sub(r'^\s*(?:[-*]|\d+\.)\s*(?:\[[ xX]\]\s*)?', '', line))
        for i, item in enumerate(extra):
            criteria.append({'id': 'brief-%02d' % (i + 1), 'text': item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)})
        req = {'schema': 'delivery-requirements/1', 'brief_key': rec.get('brief_key') or rec.get('key') or folder.name, 'role': role, 'created_at': now(),
               'format': 'carousel' if rec.get('kind') in ('sequence', 'carousel') else 'flexible',
               'creative_flexibility': True, 'slots': slots, 'criteria': criteria,
               'state': 'ready' if slots else 'needs-scope', 'source_sha256': hashlib.sha256(text.encode()).hexdigest()}
        write(folder / CONTRACT, req)
    if not (folder / STATE).is_file():
        write(folder / STATE, {'schema': 'delivery-state/1', 'state': 'in-progress', 'round': 0,
                              'revision_id': req['brief_key'] + '-R00', 'updated_at': now()})
    template(folder)
    instruction = (HERE / 'delivery-completeness.md').read_text(encoding='utf-8')
    (folder / 'DELIVERY-CHECKLIST.md').write_text(render(req, read(folder / STATE)) + '\n' + instruction, encoding='utf-8')
    pointer = '\n\n<!-- delivery-contract:start -->\n## Delivery acceptance\n\nRead `DELIVERY-CHECKLIST.md` and fill the current revision’s submission template. Creative substitutions are allowed; all deliverable slots and checks must be completed. Incomplete work stays with the maker and cannot enter owner review.\n<!-- delivery-contract:end -->\n'
    for doc in [folder / 'BRIEF.md', folder / 'HANDOFF.md', folder / 'handoff.md']:
        if doc.is_file():
            txt = doc.read_text(encoding='utf-8')
            if '<!-- delivery-contract:start -->' not in txt:
                doc.write_text(txt.rstrip() + pointer, encoding='utf-8')
    return req


def render(req, state):
    lines = ['# Delivery checklist · ' + req['brief_key'], '', '**' + state['revision_id'] + ' · ' + state['state'] + '**', '',
             'Creative alternatives may fill a required slot. Record what changed; do not reduce the required count.', '', '## Required deliverables', '']
    lines += ['- [ ] `%s` — %s%s' % (x['id'], x['label'], ' + its own thumbnail and record' if x.get('cover_required') else '') for x in req['slots']]
    if not req['slots']:
        lines.append('HELD: the brief has no machine-readable deliverable list. Define its required slots before production or delivery.')
    lines += ['', '## Acceptance criteria', ''] + ['- [ ] `%s` — %s' % (x['id'], x['text']) for x in req['criteria']]
    return '\n'.join(lines) + '\n'


def template(folder):
    req, state = read(folder / CONTRACT), read(folder / STATE)
    dest = folder / 'revisions' / state['revision_id'] / 'submission.template.json'
    if dest.exists() and read(dest).get('requirements_sha256') == digest(req):
        return dest
    write(dest, {'schema': 'delivery-submission/1', 'brief_key': req['brief_key'], 'revision_id': state['revision_id'],
                 'requirements_sha256': digest(req), 'submitted_by': '', 'submitted_at': '', 'production_records': [],
                 'items': [{'slot_id': s['id'], 'file': '', 'sha256': '', 'creative_changes': '',
                            **({'cover': '', 'cover_sha256': '', 'cover_record': ''} if s.get('cover_required') else {})} for s in req['slots']],
                 'checks': {c['id']: {'checked': False, 'by': '', 'at': '', 'evidence': ''} for c in req['criteria']}})
    return dest


def inside(folder, rel):
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        raise Incomplete('Every submitted file must be a relative path inside this handoff')
    p = (folder / rel).resolve()
    if folder.resolve() not in p.parents or not p.is_file():
        # a finished file handed to the Drive (run_kit.drive_hand) leaves a pointer at its place: it counts when the
        # path as written is in this handoff and the pointer leads to that same file's own Drive copy (2026-11-21)
        lex = Path(os.path.normpath(str(folder / rel)))
        try:
            from run_kit import drive_hand as DH
            own = DH.drive_path(lex)
        except Exception:  # noqa: BLE001 - no Drive helper: the plain rule stands
            own = None
        if not (folder.resolve() in Path(os.path.normpath(str(folder.resolve() / rel))).parents and own
                and lex.is_symlink() and Path(os.path.realpath(str(own))) == p and p.is_file()):
            raise Incomplete('Missing or outside this handoff: ' + rel)
    return p


def media_info(path, kind):
    if kind == 'video':
        p = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True)
        if p.returncode:
            raise Incomplete('Unreadable video: ' + path.name)
        data = json.loads(p.stdout)
        streams = data.get('streams', [])
        video = next((s for s in streams if s.get('codec_type') == 'video'), {})
        if not video or float(data.get('format', {}).get('duration', 0)) <= 0:
            raise Incomplete('No playable video: ' + path.name)
        if not any(s.get('codec_type') == 'audio' for s in streams):
            raise Incomplete('Video has no sound: ' + path.name)
        return int(video.get('width', 0)), int(video.get('height', 0))
    from PIL import Image
    with Image.open(path) as image:
        image.load()
        return image.size


def validate(folder, submission=None):
    folder = Path(folder).resolve()
    req, state = read(folder / CONTRACT), read(folder / STATE)
    if not req or req.get('state') != 'ready' or not req.get('slots'):
        raise Incomplete('Delivery scope is unresolved: ' + str(folder / CONTRACT))
    if not state or not state.get('revision_id'):
        raise Incomplete('Missing delivery revision state')
    path = Path(submission) if submission else folder / 'returned' / state['revision_id'] / SUBMISSION
    sub = read(path)
    if not sub:
        raise Incomplete('Missing completed submission for ' + state['revision_id'] + '; finish every required item and check')
    if sub.get('brief_key') != req['brief_key'] or sub.get('revision_id') != state['revision_id']:
        raise Incomplete('Submission is for a different brief or stale revision')
    if sub.get('requirements_sha256') != digest(req):
        raise Incomplete('Submission checklist is stale or does not match the issued requirements')
    if not sub.get('submitted_by') or not sub.get('submitted_at'):
        raise Incomplete('Submission needs its maker and timestamp')
    for rel in sub.get('production_records', []):
        inside(folder, rel)
    if any(c['id'] == 'generation-record' for c in req['criteria']):
        g = read(inside(folder, sub.get('generation_record') or 'GENERATIONS.json'))
        runs = g.get('generations') if isinstance(g, dict) else g
        if not isinstance(runs, list) or not runs:
            raise Incomplete('Missing GENERATIONS.json: list every generation tried and kept, with its tool, id or link and exact prompt')
        for i, x in enumerate(runs, 1):
            if not isinstance(x, dict) or not str(x.get('prompt') or '').strip() or not (x.get('id') or x.get('link')):
                raise Incomplete('GENERATIONS.json row %d needs its id or link and the exact prompt used' % i)
    for criterion in req['criteria']:
        check = sub.get('checks', {}).get(criterion['id'], {})
        if check.get('checked') is not True or not all(str(check.get(k) or '').strip() for k in ('by', 'at', 'evidence')):
            raise Incomplete('Unchecked criterion: ' + criterion['id'] + ' — ' + criterion['text'])
    items = sub.get('items', [])
    ids = [x.get('slot_id') for x in items]
    expected = [s['id'] for s in req['slots']]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise Incomplete('Return must fill every required slot exactly once; missing: ' + ', '.join(sorted(set(expected) - set(ids))))
    rows, seen, covers = [], set(), set()
    for slot in req['slots']:
        item = next(x for x in items if x['slot_id'] == slot['id'])
        f = inside(folder, item.get('file'))
        fingerprint = sha(f)
        if fingerprint != item.get('sha256'):
            raise Incomplete('File changed after checklist: ' + f.name)
        if fingerprint in seen:
            raise Incomplete('The same file cannot fill two required creative slots')
        seen.add(fingerprint)
        w, h = media_info(f, slot['kind'])
        if slot['kind'] == 'video' and (w < 1080 or not h or abs(w / h - 9 / 16) > .01):
            raise Incomplete('Required 9:16, at least 1080 wide: ' + f.name)
        row = {'slot_id': slot['id'], 'label': slot['label'], 'file': f, 'sha256': fingerprint,
               'creative_changes': item.get('creative_changes') or 'No creative changes declared'}
        if slot.get('cover_required'):
            c = inside(folder, item.get('cover'))
            ch = sha(c)
            if ch != item.get('cover_sha256') or ch in covers:
                raise Incomplete('Cover changed or is reused across versions: ' + c.name)
            covers.add(ch)
            cw, cheight = media_info(c, 'image')
            if cw < 1080 or abs(cw / cheight - 9 / 16) > .01 or c.stat().st_size >= 10 * 1024 * 1024:
                raise Incomplete('Cover must be 9:16, at least 1080 wide and under 10 MB')
            if item.get('cover_manual') is True:
                # a thumbnail the editor made or picked by hand: no swipe, frame or tool record needed
                rec = c.with_suffix('.cover.json')
                write(rec, {'manual': True, 'version': slot['label'], 'by': sub.get('submitted_by') or '', 'video_sha256': fingerprint})
                sys.path.insert(0, str(HERE.parent / 'image-production'))
                from image_production import provenance as PV
                PV.stamp(c, 'manual-cover', brief=req['brief_key'])
            else:
                rec = inside(folder, item.get('cover_record'))
                proof = read(rec)
                frame = proof.get('frame') or {}
                if frame.get('video_sha256') != fingerprint or frame.get('t') is None:
                    raise Incomplete('Cover record must identify its own video hash and source-frame time')
                sys.path.insert(0, str(HERE.parent / 'meta-upload'))
                import cover_rule as CR
                problem = CR.swipe_problem(str(proof.get('swipe') or ''))
                if problem:
                    raise Incomplete('Cover swipe: ' + problem)
            row.update(cover=c, cover_record=rec, cover_sha256=ch)
        rows.append(row)
    return {'requirements': req, 'state': state, 'submission': sub, 'submission_sha256': sha(path), 'rows': rows, 'folder': folder}


def find_handoff(brand, brief, product=None, repo=None):
    base = Path(repo or REPO) / 'runs/handoffs'
    number = re.search(r'\d+', str(brief or ''))
    if not number:
        return None
    matches = []
    for role in ROLES:
        for folder in (base / role / brand).glob('*'):
            hit = re.search(r'brief-(\d+)', folder.name)
            if hit and int(hit.group(1)) == int(number.group()) and folder.is_dir():
                matches.append(folder)
    if len(matches) > 1 and product:
        matches = [f for f in matches if f.name.startswith(brand + '_' + product + '_')]
    if len(matches) > 1:
        raise Incomplete('Ambiguous handoff; specify the full product/brief identity')
    return matches[0] if matches else None


def gate(brand, brief, product, media, thumbs, made_by=None, repo=None):
    folder = find_handoff(brand, brief, product, repo)
    if folder is None:
        if (made_by or {}).get('tool') in ROLES:
            raise Incomplete('Maker delivery has no issued handoff checklist')
        return None
    if read(folder / 'run.json').get('packet_kind') == 'filming-assignment':
        return None
    result = validate(folder)
    if [Path(p).resolve() for p in media] != [r['file'] for r in result['rows']]:
        raise Incomplete('Card media must match the complete validated submission, in checklist order')
    wanted = [r.get('cover') for r in result['rows']]
    if any(wanted) and [Path(p).resolve() if p else None for p in thumbs or []] != wanted:
        raise Incomplete('Every video must be filed with its validated cover, in checklist order')
    return result


def request_revision(folder, note, by, request_key, card_id=None):
    folder = Path(folder)
    with (folder / '.delivery.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _request_revision(folder, note, by, request_key, card_id)


def _request_revision(folder, note, by, request_key, card_id=None):
    """Idempotent owner revision request; keeps every earlier request and return."""
    folder = Path(folder)
    if not note.strip() or not by.strip() or not request_key.strip():
        raise Incomplete('Revision needs owner, reason and a stable request key')
    if not (folder / CONTRACT).exists():
        pack(folder)
    state = read(folder / STATE)
    for p in (folder / 'revisions').glob('*/request.json'):
        old = read(p)
        if old.get('request_key') == request_key:
            return old
    if state.get('state') == 'back-for-revision':
        raise Incomplete('An unresolved revision is already open: ' + state['revision_id'])
    rnd = int(state.get('round', 0)) + 1
    if rnd > 25:
        raise Incomplete('More than 25 revision rounds needs an explicit new batch assignment')
    rid = read(folder / CONTRACT)['brief_key'] + '-R%02d' % rnd
    request = {'schema': 'revision-request/1', 'brief_key': read(folder / CONTRACT)['brief_key'], 'revision_id': rid, 'round': rnd,
               'request_key': request_key, 'requested_by': by, 'requested_at': now(), 'note': note,
               'previous_revision': state['revision_id'], 'previous_card': card_id,
               'batch': 'batch-' + datetime.now().strftime('%Y-%m-%d') + '-' + chr(97 + rnd),
               'requirements_sha256': digest(read(folder / CONTRACT))}
    write(folder / 'revisions' / rid / 'request.json', request)
    write(folder / STATE, {**state, 'state': 'back-for-revision', 'round': rnd, 'revision_id': rid, 'updated_at': now(),
                          'request': 'revisions/' + rid + '/request.json', 'previous_card': card_id, 'batch': request['batch']})
    (folder / 'REVISION.md').write_text('# Back for revision · ' + rid + '\n\n' + note + '\n\nReturn the full completed set in `returned/' + rid + '/` with `submission.json`. Creative alternatives are welcome; missing slots or unchecked criteria block delivery.\n', encoding='utf-8')
    pack(folder)
    return request


def submit(folder, dry_run=False, root=None):
    result = validate(folder)
    folder = Path(folder)
    req, state, rows = result['requirements'], result['state'], result['rows']
    match = re.fullmatch(r'([^_]+)_(.+)_(brief-\d+)', req['brief_key'])
    if not match:
        raise Incomplete('Handoff key must identify brand, product and brief')
    brand, product, brief = match.groups()
    sys.path.append(str(HERE.parent / 'meta-upload'))
    import to_check as T
    fmt = req.get('format', 'flexible')
    p = T.to_check(brand, 'video' if req['role'] == 'video-editor' else ('carousel' if fmt == 'carousel' else 'image'), fmt, [r['file'] for r in rows],
                   made_by={'tool': req['role'], 'run': str(folder.relative_to(REPO)) if REPO in folder.parents else 'runs/handoffs/' + req['role'] + '/' + brand + '/' + folder.name},
                   product=product, brief=brief, batch=state.get('batch') or 'batch-' + datetime.now().strftime('%Y-%m-%d') + '-a',
                   thumbs=[r.get('cover') for r in rows] if req['role'] == 'video-editor' else None,
                   cover_records=[str(r['cover_record']) for r in rows] if req['role'] == 'video-editor' else None,
                   dry_run=dry_run, root=root, replace=True)
    return p


def publish(folder):
    """Publish only issued delivery/revision instructions through gdrive-creator."""
    folder = Path(folder).resolve()
    relative = folder.relative_to(REPO)
    sys.path.insert(0, str(HERE.parent / 'gdrive-creator'))
    from gdrive_creator import engine as E
    svc = E.service()
    label = 'Shared Assets/' + relative.as_posix()
    dest = E.folder_by_path(label, svc=svc)
    if not dest:
        raise Incomplete('Handoff is missing on Drive: ' + label)
    files = [folder / n for n in (CONTRACT, STATE, 'DELIVERY-CHECKLIST.md', 'REVISION.md')]
    files += list((folder / 'revisions').rglob('*.json'))
    uploaded = []
    for file in files:
        if not file.is_file():
            continue
        rel = file.relative_to(folder)
        parent = dest
        for part in rel.parts[:-1]:
            parent = E.folder(part, parent, svc=svc)
        fid, created = E.upload_file(file, file.name, parent, svc=svc)
        uploaded.append({'path': rel.as_posix(), 'drive_id': fid})
    uploaded += publish_brief_pointers(folder, svc=svc, dest=dest)
    return uploaded


def publish_brief_pointers(folder, svc=None, dest=None):
    """Refresh only marked policy appendices in the live briefs; preserve creative text."""
    folder = Path(folder).resolve()
    sys.path.insert(0, str(HERE.parent / 'gdrive-creator'))
    from gdrive_creator import engine as E
    svc = svc or E.service()
    label = 'Shared Assets/' + folder.relative_to(REPO).as_posix()
    dest = dest or E.folder_by_path(label, svc=svc)
    if not dest:
        return []
    pointer = '\n\n<!-- delivery-contract:start -->\n## Required before delivery\n\nRead `DELIVERY-CHECKLIST.md` and the latest `REVISION.md`. Complete every required deliverable and acceptance check, then submit the current revision template. Creative changes to words, hooks, scenes and variations are welcome; record which slot each fulfills. This supersedes older verbatim-creative directions. Missing items or unchecked criteria block delivery to owner review.\n<!-- delivery-contract:end -->\n'
    refs = [(dest, name) for name in ('BRIEF.md', 'HANDOFF.md', 'handoff.md', 'VIDEO-DELIVERY.md')]
    for local in (folder / 'briefs').glob('*/brief.md'):
        parent = E.folder_by_path(label + '/' + local.parent.relative_to(folder).as_posix(), svc=svc)
        if parent:
            refs.append((parent, local.name))
    parents, uploaded = {}, []
    with tempfile.TemporaryDirectory(prefix='delivery-appendix-') as tmp:
        for parent, name in refs:
            if parent not in parents:
                parents[parent] = E.list_files(parent, svc=svc)
            remote = next((f for f in parents[parent] if f['name'] == name), None)
            if not remote or remote.get('mimeType', '').startswith('application/vnd.google-apps'):
                continue
            local = Path(tmp) / name
            E.get_media(remote['id'], str(local), svc=svc)
            before = local.read_text(encoding='utf-8')
            if name == 'VIDEO-DELIVERY.md':
                after = (HERE / 'video-delivery.md').read_text(encoding='utf-8')
            else:
                start, end = '<!-- delivery-contract:start -->', '<!-- delivery-contract:end -->'
                if start in before:
                    left, tail = before.split(start, 1)
                    if end not in tail:
                        raise Incomplete('Unclosed delivery appendix in ' + name)
                    after = left.rstrip() + pointer + tail.split(end, 1)[1]
                else:
                    after = before.rstrip() + pointer
                vs, ve = '<!-- video-delivery-instructions:start -->', '<!-- video-delivery-instructions:end -->'
                if vs in after and ve in after:
                    left, tail = after.split(vs, 1)
                    after = left + vs + '\n\n' + (HERE / 'video-delivery.md').read_text(encoding='utf-8') + '\n' + ve + tail.split(ve, 1)[1]
            if after != before:
                local.write_text(after, encoding='utf-8')
                fid, created = E.upload_file(local, name, parent, svc=svc)
                uploaded.append({'path': name, 'drive_id': fid})
    return uploaded


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['pack', 'check', 'submit', 'revise'])
    ap.add_argument('folder', type=Path)
    ap.add_argument('--role', choices=ROLES)
    ap.add_argument('--note')
    ap.add_argument('--by')
    ap.add_argument('--request-key')
    ap.add_argument('--card-id')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    try:
        if args.command == 'pack':
            r = pack(args.folder, args.role); print(json.dumps(r, indent=2))
        elif args.command == 'check':
            r = validate(args.folder); print('COMPLETE ' + r['state']['revision_id'])
        elif args.command == 'revise':
            print(json.dumps(request_revision(args.folder, args.note or '', args.by or '', args.request_key or '', args.card_id), indent=2))
        else:
            p = submit(args.folder.resolve(), args.dry_run); print(p['state'], p['card']['ad_name'])
    except (Incomplete, ValueError) as e:
        print('HELD: ' + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
