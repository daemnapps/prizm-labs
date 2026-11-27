"""Explicit owner controls for one writing run; generated output cannot set these.

Optional owner-controls.json: schema=1, authority=owner-instruction, decision_date,
constraints={dial: {level, source, quote}}. Sources are the run's own RULINGS.md,
story.md or owner-script.md. Defaults and other shared floors remain unchanged.
"""
import json
from datetime import date
from pathlib import Path


class InvalidOwnerControls(ValueError):
    pass


def load(run_dir):
    root = Path(run_dir).resolve()
    path = root / 'owner-controls.json'
    if not path.exists():
        if path.is_symlink():
            raise InvalidOwnerControls('owner-controls.json is a broken source link')
        return {}
    try:
        path.resolve().relative_to(root)
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise InvalidOwnerControls('owner-controls.json must be readable inside its own run')
    if not isinstance(data, dict) or data.get('schema') != 1 or data.get('authority') != 'owner-instruction':
        raise InvalidOwnerControls('owner-controls.json requires schema 1 and explicit owner-instruction authority')
    try:
        date.fromisoformat(data['decision_date'])
    except (KeyError, ValueError, TypeError):
        raise InvalidOwnerControls('owner-controls.json needs the owner decision_date (YYYY-MM-DD)')
    constraints = data.get('constraints')
    if not isinstance(constraints, dict) or not constraints:
        raise InvalidOwnerControls('owner-controls.json needs explicit dial constraints')
    # Same public control definitions as the hook check, never a second scale.
    import hook_matrix
    scales = {d['id']: {s['level'] for s in d['scale']} for d in hook_matrix.controls().dials('video')}
    result = {}
    for dial, rule in constraints.items():
        if dial not in scales or not isinstance(rule, dict):
            raise InvalidOwnerControls('Unknown owner control: %s' % dial)
        if type(rule.get('level')) is not int or rule['level'] not in scales[dial]:
            raise InvalidOwnerControls('Invalid owner control level: %s' % dial)
        source, quote = rule.get('source'), rule.get('quote')
        if source not in ('RULINGS.md', 'story.md', 'owner-script.md'):
            raise InvalidOwnerControls('Owner source must be the run RULINGS.md, story.md or owner-script.md')
        if not isinstance(quote, str) or not quote.strip():
            raise InvalidOwnerControls('Owner control needs an exact source quote: %s' % dial)
        file = root / source
        try:
            file.resolve().relative_to(root)
            text = file.read_text(encoding='utf-8')
        except (OSError, ValueError):
            raise InvalidOwnerControls('Owner control source is missing or escapes the run: %s' % source)
        if quote not in text:
            raise InvalidOwnerControls('Owner control quote is absent from %s: %s' % (source, dial))
        result[dial] = dict(level=rule['level'], source=source, quote=quote,
                            decision_date=data['decision_date'])
    return result


def block(run_dir):
    constraints = load(run_dir)
    if not constraints:
        return ''
    lines = ['## Explicit owner controls for this run',
             'Use these exact levels for the delivered control and every reference alternative. '
             'Only these named dials replace their shared targets and floors; every other check still applies.']
    for dial, rule in sorted(constraints.items()):
        lines.append('- %s = %s. Owner instruction %s, %s: %s' %
                     (dial, rule['level'], rule['decision_date'], rule['source'], json.dumps(rule['quote'], ensure_ascii=False)))
    return '\n'.join(lines) + '\n\n'
