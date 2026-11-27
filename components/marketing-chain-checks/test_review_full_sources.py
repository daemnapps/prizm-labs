"""Review the evidence actually supplied, including citations late in large files."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marketing_chain_checks import review


class FullSources(unittest.TestCase):
    def test_late_file_evidence_reaches_the_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'source.md'
            content = ('roster context\n' * 15000) + '\nRECORD-TAIL: quoted supporting evidence'
            p.write_text(content)
            seen = []
            def caller(parts):
                seen.extend(parts)
                return {'a': {'ok': True, 'problems': []}}
            review.review('test-tool', 'test-stage', [{'id': 'a', 'output': ['short draft']}], sources=[p], caller=caller)
            self.assertTrue(any(part.get('text') == '--- source.md ---\n' + content for part in seen))

    def test_long_inline_sources_and_output_are_complete(self):
        source = 'source ' * 30000 + 'END OF EVIDENCE'
        output = 'output ' * 16000 + 'END OF OUTPUT'
        seen = []
        verdict = {'a': {'ok': False, 'severity': 'BLOCKER', 'problems': ['real mismatch']}}
        def caller(parts):
            seen.extend(parts)
            return verdict
        result = review.review('test-tool', 'test-stage', [{'id': 'a', 'compare': [source], 'output': [output]}], caller=caller)
        texts = [part.get('text') for part in seen]
        self.assertIn(source, texts)
        self.assertIn(output, texts)
        self.assertEqual(result, verdict)

    def test_short_source_keeps_label_and_content(self):
        self.assertEqual(review._labelled('SOURCE', ['inline evidence']),
                         [{'text': '\n=== SOURCE ===\n'}, {'text': 'inline evidence'}])


if __name__ == '__main__':
    unittest.main()
