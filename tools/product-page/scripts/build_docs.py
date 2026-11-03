#!/usr/bin/env python3
"""Writes BLOCKS.md from blocks.json, so the block library has one source."""
import json, os
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lib = json.load(open(os.path.join(here, 'blocks.json')))
out = ['# The blocks', '', lib['about'], '', '## Inputs', ''] + [f'- **{k}**: {v}' for k, v in lib['inputs'].items()] + ['', 'Moves used when refining a page: ' + ', '.join(lib['moves']) + '.', '']
for zone in lib['zones']:
    out += [f'## {zone}', '']
    for b in [b for b in lib['blocks'] if b['zone'] == zone]:
        out += [f"### {b['id']}", '', f"**Job:** {b['job']}", '', f"**Inputs:** {'; '.join(b['inputs'])}", '',
                f"**Evidence:** {b['evidence']}", '', '**Rules:**', ''] + [f'- {r}' for r in b['rules']] + ['']
        if b['artwork']:
            out += [f"**Artwork:** {'; '.join(b['artwork'])}", '']
        out += ['**Checks:**', ''] + [f'- [ ] {c}' for c in b['checks']] + ['']
out += ['## Kinds of product', ''] + [f'- **{k}**: {v}' for k, v in lib['kinds'].items()] + ['', '## Recipes: block order per kind', '']
for kind, ids in lib['recipes'].items():
    out += [f'**{kind}**: ' + ' → '.join(ids), '']
open(os.path.join(here, 'BLOCKS.md'), 'w').write('\n'.join(out))
print('BLOCKS.md written:', len(lib['blocks']), 'blocks,', len(lib['recipes']), 'recipes')
