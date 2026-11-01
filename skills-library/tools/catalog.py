"""catalog.py — index every SKILL.md in the library and, read-only, in the team workspace.

Writes catalog.json (local only, never committed). Run from skills-library/:
    python3 tools/catalog.py
The team workspace is read in place: nothing is copied out of it and nothing is written to it.
"""
import os, re, json
LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = {'library': os.path.join(LIB, 'references'),
         'workspace': os.path.expanduser('~/Projects/workspace')}
SKIP = {'.git', 'node_modules', 'archive', '_archive', 'runs', 'output', 'worktrees', 'inbound'}
try:
    import yaml
except ImportError:
    yaml = None

def meta_of(text):
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.S)
    if not m: return {}
    if yaml:
        try: return yaml.safe_load(m.group(1)) or {}
        except Exception: pass
    meta, k = {}, None
    for line in m.group(1).splitlines():
        if line[:1] not in (' ', '\t') and ':' in line:
            k, v = line.split(':', 1); k, v = k.strip(), v.strip()
            meta[k] = '' if v in ('>', '|', '>-', '|-') else v.strip('"\'')
        elif k and line.strip():
            meta[k] = (meta[k] + ' ' + line.strip()).strip()
    return meta

out = []
for label, root in ROOTS.items():
    if not os.path.isdir(root): continue
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP]
        if 'SKILL.md' not in fn: continue
        p = os.path.join(dp, 'SKILL.md')
        meta = meta_of(open(p, encoding='utf-8', errors='ignore').read())
        rel = os.path.relpath(p, root)
        out.append({'name': str(meta.get('name') or os.path.basename(dp)),
                    'description': ' '.join(str(meta.get('description', '')).split())[:400],
                    'source': label if label != 'library' else rel.split('/')[0],
                    'root': label, 'path': rel})
json.dump(out, open(os.path.join(LIB, 'catalog.json'), 'w'), indent=1)
print(len(out), 'skills;', sum(o['root'] == 'workspace' for o in out), 'from the team workspace (read in place)')
