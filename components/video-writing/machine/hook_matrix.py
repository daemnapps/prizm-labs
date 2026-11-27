"""Check per-opening use of the shared creative controls and format contract.

These are planned scores, not measured audience performance. Visual truth still
requires inspection of the generated frames and clips.
"""
import importlib.util
import json
import re
from pathlib import Path


def controls():
    path = Path(__file__).resolve().parents[2] / 'creative-controls/creative_controls.py'
    spec = importlib.util.spec_from_file_location('hook_creative_controls', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(matrix, brand=None, preset='maxed', constraints=None):
    """`preset` is the run's own (writing_v2.controls_preset: chosen by its awareness level since 2026-11-18),
    so the openings are held to the same targets the pass was handed; the house preset when none is named."""
    if not isinstance(matrix, dict):
        return ['hook-matrix must be an object']
    cc = controls()
    if (preset or 'maxed') == 'maxed' and matrix.get('controls_preset'):
        preset = matrix['controls_preset']    # a filed matrix names the preset it was written to; a reader passes none
    _, targets = cc.target(preset or 'maxed', brand, 'video')
    scales = {d['id']: {s['level'] for s in d['scale']} for d in cc.dials('video')}
    floor = cc.load().get('floor', {}).get('levels', {})
    conditional = set(cc.load().get('floor', {}).get('when_set', []))
    constraints = constraints or {}
    if not isinstance(constraints, dict):
        return ['explicit owner controls must be a validated mapping']
    errors = []
    for dial, rule in constraints.items():
        if dial not in scales or not isinstance(rule, dict) or type(rule.get('level')) is not int or rule['level'] not in scales[dial]:
            errors.append('invalid explicit owner control: %s' % dial)
    if errors:
        return errors
    contract = matrix.get('format_contract') or {}
    if not isinstance(contract, dict):
        return ['format_contract must be an object']
    if not contract or any(not str(v).strip() for v in contract.values()):
        errors.append('format_contract must name the indispensable visual facts')
    rows = matrix.get('openings') or []
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        return ['openings must be an array of objects']
    if [r.get('id') for r in rows] != ['V%d' % n for n in range(6)]:
        errors.append('six ordered openings V0 through V5 are required')
    for row in rows:
        label = row.get('id', '?')
        for field in ('line', 'scroll', 'thumb', 'watch_payoff', 'body_join'):
            if not str(row.get(field) or '').strip():
                errors.append('%s: missing %s' % (label, field))
        evidence = row.get('format_evidence') or {}
        if not isinstance(evidence, dict):
            errors.append('%s: format_evidence must be an object' % label)
            evidence = {}
        for key in contract:
            if not str(evidence.get(key) or '').strip():
                errors.append('%s: missing format evidence for %s' % (label, key))
        scores = row.get('controls') or {}
        if not isinstance(scores, dict):
            errors.append('%s: controls must be an object' % label)
            scores = {}
        for key in scores.keys() - targets.keys():
            errors.append('%s: unknown video dial %s' % (label, key))
        for key, target in targets.items():
            score = scores.get(key) or {}
            if not isinstance(score, dict):
                errors.append('%s: %s must be an object' % (label, key))
                continue
            if key in conditional and key not in constraints and str(score.get('not_applicable') or '').strip():
                continue
            level = score.get('level')
            if type(level) is not int or level not in scales[key]:
                errors.append('%s: missing or invalid %s level' % (label, key))
                continue
            if not str(score.get('evidence') or '').strip():
                errors.append('%s: %s needs visible or audible evidence' % (label, key))
            if key in constraints:
                required = constraints[key]['level']
                if level != required:
                    errors.append('%s: %s must equal explicit owner level %s' % (label, key, required))
                continue
            if label == 'V0':  # preserve the approved control; report its gaps
                continue
            if level != target and not str(score.get('exception') or '').strip():
                errors.append('%s: %s differs from shared target %s without a reason' % (label, key, target))
            if key in floor and level < floor[key]:
                errors.append('%s: %s is below the shared floor' % (label, key))
    return errors


def from_text(text, brand=None, preset='maxed', constraints=None):
    blocks = re.findall(r'```hook-matrix\s*\n(.*?)\n```', text, re.S)
    if len(blocks) != 1:
        return None, ['one hook-matrix JSON block is required']
    try:
        matrix = json.loads(blocks[0])
    except ValueError:
        return None, ['hook-matrix JSON is invalid']
    if not isinstance(matrix, dict):
        return None, ['hook-matrix must be an object']
    errors = check(matrix, brand, preset, constraints=constraints)
    if not isinstance(matrix.get('openings'), list) or any(not isinstance(r, dict) for r in matrix['openings']):
        return matrix, errors
    for row in matrix.get('openings') or []:
        for prefix, field in [('LINE', 'line'), ('SCROLL', 'scroll'), ('THUMB', 'thumb')]:
            match = re.search(r'^%s %s:\s*(.+)$' % (prefix, re.escape(str(row.get('id')))), text, re.M)
            if not match or match.group(1).strip() != str(row.get(field, '')).strip():
                errors.append('%s: %s differs between prose and matrix' % (row.get('id'), field))
    return matrix, errors
