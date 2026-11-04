"""Evaluate a frozen local feedback set; never promote rules or edit assets."""
import ast
import hashlib
import json
from pathlib import Path

from engine import Refused
from pilot import REPO
from decision import classify, suggested_route, MAX_CALL_USD, LABELS


def load_cases(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    rows = data.get('cases', [])
    if not 1 <= len(rows) <= 100 or not data.get('label_status'):
        raise Refused('Need 1–100 cases with a labeling disclosure')
    ids = set()
    for row in rows:
        if not isinstance(row.get('id'), str) or row['id'] in ids:
            raise Refused('Unique case IDs required')
        ids.add(row['id'])
        if row.get('expected') not in LABELS:
            raise Refused('Unknown expected label')
        if not all(isinstance(row.get(k), str) and row[k].strip()
                   for k in ('feedback', 'context', 'source', 'label_basis')):
            raise Refused('Feedback, context and provenance required')
    return data, hashlib.sha256(raw).hexdigest()


def baseline_evidence():
    """Refuse a stale baseline if the observed unconditional add changes.

    Inspect AST only; importing the production approval server could load keys.
    This is policy replay, not a call to production redo().
    """
    path = REPO / 'tools/email-production/approve_klaviyo.py'
    tree = ast.parse(path.read_text())
    redo = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'redo')
    direct = [n.value for n in redo.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)]
    matching = [n for n in direct if isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == 'LN'
                and n.func.attr == 'add' and len(n.args) >= 4
                and isinstance(n.args[2], ast.Constant) and n.args[2].value == 'do'
                and ast.unparse(n.args[3]) == 'note.strip()']
    if len(matching) != 1:
        raise Refused('Existing redo policy changed; reassess the baseline')
    return dict(name='Existing email redo policy replay: every note becomes a standing rule',
                choice='reusable_rule', source=str(path.relative_to(REPO)),
                line=matching[0].lineno, source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                scope='Counterfactual replay on creator feedback, not historical email actions; send_back only logs notes.')


def compare(store, path, live=False, cap=1, caller=None, token=None):
    data, sha = load_cases(path)
    baseline = baseline_evidence()
    report_path = store.root / 'workflow-results.json'
    if report_path.exists():
        raise Refused('Comparison receipt already exists; keep it immutable and use a new explicitly chosen report before another paid run')
    if not live:
        return dict(status='not_run', cases=len(data['cases']), dataset_sha256=sha,
                    maximum_reserved_usd=len(data['cases'])*MAX_CALL_USD, baseline=baseline)
    if token is None:
        import sys
        sys.path.insert(0, str(REPO / 'components/keys'))
        from loader import key
        token = key('TYPESAFE_API_KEY')
    # Preflight the entire batch, then reserve each attempt transactionally.
    with store.connect() as db:
        used = db.execute('SELECT coalesce(sum(reserved),0) FROM calls').fetchone()[0]
    if used + len(data['cases'])*MAX_CALL_USD > cap:
        raise Refused('Insufficient remaining cumulative allowance for this comparison')
    rows = []
    for case in data['cases']:
        ident = store.reserve_call(cap, MAX_CALL_USD)
        # Expected labels, historical fixes and source files never enter the request.
        supplied = json.dumps({'context': case['context'], 'feedback': case['feedback']}, ensure_ascii=False)
        receipt = (caller or classify)(supplied, token)
        row = dict(receipt, **case, route=suggested_route(receipt),
                   correct=receipt['status']=='answered' and receipt['choice']==case['expected'],
                   baseline_choice='reusable_rule', baseline_correct=case['expected']=='reusable_rule')
        store.save_call(ident, row)
        rows.append(row)
        report_path.write_text(json.dumps(dict(status='incomplete', dataset_sha256=sha, results=rows), indent=2))
    routed = [r for r in rows if r['route']!='needs_review']
    baseline.update(correct=sum(r['baseline_correct'] for r in rows),
                    persistent_rules=len(rows),
                    unsupported_rule_candidates=sum(r['expected']!='reusable_rule' for r in rows),
                    model_api_usd=0)
    result = dict(status='completed', synthetic=False, name=data.get('name'),
                  label_status=data['label_status'], limitations=data.get('limitations', []),
                  dataset_sha256=sha, threshold=.85, policy=rows[0]['policy'], model=rows[0]['model'],
                  cases=len(rows), answered=sum(r['status']=='answered' for r in rows),
                  correct=sum(r['correct'] for r in rows), routed=len(routed),
                  routed_correct=sum(r['correct'] for r in routed),
                  unsupported_rule_candidates=sum(r['route']=='candidate_rule' and r['expected']!='reusable_rule' for r in rows),
                  baseline=baseline, known_estimated_usd=sum(r.get('estimated_usd') or 0 for r in rows),
                  reserved_this_run_usd=len(rows)*MAX_CALL_USD,
                  cumulative_reserved_usd=used+len(rows)*MAX_CALL_USD,
                  seconds=sum(r['seconds'] for r in rows), results=rows)
    report_path.write_text(json.dumps(result, indent=2))
    lines=['# Historical workflow feedback comparison', '', data['label_status'], '',
           f"Jev: {result['correct']}/{len(rows)} label matches; {result['routed_correct']}/{len(routed)} correct routing candidates.",
           f"Existing redo policy replay: {baseline['correct']}/{len(rows)} label matches, {baseline['unsupported_rule_candidates']} unsupported standing-rule candidates.",
           f"Estimated Jev usage: ${result['known_estimated_usd']:.8f}. Cumulative reserved allowance: ${result['cumulative_reserved_usd']:.6f}.",
           '', *['- '+x for x in result['limitations']], '',
           '| Case | Expected | Jev | Confidence | Route |', '|---|---|---|---|---|']
    lines += [f"| {r['id']} | {r['expected']} | {r['choice']} | {r.get('confidence', 'unavailable')} | {r['route']} |" for r in rows]
    (store.root/'WORKFLOW-COMPARISON.md').write_text('\n'.join(lines)+'\n')
    return result
