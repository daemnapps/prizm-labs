"""The audit station has its own bars without changing neighboring stage routing."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from marketing_chain_checks import review


class VideoAuditDefinition(unittest.TestCase):
    def test_exact_audit_station_uses_report_and_verdict_bars(self):
        got = review.stage_def('video-teardown', 'stage4e')
        self.assertIn('audit report', got['what'])
        self.assertIn('displayed 4f', got['what'])
        self.assertIn('audit prompt', got['compare_against'])
        self.assertTrue(any('unresolved required failure cannot receive SHIP' in x for x in got['hard_bars']))
        self.assertTrue(any('every check' in x for x in got['hard_bars']))

    def test_merged_build_still_uses_generic_writing_definition(self):
        defs = review.definitions()['tools']['video-teardown']['stages']
        self.assertEqual(review.stage_def('video-teardown', 'stage4v2b'), defs['stage4'])
        self.assertIn('placement, expansion, close, spice', defs['stage4']['what'])

    def test_other_exact_and_default_routes_unchanged(self):
        tools = review.definitions()['tools']
        self.assertEqual(review.stage_def('video-teardown', 'stage4b'), tools['video-teardown']['stages']['stage4b'])
        self.assertEqual(review.stage_def('copywriter', 'stage4e'), tools['copywriter']['default'])


if __name__ == '__main__':
    unittest.main()
