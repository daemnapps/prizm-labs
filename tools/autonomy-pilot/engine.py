"""Durable local pilot. Role-bound reviews and idempotent local handoffs.

Single-machine trusted-user tool, not a multi-user authentication boundary.
No publishing, arbitrary shell commands, shared Drive or external messaging.
"""
import hashlib
import json
import sqlite3
import threading
import uuid
from pathlib import Path
from contextlib import contextmanager

LANES = {'creator': ['script', 'finished_asset'], 'video': ['script', 'storyboard', 'image_draft', 'finished_asset'],
         'image': ['image_draft', 'finished_asset'],
         'email': ['email_draft', 'image_draft', 'finished_asset']}
MODES = ('observe', 'prepare', 'handoff')
MAX_BYTES = 20_000_000


class Refused(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'pilot.db'
        self.worker_lock = threading.RLock()
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, job TEXT, action TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, job TEXT, data TEXT, status TEXT);
            CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY, reserved REAL, receipt TEXT);''')

    def connect(self):
        db = sqlite3.connect(str(self.db), timeout=10, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, lane, mode='observe', integration=None, input_hash=None):
        if lane not in LANES or mode not in MODES:
            raise Refused('Unknown lane or autonomy level')
        if integration not in (None, 'creator-brief') or (integration and (lane != 'creator' or not isinstance(input_hash, str) or len(input_hash) != 64 or any(c not in '0123456789abcdef' for c in input_hash))):
            raise Refused('Invalid integration or input fingerprint')
        job = dict(integration=integration, input_hash=input_hash, id=uuid.uuid4().hex, lane=lane, mode=mode, index=0, revision=1,
                   state='awaiting_draft', stages={}, handoff=None, history=[])
        with self.transaction() as db:
            db.execute('INSERT INTO jobs VALUES (?,?)', (job['id'], json.dumps(job)))
        return job

    def jobs(self):
        with self.connect() as db:
            return [json.loads(row['data']) for row in db.execute('SELECT data FROM jobs ORDER BY rowid DESC')]

    def get(self, ident, db=None):
        if db is None:
            with self.connect() as conn:
                return self.get(ident, conn)
        row = db.execute('SELECT data FROM jobs WHERE id=?', (ident,)).fetchone()
        if not row:
            raise Refused('Unknown job')
        return json.loads(row['data'])

    def current(self, job):
        return LANES[job['lane']][min(job['index'], len(LANES[job['lane']]) - 1)]

    def blob(self, job, path):
        source = Path(path).resolve()
        if not source.is_file() or source.stat().st_size > MAX_BYTES:
            raise Refused('Artifact missing or exceeds pilot size limit')
        data = source.read_bytes()
        if not data:
            raise Refused('Empty artifact')
        # Content-addressed snapshots, independent of source filenames.
        sha = digest(data)
        target = self.root / 'blobs' / sha
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(data)
        return dict(sha=sha, file=str(target.relative_to(self.root)), size=len(data),
                    suffix=source.suffix.lower(), revision=job['revision'])

    def verify(self, artifact):
        path = self.root / 'blobs' / artifact['sha']
        if not path.is_file() or digest(path.read_bytes()) != artifact['sha']:
            raise Refused('Artifact changed or missing; submit again before approval')

    def change(self, ident, action, payload, event_id, actor='worker'):
        if actor not in ('worker', 'reviewer', 'operator'):
            raise Refused('Unknown actor')
        if not isinstance(event_id, str) or not event_id or len(event_id) > 200:
            raise Refused('Event ID required')
        signature = json.dumps({'actor': actor, 'payload': payload}, sort_keys=True)
        with self.transaction() as db:
            previous = db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
            if previous:
                if (previous['job'], previous['action'], previous['payload']) != (ident, action, signature):
                    raise Refused('Event ID reused with different input')
                return self.get(ident, db)
            job = self.get(ident, db)
            stage = self.current(job)
            if action == 'submit':
                if actor != 'worker' or job['state'] != 'awaiting_draft' or stage == 'finished_asset':
                    raise Refused('Stage is not accepting a draft')
                if payload.get('revision') != job['revision'] or payload.get('stage') != stage:
                    raise Refused('Draft was generated for an older stage or revision')
                job.pop('worker_error', None)
                job['stages'][stage] = self.blob(job, payload['path'])
                job['state'] = 'needs_review'
            elif action == 'approve':
                if actor != 'reviewer' or job['state'] != 'needs_review':
                    raise Refused('Only a reviewer can approve a waiting artifact')
                artifact = job['stages'][stage]
                self.verify(artifact)
                if payload.get('sha') != artifact['sha'] or payload.get('revision') != job['revision']:
                    raise Refused('Stale review; reload the current artifact')
                for earlier in LANES[job['lane']][:job['index']]:
                    prior = job['stages'].get(earlier, {})
                    if not prior.get('approved'):
                        raise Refused('Upstream approval missing')
                    self.verify(prior)
                artifact['approved'] = True
                job['index'] += 1
                if stage == 'finished_asset':
                    job['state'] = 'ready_for_distribution'
                elif self.current(job) == 'finished_asset':
                    job['state'] = 'ready_for_handoff'
                else:
                    job['state'] = 'awaiting_draft'
            elif action in ('reject', 'revise'):
                if actor != 'reviewer':
                    raise Refused('Revision requires a reviewer')
                if not isinstance(payload.get('note'), str) or not payload['note'].strip():
                    raise Refused('Revision note required')
                chosen = payload.get('stage', stage)
                if chosen not in LANES[job['lane']] or chosen not in job['stages']:
                    raise Refused('No submitted artifact for that stage')
                artifact = job['stages'][chosen]
                if payload.get('sha') != artifact['sha'] or payload.get('revision') != job['revision']:
                    raise Refused('Stale revision request')
                point = LANES[job['lane']].index(chosen)
                job['stages'] = {s: a for s, a in job['stages'].items() if LANES[job['lane']].index(s) < point}
                job['index'], job['revision'] = point, job['revision'] + 1
                job['state'] = 'ready_for_handoff' if chosen == 'finished_asset' else 'awaiting_draft'
                if job['handoff']:
                    db.execute('UPDATE outbox SET status=? WHERE id=?', ('superseded', job['handoff']))
                job['handoff'] = None
                job['revision_note'] = payload['note']
            elif action == 'handoff':
                if actor != 'worker' or job['mode'] != 'handoff' or job['state'] != 'ready_for_handoff':
                    raise Refused('Automatic handoff is not enabled or drafts are unapproved')
                required = LANES[job['lane']][:-1]
                for name in required:
                    a = job['stages'].get(name, {})
                    if not a.get('approved'):
                        raise Refused('Draft approval missing')
                    self.verify(a)
                handoff_id = ident + '-r' + str(job['revision'])
                package = dict(id=handoff_id, job=ident, revision=job['revision'], lane=job['lane'],
                               role='creator' if job['lane'] == 'creator' else ('video-editor' if job['lane'] == 'video' else 'production-operator'),
                               artifacts=job['stages'], expected='finished_asset', status='local_only')
                db.execute('INSERT INTO outbox VALUES (?,?,?,?)', (handoff_id, ident, json.dumps(package), 'pending'))
                job['handoff'], job['state'] = handoff_id, 'awaiting_return'
            elif action == 'return':
                if actor != 'operator' or job['state'] != 'awaiting_return' or payload.get('handoff') != job['handoff']:
                    raise Refused('Return does not match an active handoff')
                artifact = self.blob(job, payload['path'])
                allowed = {'creator': {'.mp4', '.mov'}, 'video': {'.mp4', '.mov'}, 'image': {'.png', '.jpg', '.jpeg', '.webp'},
                           'email': {'.html', '.eml'}}[job['lane']]
                if artifact['suffix'] not in allowed:
                    raise Refused('Wrong returned file type for this lane')
                # Actual media rendering/quality remains a lane-adapter check + human review.
                job['stages']['finished_asset'] = artifact
                job['state'] = 'needs_review'
                db.execute('UPDATE outbox SET status=? WHERE id=?', ('received', job['handoff']))
            else:
                raise Refused('Unknown event')
            job['history'].append(dict(action=action, actor=actor, stage=stage, event=event_id))
            db.execute('UPDATE jobs SET data=? WHERE id=?', (json.dumps(job), ident))
            db.execute('INSERT INTO events VALUES (?,?,?,?)', (event_id, ident, action, signature))
            return job

    def tick(self, handlers):
        with self.worker_lock:
            return self._tick(handlers)

    def _tick(self, handlers):
        """Call explicitly registered local adapters. One step per job, no shell.

        Run one worker per pilot store. Adapter should be idempotent by job/revision/stage.
        If adapter fails, leave the stage pending for inspection; no silent paid retry.
        """
        results = []
        for job in self.jobs():
            stage = self.current(job)
            if job['mode'] in ('prepare', 'handoff') and job['state'] == 'awaiting_draft':
                handler = handlers.get((job['lane'], stage))
                if handler:
                    try:
                        path = handler(job)
                    except Refused as exc:
                        with self.transaction() as db:
                            held = self.get(job['id'], db)
                            held['worker_error'] = str(exc)
                            db.execute('UPDATE jobs SET data=? WHERE id=?', (json.dumps(held), job['id']))
                        continue
                    if path is None:
                        continue
                    results.append(self.change(job['id'], 'submit', {'path': str(path), 'revision': job['revision'], 'stage': stage},
                        'submit-' + job['id'] + '-' + str(job['revision']) + '-' + stage))
            elif job['mode'] == 'handoff' and job['state'] == 'ready_for_handoff':
                results.append(self.change(job['id'], 'handoff', {},
                    'handoff-' + job['id'] + '-' + str(job['revision'])))
        self.export_outbox()
        return results

    def export_outbox(self):
        """Rebuild local delivery packages from committed DB rows after a crash."""
        with self.connect() as db:
            for row in db.execute('SELECT * FROM outbox'):
                folder = self.root / 'outbox' / row['id']
                folder.mkdir(parents=True, exist_ok=True)
                value = json.loads(row['data'])
                value['status'] = row['status']
                # Resolved media bytes travel only within this local output tree.
                media = folder / 'artifacts'
                media.mkdir(exist_ok=True)
                for name, artifact in value['artifacts'].items():
                    self.verify(artifact)
                    target = media / (name + artifact['suffix'])
                    target.write_bytes((self.root / artifact['file']).read_bytes())
                    artifact['package_file'] = str(target.relative_to(folder))
                tmp = folder / 'manifest.tmp'
                tmp.write_text(json.dumps(value, indent=2))
                tmp.replace(folder / 'manifest.json')

    def reserve_call(self, cap, amount):
        if not 0 < cap <= 1 or not 0 < amount <= cap:
            raise Refused('Pilot API cap must be between one call reserve and $1')
        with self.transaction() as db:
            used = db.execute('SELECT coalesce(sum(reserved),0) FROM calls').fetchone()[0]
            if used + amount > cap + 1e-12:
                raise Refused('API budget exhausted; all attempts remain reserved')
            ident = uuid.uuid4().hex
            db.execute('INSERT INTO calls VALUES (?,?,NULL)', (ident, amount))
        return ident

    def save_call(self, ident, receipt):
        with self.connect() as db:
            db.execute('UPDATE calls SET receipt=? WHERE id=?', (json.dumps(receipt), ident))
