#!/usr/bin/env python3
"""Offer workspace contract and explicitly adapted shared tools; standard library only."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PRIZM = HERE.parents[1]

def local(root, value):
    p = (root / value).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError('Workspace path escapes its repository: ' + str(value))
    return p

def load(root):
    manifest = json.loads((root / 'offer-workspace.json').read_text())
    if manifest.get('schema_version') != 1:
        raise ValueError('Unsupported workspace schema')
    brand_id = manifest['brand_id']
    if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', brand_id):
        raise ValueError('Invalid brand ID')
    if manifest['brand_root'] != 'brands/' + brand_id:
        raise ValueError('Brand folder must match brand ID')
    for key in ('brand_root','offers_root','runs_root'):
        local(root, manifest[key])
    return manifest

def check(root):
    m = load(root)
    brand = local(root, m['brand_root'])
    errors = []
    for name in ('operations/brand.json','core-avatars/primary/profile.md','strategy/angles.json','products/offer-bank.md','sources/index.json'):
        if not (brand / name).is_file(): errors.append('Missing brand context: ' + name)
    peers = [x.name for x in (root/'brands').iterdir() if x.is_dir() and x.name != m['brand_id']]
    if peers: errors.append('Unexpected other brand folders: '+', '.join(peers))
    offers = sorted(local(root,m['offers_root']).glob('*/offer.json'))
    if not offers: errors.append('No structured offers')
    ids = set()
    for p in offers:
        x = json.loads(p.read_text())
        if x.get('id') != p.parent.name or x['id'] in ids: errors.append('Duplicate/mismatched offer ID: '+str(p))
        ids.add(x.get('id'))
        if x.get('brand_id') != m['brand_id']: errors.append('Offer belongs to another brand')
        if not x.get('outcome') or not x.get('deliverables'): errors.append('Offer missing outcome or deliverables')
        if x.get('status') not in ('hypothesis','draft','validated','retired'): errors.append('Unknown offer status')
        if not isinstance(x.get('version'),int) or x['version']<1: errors.append('Invalid offer version')
    sources = json.loads((brand/'sources/index.json').read_text()) if (brand/'sources/index.json').is_file() else []
    for s in sources:
        if s.get('status') not in ('observed','operator-reported','proposed','unknown'): errors.append('Invalid source status: '+s.get('id',''))
    return {'brand_id':m['brand_id'],'offers':sorted(ids),'errors':errors,'status':'pass' if not errors else 'fail'}

def context(root):
    m=load(root)
    return {**m,'resolved_brand_root':str(local(root,m['brand_root'])),
            'shared_tools':str(PRIZM/'tools'),'shared_components':str(PRIZM/'components'),
            'shared_skills':str(PRIZM/'skills-library'),'adapted_commands':['check','context','page','offer','skills-find'],
            'legacy_tools':'Available for inspection; tools that write beside their code need an output-path adapter before running. A brand environment variable alone is not sufficient isolation.'}

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True,type=Path)
    p.add_argument('command',choices=['check','context','page','offer','skills-find']);p.add_argument('args',nargs=argparse.REMAINDER)
    a=p.parse_args(argv);root=a.workspace.resolve();m=load(root)
    if a.command in ('check','context'):
        value=check(root) if a.command=='check' else context(root)
        print(json.dumps(value,indent=2));return 1 if value.get('errors') else 0
    if a.command=='skills-find':
        if a.args in (['--help'],['-h']):
            print('Usage: scripts/prizm.py skills-find <words> — search versioned local tool/skill documents');return 0
        words=' '.join(a.args).lower().split()
        candidates=list((PRIZM/'skills-library').rglob('*.md'))
        for folder in ('tools','components'):
            candidates += [f for f in (PRIZM/folder).rglob('*.md') if f.name in ('SKILL.md','README.md','CLAUDE.md')]
        hits=[]
        for f in sorted(set(candidates)):
            if f.is_symlink() or f.stat().st_size>200000:continue
            rel=f.relative_to(PRIZM).as_posix();body=f.read_text(errors='replace')
            if all(w in (rel+' '+body).lower() for w in words):
                hits.append({'path':rel,'title':next((l.lstrip('# ').strip() for l in body.splitlines() if l.startswith('#')) ,f.stem)})
        print(json.dumps({'query':' '.join(words),'matches':len(hits),'documents':hits[:50],'note':'Discovery only. Inspect each capability and its external dependencies before execution.'},indent=2));return 0
    env=os.environ.copy();env.update(AI_WORKSPACE=str(root),PRIZM_BRAND_ROOT=str(local(root,m['brand_root'])),VIDEO_MACHINE_BRANDS=str(root/'brands'),PRIZM_RUNS_ROOT=str(local(root,m['runs_root'])))
    entry={'page':HERE/'page/scripts/page_build.py','offer':HERE/'offer/scripts/offer.py','skills-find':PRIZM/'skills-library/tools/find.py'}[a.command]
    if a.command=='page':
        env['PRIZM_PAGE_SECTIONS']=str(local(root,m['page_sections']))
    return subprocess.run([sys.executable,str(entry),*a.args],cwd=root,env=env).returncode

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as e:raise SystemExit('Workspace error: '+str(e))
