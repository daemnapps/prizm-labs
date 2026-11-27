"""Add the regular SMS companions to a saved month. No model or platform calls.

    python3 machine/weekly_sms.py <month-folder> [--write]

Without --write, prints additions only. Existing IDs and promotional reminders stay intact.
"""
import argparse
import calendar
import datetime as dt
import json
from pathlib import Path


def add_weekly_sms(slots, month, cadence):
    rule = cadence.get('weekly') or {}
    if not rule.get('enabled'):
        return []
    start = dt.date.fromisoformat(rule['start_date'])
    year, number = map(int, month.split('-'))
    first = dt.date(year, number, 1)
    last = dt.date(year, number, calendar.monthrange(year, number)[1])
    weekday = int(rule.get('preferred_weekday', 1))
    quiet = cadence.get('quiet_hours') or {'to': 9, 'from': 21}
    opening, closing = int(quiet['to']), int(quiet['from'])
    hour = max(opening, min(int(cadence.get('hour', 12)), closing - 1))
    emails = [s for s in slots if s.get('channel', 'email') == 'email']
    additions = []
    serial = max([int(s['id'].rsplit('-', 1)[1]) for s in slots] or [0])
    prefix = slots[0]['id'].rsplit('-', 1)[0] if slots else first.strftime('%b').lower()
    preferred = first + dt.timedelta(days=(weekday - first.weekday()) % 7)
    while preferred <= last:
        monday = preferred - dt.timedelta(days=weekday)
        week = monday.isoformat()
        if preferred >= start and not any(s.get('sms_beat') == 'weekly' and s.get('cadence_week') == week for s in slots):
            candidates = []
            for email in emails:
                date = dt.date.fromisoformat(email['date'])
                if date < start or not monday <= date <= monday + dt.timedelta(days=6):
                    continue
                send_hour = max(hour, int(email.get('hour', 0)) + 1)
                if send_hour >= closing:
                    continue
                # Regular texts supplement reminders; they never displace one or add a second text that day.
                if any(s.get('channel') == 'sms' and s['date'] == email['date'] for s in slots):
                    continue
                candidates.append((abs((date - preferred).days), -int(email.get('hour', 0)), email, send_hour))
            if candidates:
                _, _, email, send_hour = min(candidates, key=lambda x: (x[0], x[1], x[2]['id']))
                serial += 1
                sms = dict(email, id='%s-%02d' % (prefix, serial), channel='sms', hour=send_hour,
                           follows=email['id'], then=None, sms_beat='weekly', sms_job='engagement',
                           cadence_week=week, kind='sms', format=None,
                           audience_rule=cadence.get('audience', 'SMS-consented members only'),
                           why='One regular SMS for the week of %s, alongside %s; existing promotional reminders remain. Same audience and offer as that email; no new urgency or offer.' % (week, email['id']),
                           kind_why='Regular weekly text companion; words only, one link and opt-out.')
                sms.pop('offer_mix', None)
                slots.append(sms)
                if not email.get('then'):
                    email['then'] = sms['id']
                additions.append(sms)
        preferred += dt.timedelta(days=7)
    return additions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('month_folder', type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    cadence = json.loads((Path(__file__).resolve().parents[1] / 'definitions/sms-cadence.json').read_text())
    path = args.month_folder / 'slots.json'
    slots = json.loads(path.read_text())
    added = add_weekly_sms(slots, args.month_folder.name, cadence)
    print(json.dumps(added, indent=1))
    if args.write:
        path.write_text(json.dumps(slots, indent=1) + '\n')
        (args.month_folder / 'weekly-sms.json').write_text(json.dumps({'rule': cadence['weekly'], 'added_ids': [s['id'] for s in added]}, indent=1) + '\n')


if __name__ == '__main__':
    main()
