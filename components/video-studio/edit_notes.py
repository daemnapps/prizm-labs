"""THE EDIT STAGE'S READS: every spoken shot against its own line, and every edit note the brief carries.

The rules are the chain's: components/video-edit/machine/edit_notes.py (owner ruling 2026-11-16, V57 (swipe is the backbone): the rules live
in the chain so every editing path gets them). This file makes `import edit_notes` in the Studio that module itself,
so the Studio, its tests and the chain run one copy.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as ST  # noqa: E402

sys.modules[__name__] = ST.chain("video-edit", "edit_notes")
