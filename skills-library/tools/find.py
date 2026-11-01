"""find.py <words...> — rank the skill library for a job. Reads catalog.json next to this folder."""
import json, os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
lib = os.path.dirname(here)
cat = json.load(open(os.path.join(lib, 'catalog.json')))
ROOT = {'library': 'references', 'workspace': '~/Projects/workspace'}
# trust tier: official vendors first, then high-adoption community
TIER = {'anthropics_skills': 3, 'anthropics_claude-plugins-official': 3, 'anthropics_knowledge-work-plugins': 3,
        'expo_skills': 3, 'greensock_gsap-skills': 3, 'remotion-dev_skills': 3, 'NextCommerceCo_skills': 3,
        'obra_superpowers': 2, 'coreyhaines31_marketingskills': 2, 'wshobson_agents': 2,
        'nextlevelbuilder_ui-ux-pro-max-skill': 2, 'workspace': 3, 'rampstackco_claude-skills': 1, 'jgerton_brand-toolkit': 1}
words = [w.lower() for w in re.findall(r'\w+', ' '.join(sys.argv[1:])) if len(w) > 2]
seen, hits = set(), []
for s in cat:
    key = (s['name'], s['source'])
    if key in seen: continue
    seen.add(key)
    name, desc = s['name'].lower(), s['description'].lower()
    score = sum(3 * (w in name) + desc.count(w) for w in words)
    if score: hits.append((score + TIER.get(s['source'], 0), s))
hits.sort(key=lambda h: -h[0])
for sc, s in hits[:int(os.environ.get('N', 12))]:
    print(f"{sc:>3}  {s['name']:<34} {s['source']:<38} {ROOT[s.get('root','library')]}/{s['path']}\n     {s['description'][:160]}")
