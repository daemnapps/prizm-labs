"""Source-bound slot filling: no network, model calls, or real brands."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import slot_research as slots


class ResearchReceipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'runs' / 'video-teardown' / '_work' / 'fixture'
        (self.run / 'stages').mkdir(parents=True)
        (self.run / 'run.json').write_text(json.dumps({'brand': 'test-brand', 'product': 'device'}))
        self.stage = self.run / 'stages' / 'test.md'
        self.stage.write_text('The the original line [RESEARCH: duration].\n')
        self.key = 'brands/test-brand/products/device.md'
        self.quote = 'The device session lasts 90 seconds. ' + ('unabridged source evidence ' * 25).strip()
        self.product = self.write(self.key, 'x' * 65000 + '\n' + self.quote + '\n')
        self.proposal = 'runs/video-production/test-brand/research-proposals/facts-found.md'
        self.write(self.proposal, 'one minute (old file product.device.json:329)\n')
        self.cast = 'runs/casting/test-brand/CAST.md'
        self.write(self.cast, 'The banked fixture performer is Alma.\n')
        sf = slots._slotfill()
        for patcher in (patch.object(slots, 'WS', self.root), patch.object(sf, 'WS', self.root),
                        patch.object(slots, '_slotfill', return_value=sf)):
            patcher.start(); self.addCleanup(patcher.stop)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def row(self, **kw):
        return {**{'id': 'H1', 'fill': '90 seconds', 'source': 'brand', 'source_path': self.key,
                   'receipt': self.quote}, **kw}

    def fill(self, *rows):
        return slots.fill(self.run, stage_file='test.md', find=slots.markers,
                          call=lambda prompt: json.dumps({'holes': rows}))

    def test_long_source_context_receipt_and_exact_digests(self):
        self.stage.write_text('The the original ' + 'z' * 1100 + ' [RESEARCH: duration].\n')
        before = self.stage.read_bytes()
        product_before = self.product.read_bytes()
        result = self.fill(self.row())
        self.assertEqual(self.stage.read_bytes(), before.replace(b'[RESEARCH: duration]', b'90 seconds'))
        self.assertEqual(product_before, self.product.read_bytes())
        rec = self.run / result['evidence']
        receipt = json.loads(rec.read_text())
        for filename, key in [('request.md', 'request_sha256'), ('reply.txt', 'reply_sha256'), ('stage-before.md', 'before_sha256')]:
            self.assertEqual(hashlib.sha256((rec.parent / filename).read_bytes()).hexdigest(), receipt[key])
        self.assertIn(self.product.read_text(), (rec.parent / 'request.md').read_text())
        self.assertIn('z' * 1100, (rec.parent / 'request.md').read_text())
        self.assertEqual((rec.parent / 'receipt.sha256').read_text().split()[0], hashlib.sha256(rec.read_bytes()).hexdigest())
        self.assertEqual(receipt['filled'][0]['receipt'], self.quote)
        self.assertEqual(receipt['filled'][0]['receipt_sha256'], hashlib.sha256(self.quote.encode()).hexdigest())
        self.assertEqual(receipt['filled'][0]['source_sha256'], hashlib.sha256(product_before).hexdigest())
        self.assertIn(self.quote, (self.root / self.proposal).read_text())

    def test_proposal_missing_source_invented_quote_and_invented_fill_remain_pending(self):
        for row in (self.row(source_path=self.proposal, receipt='one minute', fill='one minute'),
                    self.row(source_path='brands/test-brand/products/product.device.json', receipt='one minute', fill='one minute'),
                    self.row(receipt='one minute', fill='one minute'), self.row(fill='one minute'),
                    self.row(fill='0 seconds'), self.row(source_path='../' + self.key)):
            with self.subTest(row=row):
                before = self.stage.read_bytes()
                result = self.fill(row)
                self.assertFalse(result['filled'])
                self.assertEqual(result['pending'][0]['candidate'], row)
                self.assertEqual(self.stage.read_bytes(), before)

    def test_external_quote_and_url_retained_for_independent_verification(self):
        row = self.row(source='web', source_path='https://example.com/primary', receipt='The rival costs $40.', fill='$40')
        result = self.fill(row)
        self.assertEqual(result['filled'], [])
        self.assertIn('page capture', result['pending'][0]['reason'])
        self.assertEqual(result['pending'][0]['candidate'], row)
        self.assertIn('[RESEARCH: duration]', self.stage.read_text())

    def test_cast_source_and_same_marker_at_different_offsets(self):
        self.stage.write_text('First [RESEARCH: person] then [RESEARCH: person].\n')
        row = self.row(fill='Alma', source='cast', source_path=self.cast, receipt='The banked fixture performer is Alma.')
        result = self.fill(row, {**row, 'id':'H2', 'fill':'Another name'})
        self.assertEqual(self.stage.read_text(), 'First Alma then [RESEARCH: person].\n')
        self.assertEqual([r['id'] for r in result['pending']], ['H2'])

    def test_changed_canonical_source_and_unparseable_reply_cannot_fill(self):
        def changed(prompt):
            self.product.write_text('Changed during research.\n')
            return json.dumps({'holes':[self.row()]})
        before = self.stage.read_bytes()
        result = slots.fill(self.run, call=changed, stage_file='test.md', find=slots.markers)
        self.assertIn('changed', result['pending'][0]['reason'])
        with self.assertRaises(ValueError):
            slots.fill(self.run, call=lambda p:'raw unparseable answer', stage_file='test.md', find=slots.markers)
        records = [json.loads(p.read_text()) for p in (self.run / 'slot-research').glob('*/receipt.json')]
        bad = next(r for r in records if r['state'] == 'unavailable')
        self.assertEqual(bad['reply_sha256'], hashlib.sha256(b'raw unparseable answer').hexdigest())
        self.assertEqual(before, self.stage.read_bytes())

    def test_existing_fill_log_and_outside_section_are_not_script_slots(self):
        self.stage.write_text('1. THE INJECTED SCRIPT\nIt lasts [SLOT: duration].\n2. DOMINANT\n[SLOT: duration]\n\n## Slots filled by research (automatic, yesterday)\n[SLOT: duration]\n')
        result = slots.fill(self.run, call=lambda p:json.dumps({'holes':[self.row()]}), stage_file='test.md')
        self.assertEqual(result['holes'], 1)
        self.assertEqual(self.stage.read_text().count('[SLOT: duration]'), 2)


if __name__ == '__main__':
    unittest.main()
