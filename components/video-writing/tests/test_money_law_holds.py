"""Only money and law hold a finished script (owner ruling, 2026-11-20). No network, no spend."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

COMP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMP / 'machine'))
import holds as H
import writing_revalidate as V
from test_writing_state import fixture, save, W, R

PRODUCT = '''---
known-issues: none open. Settled: 'turmeric tells those cells to stop' stands in every channel
---
# Fixture scrub

## Price
Offer: $29.99 a jar, 60-day money-back guarantee.

## Claims

**Allowed:** helps fade dark spots

**Forbidden:**
- cures / removes / erases / fixes / corrects / treats
- any dated result promise

## Images
'''


def brand_tree(root):
    b = root / 'brands' / 'fixture'
    (b / 'products' / 'scrub').mkdir(parents=True)
    (b / 'products' / 'scrub' / 'product.md').write_text(PRODUCT)
    (b / 'products' / 'offer-bank.md').write_text('## scrub — offer\nBuy two, get one free.\n')
    lang = b / 'core-avatars' / 'spot-hider' / 'language'
    lang.mkdir(parents=True)
    (lang / 'rules.md').write_text('- [language_pain] "I hide my arms all summer long"\n')
    return root


def reader(*answers):
    replies = iter(json.dumps(a) for a in answers)
    return SimpleNamespace(pick=mock.Mock(return_value=('fixture-check', None)),
                           call=mock.Mock(side_effect=lambda *a, **k: next(replies)))


class ClaimsHoldOnlyMoneyAndLaw(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = brand_tree(Path(self.tmp.name))
        self.ev = self.root / 'evidence'
        self.ev.mkdir()
        self.patch = mock.patch.object(H, 'WS', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def check(self, lines, *answers):
        rows = [{'id': i, 'text': t} for i, t in lines]
        cf = SimpleNamespace(lines_of=lambda doc: rows, claim_rules=lambda *a: 'rules on file')
        rd = reader(*answers)
        with mock.patch.object(V, 'module', return_value=cf), \
                mock.patch.dict(sys.modules, {'run_kit': SimpleNamespace(model=rd)}):
            out = V.claims_check({}, {'brand': 'fixture', 'product': 'scrub'}, self.ev)
        return out, rd

    def verdict(self, ids, violations):
        return {'checked_ids': ids, 'violations': violations}

    def test_a_line_the_brand_file_settles_passes_as_a_note(self):
        v = [{'id': 'S4.voice', 'words': 'Turmeric tells those cells to stop.', 'rule': 'no clinical words'}]
        out, rd = self.check([('S4.voice', 'Turmeric tells those cells to stop.')], self.verdict(['S4.voice'], v))
        self.assertTrue(out['passed'])
        self.assertEqual(out['notes'][0]['id'], 'S4.voice')
        rd.call.assert_called_once()                # nothing to confirm, no second ask

    def test_a_language_bank_quote_passes(self):
        v = [{'id': 'S1.voice', 'words': 'I hide my arms all summer long', 'rule': 'register'}]
        out, _ = self.check([('S1.voice', 'I hide my arms all summer long.')], self.verdict(['S1.voice'], v))
        self.assertTrue(out['passed'])

    def test_a_taste_flag_is_a_note_never_a_stop(self):
        v = [{'id': 'S2.voice', 'words': 'made in a lab in Italy', 'rule': 'unsupported origin'}]
        out, rd = self.check([('S2.voice', 'It is made in a lab in Italy.')], self.verdict(['S2.voice'], v))
        self.assertTrue(out['passed'])
        self.assertEqual(len(out['notes']), 1)
        rd.call.assert_called_once()

    def test_an_offer_flag_that_does_not_repeat_is_a_note(self):
        line = 'Get 50% off today with a lifetime guarantee.'
        v = [{'id': 'S9.voice', 'words': line, 'rule': 'offer terms'}]
        out, rd = self.check([('S9.voice', line)], self.verdict(['S9.voice'], v), self.verdict(['S9.voice'], []))
        self.assertTrue(out['passed'])
        self.assertEqual(rd.call.call_count, 2)
        self.assertIn('did not repeat', out['notes'][0]['note'])

    def test_an_offer_not_word_for_word_that_repeats_holds(self):
        line = 'Get 50% off today with a lifetime guarantee.'
        v = [{'id': 'S9.voice', 'words': line, 'rule': 'offer terms'}]
        out, _ = self.check([('S9.voice', line)], self.verdict(['S9.voice'], v), self.verdict(['S9.voice'], v))
        self.assertFalse(out['passed'])
        self.assertEqual(out['violations'][0]['class'], 'money')

    def test_an_offer_word_for_word_from_the_offer_bank_passes(self):
        v = [{'id': 'S9.voice', 'words': 'Buy two, get one free.', 'rule': 'offer terms'}]
        out, rd = self.check([('S9.voice', 'Buy two, get one free.')], self.verdict(['S9.voice'], v))
        self.assertTrue(out['passed'])
        rd.call.assert_called_once()

    def test_a_cure_remove_erase_claim_holds_by_code_even_when_the_judge_passes_it(self):
        out, _ = self.check([('S3.voice', 'It removes every dark spot.')], self.verdict(['S3.voice'], []))
        self.assertFalse(out['passed'])
        self.assertEqual(out['violations'][0]['class'], 'law')

    def test_the_brands_own_banned_word_holds_when_flagged_twice(self):
        line = 'This fixes the spots on your legs.'
        v = [{'id': 'S5.voice', 'words': 'fixes the spots', 'rule': 'Forbidden: fixes'}]
        out, _ = self.check([('S5.voice', line)], self.verdict(['S5.voice'], v), self.verdict(['S5.voice'], v))
        self.assertFalse(out['passed'])
        self.assertEqual(H.law_words('fixture', 'scrub'),
                         {'cures', 'removes', 'erases', 'fixes', 'corrects', 'treats'})

    def test_an_answer_printed_twice_is_read_once(self):
        rows = [{'id': 'S1.voice', 'text': 'Words.'}]
        cf = SimpleNamespace(lines_of=lambda doc: rows, claim_rules=lambda *a: 'rules')
        one = json.dumps({'checked_ids': ['S1.voice'], 'violations': []})
        rd = SimpleNamespace(pick=lambda *a: ('m', None), call=lambda *a, **k: one + '\n' + one)
        with mock.patch.object(V, 'module', return_value=cf), \
                mock.patch.dict(sys.modules, {'run_kit': SimpleNamespace(model=rd)}):
            self.assertTrue(V.claims_check({}, {'brand': 'fixture', 'product': 'scrub'}, self.ev)['passed'])

    def test_a_forbidden_list_settles_nothing(self):
        corpus = H.settled_sources('fixture', 'scrub')
        self.assertFalse(H.is_settled('cures removes erases fixes', corpus))


class SectionLabelsAreNotes(unittest.TestCase):
    def test_a_label_disagreement_relabels_on_the_receipt_and_the_brief_is_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            fixture(d, 'held')
            doc = {'scenes': [{'id': 'S1', 'voice': 'Exact words', 'section': 'hook'}]}
            src = d / 'stages/5-brief.md'
            src.write_text('```json\n' + json.dumps(doc) + '\n```')
            before = src.read_bytes()

            def manifest(dd, brand, name):
                (dd / 'manifest.json').write_text(json.dumps({'core_missing': [], 'to_make': []}))
                return True, []
            misfit = {'id': 'S1', 'given': 'hook', 'fits': False, 'should_be': 'unique-mechanism',
                      'votes': '2 of 3', 'why': 'it explains how'}
            modules = {
                'slotfill': SimpleNamespace(holes_of=lambda doc: []),
                'scenes': SimpleNamespace(json_block=lambda text: (doc, None)),
                'sectionfit': SimpleNamespace(plan_of=lambda out: doc, check=lambda *a, **k: {
                    'pass': False, 'scenes': [misfit], 'misfits': [misfit], 'order': []}),
                'spoken_check': SimpleNamespace(check_lines=lambda rows: []),
                'cast_match': SimpleNamespace(check=lambda *a: ([], [])),
                'model_inputs': SimpleNamespace(brief_violations=lambda doc: []),
                'storyboard_plan': SimpleNamespace(swipe_carry=lambda *a: []),
                'swipe_match': SimpleNamespace(check=lambda *a: (True, []), unstamped=lambda text: text),
                'manifest': SimpleNamespace(check=manifest),
                'scene_shots': None}
            with mock.patch.object(V, 'module', side_effect=lambda component, name: modules[name]), \
                    mock.patch.object(V, 'claims_check', return_value={'passed': True, 'notes': []}), \
                    mock.patch.object(W, 'owner_words_check', return_value=None):
                result = V.revalidate(d)
            self.assertTrue(result['accepted'])
            self.assertEqual(src.read_bytes(), before)        # revalidation never rewrites the brief
            notes = json.loads((d / 'run.json').read_text())['writing_notes']['sections']
            self.assertEqual(notes[0]['relabel_to'], 'unique-mechanism')
            self.assertEqual(result['notes']['sections'][0]['id'], 'S1')


class SpentAuditWritesTheBrief(unittest.TestCase):
    def test_spent_repairs_go_on_to_the_brief_with_the_audit_as_notes(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / 'stages').mkdir()
            st = {'brand': 'fixture', 'production_route': 'ai', 'writing_lane': {'lane': 'swipe'}, 'stages': {},
                  'writing_retry_budget': {'limit': 2, 'used': 2, 'pending': [], 'history': []}}
            save(d, st)
            plan = [{'key': k, 'id': k, 'name': k, 'splits': None} for k in ('stage3', 'stage4e', 'stage5')]
            ran = []

            def run_stage(dd, cur, p, extras, redo=False):
                k = p['key']
                ran.append(k)
                path = 'stages/' + k + '.md'
                (dd / path).write_text('VERDICT: RE-RUN BUILD\nThe close names the wrong price.' if k == 'stage4e' else 'words')
                cur['stages'][k] = {'status': 'held' if k == 'stage4e' else 'done', 'out': path}
                W._CURRENT['calls'] = [{'stage': k, 'cost_usd': 0, 'api_seconds': 0}]
                save(dd, cur)
                return k != 'stage4e'
            with mock.patch.object(W, 'plan', return_value=plan), mock.patch.object(W, 'run_inputs', return_value={}), \
                    mock.patch.object(W, 'declared_layers', return_value=''), \
                    mock.patch.object(W, 'apply_call', side_effect=lambda dd, s: s), \
                    mock.patch.object(W, 'format_approved', return_value=True), \
                    mock.patch.object(W, 'keep_controls_preset', return_value=None), \
                    mock.patch.object(R, 'run_stage', side_effect=run_stage), \
                    mock.patch.object(R, 'save', side_effect=save), mock.patch.object(R, 'say'):
                W.run_writing(d, st, {})
                after = json.loads((d / 'run.json').read_text())
                self.assertEqual(ran, ['stage3', 'stage4e', 'stage5'])       # the brief is written
                self.assertEqual(after['stages']['stage4e']['status'], 'done')
                self.assertTrue(after['stages']['stage4e']['audit_spent'])
                note = after['writing_notes']['audit'][0]
                self.assertIn('wrong price', note['words'])
                self.assertIn('price', note['money_or_law_named'])
                n = len(ran)
                W.run_writing(d, after, {})                                  # resume: no new audit call
                self.assertNotIn('stage4e', ran[n:])


class ClaimFixerKeepsSettledLines(unittest.TestCase):
    def test_a_settled_line_is_never_rewritten(self):
        spec = importlib.util.spec_from_file_location(
            'cf_settled', COMP.parent / 'video-production/machine/claimfix.py')
        cf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cf)
        with tempfile.TemporaryDirectory() as t:
            brief = Path(t) / 'b.md'
            doc = {'scenes': [{'id': 'S4', 'voice': 'Turmeric tells those cells to stop'},
                              {'id': 'S5', 'voice': 'It erases spots'}]}
            brief.write_text('```json\n' + json.dumps(doc) + '\n```\n')
            reply = json.dumps({'fixes': [{'id': 'S4.voice', 'now': 'Turmeric helps', 'rule': 'r'},
                                          {'id': 'S5.voice', 'now': 'It helps fade the look of spots', 'rule': 'r'}]})
            with mock.patch.object(cf, 'claim_rules', return_value="known-issues: 'turmeric tells those cells to stop' settled"):
                done = cf.fix(brief, 'fixture', 'scrub', call=lambda p: reply)
            self.assertEqual([c['scene'] for c in done], ['S5'])
            self.assertIn('Turmeric tells those cells to stop', brief.read_text())


class RollbackSwitch(unittest.TestCase):
    def test_one_machine_can_put_one_lane_back(self):
        with mock.patch.dict('os.environ', {'WRITING_HOLDS_OLD': 'claims'}):
            self.assertFalse(H.notes_rule('claims'))
            self.assertTrue(H.notes_rule('sections'))
        with mock.patch.dict('os.environ', {'WRITING_HOLDS_OLD': 'all'}):
            self.assertFalse(H.notes_rule('audit'))
        with mock.patch.dict('os.environ', {'WRITING_HOLDS_OLD': ''}):
            self.assertTrue(all(H.notes_rule(x) for x in ('sections', 'claims', 'audit')))

    def test_claims_rolled_back_holds_on_any_judge_flag(self):
        rows = [{'id': 'S2.voice', 'text': 'Made in a lab in Italy.'}]
        cf = SimpleNamespace(lines_of=lambda doc: rows, claim_rules=lambda *a: 'rules')
        v = {'checked_ids': ['S2.voice'], 'violations': [{'id': 'S2.voice', 'words': 'a lab in Italy', 'rule': 'r'}]}
        with tempfile.TemporaryDirectory() as t, mock.patch.object(V, 'module', return_value=cf), \
                mock.patch.dict(sys.modules, {'run_kit': SimpleNamespace(model=reader(v))}), \
                mock.patch.dict('os.environ', {'WRITING_HOLDS_OLD': 'claims'}):
            self.assertFalse(V.claims_check({}, {'brand': 'fixture', 'product': 'scrub'}, Path(t))['passed'])



class OneAdOffer(unittest.TestCase):
    """A bank that marks its one ad offer settles an ad's line from that mark only (owner ruling, 2026-11-25)."""
    BANK = ('# Offer bank\n\n## scrub — Scrub\n- Sold in the funnel: Buy 2, get 1 free, $19 a tube\n\n### guarantee — words\n'
            '> every penny back\n\n### rules — Standing\n<!-- ad-offer -->\n- "Free guide" · "Free shipping"\n<!-- /ad-offer -->\n'
            '- never in an ad: the pouch\n')

    def test_only_the_marked_offer_and_the_guarantee_settle_a_line(self):
        got = H.norm(H.ad_offer(self.BANK))
        for ok in ('Free guide', 'Free shipping', 'every penny back'):
            self.assertIn(H.norm(ok), got)
        for no in ('Buy 2, get 1 free', '$19 a tube', 'the pouch'):
            self.assertNotIn(H.norm(no), got)

    def test_a_bank_with_no_mark_is_read_whole(self):
        plain = self.BANK.replace('<!-- ad-offer -->', '').replace('<!-- /ad-offer -->', '')
        self.assertEqual(H.ad_offer(plain), plain)


if __name__ == '__main__':
    unittest.main()
