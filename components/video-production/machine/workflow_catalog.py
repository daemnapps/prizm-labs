"""Read execution recipes from the existing format families; never invent format IDs."""
import copy
import json
from pathlib import Path

import playbook as PB


def known_formats(workspace):
    paths = [Path(workspace) / 'components/video-production/formats/bank.json',
             Path(workspace) / 'components/elements/library/format.video.json']
    rows = {}
    for path in paths:
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        for row in data.get('formats', data.get('rows', [])):
            if isinstance(row, dict) and row.get('id') and row.get('status') != 'deprecated':
                rows[row['id']] = row
    for family in PB.families():
        rows.setdefault(family['format_id'], family)
        for variant in PB.live_variants(family):
            for value in [variant.get('id')] + (variant.get('format_ids') or []):
                if value:
                    rows.setdefault(value, variant)
    return rows


def person_stops(workflow):
    """The stations that stop a run for a person: under the owner's ruling, the quote alone."""
    return [{'id': s.get('id'), 'stops_for': s.get('stops_for') or s.get('gate')}
            for s in workflow.get('steps', []) if s.get('quote') or s.get('gate') or s.get('stops_for')]


def validate(workflow):
    """Validate the live definitions, not merely the runner's test fixtures.

    THE ONLY PERSON STOP IS THE QUOTE (owner, 2026-11-27, across all briefs): every review station is a decided
    station (the decision layer passes the exact version and files the call for the owner to overrule), a person stop
    is allowed only on a quote station (quote: true), and no paid station runs before a quote."""
    errors, seen, previous_outputs, quoted = [], set(), set(), False
    for step in workflow.get('steps', []):
        sid = step.get('id')
        if not sid or sid in seen:
            errors.append('Each station needs a unique id: %s' % sid)
        seen.add(sid)
        executor = step.get('executor')
        if executor not in ('agent', 'command', 'review', 'decided'):
            errors.append('%s: explicit executor required' % sid)
        if step.get('gate') and executor != 'review':
            errors.append('%s: named gate must be a separate review station' % sid)
        if (step.get('gate') or step.get('stops_for')) and not step.get('quote'):
            errors.append('%s: a person stop that is not the quote (the only stop is the quote; '
                          'make it a decided station)' % sid)
        if step.get('paid') and not quoted:
            errors.append('%s: a paid station needs the quote and the owner\'s go before it' % sid)
        if step.get('quote'):
            quoted = True
        outputs = set(step.get('evidence') or [])
        if step.get('done_when'):
            outputs.add(step['done_when'])
        if executor in ('review', 'decided'):
            asset = step.get('review_asset')
            if executor == 'review' and not step.get('gate'):
                errors.append('%s: review needs a named person and exact asset' % sid)
            if executor == 'decided' and not step.get('overrule'):
                errors.append('%s: a decided station names who may overrule it' % sid)
            if not asset or any(x in asset for x in '*?['):
                errors.append('%s: %s needs an exact asset' % (sid, executor))
            if asset not in previous_outputs:
                errors.append('%s: %s must follow authoring of its actual asset' % (sid, executor))
        else:
            if not outputs:
                errors.append('%s: concrete output evidence required' % sid)
            if executor == 'command' and not (step.get('run') or step.get('commands')):
                errors.append('%s: command missing' % sid)
        previous_outputs.update(outputs)
    if not seen:
        errors.append('Workflow has no stations')
    return errors


def resolve(fmt, workspace, production_route='ai'):
    if production_route not in ('ai', 'creator', 'founder'):
        raise ValueError('Choose production_route: ai, creator or founder')
    fid = PB.normalise_id(fmt)
    if not fid or fid not in known_formats(workspace):
        _fam, gone = PB.retired_variant(fid)
        if gone:
            raise ValueError('%s was retired (%s); run it as %s' % (
                fid, gone.get('state') or 'deprecated', gone.get('replaced_by') or 'an existing format'))
        raise ValueError('Choose an existing format; no format has been inferred: %r' % fmt)
    family = PB.playbook_for(fid)
    own = PB.own_file(fid)
    parent, _variant = PB.find_variant(fid) if not own else (None, None)
    source = own or parent or {}
    matches = [{'family': f['format_id'], 'variant': v}
               for f in PB.families() for v in PB.live_variants(f)
               if fid in [PB.normalise_id(x) for x in [v.get('id')] + (v.get('format_ids') or [])]]
    field = 'workflow' if production_route == 'ai' else 'creator_workflow'
    native = source.get(field)
    wf = native or PB.default_playbook().get(field)
    if not wf:
        raise ValueError('%s has no %s execution recipe' % (fid, production_route))
    errors = validate(wf)
    if errors:
        raise ValueError('; '.join(errors))
    return {
        'format_id': fid, 'production_route': production_route,
        'family': family.get('format_id'), 'family_resolution': family.get('_source'),
        'family_source': 'components/video-production/formats/playbooks/' + (source.get('format_id') or 'default') + '.json',
        'variant': copy.deepcopy(family.get('variant')),
        'variant_matches': matches,
        'selection_required': len(matches) > 1 or (bool(family.get('variant')) and family['variant'].get('status') != 'approved'),
        'selection_note': 'A stored draft variant match is provenance, not confirmation that this brief has that structure.' if family.get('variant') else '',
        'recipe_source': 'components/video-production/formats/playbooks/' + (source.get('format_id') if native else 'default') + '.json',
        'coverage': 'declared' if native else 'draft-reviewed-intake',
        'proven': False,  # execution coverage is not evidence of creative performance
        'person_stops': person_stops(wf),
        'decided': [s['id'] for s in wf['steps'] if s.get('executor') == 'decided'],
        'workflow': copy.deepcopy(wf),
    }


def line_of(fid):
    """'live' when the format resolves to a family of its own line that is not parked; else 'parked'
    (a parked family, or the shared chain alone, which no format has been proven on end to end)."""
    family = PB.playbook_for(fid)
    if family.get('_source') == 'default' or not family.get('format_id') or family.get('format_id') == 'default':
        return 'parked'
    own = PB.own_file(family['format_id'])
    return 'parked' if PB.parked(own) else 'live'


def inventory(workspace):
    rows = [{'format_id': fid, 'family': PB.playbook_for(fid).get('format_id'),
             'coverage': resolve(fid, workspace)['coverage'], 'line': line_of(fid)}
            for fid in sorted(known_formats(workspace))]
    return sorted(rows, key=lambda r: (r['line'] != 'live', r['format_id']))
