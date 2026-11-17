#!/usr/bin/env python3
"""
build.py — turns src/pages/*.html fragments + src/references.json into the static site.

Why a build step? So the resource can be updated as evidence changes without hand-editing
seven pages of navigation, numbering and reference lists. To update the site:

  1. edit a fragment in src/pages/ (or add a reference to src/references.json — APPEND new
     references at the end so existing numbers never change)
  2. run:  python build.py
  3. commit the regenerated *.html files and push (GitHub Pages serves them as-is)

Macros available inside fragments
  {{cite:key1,key2}}        numbered citation(s) linking to references.html
  {{lo:RW7}}                Delphi learning-outcome tag (links to curriculum.html)
  {{basic}} / {{adv}}       level chips
  {{band:alpha}}            colour swatch matching the figures
  {{fig:file.png|alt|caption}}
  {{sfig:drug_sevo|alt|caption}}   figure that swaps with the band-scheme toggle
                                   (expects img/drug_sevo_purdon.png and img/drug_sevo_lee.png)
Fragment header (HTML comment, first thing in the file):
  title / nav / module (number, optional) / description / reviewed (YYYY-MM-DD)
No third-party packages needed.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "pages")
SITE_TITLE = "EEG for Anaesthetists"

REFS = json.load(open(os.path.join(ROOT, "src", "references.json"), encoding="utf-8"))
REF_NUM = {r["key"]: i + 1 for i, r in enumerate(REFS)}

COURSE = ["fundamentals", "raw-eeg", "drug-signatures", "processed-eeg", "in-theatre", "evidence", "under-the-hood"]
REFERENCE = ["curriculum", "further-learning", "references", "roadmap", "about"]


def parse(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"\s*<!--(.*?)-->", raw, re.S)
    meta = {}
    for line in m.group(1).strip().splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    meta["body"] = raw[m.end():]
    meta["slug"] = os.path.splitext(os.path.basename(path))[0]
    return meta


def cite(m):
    keys = [k.strip() for k in m.group(1).split(",")]
    for k in keys:
        if k not in REF_NUM:
            raise SystemExit(f"unknown reference key: {k}")
    links = ",".join(f'<a href="references.html#r-{k}" title="{html.escape(REFS[REF_NUM[k]-1]["text"][:140])}">{REF_NUM[k]}</a>' for k in keys)
    return f'<sup class="ref">[{links}]</sup>'


def fig(m, swap):
    name, alt, cap = (p.strip() for p in m.group(1).split("|", 2))
    syn = '<span class="synthetic"> Synthetic signal generated for teaching (<a href="under-the-hood.html#figures">how</a>).</span>'
    cap = cap.replace("[nosyn]", "")
    syn = "" if "[nosyn]" in m.group(1) else syn
    if swap:
        imgs = (f'<img data-show-scheme="purdon" src="img/{name}_purdon.png" alt="{html.escape(alt)} (Purdon band definitions)" loading="lazy">'
                f'<img data-show-scheme="lee" src="img/{name}_lee.png" alt="{html.escape(alt)} (Lee band definitions)" loading="lazy">')
    else:
        imgs = f'<img src="img/{name}" alt="{html.escape(alt)}" loading="lazy">'
    return f'<figure class="fig-wide">{imgs}<figcaption>{cap}{syn}</figcaption></figure>'


def render(body):
    body = re.sub(r"\{\{cite:([^}]+)\}\}", cite, body)
    body = re.sub(r"\{\{lo:([A-Z]{2}\d+)\}\}", lambda m: f'<span class="lo">Delphi <a href="curriculum.html#{m.group(1)}">{m.group(1)}</a></span>', body)
    body = body.replace("{{basic}}", '<span class="lvl basic">Basic</span>').replace("{{adv}}", '<span class="lvl adv">Advanced</span>')
    body = re.sub(r"\{\{band:(\w+)\}\}", lambda m: f'<span class="band b-{m.group(1)}" aria-hidden="true"></span>', body)
    body = re.sub(r"\{\{sfig:(.+?)\}\}", lambda m: fig(m, True), body, flags=re.S)
    body = re.sub(r"\{\{fig:(.+?)\}\}", lambda m: fig(m, False), body, flags=re.S)
    if "{{" in body:
        raise SystemExit("unexpanded macro: " + body[body.index("{{"):][:60])
    return body


def nav(pages, current):
    def link(slug):
        p = pages[slug]
        cur = ' aria-current="page"' if slug == current else ""
        return f'<li><a href="{slug}.html"{cur}>{html.escape(p["nav"])}</a></li>'
    home_cur = ' aria-current="page"' if current == "index" else ""
    return (f'<nav class="site-nav" id="site-nav" aria-label="Site">'
            f'<ul><li><a href="index.html"{home_cur}>Start here</a></li></ul>'
            f'<h2>Course</h2><ol>{"".join(link(s) for s in COURSE)}</ol>'
            f'<h2>Reference</h2><ul>{"".join(link(s) for s in REFERENCE)}</ul></nav>')


def pager(pages, slug):
    if slug not in COURSE:
        return ""
    i = COURSE.index(slug)
    prev = f'<a href="{COURSE[i-1]}.html"><span>Previous</span>{html.escape(pages[COURSE[i-1]]["title"])}</a>' if i else '<a href="index.html"><span>Previous</span>Start here</a>'
    nxt = f'<a href="{COURSE[i+1]}.html" style="text-align:right"><span>Next</span>{html.escape(pages[COURSE[i+1]]["title"])}</a>' if i < len(COURSE) - 1 else '<a href="curriculum.html" style="text-align:right"><span>Next</span>Curriculum map</a>'
    return f'<nav class="pager" aria-label="Course pages">{prev}{nxt}</nav>'


TEMPLATE = """<!doctype html>
<html lang="en-ZA" data-scheme="purdon">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/site.css">
<script>try{{var s=localStorage.getItem("eeg-scheme");if(s==="lee"||s==="purdon")document.documentElement.dataset.scheme=s;}}catch(e){{}}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <a class="brand" href="index.html">{site} <span>· an open teaching resource</span></a>
  <div class="scheme">
    <span id="scheme-label">Band definitions</span>
    <div role="radiogroup" aria-labelledby="scheme-label">
      <button type="button" role="radio" data-scheme-btn="purdon" aria-checked="true">Purdon 2015</button>
      <button type="button" role="radio" data-scheme-btn="lee" aria-checked="false">Lee 2021</button>
    </div>
  </div>
  <button class="nav-toggle" type="button" aria-controls="site-nav" aria-expanded="false">Menu</button>
</header>
<div class="layout">
{nav}
<main id="main">
<article class="prose-root">
{body}
</article>
{pager}
</main>
</div>
<footer class="site-foot">
  <p>For education only. This is not a clinical protocol and does not replace your monitor's instructions for use, your department's guidelines or clinical judgement. Every EEG image on this site is synthetic unless stated otherwise.</p>
  <p>Page last reviewed {reviewed}. Content licensed <a href="about.html#licence">CC BY-NC-SA 4.0</a>. Found an error or new evidence? See <a href="about.html#contribute">how to contribute</a>.</p>
</footer>
<script src="assets/site.js"></script>
</body>
</html>
"""


def main():
    pages = {}
    for fn in sorted(os.listdir(SRC)):
        if fn.endswith(".html"):
            p = parse(os.path.join(SRC, fn))
            pages[p["slug"]] = p
    missing = [s for s in COURSE + REFERENCE + ["index"] if s not in pages]
    if missing:
        raise SystemExit(f"missing fragments: {missing}")
    for slug, p in pages.items():
        body = render(p["body"])
        if slug == "index":
            body = body.replace("<!--HEROPATH-->", open(os.path.join(ROOT, "img", "hero_path.txt")).read().strip())
        if slug == "references":
            body = body.replace("<!--REFLIST-->", reflist())
        title = SITE_TITLE if slug == "index" else f'{p["title"]} — {SITE_TITLE}'
        out = TEMPLATE.format(title=html.escape(title), desc=html.escape(p.get("description", "")),
                              site=SITE_TITLE, nav=nav(pages, slug), body=body,
                              pager=pager(pages, slug), reviewed=p.get("reviewed", ""))
        open(os.path.join(ROOT, f"{slug}.html"), "w", encoding="utf-8").write(out)
        print("built", slug + ".html")


def reflist():
    items = []
    for r in REFS:
        bits = [html.escape(r["text"])]
        if r.get("doi"):
            bits.append(f'doi: <a href="https://doi.org/{r["doi"]}">{r["doi"]}</a>')
        if r.get("url"):
            bits.append(f'<a href="{r["url"]}">Full text / link</a>')
        note = f'<br><span class="licence">{html.escape(r["note"])}</span>' if r.get("note") else ""
        items.append(f'<li id="r-{r["key"]}">{". ".join(bits)}{note}</li>')
    return '<ol class="refs">' + "".join(items) + "</ol>"


if __name__ == "__main__":
    main()
