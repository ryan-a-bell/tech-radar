#!/usr/bin/env python3
"""
edit_server.py — local curation server for the technology radar.

  python edit_server.py          # http://localhost:8001/
  python edit_server.py 8080     # custom port

Serves the SAME index.html + dashboard.jsx as the public site, but with one
difference: it answers GET /config.js with `window.RADAR_EDIT = true`, which
unlocks the in-browser ring editor. Ring changes POST to /api/promote and are
written straight to data/items/*.json, rebuilding radar.json immediately.

The deployed GitHub Pages build ships config.js as `false` and has no backend,
so the public radar can't be edited — this server is the only thing that turns
editing on, and only on your machine.
"""

import json
import os
import sys
from datetime import date
from http.server import HTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import radar_core as core
from runner import build_radar_json


class EditHandler(SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self._cors(204)

    def do_GET(self):
        # Override the static config.js to flip the dashboard into edit mode.
        # Everything else (index.html, dashboard.jsx, data/) is served as-is.
        if self.path.split("?")[0] == "/config.js":
            body = b"window.RADAR_EDIT = true;\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/promote":
            body = self._read_json()
            item_id = body.get("id", "")
            ring = body.get("ring", "")

            if ring not in core.RINGS:
                return self._json({"error": f"ring must be one of {core.RINGS}"}, 400)

            path = core.id_to_path(item_id)
            if not os.path.exists(path):
                return self._json({"error": "item not found"}, 404)

            with open(path, encoding="utf-8") as f:
                item = json.load(f)
            old_ring = item["ring"]
            item["ring"] = ring
            # maintain the archived_at stamp on the way in/out of Archived,
            # matching radar.py's _set_ring so both curation paths agree
            if ring == "Archived":
                item["archived_at"] = item.get("archived_at") or date.today().isoformat()
            else:
                item["archived_at"] = None
            with open(path, "w", encoding="utf-8") as f:
                json.dump(item, f, indent=2)
            build_radar_json()

            print(f"  {item['name']}: {old_ring} → {ring}")
            self._json({"ok": True, "id": item_id, "ring": ring, "name": item["name"]})
        else:
            self._json({"error": "unknown endpoint"}, 404)

    # --- helpers ---

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self, status):
        self.send_response(status)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "http://localhost:8001")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        if args and str(args[0]).startswith("POST"):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    os.chdir(HERE)
    server = HTTPServer(("", port), EditHandler)
    print(f"  edit server → http://localhost:{port}/")
    print("  Ctrl+C to stop")
    server.serve_forever()
