#!/usr/bin/env python3
"""One file for one set: only the recipe steps that set needs, ready to run in a single edit in a new project.

    python3 pack.py <recipe> <output> <step> [<step> ...]

Earlier renders are switched off; the last step's render stays so the run ends with a picture to check."""
import re
import sys
from pathlib import Path

STUB = '''class _T:
    path = "/tmp/_skip.png"
    def publish(self): pass
class _A:
    def file(self, **k): return _T()
_real_artifacts, artifacts = artifacts, _A()
'''


def pack(recipe, steps):
    here = Path(__file__).parent / recipe
    out = [STUB]
    for i, n in enumerate(steps):
        code = (here / f"step-{int(n):02d}.py").read_text()
        if i == len(steps) - 1:
            out.append("artifacts = _real_artifacts\n")
        else:
            code = re.sub(r"bpy\.ops\.render\.render\([^)]*\)", "pass", code)
        out += [f"# step {int(n)}\n", code.rstrip() + "\n"]
    return "".join(out)


if __name__ == "__main__":
    recipe, output, *steps = sys.argv[1:]
    Path(output).write_text(pack(recipe, steps))
