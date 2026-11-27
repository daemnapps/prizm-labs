#!/usr/bin/env python3
"""Read-only intake for writing runs; imports no production engine or provider."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}

def inspect_intake(run_dir, repo_root=None):
    run = Path(run_dir).resolve()
    source = run / 'stages' / '5-brief.md'
    record = read(run / 'run.json')
    # Human writing may file its accepted brief directly into deliverable/.
    # Keep AI's existing stage-5 source contract unchanged.
    if record.get('production_route') in ('creator', 'founder'):
        rel = ((record.get('stages') or {}).get('stage5') or {}).get('out')
        candidate = (run / rel).resolve() if rel else source
        if run in candidate.parents:
            source = candidate
    gaps = []
    def gap(code, detail):
        gaps.append({'code': code, 'detail': detail})
    source_text = source.read_text() if source.is_file() else ''
    doc, why = load(HERE / 'scenes.py', 'intake_scenes').json_block(source_text)
    has_doc = isinstance(doc, dict)
    doc = doc if has_doc else {}
    piece = doc.get('piece') or {}
    route = record.get('production_route') or piece.get('production_route') or doc.get('production_route')
    human = route in ('creator', 'founder')
    if not has_doc and not human:
        gap('brief_schema', why or 'Brief must contain a JSON object.')
    if route not in ('ai', 'creator', 'founder'):
        gap('production_route', 'Select ai, creator or founder; source route is separate.')
    fid = record.get('format_id') or piece.get('format') or piece.get('format_id')
    if not fid or fid in ('unknown', 'none', 'NEW'):
        gap('format', 'Select a banked format before production.')
        fid = None
    elif piece.get('format') not in (None, '', 'unknown', fid):
        gap('format_conflict', 'Run format and brief format disagree.')
    sha = hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None
    writing = load(HERE.parents[1] / 'video-writing' / 'machine' / 'writing_result.py', 'intake_writing_result').inspect_result(run)
    if not writing.get('accepted'):
        gap('writing_acceptance', 'Writing is %s; resolve its blockers without discarding the draft.' % writing.get('state', 'unverified'))
    checks = read(run / 'writing-resume-checks.json')
    if checks:
        if checks.get('source_sha256') != sha:
            gap('stale_checks', 'Saved local checks refer to a different brief version.')
        else:
            for name in (('spoken_findings',) if human else ('cast_findings', 'production_contract', 'spoken_findings')):
                findings = (checks.get('checks') or {}).get(name) or []
                if findings:
                    gap(name, '%d current finding(s); see writing-resume-checks.json.' % len(findings))
            if (checks.get('final_judge') or {}).get('status') == 'blocked' and not writing.get('accepted'):
                gap('review_provider', (checks.get('final_judge') or {}).get('error', 'Final review unavailable.'))
    scenes = doc.get('scenes') or []
    filming = None
    if human:
        # Public packet preview: stdlib only; never constructs Chain or consults AI banks.
        sheet = load(HERE.parents[1] / 'briefs' / 'runsheet.py', 'intake_filming_runsheet')
        final = run / 'deliverable' / '7-final-brief.md'
        brief_file = final if final.is_file() and final.read_text() == source_text else source
        key = record.get('brief_key') or record.get('brief_id') or record.get('brief') or run.name
        packet = sheet.filming_assignment(key, {**record, 'brand': record.get('brand') or 'unknown'},
                                          brief_file, source_text, route, Path(repo_root or HERE.parents[2]))
        takes = packet['takes']
        if not takes:
            gap('filming_instructions', 'No explicit filming instructions found; finish the human assignment upstream.')
        if any(type(t['expected_takes']) is not int or not 1 <= t['expected_takes'] <= 100 for t in takes):
            gap('expected_takes', 'Every filming asset needs an expected take count from 1 to 100.')
        filming = {'asset_count': len(takes), 'state': packet['state'],
                   'execution_ready': packet['execution_ready'], 'blockers': packet['readiness']['blockers'],
                   'validation_required': True}
        # Intake readiness means ready to BUILD the packet. Registration and the final
        # brief remain the handoff door's checks; a stage-5 draft is never certified for filming.
        scene_count = len(takes)
    else:
        if not scenes:
            gap('scenes', 'No scenes available.')
        ids = [s.get('id') for s in scenes if isinstance(s, dict)]
        if len(ids) != len(scenes) or None in ids or len(ids) != len(set(ids)):
            gap('scene_ids', 'Every scene needs a unique stable ID.')
        scene_count = len(scenes)
    for scene in scenes:
        if isinstance(scene, dict) and scene.get('held'):
            gap('held_scene', '%s: %s' % (scene.get('id'), scene['held']))
    cast = doc.get('cast') or []
    unresolved = [c.get('id') or c.get('name') for c in cast if isinstance(c, dict) and c.get('bank_id') in (None, '', 'NEW', 'new')]
    if route == 'ai' and unresolved:
        gap('cast_assignment', 'Resolve cast references: ' + ', '.join(str(x) for x in unresolved))
    style = piece.get('style_id')
    if route == 'ai' and (not style or str(style).startswith('new:')):
        gap('style_definition', 'Resolve the proposed style before generation.')
    if gaps:
        kind, detail = 'resolve_intake', gaps[0]['detail']
    elif route in ('creator', 'founder'):
        kind, detail = 'filming_assignment', 'Validate and build the final filming packet with an expected-take return manifest; intake is not filming approval.'
    else:
        kind, detail = 'workflow_preview', 'Preview the selected production workflow.'
    result = {'schema_version': 1, 'run_id': record.get('slug') or run.name,
            'source': {'path': str(source.relative_to(run)), 'sha256': sha}, 'route': route, 'format': fid,
            'style': style, 'scene_count': scene_count,
            'identity': {'candidate': record.get('brief_id') or record.get('brief'), 'verified': False},
            'writing': writing, 'gaps': gaps, 'ready': not gaps,
            'next_action': {'kind': kind, 'detail': detail}}
    if filming is not None:
        result['filming_packet'] = filming
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir'); parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    result = inspect_intake(args.run_dir)
    print(json.dumps(result, indent=2) if args.json else '\n'.join([
        '%s · %s · %s' % (result['run_id'], result['route'], 'ready for next step' if result['ready'] else 'draft / held'),
        *['- %s: %s' % (g['code'], g['detail']) for g in result['gaps']],
        'Next: ' + result['next_action']['detail']]))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
