import unittest
import storyboard_plan as S

class SourceOverlays(unittest.TestCase):
    def test_house_rule_excludes_photography_disclaimer_but_keeps_instructions(self):
        rows = [{'text': 'Due to lighting and photography equipment, actual product photos may differ.', 'where': 'bottom center', 'look': 'small'},
                {'text': 'Apply an even layer', 'where': 'top center', 'look': 'large'},
                {'text': 'Wait one minute', 'where': 'bottom center', 'look': 'small'},
                {'text': 'Save 20%', 'where': 'bottom center', 'look': 'small'}]
        result = S.overlays({'map': {'on_screen': rows}}, [])
        self.assertEqual([x['text'] for x in result], ['Apply an even layer', 'Wait one minute', 'Save 20%'])

    def test_top_headline_is_not_misclassified_as_footer(self):
        words = 'Due to lighting, this room is too dark'
        self.assertEqual(S.overlays({'map': {'on_screen': [{'text': words, 'where': 'top center'}]}}, [])[0]['text'], words)

    def test_center_animated_speech_is_caption_not_an_independent_overlay(self):
        import copy
        rows = [{'text': 'A familiar problem', 'where': 'center', 'look': 'uppercase, pops on word by word'},
                {'text': 'A familiar problem', 'where': 'center', 'look': 'large static headline'},
                {'text': 'Apply an even layer', 'where': 'center', 'look': 'instruction, highlighted word by word'},
                {'text': 'Save twenty percent', 'where': 'center', 'look': 'uppercase, pops on word by word'}]
        before = copy.deepcopy(rows)
        transcript = [{'text': 'A familiar problem. Apply an even layer.'}]
        result = S.overlays({'map': {'on_screen': rows}}, transcript)
        self.assertEqual([x['text'] for x in result], ['A familiar problem', 'Apply an even layer', 'Save twenty percent'])
        self.assertEqual(rows, before)

    def test_timed_caption_tail_and_neighbor_spelling_need_evidence(self):
        rows = [{'t': 0, 'until': 0.1, 'text': 'Until now', 'where': 'center', 'look': 'fades out'},
                {'t': 0.1, 'until': 1.1, 'text': 'A fist full of', 'where': 'center', 'look': 'background, uppercase, pop'},
                {'t': 1.1, 'until': 2.1, 'text': 'Parsley half a lemon', 'where': 'center', 'look': 'background, uppercase, pop'}]
        transcript = [{'text': 'Until now. A fistful of parsley, half a lemon.'}]
        # The tail has no directly exact animated neighbor; it remains visible.
        self.assertEqual([x['text'] for x in S.overlays({'map': {'on_screen': rows}}, transcript)], ['Until now'])
        rows[1]['text'] = 'A fistful of'
        self.assertEqual(S.overlays({'map': {'on_screen': rows}}, transcript), [])
        self.assertEqual(len(S.overlays({'map': {'on_screen': rows}}, [])), 3)
        rows[1]['text'] = 'A fist full of chemicals'
        self.assertIn('A fist full of chemicals', [x['text'] for x in S.overlays({'map': {'on_screen': rows}}, transcript)])
        self.assertFalse(S.near_caption_spelling(['not', 'safe', 'now'], ['safe', 'now']))

    def test_explicit_spoken_subtitle_still_needs_animation_and_no_headline(self):
        look = 'spoken subtitle; white text, blue highlight on active word, pop'
        rows = [{'text': 'See when limbs stops draining', 'where': 'center', 'look': look},
                {'text': 'See when limbs stops draining', 'where': 'center', 'look': look + '; headline'},
                {'text': 'See when limbs stops draining', 'where': 'center', 'look': 'spoken subtitle; static'}]
        transcript = [{'text': 'See, when lymph stops draining.'}]
        result = S.overlays({'map': {'on_screen': rows}}, transcript)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]['look'].endswith('headline'))
        self.assertTrue(result[1]['look'].endswith('static'))

class ClassifiedStaticSubtitles(unittest.TestCase):
    def test_explicit_static_subtitle_needs_exact_transcript_and_no_independent_role(self):
        rows = [{'text': 'A familiar problem', 'where': 'center', 'look': 'spoken subtitle; white outline; static'},
                {'text': 'A new problem', 'where': 'center', 'look': 'spoken subtitle; white outline; static'},
                {'text': 'A familiar problem', 'where': 'center', 'look': 'spoken subtitle; static headline'},
                {'text': 'A familiar problem', 'where': 'center', 'look': 'spoken subtitle; static instruction'},
                {'text': 'A familiar problem', 'where': 'center', 'look': 'white outline; static'}]
        transcript = [{'text': 'We have a familiar problem today.'}]
        result = S.overlays({'map': {'on_screen': rows}}, transcript)
        self.assertEqual(result, rows[1:])
        self.assertEqual(len(S.overlays({'map': {'on_screen': rows}}, [])), 5)

class SourceSmallPrint(unittest.TestCase):
    def test_only_explicit_corner_source_watermark_small_print_is_excluded(self):
        base = {'text': 'source attribution', 'where': 'top left',
                'look': 'source watermark; small print; white, static'}
        keep = [dict(base, look=base['look'] + '; ' + role)
                for role in ('headline', 'instruction', 'callout', 'badge', 'product logo')]
        keep += [dict(base, look='white, small, static'),
                 dict(base, look='source watermark; white, static'),
                 dict(base, look='small print; white, static'),
                 dict(base, where='center')]
        result = S.overlays({'map': {'on_screen': [base] + keep}}, [])
        self.assertEqual(result, keep)

if __name__ == '__main__':unittest.main()
