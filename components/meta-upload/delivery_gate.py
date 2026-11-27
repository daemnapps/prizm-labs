"""Approval seam for the public briefs.delivery_contract contract.

Both filing and owner approval fail closed for maker handoffs without a complete,
current submission. Receipts bind the reviewed checklist to the filed bytes.
"""
import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('briefs_delivery_contract_gate', HERE.parent / 'briefs/delivery_contract.py')
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
ROOT = D.REPO


def plan(card, media, thumbs):
    return D.gate(card['brand'], card.get('brief_id'), card.get('product'), media, thumbs, card.get('made_by'), repo=ROOT)


def receipt(result, folder, card):
    if result is None:
        return
    names = list(card['media']) + list((card.get('thumbs') or {}).values())
    card['delivery'] = {'schema': 'delivery-receipt/1', 'brief_key': result['requirements']['brief_key'],
                        'revision_id': result['state']['revision_id'], 'round': result['state']['round'],
                        'requirements_sha256': D.digest(result['requirements']),
                        'submission_sha256': result['submission_sha256'],
                        'checks': result['submission']['checks'],
                        'items': [{'slot_id': r['slot_id'], 'label': r['label'], 'creative_changes': r['creative_changes']} for r in result['rows']],
                        'file_sha256': {n: D.sha(folder / n) for n in names}}


def refresh_ledger():
    spec = importlib.util.spec_from_file_location("briefs_revision_ledger", HERE.parent / "briefs/ledger.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.refresh_delivery_states(ROOT)


def filed(result, card):
    if result is not None:
        f = result['folder']
        state = D.read(f / D.STATE)
        state.update(state='ready-for-review', updated_at=D.now(), card=card['ad_name'])
        D.write(f / D.STATE, state)
        D.pack(f)
        refresh_ledger()


def check(folder, card):
    handoff = D.find_handoff(card.get('brand'), card.get('brief_id'), card.get('product'), repo=ROOT)
    if handoff is None and (card.get('made_by') or {}).get('tool') not in D.ROLES and not card.get('delivery'):
        return {}
    try:
        if handoff is None:
            raise D.Incomplete('Cannot verify the issued maker checklist')
        result = D.validate(handoff)
        rec = card.get('delivery') or {}
        if rec.get('revision_id') != result['state']['revision_id'] or rec.get('requirements_sha256') != D.digest(result['requirements']) or rec.get('submission_sha256') != result['submission_sha256']:
            raise D.Incomplete('Card has no complete current-revision delivery receipt')
        names = list(card.get('media') or []) + list((card.get('thumbs') or {}).values())
        if set(rec.get('file_sha256', {})) != set(names):
            raise D.Incomplete('Card assets differ from the checked delivery')
        for n in names:
            if D.sha(Path(folder) / n) != rec['file_sha256'][n]:
                raise D.Incomplete('A filed asset changed after delivery checks: ' + n)
        return {'delivery_complete': {'ok': True, 'why': rec['revision_id'] + ' · every deliverable and criterion checked'}}
    except Exception as e:
        return {'delivery_complete': {'ok': False, 'why': str(e)}}


def revise(card, note, by, card_id):
    folder = D.find_handoff(card['brand'], card.get('brief_id'), card.get('product'), repo=ROOT)
    if folder is None:
        if (card.get('made_by') or {}).get('tool') in D.ROLES:
            raise D.Incomplete('Cannot send back: maker handoff is not available')
        return None
    req = D.request_revision(folder, note, by, 'card:' + card_id, card_id)
    # Publish through the existing Drive-key handoff surface before reporting sent.
    D.publish(folder)
    index_spec = importlib.util.spec_from_file_location("maker_handoff_index", HERE.parent / "image-edit/handoff_index.py")
    index = importlib.util.module_from_spec(index_spec)
    index_spec.loader.exec_module(index)
    index.refresh(repo=ROOT, drive=True)
    refresh_ledger()
    return req
