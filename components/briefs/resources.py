"""Resource queues over existing creative assignments and the public dev board.

Read-only. Does not assign work, infer owners from builders, or dispatch it.
Public: development(root), project(queue, development_view, now=None).
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def development(root):
    """Cache the existing read-only board command across HTTP module reloads."""
    key = str(Path(root).resolve())
    cache = getattr(sys, '_brief_resource_dev_cache', {})
    sys._brief_resource_dev_cache = cache
    prior = cache.get(key)
    if prior and time.monotonic() - prior['loaded'] < 120:
        return prior['view']
    command = Path(root) / 'components/page-features/dev_queue.py'
    if not command.is_file():
        return {'error': 'Development queue source is not installed', 'cards': []}
    try:
        result = subprocess.run([sys.executable, str(command), '--root', key],
                                capture_output=True, text=True, timeout=30, check=True)
        view = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        view = dict(prior['view']) if prior else {'cards': []}
        view['error'] = 'Development queue refresh failed: ' + type(exc).__name__
    cache[key] = {'loaded': time.monotonic(), 'view': view}
    return view


def role_handoffs(root):
    """Use the existing task fold; manifests alone cannot prove current state."""
    root = Path(root)
    sys.path.insert(0, str(root / 'new-workflow-design/builds/pm-tool'))
    try:
        import role_tasks
        import mytasks
        tasks = []
        for task in mytasks.load_tasks(role_tasks.local_fetch(root)).values():
            if 'role-handoff' not in task.get('tags', []) or task.get('status') in ('done', 'dropped'):
                continue
            row = {k: task.get(k) for k in ('id', 'title', 'status', 'assignees', 'due', 'priority', 'created')}
            row['role'] = role_tasks.role_of(task)
            row['card'] = role_tasks.card_of(task)
            row['handoff'] = role_tasks.card_path(root, row['card']).read_text()
            tasks.append(row)
        return {'tasks': tasks, 'updated_at': datetime.now(timezone.utc).isoformat(), 'error': None}
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        return {'tasks': [], 'error': 'Role handoff source unavailable: ' + type(exc).__name__}


def project(queue, dev, now=None, role_view=None):
    """Each person's responsibilities; shared reviews are distinct from execution.

    Private dev cards stay off this shared view. Only explicit assignees and the
    dev board's pending reviewer records route work. Builder/owner is not assignment.
    """
    now = now or datetime.now(timezone.utc)
    rows = []
    def age(value):
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return round(max(0, (now-dt).total_seconds()/3600), 2)
        except (ValueError, TypeError):
            return None
    def add(identifier, title, source, person, relation, state, category, **fields):
        rows.append(dict(id=source + ':' + identifier + ':' + relation + ':' + str(person or ''),
                         work_id=identifier, title=title, source=source, person_id=person,
                         relation=relation, state=state, category=category, **fields))
    for group in ('items', 'backlog'):
        for row in queue.get(group, []):
            if row.get('stage') == 'live':
                continue
            w = row.get('workflow') or {}
            state = w.get('delivery_state') or row.get('stage') or 'unknown'
            category = ('backlog' if group == 'backlog' else 'revision' if state == 'back-for-revision'
                        else 'review' if state in ('ready-for-review', 'final-needs-you', 'brief-needs-you')
                        else 'active' if state in ('making', 'editing') else 'queued')
            add(row['id'], row.get('title') or row['id'], 'creative', w.get('person_id'), 'assigned',
                state, category, assigned_label=row.get('who'), elapsed_hours=w.get('queue_elapsed_hours'),
                created_at=w.get('queued_at'), priority=row.get('priority'), type=row.get('type'),
                revision_id=w.get('revision_id'), tokens=w.get('tokens'), source_path='runs/queue/')
    for card in dev.get('cards', []):
        if card.get('private'):
            continue
        state = card.get('state')
        column = card.get('column')
        common = dict(priority='urgent' if card.get('urgent') else None,
                      source_path=card.get('deck'), type='development')
        if state in ('up-next', 'in-progress'):
            pending = card.get('pending')
            category = 'blocked' if pending in ('held', 'waiting') else 'active' if state == 'in-progress' else 'queued'
            label = 'flagged' if column == 'flagged' else pending or card.get('progress') or state
            add(card['id'], card['title'], 'development', card.get('assignee'), 'assigned', label, category,
                created_at=card.get('carded_on'), elapsed_hours=age(card.get('carded_on')), **common)
        if state == 'shipped':
            for review in card.get('review') or []:
                if not review.get('understood'):
                    created = (card.get('merged') or {}).get('at')
                    add(card['id'], card['title'], 'development', review['person'], 'review',
                        'review-requested', 'review', created_at=created, elapsed_hours=age(created), **common)
    # Follow-ups already occur in issues; don't duplicate them from dev.acts.
    for item in dev.get('issues', []):
        if item.get('kind') not in ('issue', 'follow-up') or item.get('state') not in ('raised', 'discussing'):
            continue
        for person in item.get('assignees') or [None]:
            add(item['id'], item['title'], 'development', person, item['kind'], item['state'], 'queued',
                created_at=item.get('created'), elapsed_hours=age(item.get('created')),
                priority=item.get('priority'), type=item['kind'], source_path='platform/data/records/tasks/')
    role_view = role_view or {}
    for task in role_view.get('tasks', []):
        if task.get('status') in ('done', 'dropped'):
            continue
        category = {'in_progress': 'active', 'doing': 'active', 'in_review': 'review', 'blocked': 'blocked'}.get(task.get('status'), 'queued')
        for person in task.get('assignees') or [None]:
            # A role task appearing in another projection keeps one execution row.
            rows = [r for r in rows if not (r['work_id'] == task['id'] and r['person_id'] == person)]
            add(task['id'], task['title'], 'role-handoffs', person, 'assigned', task.get('status'), category,
                created_at=task.get('created'), elapsed_hours=age(task.get('created')), due=task.get('due'),
                priority='urgent' if task.get('priority') == 1 else 'high' if task.get('priority') == 2 else None,
                role=task.get('role'), handoff=task.get('handoff'), source_path=task.get('card'), type='workflow')
    people = {p['id']: dict(p) for p in queue.get('workforce', [])}
    # Keep unresolved assignment labels visible without making new user identities.
    for row in rows:
        if row['person_id'] not in people:
            row['unresolved_assignment'] = row.get('assigned_label') or row['person_id']
            row['person_id'] = None
    rank = {'revision': 0, 'active': 1, 'review': 2, 'queued': 3, 'blocked': 4, 'backlog': 5}
    rows.sort(key=lambda r: (r.get('priority') != 'urgent', rank.get(r['category'], 6), -(r.get('elapsed_hours') or 0), r['id']))
    resources = []
    for person in list(people.values()) + [{'id': None, 'name': 'Unassigned / unresolved', 'roles': []}]:
        assigned = [r for r in rows if r['person_id'] == person['id']]
        counts = {key: sum(r['category'] == key for r in assigned) for key in rank}
        resources.append({**person, 'queue': assigned, 'counts': counts, 'total': len(assigned)})
    return {'resources': resources, 'development_updated_at': dev.get('now'),
            'development_error': dev.get('error') or (dev.get('marks') or {}).get('error'),
            'development_warnings': (dev.get('sources') or {}).get('warnings', []),
            'role_handoffs_error': role_view.get('error'),
            'role_handoffs_updated_at': role_view.get('updated_at'),
            'coverage': 'Recorded role handoffs, creative assignments, development assignments, open issues/follow-ups and pending reviews. No personal sessions or inferred assignments.',
            'order': 'Urgent first, then revisions, active work, review, queued work, held work and backlog; oldest first within each group.',
            'sources': ['runs/role-handoffs/ + platform/data/records/tasks/', 'runs/queue/', 'components/page-features/dev_queue.py', 'team/people/<person>/identity.json']}
