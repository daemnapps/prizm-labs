"""Existing writing callers supply the actual run rulings to section-fit."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
MACHINE = ROOT / 'components/video-writing/machine'
sys.path.insert(0, str(MACHINE))
spec = importlib.util.spec_from_file_location('section_context_revalidate', MACHINE / 'writing_revalidate.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
DOC = {'scenes': [{'id': 'S1', 'section': 'proof', 'voice': 'A source account.'}]}


class SectionRulingsContext(unittest.TestCase):
    def test_revalidation_passes_full_snapshot_rulings_and_missing_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            out = d / '5-brief.md'
            out.write_text('```json\n' + json.dumps(DOC) + '\n```\n')
            seen = []
            def check(plan, **kwargs):
                seen.append(kwargs['run_rulings'])
                return {'pass': False, 'scenes': [{'id': 'S1'}], 'misfits': [{'id': 'S1'}]}
            modules = {'slotfill': SimpleNamespace(holes_of=lambda doc: []),
                       'scenes': SimpleNamespace(json_block=lambda text: (DOC, None)),
                       'sectionfit': SimpleNamespace(plan_of=lambda path: DOC, check=check)}
            with patch.object(V, 'module', side_effect=lambda component, name: modules[name]), \
                    patch.object(V, 'claims_check', return_value={'passed': True}):
                for text in (None, 'Specific source rule.\n' * 6000):
                    if text is not None:
                        (d / 'RULINGS.md').write_text(text)
                    checks = V.check_final(d, {}, out)
                    next(checks); next(checks)
                    name, result = next(checks)
                    self.assertEqual(name, 'sections')
                    # a label disagreement is a note, never a hold (owner ruling, 2026-11-20)
                    self.assertTrue(result['passed'])
                    self.assertFalse(result['judge_pass'])
                    self.assertEqual(result['relabel_notes'][0]['id'], 'S1')
                    self.assertEqual(seen[-1], text or '')
                    checks.close()

    def test_normal_writing_callsite_reads_own_run_rulings(self):
        # Execute the actual call-site statements with a fake section gate,
        # avoiding the unrelated model calls in the large writing runner.
        tree = ast.parse((ROOT / 'components/video-teardown/machine/run.py').read_text())
        assignments = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
        source = next(n for n in assignments if any(isinstance(t, ast.Name) and t.id == '_rulings' for t in n.targets))
        call = next(n for n in assignments if isinstance(n.value, ast.Call)
                    and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'check'
                    and isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == '_sf')
        code = compile(ast.fix_missing_locations(ast.Module(body=[source, call], type_ignores=[])), '<normal section call>', 'exec')
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp); seen = []
            gate = SimpleNamespace(plan_of=lambda out: DOC,
                                   check=lambda plan, **kw: seen.append(kw) or {'pass': False})
            env = {'d': d, 'out': d / 'brief.md', '_sf': gate}
            exec(code, env)
            self.assertEqual(seen[-1]['run_rulings'], '')
            text = 'Exact owner source.\n' * 6000
            (d / 'RULINGS.md').write_text(text)
            exec(code, env)
            self.assertEqual(seen[-1]['run_rulings'], text)
            self.assertEqual(seen[-1]['out_dir'], d / 'section-fit')
            self.assertFalse(env['_res']['pass'])


if __name__ == '__main__':
    unittest.main()
