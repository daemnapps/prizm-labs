"""Audit/reconcile local calendar metadata and list actual copy-review readiness. Never renders or calls a provider.

python3 reconcile_calendar.py --brand <brand> --month YYYY-MM [--from-date YYYY-MM-DD] [--write]
"""
import argparse
import datetime
import json
import re
from pathlib import Path
import calendar_handoff as CH
from paths import WORKSPACE


def audit_brand(root,brand,month,start=None,write=False):
    root=Path(root);base=root/'runs/email-production'/brand
    report={'brand':brand,'month':month,'at':datetime.datetime.now().isoformat(timespec='seconds'),
            'status':'draft','mode':'local metadata only','runs':[]}
    import simple_email as S
    for rj in sorted(base.glob('*/run.json')):
        rd=rj.parent;state=CH.read(rj,{})
        date=(state.get('assignment') or {}).get('send_date') or ''
        email=CH.read(rd/'deliverable/email.json',None)
        if not date.startswith(month) or (start and date<start) or not email:continue
        audit=CH.inspect(root,brand,rd,copy=email,state=state)
        old=CH.read(rd/'klaviyo/card.json',{})
        spec=CH.read(rd/'design/email.json',{})
        spec.setdefault('segments',old.get('segments') or [])
        spec.setdefault('date',date)
        look=CH.read(root/'brands'/brand/'email-sms/design-system.json',{})
        updates=CH.metadata(root,brand,rd,spec,look,old) if old else {'calendar_handoff':audit}
        after=dict(old,**updates) if old else {}
        report_row={'run':rd.name,'date':date,'source':str(rd.relative_to(root)),
            'slot_id':(audit.get('expected') or {}).get('slot_id'),'handoff':updates['calendar_handoff'],
            'platform_record_preserved':CH.protected(old),'card_status':old.get('status'),
            'metadata_changed':[k for k in updates if k!='calendar_handoff' and old.get(k)!=updates[k]]}
        # Re-run deterministic delivery checks; do not turn a saved model verdict into a new model review.
        try:delivery=S.delivery_problems(email,brand,rd)
        except Exception as e:delivery=['delivery check unavailable: '+type(e).__name__+': '+str(e)[:180]]
        saved=(CH.read(rd/'deliverable/check.json',{}) or {}).get('delivery',{})
        saved_problems=saved.get('problems') or []
        # Do not silently clear a previously saved fact/source hold through a broad standing ruling.
        unresolved=[p for p in saved_problems if not re.match(r'subject pair \d+:',p)] if saved.get('result')!='pass' else []
        delivery=list(dict.fromkeys(delivery+unresolved))
        valid=[]
        if not unresolved:
            for i in range(len(email.get('subjects') or [])):
                try:
                    if not S.delivery_problems(email,brand,rd,i):valid.append(i)
                except Exception:pass
        report_row['valid_subject_picks']=valid
        if valid:
            delivery=[p for p in delivery if not re.match(r'subject pair \d+:',p)]
        report_row['subject_choice_required']=bool(valid and 0 not in valid)
        report_row['delivery_problems']=delivery
        holds=list(dict.fromkeys(updates['calendar_handoff']['problems']+delivery))
        report_row['review_state']=('existing-platform-work' if CH.protected(old) else 'held' if holds else 'copy-review')
        report_row['release_problems']=CH.card_problems(root,brand,rd,after) if after else ['No approval card built']
        report_row['problems']=holds
        report_row['completion_scope']='saved copy review only; design/images and platform release require separate checks'
        if write:
            f=rd/'calendar-handoff.json';f.write_text(json.dumps(report_row,indent=1,ensure_ascii=False)+'\n')
            if old:
                backup=rd/'klaviyo/calendar-handoff-before.json'
                if not backup.exists():backup.write_text(json.dumps(old,indent=1,ensure_ascii=False)+'\n')
                after['calendar_handoff']=updates['calendar_handoff']
                (rd/'klaviyo/card.json').write_text(json.dumps(after,indent=1,ensure_ascii=False)+'\n')
        report['runs'].append(report_row)
    report['counts']={k:sum(x['review_state']==k for x in report['runs']) for k in ('copy-review','held','existing-platform-work')}
    if write:
        out=base/('calendar-handoff-'+month);out.mkdir(parents=True,exist_ok=True)
        (out/'report.json').write_text(json.dumps(report,indent=1,ensure_ascii=False)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--brand',required=True);p.add_argument('--month',required=True)
    p.add_argument('--from-date');p.add_argument('--write',action='store_true')
    a=p.parse_args();report=audit_brand(WORKSPACE,a.brand,a.month,a.from_date,a.write)
    print(json.dumps({'brand':a.brand,'counts':report['counts'],'mode':report['mode'],'written':a.write}))


if __name__=='__main__':main()
