// Runtime config for the dashboard. The static (GitHub Pages) build ships this
// file unchanged, so the public radar is READ-ONLY. edit_server.py intercepts
// the request for this file and returns `true` instead, which is what flips on
// the in-browser ring editor. One dashboard.jsx, two behaviours — decided here.
window.RADAR_EDIT = false;
