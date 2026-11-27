"""Claim evidence reads canonical flat products and legacy nested claims locally."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('claims_under_test', HERE / 'claimfix.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


class ClaimRules(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ws = Path(self.temp.name)
        self.brand = self.ws / 'brands' / '_claims-fixture'
        self.products = self.brand / 'products'
        self.products.mkdir(parents=True)
        self.patch = mock.patch.object(C, 'WS', self.ws)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def flat(self, name='device', text=None):
        text = text or ('# Sonic device\n\n`device` · live on the storefront\n\n'
                        '## What it does\n\n- Ten settings up to 9000 RPM\n\n'
                        '## The mechanism in plain terms\n\n'
                        'What may be said about the device itself is the list above.\n'
                        'A depth in millimetres is not on file.\n')
        (self.products / (name + '.md')).write_text(text)
        return text

    def test_flat_unheaded_restrictions_are_supplied_whole_and_verbatim(self):
        text = self.flat()
        self.assertEqual(C.claim_rules('_claims-fixture', 'device'),
                         '### brands/_claims-fixture/products/device.md\n' + text)

    def test_full_position_and_product_rules_reach_reviewer_verbatim(self):
        product = self.flat(text=("# Device\nThe position's reach claim is allowed.\n"
                                  "No measured depth. No inferred material. Speed is a range.\n"))
        position = self.brand / 'brand-identity' / 'position.md'
        position.parent.mkdir()
        base = '# Position\r\n\r\nA surface comparison.\r\n\r\n## Mechanism\r\nExact mechanism — café.\r\n'
        position.write_bytes(base.encode('utf-8'))
        (self.brand / 'position.md').write_text('An old copy that should lose to the canonical file.')
        expected = ('### brands/_claims-fixture/products/device.md\n' + product
                    + '\n\n### brands/_claims-fixture/brand-identity/position.md\n' + base)
        self.assertEqual(C.claim_rules('_claims-fixture', 'device'), expected)

    def test_named_product_adds_entire_scoped_offer_source_only_when_product_exists(self):
        product = self.flat()
        offer = '# Offers\r\nA condition for another product.\r\n' + ('context · ' * 3000) + '\r\nDevice: exact refund terms.\r\n'
        (self.products / 'offer-bank.md').write_bytes(offer.encode('utf-8'))
        rules = C.claim_rules('_claims-fixture', 'device')
        self.assertIn(product, rules)
        self.assertIn('Offer scope: brand _claims-fixture, product device.', rules)
        self.assertIn('### brands/_claims-fixture/products/offer-bank.md\n' + offer, rules)
        self.assertEqual(C.claim_rules('_claims-fixture', 'missing'), '(no claim rules on file)')

    def test_legacy_flat_position_resolves_alongside_nested_product_rules(self):
        product = self.products / 'legacy' / 'product.md'
        product.parent.mkdir()
        product.write_text('# Legacy\n## Claims\nKeep the material restriction.\n')
        text = 'Full historical base.\n\nAll lines apply.\n'
        (self.brand / 'position.md').write_text(text)
        rules = C.claim_rules('_claims-fixture', 'legacy')
        self.assertIn('Keep the material restriction.', rules)
        self.assertIn('### brands/_claims-fixture/position.md\n' + text, rules)

    def test_missing_or_empty_position_preserves_rules_and_cannot_replace_product(self):
        product = self.flat()
        expected = '### brands/_claims-fixture/products/device.md\n' + product
        self.assertEqual(C.claim_rules('_claims-fixture', 'device'), expected)
        position = self.brand / 'position.md'
        position.write_text('   \n')
        self.assertEqual(C.claim_rules('_claims-fixture', 'device'), expected)
        position.write_text('Brand-level positioning alone.\n')
        self.assertEqual(C.claim_rules('_claims-fixture', 'missing'), '(no claim rules on file)')

    def test_flat_claims_heading_still_preserves_the_complete_product_source(self):
        text = self.flat(text='# Device\n\n## Claims\nAllowed claim.\n\n## Restrictions\nKeep this exact.\n')
        self.assertIn(text, C.claim_rules('_claims-fixture', 'device'))

    def test_legacy_nested_claims_extraction_stays_unchanged(self):
        old = self.products / 'legacy' / 'product.md'
        old.parent.mkdir()
        old.write_text('# Legacy\nKnown-issues: retain this note\n\n## Details\nOther material.\n\n'
                       '## Claims\nAllowed and forbidden.\n\n## Directions\nExcluded.\n')
        rules = C.claim_rules('_claims-fixture', 'legacy')
        self.assertIn('Known-issues: retain this note', rules)
        self.assertIn('## Claims\nAllowed and forbidden.\n\n', rules)
        self.assertNotIn('Other material', rules)
        self.assertNotIn('Excluded', rules)
        self.assertIn(rules, C.claim_rules('_claims-fixture'))

    def test_canonical_flat_file_wins_over_a_legacy_copy_for_named_product(self):
        text = self.flat()
        old = self.products / 'device' / 'product.md'
        old.parent.mkdir()
        old.write_text('## Claims\nStale claim.\n')
        rules = C.claim_rules('_claims-fixture', 'device')
        self.assertIn(text, rules)
        self.assertNotIn('Stale claim', rules)

    def test_all_products_uses_sellable_catalog_and_excludes_metadata(self):
        text = self.flat()
        self.flat('draft', '`draft` · live on the storefront\nDraft restrictions.\n')
        (self.products / 'heroes.json').write_text(json.dumps({'sellable': [{'handle': 'device'}]}))
        for name in ('README.md', 'offer-bank.md', 'asset-bed.md', 'subscriptions.md'):
            (self.products / name).write_text('Metadata claims must stay out.\n')
        (self.products / 'reader.py').write_text('print("not product evidence")')
        rules = C.claim_rules('_claims-fixture')
        self.assertIn(text, rules)
        self.assertNotIn('Draft restrictions', rules)
        self.assertNotIn('Metadata claims', rules)
        self.assertNotIn('reader.py', rules)

    def test_store_snapshot_fallback_excludes_unavailable_products(self):
        self.flat()
        self.flat('draft', 'Draft claim.\n')
        (self.products / 'store.json').write_text(json.dumps({'products': [
            {'handle': 'device', 'available': True}, {'handle': 'draft', 'available': False}]}))
        rules = C.claim_rules('_claims-fixture')
        self.assertIn('device.md', rules)
        self.assertNotIn('draft.md', rules)

    def test_without_catalog_only_storefront_marked_flat_products_are_included(self):
        self.flat()
        (self.products / 'offer-bank.md').write_text('## Claims\nOffer metadata.\n')
        rules = C.claim_rules('_claims-fixture')
        self.assertIn('device.md', rules)
        self.assertNotIn('offer-bank.md', rules)

    def test_product_folder_alias_uses_the_canonical_brandpath_reader(self):
        catalog = self.brand / 'catalog'
        self.products.rename(catalog)
        (self.brand / 'FOLDERS.json').write_text(json.dumps({'products': ['catalog']}))
        (catalog / 'device.md').write_text('Exact mapped product source.\n')
        self.assertEqual(C.claim_rules('_claims-fixture', 'device'),
                         '### brands/_claims-fixture/catalog/device.md\nExact mapped product source.\n')

    def test_missing_product_or_empty_catalog_retains_no_rules_result(self):
        self.assertEqual(C.claim_rules('_claims-fixture', 'missing'), '(no claim rules on file)')
        self.assertEqual(C.claim_rules('_claims-fixture'), '(no claim rules on file)')
        self.flat(text='\n')
        self.assertEqual(C.claim_rules('_claims-fixture', 'device'), '(no claim rules on file)')


class ClaimLineCoverage(unittest.TestCase):
    def test_on_screen_strings_are_exact_distinct_locations_alongside_existing_lines(self):
        text = ' AND SOFT / SILICONE BRISTLES…\nSecond line. '
        doc = {'scenes': [{'id': 'S1', 'voice': text, 'on_screen': text,
                           'card': {'lines': ['Card copy']},
                           'screen': {'offer_lines': ['Offer copy']},
                           'endcard': {'lines': ['End copy']}},
                          {'id': 'S2', 'on_screen': '   '},
                          {'id': 'S3', 'on_screen': {'lines': ['Existing dict representation']}}]}
        rows = C.lines_of(doc)
        by_id = {row['id']: row for row in rows}
        self.assertEqual(len(rows), 5)
        self.assertEqual(len(by_id), len(rows))
        self.assertEqual(len({id(row) for row in rows}), len(rows))
        self.assertEqual(by_id['S1.on_screen']['text'], text)
        self.assertEqual(by_id['S1.on_screen']['path'], ('on_screen', None))
        self.assertEqual(by_id['S1.voice']['text'], text)
        self.assertEqual(by_id['S1.card.lines.0']['text'], 'Card copy')
        self.assertEqual(by_id['S1.screen.offer_lines.0']['text'], 'Offer copy')
        self.assertEqual(by_id['S1.endcard.lines.0']['text'], 'End copy')

    def test_fix_applies_top_level_caption_and_voice_corrections_through_existing_paths(self):
        doc = {'scenes': [{'id': 'S1', 'voice': 'And soft silicone bristles.',
                           'on_screen': 'AND SOFT / SILICONE BRISTLES…',
                           'shots': [{'lines': [{'say': 'And soft'}, {'say': 'silicone bristles.'}]}],
                           'card': {'lines': ['Keep this card']}}]}
        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / 'brief.md'
            brief.write_text('```json\n' + json.dumps(doc, ensure_ascii=False) + '\n```\n')
            def fake_call(prompt):
                self.assertIn('S1.on_screen: "AND SOFT / SILICONE BRISTLES…"', prompt)
                return json.dumps({'fixes': [
                    {'id': 'S1.voice', 'now': 'And soft bristles.', 'rule': 'Material unconfirmed'},
                    {'id': 'S1.on_screen', 'now': 'AND SOFT / BRISTLES…', 'rule': 'Material unconfirmed'}]})
            with mock.patch.object(C, 'claim_rules', return_value='Material unconfirmed'):
                fixes = C.fix(brief, '_claims-fixture', 'device', call=fake_call)
            scene = C.SL._block(brief.read_text())[1]['scenes'][0]
            self.assertEqual(scene['voice'], 'And soft bristles.')
            self.assertEqual(scene['on_screen'], 'AND SOFT / BRISTLES…')
            self.assertEqual(C._norm(scene['on_screen']), C._norm(scene['voice']))
            self.assertEqual(C._norm(' '.join(line['say'] for shot in scene['shots']
                                            for line in shot['lines'])), C._norm(scene['voice']))
            self.assertEqual(scene['card']['lines'], ['Keep this card'])
            self.assertEqual(len(fixes), 2)
            self.assertTrue(all(fix['lines_join'] for fix in fixes))


if __name__ == '__main__':
    unittest.main()
