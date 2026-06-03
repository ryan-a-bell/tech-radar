#!/usr/bin/env python3
"""
build_site.py — assemble a static, deployable dashboard into ./site/

  python build_site.py

Produces a self-contained folder you can drop on GitHub Pages, Netlify,
or open locally with a static server. Steps:
  1. rebuild data/radar.json from the per-tech files
  2. copy index.html + the dashboard into site/
  3. copy data/radar.json into site/data/
  4. strip the `export default` keyword so the CDN/Babel setup can run it

The dashboard stays a plain static page — no bundler, no node_modules.
"""

import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")


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

    # 3. copy index.html
    shutil.copy(os.path.join(HERE, "index.html"),
                os.path.join(SITE, "index.html"))

    # 4. copy dashboard.jsx, stripping `export default` so the
    #    in-browser Babel setup (which expects a global `App`) works.
    with open(os.path.join(HERE, "dashboard.jsx")) as f:
        src = f.read()
    src = re.sub(r"export\s+default\s+function\s+App",
                 "function App", src)
    # the CDN build pulls React via <script>, so drop the import line
    src = re.sub(r'^import\s+React.*?;\s*$', "", src, flags=re.M)
    # re-expose the hooks the dashboard uses from the global React
    hooks = "const { useState, useMemo, useEffect } = React;\n"
    with open(os.path.join(SITE, "dashboard.jsx"), "w") as f:
        f.write(hooks + src)

    # 5. copy the data the dashboard fetches
    shutil.copy(os.path.join(HERE, "data", "radar.json"),
                os.path.join(SITE, "data", "radar.json"))

    print(f"site/ ready — {len(os.listdir(SITE))} entries")
    print("preview locally:  cd site && python -m http.server 8000")
    print("deploy: push site/ to GitHub Pages, or drag it onto Netlify")


if __name__ == "__main__":
    main()
