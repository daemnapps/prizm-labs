"""Capture: write a Higgsfield pull, word for word, from a Claude session's raw transcripts into sources/higgsfield/.

    python3 components/workflow-teardown/tools/harvest.py <session transcript folder or .jsonl> [--out <dir>]

Run it after a session has made the read-only calls (get_workflow_instructions, get_workflow_bundle_file,
get_preset_instructions, ads_studio_story_presets, ads_studio_story_recipe). It reads the session's own .jsonl and its
subagents/ transcripts, follows results the harness saved to disk, and writes each answer as the tool gave it. Nothing is
retyped. Python 3.9, stdlib only.
"""
import json, glob, os, re, sys

if len(sys.argv) < 2:
    sys.exit(__doc__)
SESS = sys.argv[1][:-6] if sys.argv[1].endswith('.jsonl') else sys.argv[1].rstrip('/')
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sources', 'higgsfield')
TOOLS = {'get_workflow_instructions', 'get_workflow_bundle_file', 'get_preset_instructions',
         'ads_studio_story_presets', 'ads_studio_story_recipe'}
PATH_RE = re.compile(r'saved to:? (/\S+?\.txt)')

files = [f for f in [SESS + '.jsonl'] if os.path.exists(f)] + sorted(glob.glob(SESS + '/subagents/agent-*.jsonl'))
uses, results = {}, []
for f in files:
    for line in open(f):
        try: e = json.loads(line)
        except Exception: continue
        c = e.get('message', {}).get('content')
        if not isinstance(c, list): continue
        for b in c:
            if b.get('type') == 'tool_use':
                n = b['name'].split('__')[-1]
                if n in TOOLS: uses[b['id']] = (n, b.get('input') or {})
            elif b.get('type') == 'tool_result' and b.get('tool_use_id') in uses:
                cc = b['content']
                if isinstance(cc, list): cc = ''.join(x.get('text', '') for x in cc if x.get('type') == 'text')
                results.append((uses[b['tool_use_id']], cc))

def load(cc):
    m = PATH_RE.search(cc[:1500])
    if m and os.path.exists(m.group(1)) and (cc.startswith('Error: result') or cc.startswith('<persisted-output>')):
        cc = open(m.group(1)).read()
    try: return json.loads(cc)
    except Exception: return cc

def safe(s): return re.sub(r'[^A-Za-z0-9._-]+', '-', s).strip('-').lower() or 'index'

def write(rel, text):
    p = os.path.join(OUT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w').write(text if text.endswith('\n') else text + '\n'); written.append(rel)

def md_for(path, content):
    if path.endswith('.md'): return path, content
    ext = path.rsplit('.', 1)[-1] if '.' in path else ''
    lang = {'py': 'python', 'json': 'json', 'js': 'javascript', 'html': 'html', 'txt': '', 'yaml': 'yaml', 'yml': 'yaml', 'css': 'css', 'sh': 'bash'}.get(ext, '')
    return path + '.md', f'<!-- verbatim copy of {path} -->\n\n```{lang}\n{content}\n```\n'

written, errors, catalogs = [], [], {}
for (name, inp), cc in results:
    d = load(cc)
    if name == 'get_workflow_instructions':
        if not isinstance(d, dict): errors.append((name, inp, str(d)[:200])); continue
        if d.get('mode') == 'catalog': catalogs['workflows'] = d; continue
        wf = d['workflow']
        write(f'{wf}/SKILL.md', d['instructions_markdown'])
        meta = {k: v for k, v in d.items() if k != 'instructions_markdown'}
        write(f'{wf}/_files.md', '# Files in this workflow\n\n```json\n' + json.dumps(meta, indent=1, ensure_ascii=False) + '\n```')
    elif name == 'get_workflow_bundle_file':
        if not isinstance(d, dict) or 'content' not in d:
            if isinstance(d, dict) and d.get('kind') == 'directory':
                continue
            errors.append((name, inp, str(d)[:200])); continue
        if d.get('kind') == 'directory': continue
        rel, text = md_for(d['path'], d['content'])
        write(f"{d['workflow']}/{rel}", text)
    elif name == 'get_preset_instructions':
        if not isinstance(d, dict): errors.append((name, inp, str(d)[:200])); continue
        if d.get('mode') == 'catalog' and 'presets' in d and not inp.get('preset'): catalogs['presets'] = d; continue
        p = inp.get('preset', 'index')
        body = d.get('instructions_markdown')
        if body is None: body = '```json\n' + json.dumps(d, indent=1, ensure_ascii=False) + '\n```'
        pid = (d.get('preset') or {}).get('id') if isinstance(d.get('preset'), dict) else None
        folder = 'presets' if pid and ('/' + pid) == p else 'commands'
        write(f'{folder}/{safe(p)}.md', body)
    elif name == 'ads_studio_story_presets':
        write('drama-ads/catalog/_cards.md', '# Drama Ads catalog (ads_studio_story_presets)\n\n```json\n' + (json.dumps(d, indent=1, ensure_ascii=False) if not isinstance(d, str) else d) + '\n```')
    elif name == 'ads_studio_story_recipe':
        write(f"drama-ads/catalog/{safe(inp['preset_id'])}.md", '```json\n' + (json.dumps(d, indent=1, ensure_ascii=False) if not isinstance(d, str) else d) + '\n```')

if 'workflows' in catalogs:
    write('_catalog-workflows.md', '# Workflow catalog (get_workflow_instructions, no argument)\n\n```json\n' + json.dumps(catalogs['workflows'], indent=1, ensure_ascii=False) + '\n```')
if 'presets' in catalogs:
    write('_catalog-presets.md', '# Preset catalog (get_preset_instructions, no argument)\n\n```json\n' + json.dumps(catalogs['presets'], indent=1, ensure_ascii=False) + '\n```')
print(len(written), 'files written,', len(set(written)), 'unique')
for e in errors: print('ERR', e)

# name the Drama Ads catalog cards by their titles
cards = os.path.join(OUT, 'drama-ads', 'catalog', '_cards.md')
if os.path.exists(cards):
    t = open(cards).read()
    try:
        for c in json.loads(t[t.index('{'):t.rindex('}') + 1]).get('cards', []):
            src = os.path.join(OUT, 'drama-ads', 'catalog', safe(c['id']) + '.md')
            if os.path.exists(src):
                os.replace(src, os.path.join(OUT, 'drama-ads', 'catalog', safe(c['title']) + '.md'))
    except ValueError:
        pass
