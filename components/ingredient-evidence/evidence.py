#!/usr/bin/env python3
"""ingredient-evidence: the published studies on one ingredient for one problem, ranked by strength, every line linked.

    evidence.py search --ingredient "cranberry" --problem "lower urinary tract symptoms" [--men] [--max 40] --out DIR
    evidence.py show DIR

Reads PubMed (the US National Library of Medicine's free public index) through its E-utilities. No key needed;
NCBI_API_KEY in the environment raises the rate limit. Nothing is written but DIR/evidence.json and DIR/EVIDENCE.md.

Strength order, strongest first: meta-analysis, systematic review, randomised controlled trial, other clinical trial,
everything else (dropped unless nothing stronger exists). Each study keeps its PubMed link, year, journal, kind,
and its abstract's conclusion and results lines, verbatim, so the mechanism and the proof come only from these.
Python 3.9, standard library only.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RANK = [("Meta-Analysis", "meta-analysis"), ("Systematic Review", "systematic review"),
        ("Randomized Controlled Trial", "randomised trial"), ("Clinical Trial", "clinical trial")]


def get(path, **params):
    key = os.environ.get("NCBI_API_KEY")
    if key:
        params["api_key"] = key
    params.setdefault("tool", "prizm-ingredient-evidence")
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.5)


def search(ingredient, problem, men, cap):
    types = " OR ".join('"%s"[pt]' % t for t, _ in RANK)
    term = '(%s[tiab]) AND (%s) AND (%s) AND humans[mh]' % (ingredient, problem, types)
    if men:
        term += " AND male[mh]"
    ids = json.loads(get("esearch.fcgi", db="pubmed", term=term, retmax=cap, retmode="json", sort="relevance"))
    return term, ids["esearchresult"].get("idlist", [])


def text(node):
    return "".join(node.itertext()).strip() if node is not None else ""


def fetch(ids):
    out = []
    for i in range(0, len(ids), 50):
        root = ET.fromstring(get("efetch.fcgi", db="pubmed", id=",".join(ids[i:i + 50]), retmode="xml"))
        for art in root.iter("PubmedArticle"):
            pmid = text(art.find(".//PMID"))
            types = [text(t) for t in art.iter("PublicationType")]
            kind, strength = "other", len(RANK)
            for n, (t, label) in enumerate(RANK):
                if t in types:
                    kind, strength = label, n
                    break
            parts = {}
            for ab in art.iter("AbstractText"):
                lab = (ab.get("Label") or ab.get("NlmCategory") or "TEXT").upper()
                parts[lab] = (parts.get(lab, "") + " " + text(ab)).strip()
            concl = next((v for k, v in parts.items() if k.startswith("CONCLUSION")), "")
            results = next((v for k, v in parts.items() if k.startswith("RESULT")), "")
            if not concl and "TEXT" in parts:
                sents = re.split(r"(?<=[.!?])\s+", parts["TEXT"])
                concl, results = " ".join(sents[-2:]), " ".join(sents[-5:-2])
            year = text(art.find(".//PubDate/Year")) or text(art.find(".//PubDate/MedlineDate"))[:4]
            out.append({"pmid": pmid, "url": "https://pubmed.ncbi.nlm.nih.gov/%s/" % pmid,
                        "title": text(art.find(".//ArticleTitle")), "journal": text(art.find(".//Journal/Title")),
                        "year": year, "kind": kind, "strength": strength,
                        "results": results[:900], "conclusion": concl[:600]})
        time.sleep(0.4)
    return sorted(out, key=lambda s: (s["strength"], -int(s["year"] or 0)))


def write(d, doc):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "evidence.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    lines = ["# Evidence: %s for %s" % (doc["ingredient"], doc["problem"]), "",
             "Pulled %s from PubMed. Search: `%s`. %d studies, strongest first. Lines below are verbatim from each abstract." % (
                 doc["pulled"], doc["term"], len(doc["studies"])), ""]
    counts = {}
    for s in doc["studies"]:
        counts[s["kind"]] = counts.get(s["kind"], 0) + 1
    lines += ["| Kind | Studies |", "|---|---|"] + ["| %s | %d |" % (k, v) for k, v in counts.items()] + [""]
    for s in doc["studies"]:
        lines += ["## %s (%s, %s)" % (s["title"], s["kind"], s["year"]), "%s · %s" % (s["journal"], s["url"]), ""]
        if s["results"]:
            lines += ["**Results:** " + s["results"], ""]
        if s["conclusion"]:
            lines += ["**Conclusion:** " + s["conclusion"], ""]
    (d / "EVIDENCE.md").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="do", required=True)
    s = sub.add_parser("search")
    s.add_argument("--ingredient", required=True); s.add_argument("--problem", required=True)
    s.add_argument("--men", action="store_true"); s.add_argument("--max", type=int, default=40)
    s.add_argument("--out", required=True)
    v = sub.add_parser("show"); v.add_argument("dir")
    a = ap.parse_args()
    if a.do == "show":
        doc = json.loads((Path(a.dir) / "evidence.json").read_text())
        for st in doc["studies"]:
            print("%-17s %s  %s" % (st["kind"], st["year"], st["title"][:90]))
        return 0
    term, ids = search(a.ingredient, a.problem, a.men, a.max)
    studies = fetch(ids) if ids else []
    doc = {"ingredient": a.ingredient, "problem": a.problem, "men_only": a.men, "term": term,
           "pulled": time.strftime("%Y-%m-%d"), "studies": studies}
    write(a.out, doc)
    print("%d studies → %s" % (len(studies), Path(a.out) / "EVIDENCE.md"))
    return 0 if studies else 3


if __name__ == "__main__":
    sys.exit(main())
