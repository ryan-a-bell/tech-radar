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

    print(f"site/ ready — {len(os.listdir(SITE))} entries")
    print("preview locally:  cd site && python -m http.server 8000")
    print("deploy: push site/ to GitHub Pages, or drag it onto Netlify")


if __name__ == "__main__":
    main()
