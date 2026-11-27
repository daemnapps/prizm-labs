"""Moved to components/motion/blocking_blender.py (2026-11-12). Blender is started on that file by
components/motion/motion.py; this forward runs it for anything that still starts it from here."""
from pathlib import Path

exec(compile((Path(__file__).resolve().parents[1] / "motion" / "blocking_blender.py").read_text(), "blocking_blender.py", "exec"))
