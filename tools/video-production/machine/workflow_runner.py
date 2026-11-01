#!/usr/bin/env python3
"""Durable command/agent/review loop for workflow.py. No shell, scheduler or model of its own.

The active assistant services agent tasks using the named component and returns evidence.
Command stations run automatically; human reviews use the existing review component.
State: runs/video-production/<brand>/workflow-<label>/workflow-state.json.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import workflow as W


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def local(ref):
    path = (W.WS / ref).resolve()
    if not path.is_relative_to(W.WS.resolve()):
        raise ValueError('evidence and state must live in the workspace')
    return path


def snapshot(refs, step=None, values=None):
    result = {}
    for ref in refs:
        p = local(ref)
        if not p.is_file():
            raise ValueError('missing evidence: ' + ref)
        data = p.read_bytes()
        check = (step or {}).get('run_check', {})
        if check and p == local(W.fill(check['file'], values or {})):
            record = json.loads(data)
            # A later writing pass mutates run.json. Hash only this station's owned
            # stages and inputs, so successful writing does not invalidate setup.
            selected = {k: record.get(k) for k in check.get('root_fields', [])}
            selected['stages'] = {k: record.get('stages', {}).get(k) for k in check['stages']}
            data = json.dumps(selected, sort_keys=True).encode()
        result[str(p.relative_to(W.WS.resolve()))] = digest(data)
    if not result:
        raise ValueError('a station needs concrete file evidence')
    return result


def unchanged(files, step=None, values=None):
    try:
        return snapshot(list(files), step, values) == files
    except (OSError, ValueError):
        return False


def command(step, values):
    if step.get('commands') and values.get('route') not in step['commands']:
        raise ValueError('choose route: ' + ', '.join(step['commands']))
    template = step.get('commands', {}).get(values.get('route'), step.get('run', ''))
    argv = [W.fill(word, values) for word in shlex.split(template)]
    missing = sorted({slot for word in argv for slot in re.findall(r'\{(\w+)\}', word)})
    if missing:
        raise ValueError('missing inputs: ' + ', '.join(missing))
    if not argv:
        raise ValueError('no command registered for this station')
    if argv[0] == 'python3':
        argv[0] = sys.executable
    return argv


def review_module():
    spec = importlib.util.spec_from_file_location('workflow_review', W.WS / 'components/review/review_request.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def review_proof(step, values):
    """Use review's public fold; require an accepted, version-bound approval by the named person."""
    key = step['id'].replace('-', '_')
    if not key.endswith('_review'):
        key += '_review'
    item = values.get(key)
    if not item:
        raise ValueError('needs existing review item via --set ' + key + '=RQ-...')
    mod = review_module()
    state = mod.fold(mod.read_records(root=W.WS, item=item))
    request = state.get('request') or {}
    who = step['gate']
    verdict = state.get('verdicts', {}).get(who) or {}
    if not state.get('accepted') or verdict.get('verdict', {}).get('verdict') != 'approve':
        raise ValueError('review is not accepted with ' + who + "'s approval: " + item)
    asset = request.get('asset') or {}
    ref = W.fill(step.get('review_asset', ''), values)
    if not ref or '{' in ref or asset.get('warehouse') != 'repo' or asset.get('ref') != ref:
        raise ValueError('review must name this station\'s repo asset: ' + ref)
    commit = asset.get('at', '')
    if not re.fullmatch(r'[a-fA-F0-9]{7,40}', commit):
        raise ValueError('review needs a pinned asset.at commit; unversioned approval is not auto-applied')
    # A later edited request cannot inherit an earlier verdict/close.
    records = mod.read_records(root=W.WS, item=item)
    requested = max(str(r.get('created', '')) for r in records
                    if r.get('verdict', {}).get('event') == 'request')
    closed = str((state.get('close') or {}).get('created', ''))
    if not requested <= str(verdict.get('created', '')) <= closed:
        raise ValueError('review changed after approval; inspect the current request')
    result = subprocess.run(['git', 'show', commit + ':' + ref], cwd=W.WS, capture_output=True)
    if result.returncode or result.stdout != local(ref).read_bytes():
        raise ValueError('approved asset version differs from the current file')
    return {'review_item': item, 'evidence': snapshot([ref])}


def input_hash(step, values, previous):
    # Include every template argument, not just the human-readable inputs list.
    # Switching the swipe or output label must invalidate a prior execution.
    keys = set(step.get('inputs', [])) | set(re.findall(r'\{(\w+)\}', json.dumps(step)))
    return digest(json.dumps({'step': step, 'values': {k: values.get(k) for k in keys},
                              'previous': previous}, sort_keys=True).encode())


def output_refs(step, values):
    import glob
    refs = []
    for pattern in [step.get('done_when', '')] + step.get('evidence', []):
        pattern = W.fill(pattern, values)
        if pattern and '{' not in pattern:
            refs.extend(str(Path(p).resolve().relative_to(W.WS.resolve()))
                        for p in glob.glob(str(W.WS / pattern)) if Path(p).is_file())
    return sorted(set(refs))


def receipt_valid(step, values, receipt, signature):
    if not receipt or receipt.get('inputs') != signature or not unchanged(receipt.get('evidence', {}), step, values):
        return False
    if step.get('executor') == 'command' and W.is_done(step, values) is not True:
        return False
    return True


def next_step(fmt, state):
    previous = []
    values = state['values']
    for step in W.workflow(fmt)['steps']:
        signature = input_hash(step, values, previous)
        receipt = state.get('receipts', {}).get(step['id'])
        if step.get('executor') == 'review':
            try:
                proof = review_proof(step, values)
            except (ValueError, OSError) as exc:
                return step, signature, str(exc)
            # Recheck external review state on every resume, even with a local receipt.
            receipt = dict(proof, inputs=signature)
        if not receipt_valid(step, values, receipt, signature):
            return step, signature, None
        previous.append({'id': step['id'], 'inputs': signature, 'evidence': receipt['evidence'],
                         'review_item': receipt.get('review_item')})
    return None, None, None


def save(path, state):
    state['updated'] = now()
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def task(step, reason, values):
    return {'station': step['id'], 'name': step['name'], 'executor': step.get('executor', 'agent'),
            'component': step['component'], 'instructions': step['does'], 'reason': reason,
            'skill': step.get('skill'), 'required_inputs': step.get('inputs', []),
            'expected_evidence': [W.fill(p, values) for p in step.get('evidence', [])],
            'gate': step.get('gate')}


def pause(path, state, step, reason, dry=False):
    state['next'] = task(step, reason, state['values'])
    state['state'] = 'waiting'
    if not dry:
        save(path, state)
        (path.parent / 'NEXT.md').write_text(
            '# ' + step['name'] + '\n\n' + step['does'] + '\n\n' + (reason or '') +
            '\n\nComponent: ' + step['component'] + '\n\n' +
            ('Read: ' + step['skill'] + '\n\n' if step.get('skill') else '') +
            'Return the actual evidence with workflow.py complete; review gates require the existing review records.\n')
    print(json.dumps(state['next'], indent=2, ensure_ascii=False))
    return 2


def advance(fmt, path, state, allowed=(), retry=None, dry=False):
    steps = W.workflow(fmt)['steps']
    # At most one attempt per station per invocation; component failures never spin.
    for _ in range(len(steps) + 1):
        step, signature, reason = next_step(fmt, state)
        if step is None:
            state['state'] = 'complete'
            state['next'] = None
            if not dry:
                save(path, state)
            print('Workflow complete')
            return 0
        executor = step.get('executor', 'agent')
        if executor != 'command':
            return pause(path, state, step, reason or 'Active assistant: perform this station and return its evidence.', dry)
        try:
            argv = command(step, state['values'])
        except ValueError as exc:
            return pause(path, state, step, str(exc), dry)
        attempt = state.get('attempts', {}).get(step['id'], {})
        if attempt.get('state') in ('running', 'failed') and retry != step['id']:
            return pause(path, state, step, 'Previous attempt failed or was interrupted. Inspect logs; adopt checked output with complete or explicitly --retry-station ' + step['id'], dry)
        if W.is_done(step, state['values']) is True:
            return pause(path, state, step, 'Existing output found. Verify it belongs to these inputs, then adopt with complete; it will not be regenerated.', dry)
        if (step.get('paid') or state['values'].get('route') in step.get('paid_routes', [])) and step['id'] not in allowed:
            return pause(path, state, step, 'Paid station: present cost and use authorized --allow-paid ' + step['id'], dry)
        if dry:
            return pause(path, state, step, 'Would run: ' + shlex.join(argv), True)
        log = path.parent / (step['id'] + '.log')
        state.setdefault('attempts', {})[step['id']] = {'state': 'running', 'started': now(),
                                                       'argv': [Path(argv[0]).name] + argv[1:],
                                                       'log': str(log.relative_to(W.WS))}
        save(path, state)
        print('Running ' + step['name'] + ' · ' + str(log.relative_to(W.WS)), flush=True)
        try:
            with log.open('a') as out:
                result = subprocess.run(argv, cwd=W.WS, stdout=out, stderr=subprocess.STDOUT)
            passed = result.returncode == 0 and W.is_done(step, state['values']) is True
            proof = snapshot(output_refs(step, state['values']), step, state['values']) if passed else None
        except (OSError, ValueError) as exc:
            passed, proof = False, None
            result = None
            with log.open('a') as out:
                out.write('\nRunner: ' + str(exc) + '\n')
        attempt = state['attempts'][step['id']]
        attempt.update(state='finished' if passed else 'failed', finished=now(),
                       exit_code=result.returncode if result else None)
        if not passed:
            return pause(path, state, step, 'Component failed or completion checks did not pass. Inspect ' + str(log.relative_to(W.WS)))
        state.setdefault('receipts', {})[step['id']] = {'inputs': signature, 'evidence': proof, 'at': now()}
        save(path, state)
    raise RuntimeError('workflow did not converge')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['run', 'complete'])
    ap.add_argument('format')
    ap.add_argument('--brand')
    ap.add_argument('--label')
    ap.add_argument('--brief-key')
    ap.add_argument('--from-state')
    ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--allow-paid', action='append', default=[])
    ap.add_argument('--retry-station')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--station')
    ap.add_argument('--evidence', action='append', default=[])
    ap.add_argument('--note', default='')
    a = ap.parse_args(argv)
    try:
        incoming = json.loads(local(a.from_state).read_text()) if a.from_state else {}
        if incoming.get('format', a.format) != a.format:
            raise ValueError('saved state belongs to another format')
        values = dict(incoming.get('values', {}))
        values.update({k: v for k, v in {'brand': a.brand, 'label': a.label, 'brief_key': a.brief_key}.items() if v})
        overrides = {}
        for text in a.set:
            k, sep, v = text.partition('=')
            if not sep or not re.fullmatch(r'\w+', k):
                raise ValueError('--set needs name=value')
            overrides[k] = v
        values.update(overrides)
        for k in ('brand', 'label'):
            if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', values.get(k, '')):
                raise ValueError('--' + k + ' needs a simple folder label')
        path = W.WS / 'runs/video-production' / values['brand'] / ('workflow-' + values['label']) / 'workflow-state.json'
        if not a.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
        lock = contextlib.nullcontext() if a.dry_run else (path.parent / '.lock').open('a')
        with lock as handle:
            if not a.dry_run:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            saved = json.loads(path.read_text()) if path.exists() else incoming
            if saved.get('format', a.format) != a.format:
                raise ValueError('workflow folder belongs to another format')
            merged = dict(saved.get('values', {}))
            merged.update(values)
            merged.setdefault('source_notes', str((path.parent / 'sources.md').relative_to(W.WS)))
            state = dict(saved, schema=1, format=a.format, values=merged)
            if a.action == 'complete':
                step, signature, reason = next_step(a.format, state)
                if step is None or a.station != step['id']:
                    raise ValueError('complete only the next station: ' + (step['id'] if step else 'none'))
                if step.get('executor') == 'review':
                    raise ValueError('a completion receipt cannot approve a human review; ' + (reason or 'use review records'))
                for key in step.get('inputs', []):
                    if not merged.get(key):
                        raise ValueError('missing input: ' + key)
                if step.get('executor') == 'command' and W.is_done(step, merged) is not True:
                    raise ValueError('component completion checks have not passed')
                import glob
                for pattern in step.get('evidence', []):
                    ref = W.fill(pattern, merged)
                    if '{' in ref or not any(Path(p).is_file() for p in glob.glob(str(W.WS / ref))):
                        raise ValueError('required station evidence is missing: ' + ref)
                expected = output_refs(step, merged)
                proof = snapshot(expected + a.evidence, step, merged)
                state.setdefault('receipts', {})[step['id']] = {'inputs': signature, 'evidence': proof,
                                                               'at': now(), 'note': a.note}
                if not a.dry_run:
                    save(path, state)
                print('Recorded ' + step['id'] + '; resume with run. Human approval was not inferred.')
                return 0
            return advance(a.format, path, state, a.allow_paid, a.retry_station, a.dry_run)
    except (ValueError, OSError) as exc:
        print('Workflow stopped: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
