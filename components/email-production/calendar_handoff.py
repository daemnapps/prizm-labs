"""Calendar metadata and deterministic handoff checks. No network, media or model calls.

Uses marketing-calendar's public review.py applied/load surface; keeps its edits/cuts authoritative.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re


class Held(ValueError):
    pass


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default


def segments(slot):
    edited=(slot.get('_review') or {}).get('edits') or {}
    if 'segment' in edited:
        return [slot['segment']] if slot.get('segment') else []
    values=slot.get('segments') or [slot.get('segment')]
    return list(dict.fromkeys(x for x in values if isinstance(x,str) and x.strip()))


def schedule(slot, fallback=None):
    """A calendar hour/local always wins; brand defaults are for unbound ad-hoc work only."""
    if 'hour' in slot:
        h=slot['hour']
        if isinstance(h,bool) or not isinstance(h,int) or not 0<=h<=23:
            raise Held('calendar hour must be an integer from 0 to 23')
        if not isinstance(slot.get('local'),bool):
            raise Held('calendar local must explicitly be true or false')
        return {'local':'%02d:00'%h,'recipient_time_zone':slot['local']}
    if slot.get('id') or slot.get('slot_id'):
        raise Held('calendar send has no hour; brand time cannot silently replace it')
    if fallback and fallback.get('local'):
        return dict(fallback)
    raise Held('no calendar schedule or explicit ad-hoc send time')


def snapshot(slot, brand, avatar=None):
    date=slot.get('date')
    try:
        datetime.date.fromisoformat(date or '')
    except (ValueError,TypeError):
        raise Held('calendar send has no valid ISO date')
    sch=schedule(slot)
    if not segments(slot):raise Held('calendar send has no audience')
    fields={k:slot.get(k) for k in ('id','date','hour','local','type','offer','product','angle','variants')}
    fields['segments']=segments(slot)
    return dict(version=1,brand=brand,source='runs/marketing-calendar/%s/%s/slots.json'%(brand,date[:7]),
        slot_id=slot.get('id'),fields=fields,avatar=avatar,
        fingerprint=hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest(),schedule=sch)


_REV=None
def month_slots(root,brand,month):
    global _REV
    home=Path(root)/'runs/marketing-calendar'/brand/month
    rows=read(home/'slots.json',[])
    if not isinstance(rows,list):raise Held('calendar slots are unreadable')
    if any(not isinstance(s,dict) or not s.get('id') for s in rows):raise Held('calendar slot identities are unreadable')
    review=read(home/'review.json',{})
    if not isinstance(review,dict):raise Held('calendar review is unreadable; not using the raw plan')
    review.setdefault('slots',{})
    review.setdefault('copy',{})
    if not isinstance(review['slots'],dict):raise Held('calendar review slots are unreadable')
    if not isinstance(review['copy'],dict) or any(not isinstance(v,dict) or not isinstance(v.get('edits') or {},dict) for v in review['slots'].values()):
        raise Held('calendar review entries are unreadable')
    if _REV is None:
        f=Path(__file__).resolve().parents[1]/'marketing-calendar/machine/review.py'
        spec=importlib.util.spec_from_file_location('_email_calendar_review',f)
        _REV=importlib.util.module_from_spec(spec);spec.loader.exec_module(_REV)
    return [s for s in _REV.applied(rows,review) if s.get('_review',{}).get('status')!='cut']


def resolve(root,brand,run_dir,state=None):
    """Bind by recorded identity/assignment, never by a potentially renumbered folder suffix."""
    state=read(Path(run_dir)/'run.json',{}) if state is None else state
    a=dict(state.get('assignment') or {});bound=state.get('calendar_handoff') or {}
    a['type']=a.get('type') or ((state.get('elements') or {}).get('format/email') or {}).get('id')
    date=a.get('send_date') or (bound.get('fields') or {}).get('date')
    if not date:return None
    try:datetime.date.fromisoformat(date)
    except (ValueError,TypeError):raise Held('recorded send date is not an ISO date')
    rows=[s for s in month_slots(root,brand,date[:7]) if s.get('channel','email')=='email']
    if bound.get('slot_id'):
        hits=[s for s in rows if s.get('id')==bound['slot_id']]
        if len(hits)==1:return hits[0]
        raise Held('recorded calendar send was cut or removed; do not substitute another slot')
    hits=[s for s in rows if s.get('date')==date]
    if not hits:raise Held('no reviewed calendar email on recorded send date '+date)
    if len(hits)>1:
        angle=a.get('angle');av=a.get('avatar')
        scored=[]
        for s in hits:
            angles=[s.get('angle')]+[v.get('angle') for v in s.get('variants') or [] if not av or v.get('avatar')==av]
            score=8*int(bool(angle) and angle in angles)+4*int(bool(a.get('type')) and a['type']==s.get('type'))
            score+=int(bool(a.get('offer')) and a['offer']==s.get('offer'))
            scored.append((score,s))
        best=max(x[0] for x in scored);hits=[s for score,s in scored if score==best]
        # An explicitly recorded source id can break a tie only with corroborating
        # date, angle and type evidence. It is never taken from the folder name.
        recorded=(state.get('source_reference') or '').split(':',1)[0]
        if len(hits)>1 and best>=12:
            named=[s for s in hits if s.get('id')==recorded]
            if len(named)==1:hits=named
    if len(hits)!=1:raise Held('calendar identity is ambiguous on '+date+'; no slot guessed')
    return hits[0]


OWNER=re.compile(r"\b(?:we\s+sold\s+you|you\s+(?:already\s+)?own\s+(?:our|this)\b|you\s+(?:already\s+)?(?:bought|ordered|purchased)\s+(?:our|this|it|the\s+(?:scrub|brush|tube|product|device))\b|(?:she|he)\s+(?:already\s+)?owns\s+(?:one|the|our|this)\b|the\s+(?:scrub|brush|tube|product)\s+(?:she|he|you)\s+(?:already\s+)?(?:bought|owns?|ordered))\b",re.I)
def audience_problems(slot,copy=None,job=None,avatar=None):
    """Catch explicit purchase/ownership assumptions for a lead audience, not general product language."""
    if not any(re.search(r'\bleads?\b',s,re.I) for s in segments(slot)):return []
    parts=[('calendar angle',slot.get('angle') or '')]
    parts += [('calendar angle',v.get('angle') or '') for v in slot.get('variants') or [] if not avatar or v.get('avatar')==avatar]
    if copy:
        parts += [('copy',str(copy.get('headline') or ''))]+[('copy',p) for p in copy.get('body') or [] if isinstance(p,str)]
        parts += [('subject',p.get('subject','')) for p in copy.get('subjects') or []]
    if job:parts.append(('design reader',str(job.get('reader') or '')))
    out=[]
    for source,text in parts:
        for m in OWNER.finditer(text):
            # Conditional education is valid for mixed readers; an asserted prior purchase is different.
            prefix=text[max(0,m.start()-60):m.start()]
            if re.search(r'\b(?:if|whether|unless)\b[^.!?\n]*$',prefix,re.I):continue
            message='audience mismatch: lead segment, but %s assumes an existing buyer: %s'%(source,m.group(0))
            if message not in out:out.append(message)
    return out


def inspect(root,brand,run_dir,slot=None,copy=None,state=None):
    state=read(Path(run_dir)/'run.json',{}) if state is None else state
    a=state.get('assignment') or {}
    try:
        slot=resolve(root,brand,run_dir,state) if slot is None else slot
        if slot is None:return {'state':'unbound','problems':[],'expected':None}
        expected=snapshot(slot,brand,a.get('avatar'))
    except (Held,ValueError,OSError,TypeError) as e:
        return {'state':'held','problems':['calendar handoff: '+str(e)],'expected':None}
    problems=audience_problems(slot,copy,avatar=a.get('avatar'))
    if a.get('send_date') and a['send_date']!=slot.get('date'):problems.append('calendar date changed since writing')
    if a.get('type') and a['type']!=slot.get('type'):problems.append('calendar type changed since writing')
    if (a.get('offer') or 'none')!=(slot.get('offer') or 'none'):
        bound=state.get('calendar_handoff') or {}
        if not (bound.get('effective_offer')==a.get('offer') and (bound.get('fields') or {}).get('offer')==slot.get('offer')):
            problems.append('calendar offer changed since writing')
    variants=slot.get('variants') or []
    v=next((v for v in variants if v.get('avatar')==a.get('avatar')),None)
    angle=(v or {}).get('angle') if variants else slot.get('angle')
    if a.get('angle') and angle and a['angle']!=angle:problems.append('calendar angle changed since writing')
    if a.get('avatar') and variants and v is None:problems.append('written avatar is not a current calendar version')
    if a.get('segments') and set(a['segments'])!=set(segments(slot)):problems.append('calendar audience changed since writing')
    return {'state':'held' if problems else 'ready','problems':problems,'expected':expected}


def protected(card):
    return bool(card.get('klaviyo') or card.get('scheduled') or card.get('approval') or card.get('status') in ('approved','scheduled'))


def metadata(root,brand,run_dir,spec,look,old=None):
    """Pure card metadata. Preserve released platform records and expose divergence as a hold."""
    old=old or {};copy=read(Path(run_dir)/'deliverable/email.json',{})
    audit=inspect(root,brand,run_dir,copy=copy)
    expected=audit['expected']; fields={}
    if expected:
        f=expected['fields'];fields=dict(date=f['date'],send_local=expected['schedule']['local'],
            recipient_time_zone=f['local'],segments=f['segments'],audience=', '.join(f['segments']))
        if set(spec.get('segments') or [])!=set(f['segments']):audit['problems'].append('design audience differs from the reviewed calendar')
        if protected(old):
            for key,value in fields.items():
                if key!='audience' and old.get(key)!=value:audit['problems'].append('released card differs from calendar: '+key+'; explicit platform reconciliation required')
            fields={k:old[k] for k in fields if k in old}
    elif audit['state']=='unbound':
        snd=schedule({},look.get('send') or {})
        fields=dict(date=spec.get('date'),send_local=snd['local'],recipient_time_zone=snd.get('recipient_time_zone'),
                    segments=spec.get('segments') or [],audience=', '.join(spec.get('segments') or []))
    else:
        fields={k:old[k] for k in ('date','send_local','recipient_time_zone','segments','audience') if k in old}
    audit['state']='held' if audit['problems'] else audit['state']
    fields['calendar_handoff']=audit
    return fields


def card_problems(root,brand,run_dir,card):
    audit=inspect(root,brand,run_dir,copy=read(Path(run_dir)/'deliverable/email.json',{}))
    probs=list(audit['problems']);expected=audit['expected']
    if expected:
        wanted=dict(date=expected['fields']['date'],send_local=expected['schedule']['local'],
                    recipient_time_zone=expected['fields']['local'],segments=expected['fields']['segments'])
        for k,v in wanted.items():
            if card.get(k)!=v:probs.append('calendar/card mismatch: '+k)
        if not protected(card):
            for other in (Path(root)/'runs/email-production'/brand).glob('*/klaviyo/card.json'):
                if other.parent.parent.resolve()==Path(run_dir).resolve():continue
                sibling=read(other,{})
                if not protected(sibling) or sibling.get('date')!=wanted['date']:continue
                try:slot=resolve(root,brand,other.parent.parent)
                except (Held,ValueError,OSError):continue
                if slot and slot.get('id')==expected['slot_id'] and set(sibling.get('segments') or []) & set(wanted['segments']):
                    probs.append('another version is already released for this calendar send/audience; reconcile the audience split before release')
                    break
    probs += (card.get('calendar_handoff') or {}).get('problems',[])
    return list(dict.fromkeys(probs))
