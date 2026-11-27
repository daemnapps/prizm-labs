"""A hand request keeps its language selection when another run advances."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import chain


class LanguageExposure(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.current = self.root / 'current'
        self.current.mkdir()
        self.peer = self.root / 'peer' / 'prompts'
        self.peer.mkdir(parents=True)
        self.peer.joinpath('first.md').write_text('[language_one] [language_one]')
        self.patch = patch.object(chain, 'runs_root', return_value=self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        chain._SHOWN.clear()
        self.addCleanup(chain._SHOWN.clear)

    def test_resume_ignores_peer_progress_but_new_run_rotates(self):
        original = chain.shown_counts(self.current)
        self.assertEqual(original, {'language_one': 1})
        self.peer.joinpath('second.md').write_text('[language_two]')
        chain._SHOWN.clear()  # A fresh process resuming the hand request.
        self.assertEqual(chain.shown_counts(self.current), original)
        fresh = self.root / 'fresh'
        fresh.mkdir()
        self.assertEqual(chain.shown_counts(fresh), {'language_one': 1, 'language_two': 1})

    def test_current_run_is_excluded_and_exposures_count_once_per_peer(self):
        prompts = self.current / 'prompts'
        prompts.mkdir()
        prompts.joinpath('self.md').write_text('[language_self]')
        self.peer.joinpath('second.md').write_text('[language_one]')
        self.assertEqual(chain.shown_counts(self.current), {'language_one': 1})

    def test_corrupt_snapshot_cannot_silently_pick_different_words(self):
        for value in ([], {'schema': 2, 'counts': {}}, {'schema': 1, 'counts': {'x': -1}}):
            self.current.joinpath('language-exposure.json').write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                chain.shown_counts(self.current)

    def test_concurrent_first_query_keeps_winning_complete_snapshot(self):
        real_link = chain.os.link
        def winner(source, destination):
            Path(destination).write_text(json.dumps({'schema': 1, 'counts': {'language_winner': 3}}))
            return real_link(source, destination)
        with patch.object(chain.os, 'link', side_effect=winner):
            self.assertEqual(chain.shown_counts(self.current), {'language_winner': 3})
        self.assertEqual(list(self.current.glob('.language-exposure-*')), [])


if __name__ == '__main__':
    unittest.main()
