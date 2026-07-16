#!/usr/bin/env python3
"""
build_site.py — assemble a static, deployable dashboard into ./site/

  python build_site.py

Produces a self-contained folder you can drop on GitHub Pages, Netlify,
or open locally with a static server. Steps:
  1. rebuild data/radar.json from the per-tech files
  2. copy web/{index.html, config.js, dashboard.jsx} into site/
  3. copy data/radar.json into site/data/
  4. strip the `export default` keyword so the CDN/Babel setup can run it

config.js is copied as-is (window.RADAR_EDIT = false), which is what keeps the
deployed dashboard read-only — edit mode only exists when edit_server.py is the
one serving the page.

Also copies web/{books.html, books.jsx} and data/books.json — the Reading
List page, a read-only companion to the tech radar dashboard.

The dashboard stays a plain static page — no bundler, no node_modules.
"""

import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")     # source frontend (index.html, config.js, dashboard.jsx)
SITE = os.path.join(HERE, "site")   # generated, deployable output


def main():
    # 1. refresh radar.json
    sys.path.insert(0, HERE)
    from runner import build_radar_json
    n = build_radar_json()
    print(f"built radar.json ({n} technologies)")

    # 2. clean + recreate site/
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(os.path.join(SITE, "data"))

    # 3. copy index.html + config.js from web/ (config.js ships read-only).
    #    The output stays flat — site/ is index.html + config.js + dashboard.jsx
    #    + data/, so the dashboard's relative fetches resolve unchanged.
    shutil.copy(os.path.join(WEB, "index.html"),
                os.path.join(SITE, "index.html"))
    shutil.copy(os.path.join(WEB, "config.js"),
                os.path.join(SITE, "config.js"))

    # 4. copy dashboard.jsx, stripping `export default` so the
    #    in-browser Babel setup (which expects a global `App`) works.
    with open(os.path.join(WEB, "dashboard.jsx"), encoding="utf-8") as f:
        src = f.read()
    src = re.sub(r"export\s+default\s+function\s+App",
                 "function App", src)
    # the CDN build pulls React via <script>, so drop the import line
    src = re.sub(r'^import\s+React.*?;\s*$', "", src, flags=re.M)
    # re-expose the hooks the dashboard uses from the global React
    hooks = "const { useState, useMemo, useEffect } = React;\n"
    with open(os.path.join(SITE, "dashboard.jsx"), "w", encoding="utf-8") as f:
        f.write(hooks + src)

    # 5. copy the data the dashboard fetches
    shutil.copy(os.path.join(HERE, "data", "radar.json"),
                os.path.join(SITE, "data", "radar.json"))

    # 6. Reading List page — books.html is copied as-is; books.jsx gets the
    #    same export-default strip as dashboard.jsx (expects a global BooksApp).
    shutil.copy(os.path.join(WEB, "books.html"),
                os.path.join(SITE, "books.html"))
    with open(os.path.join(WEB, "books.jsx"), encoding="utf-8") as f:
        books_src = f.read()
    books_src = re.sub(r"export\s+default\s+function\s+BooksApp",
                        "function BooksApp", books_src)
    books_src = re.sub(r'^import\s+React.*?;\s*$', "", books_src, flags=re.M)
    with open(os.path.join(SITE, "books.jsx"), "w", encoding="utf-8") as f:
        f.write(hooks + books_src)
    books_json = os.path.join(HERE, "data", "books.json")
    if os.path.exists(books_json):
        shutil.copy(books_json, os.path.join(SITE, "data", "books.json"))

    # 7. Tool Similarity page — self-contained (inline JSX), copied as-is.
    #    Reads data/radar.json and, if present, data/similarity.json (the
    #    precomputed semantic matrix from build_similarity.py). Without that
    #    file the page falls back to in-browser TF-IDF, so shipping it is
    #    optional.
    shutil.copy(os.path.join(WEB, "similarity.html"),
                os.path.join(SITE, "similarity.html"))
    sim_json = os.path.join(HERE, "data", "similarity.json")
    if os.path.exists(sim_json):
        shutil.copy(sim_json, os.path.join(SITE, "data", "similarity.json"))

    # 8. Projects page — self-contained (inline JSX), copied as-is. Rebuild
    #    data/projects.json from projects/*.md first, then ship it. The optional
    #    data/project_similarity.json (from build_similarity.py) upgrades the
    #    tool recommendations from in-browser TF-IDF to semantic embeddings.
    from build_projects import build_projects_json
    n_proj = build_projects_json()
    print(f"built projects.json ({n_proj} projects)")
    shutil.copy(os.path.join(WEB, "projects.html"),
                os.path.join(SITE, "projects.html"))
    proj_json = os.path.join(HERE, "data", "projects.json")
    if os.path.exists(proj_json):
        shutil.copy(proj_json, os.path.join(SITE, "data", "projects.json"))
    proj_sim = os.path.join(HERE, "data", "project_similarity.json")
    if os.path.exists(proj_sim):
        shutil.copy(proj_sim, os.path.join(SITE, "data", "project_similarity.json"))

    # 9. People page — self-contained (inline JSX), copied as-is. Rebuild
    #    data/people.json from people/*.md first, then ship it. The page reuses
    #    the Projects recommender in-browser (TF-IDF), and also reads the
    #    radar.json + projects.json already copied above for tech and staffing
    #    recommendations — no extra precomputed file required.
    from build_people import build_people_json
    n_people = build_people_json()
    print(f"built people.json ({n_people} {'person' if n_people == 1 else 'people'})")
    shutil.copy(os.path.join(WEB, "people.html"),
                os.path.join(SITE, "people.html"))
    people_json = os.path.join(HERE, "data", "people.json")
    if os.path.exists(people_json):
        shutil.copy(people_json, os.path.join(SITE, "data", "people.json"))
    people_sim = os.path.join(HERE, "data", "people_similarity.json")
    if os.path.exists(people_sim):
        shutil.copy(people_sim, os.path.join(SITE, "data", "people_similarity.json"))

    print(f"site/ ready — {len(os.listdir(SITE))} entries")
    print("preview locally:  cd site && python -m http.server 8000")
    print("deploy: push site/ to GitHub Pages, or drag it onto Netlify")


if __name__ == "__main__":
    main()
