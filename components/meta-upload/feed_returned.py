#!/usr/bin/env python3
"""File only completed current-revision submissions from both maker queues.

Uploads alone are work in progress. No settling timer or export count can mark
work complete. Uses Drive keys to retrieve the submitted files, then the shared
checklist gate and the existing approval filer. Never launches an ad.
"""
import argparse
import json
import sys
from pathlib import Path
import delivery_gate as G
D = G.D


def pull_submission(folder, svc):
    from gdrive_creator import engine as E
    state = D.read(folder / D.STATE)
    rid = state.get('revision_id')
    if not rid:
        return
    prefix = 'Shared Assets/' + folder.relative_to(D.REPO).as_posix()
    label = prefix + '/returned/' + rid
    parent = E.folder_by_path(label, svc=svc)
    if not parent:
        return
    files = E.list_files(parent, svc=svc)
    source = next((f for f in files if f['name'] == D.SUBMISSION), None)
    if not source:
        return
    dest = folder / 'returned' / rid / D.SUBMISSION
    dest.parent.mkdir(parents=True, exist_ok=True)
    E.get_media(source['id'], str(dest), svc=svc)
    sub = D.read(dest)
    # Read declared paths, never follow an absolute path or parent traversal.
    items = list(sub.get('items', [])) + [{'cover_record': rel} for rel in sub.get('production_records', [])]
    for item in items:
        for key in ('file', 'cover', 'cover_record'):
            rel = item.get(key)
            if not rel:
                continue
            target = (folder / rel).resolve()
            if folder.resolve() not in target.parents or Path(rel).is_absolute():
                raise D.Incomplete('Submission path escapes the handoff')
            expected = item.get('sha256' if key == 'file' else 'cover_sha256') if key != 'cover_record' else None
            if target.is_file() and expected and D.sha(target) == expected:
                continue
            fid = E.folder_by_path(prefix + '/' + Path(rel).parent.as_posix(), svc=svc)
            candidates = E.list_files(fid, svc=svc) if fid else []
            remote = next((x for x in candidates if x['name'] == Path(rel).name), None)
            if remote:
                target.parent.mkdir(parents=True, exist_ok=True)
                E.get_media(remote['id'], str(target), svc=svc)


def sweep(only=None, root=None, dry_run=False, pull=True):
    svc = None
    if pull and not dry_run:
        sys.path.insert(0, str(D.HERE.parent / 'gdrive-creator'))
        from gdrive_creator import engine as E
        svc = E.service()
    result = []
    for role in D.ROLES:
        for folder in sorted((D.REPO / 'runs/handoffs' / role).glob('*/*')):
            if not folder.is_dir() or (only and only not in folder.name):
                continue
            if not (folder / D.CONTRACT).exists():
                continue  # central filing gate still holds unissued maker work
            state = D.read(folder / D.STATE)
            if state.get('state') == 'ready-for-review':
                continue
            try:
                if svc:
                    pull_submission(folder, svc)
                p = D.submit(folder, dry_run=dry_run, root=root)
                result.append(folder.name + ': ' + p['state'])
                if not dry_run:
                    D.publish(folder)
            except Exception as e:
                result.append(folder.name + ': HELD — ' + str(e))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only')
    ap.add_argument('--root', type=Path)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-pull', action='store_true')
    args = ap.parse_args()
    print('\n'.join(sweep(args.only, args.root, args.dry_run, not args.no_pull)))


if __name__ == '__main__':
    main()
