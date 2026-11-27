"""Source-bound resume receipts. Existing unbound assets are retained and held, never silently regenerated."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def brief_doc(run, source=None):
    reference = source or read(run / 'run.json').get('brief_from')
    if reference:
        path = Path(reference)
        if not path.is_absolute():
            path = run / path if (run / path).is_file() else HERE.parents[2] / path
        if path.is_file():
            if path.suffix == '.json':
                return read(path)
            spec = importlib.util.spec_from_file_location('cache_scenes', HERE / 'scenes.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            doc, _ = module.json_block(path.read_text())
            if isinstance(doc, dict):
                return doc
            # Older prose briefs invalidate conservatively on any edit.
            return {'legacy_text': path.read_text()}
    return read(run / 'plan.json')

def input_hashes(doc, config=None):
    voice_fields = ('id', 'voice', 'say', 'speaker', 'who', 'delivery', 'voice_settings', 'lyrics', 'delivery_tag', 'lines')
    voice = {'scenes': [{k: row[k] for k in voice_fields if k in row} for row in doc.get('scenes', [])],
             'cast': [{k: c[k] for k in ('id', 'name', 'bank_id', 'voice') if k in c} for c in doc.get('cast', [])] if isinstance(doc.get('cast'), list) else doc.get('cast'),
             'song': doc.get('song'), 'voiceprint': (doc.get('piece') or {}).get('voiceprint'), 'legacy_text': doc.get('legacy_text'), 'config': config or {}}
    # Shot-level dialogue also affects the voice, but camera-only changes do not.
    voice['shot_lines'] = [[{k: shot[k] for k in ('id', 'voice', 'say', 'speaker', 'delivery', 'delivery_tag', 'lines') if k in shot}
                            for shot in row.get('shots', []) if isinstance(shot, dict)] for row in doc.get('scenes', [])]
    return {'voice': digest(voice), 'storyboard': digest({'brief': doc, 'config': config or {}})}

def outputs(run, stage):
    if stage == 'voice':
        paths = [run / 'vo' / 'timing.json', run / 'vo' / 'audio-check.json']
        paths += sorted(p for p in (run / 'vo').rglob('*') if p.suffix.lower() in ('.wav', '.mp3', '.m4a'))
    else:
        paths = [run / 'storyboard.json', run / 'vo' / 'timing.json']
    return {str(p.relative_to(run)): file_hash(p) for p in paths if p.is_file()}

def state(run, stage, source=None, config=None):
    run = Path(run)
    primary = run / ('vo/timing.json' if stage == 'voice' else 'storyboard.json')
    if not primary.is_file():
        return 'missing'
    receipt = read(run / 'cache-receipts.json').get(stage) or {}
    if not receipt:
        return 'unbound'
    if receipt.get('input_sha256') != input_hashes(brief_doc(run, source), {**(config or {}), 'voiceprint': file_hash(run / 'voiceprint.json')})[stage]:
        return 'stale_inputs'
    if receipt.get('outputs') != outputs(run, stage):
        return 'changed_outputs'
    return 'current'

def seal(run, stage, source=None, config=None):
    run = Path(run)
    receipts = read(run / 'cache-receipts.json')
    receipts[stage] = {'input_sha256': input_hashes(brief_doc(run, source), {**(config or {}), 'voiceprint': file_hash(run / 'voiceprint.json')})[stage], 'outputs': outputs(run, stage)}
    (run / 'cache-receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')

def machine_config():
    """The config every seal is made against (run_v2's `_cache_config`): the provider and v2 settings files."""
    return {name: file_hash(HERE / name) for name in ('providers.json', 'v2.json')}


def written(run, stage, source=None):
    """A step that WRITES a stage's output seals it again (2026-11-21, brief-0380: the lane re-ran the storyboard
    after it was sealed, never re-sealed, and the next run stopped on "storyboard cache is changed_outputs"). Never
    raises: a run with no brief to read is left unsealed, as before."""
    try:
        seal(run, stage, source, machine_config())
        return True
    except Exception:  # noqa: BLE001
        return False


def require_current(run, stage, source=None, config=None):
    result = state(run, stage, source, config)
    if result not in ('missing', 'current'):
        raise ValueError('%s cache is %s; retain assets and revalidate or rebuild only this stage and its dependents' % (stage, result))
    return result


def revalidate(run, stage, reason, source=None, config=None):
    """The revalidate path require_current names: a stage whose outputs are exactly the ones its receipt sealed is
    sealed again against today's inputs, with the reason kept on the receipt. Refused when its outputs changed (those
    are rebuilt, never re-blessed) or when there is no receipt. Nothing is regenerated."""
    run = Path(run)
    receipts = read(run / 'cache-receipts.json')
    old = receipts.get(stage) or {}
    if not old:
        raise ValueError('%s has no receipt to revalidate' % stage)
    if old.get('outputs') != outputs(run, stage):
        raise ValueError('%s outputs changed since they were sealed; rebuild the stage' % stage)
    seal(run, stage, source, config)
    receipts = read(run / 'cache-receipts.json')
    receipts[stage]['revalidated'] = {'reason': str(reason), 'was': old.get('input_sha256')}
    (run / 'cache-receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
    return receipts[stage]


CONFIG_FILES = ('providers.json', 'v2.json')     # run_v2._cache_config hashes these, beside this file


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='revalidate a stage whose outputs are unchanged: '
                                 'python3 cache_contract.py revalidate <run> <voice|storyboard> --reason "..."')
    ap.add_argument('cmd', choices=['revalidate', 'state'])
    ap.add_argument('run'); ap.add_argument('stage', choices=['voice', 'storyboard'])
    ap.add_argument('--reason', default='')
    a = ap.parse_args()
    cfg = {name: file_hash(HERE / name) for name in CONFIG_FILES}
    if a.cmd == 'state':
        print(state(a.run, a.stage, None, cfg))
    else:
        if not a.reason:
            raise SystemExit('--reason is required: say what changed and why the outputs still stand')
        print(json.dumps(revalidate(a.run, a.stage, a.reason, None, cfg), indent=1))
