import React, { useState, useMemo, useEffect } from "react";

/* ============================================================
   TECHNOLOGY RADAR — EDIT DASHBOARD
   Local-only curation view. Requires edit_server.py to be running.
   Ring changes POST to /api/promote and write to disk immediately —
   no copy-paste commands needed. Not for sharing; use index.html for that.

   Start with:  python edit_server.py
   Then open:   http://localhost:8001/edit.html
   ============================================================ */

const QUADRANTS = ["Techniques", "Tools", "Platforms", "Languages"];
// Discovered is the outermost ring — staging area for un-triaged tech.
const RINGS = ["Adopt", "Trial", "Assess", "Hold", "Discovered"];

const RING_COLOR = {
  Adopt: "#4ade80", Trial: "#38bdf8", Assess: "#fbbf24",
  Hold: "#f87171", Discovered: "#a78bfa",
};
const RING_INK = {
  Adopt: "#1a7f4b", Trial: "#1d6fb8", Assess: "#b8841d",
  Hold: "#b13a3a", Discovered: "#6d4fc4",
};

/* Fallback sample — used if radar.json can't be fetched. */
const SAMPLE = {
  generated: "2026-05-23",
  items: [
    { id: "github:oven-sh/bun", name: "Bun", description: "All-in-one JavaScript runtime and toolkit with a built-in bundler, test runner, and Node-compatible package manager.", quadrant: "Platforms", ring: "Trial", source: "GitHub", url: "#", stars: 78900, momentum: 72, tags: ["runtime"], first_seen: "2026-05-21", last_seen: "2026-05-23" },
    { id: "github:astral-sh/uv", name: "uv", description: "Extremely fast Python package and project manager, written in Rust.", quadrant: "Tools", ring: "Adopt", source: "GitHub", url: "#", stars: 39800, momentum: 76, tags: ["python"], first_seen: "2026-05-14", last_seen: "2026-05-23" },
    { id: "github:modelcontextprotocol/servers", name: "MCP Servers", description: "Reference implementations for the Model Context Protocol, connecting LLMs to tools and data.", quadrant: "Techniques", ring: "Trial", source: "GitHub", url: "#", stars: 28700, momentum: 91, tags: ["llm"], first_seen: "2026-05-22", last_seen: "2026-05-23" },
    { id: "github:zed-industries/zed", name: "Zed", description: "High-performance, multiplayer code editor written in Rust with an agentic editing mode.", quadrant: "Tools", ring: "Assess", source: "GitHub", url: "#", stars: 51200, momentum: 64, tags: ["editor"], first_seen: "2026-05-15", last_seen: "2026-05-23" },
    { id: "github:tursodatabase/libsql", name: "libSQL", description: "Open-source fork of SQLite with edge-replicated embedded replicas.", quadrant: "Platforms", ring: "Discovered", source: "GitHub", url: "#", stars: 12800, momentum: 58, tags: ["database"], first_seen: "2026-05-23", last_seen: "2026-05-23" },
    { id: "github:gleam-lang/gleam", name: "Gleam", description: "Type-safe, friendly language for building scalable systems on the Erlang VM.", quadrant: "Languages", ring: "Discovered", source: "GitHub", url: "#", stars: 18100, momentum: 44, tags: ["functional"], first_seen: "2026-05-23", last_seen: "2026-05-23" },
    { id: "hn:valkey-multithread", name: "Valkey", description: "Community-driven Redis fork under the Linux Foundation; multi-threaded core.", quadrant: "Platforms", ring: "Discovered", source: "HackerNews", url: "#", stars: 21500, momentum: 67, tags: ["cache"], first_seen: "2026-05-22", last_seen: "2026-05-23" },
    { id: "github:tauri-apps/tauri", name: "Tauri", description: "Build small, fast desktop and mobile apps with a web frontend and Rust backend.", quadrant: "Platforms", ring: "Trial", source: "GitHub", url: "#", stars: 89200, momentum: 61, tags: ["desktop"], first_seen: "2026-05-11", last_seen: "2026-05-23" },
    { id: "arxiv:dspy-2026", name: "DSPy", description: "Framework for programming, rather than prompting, language model pipelines.", quadrant: "Techniques", ring: "Discovered", source: "arXiv", url: "#", stars: 19200, momentum: 81, tags: ["llm"], first_seen: "2026-05-23", last_seen: "2026-05-23" },
    { id: "github:bigskysoftware/htmx", name: "htmx", description: "Access modern browser features directly from HTML, no build step required.", quadrant: "Tools", ring: "Adopt", source: "GitHub", url: "#", stars: 41000, momentum: 49, tags: ["frontend"], first_seen: "2026-05-10", last_seen: "2026-05-23" },
    { id: "github:modular/mojo", name: "Mojo", description: "Python-superset language designed for AI hardware, compiling through MLIR.", quadrant: "Languages", ring: "Discovered", source: "GitHub", url: "#", stars: 23400, momentum: 87, tags: ["ai"], first_seen: "2026-05-23", last_seen: "2026-05-23" },
    { id: "yt:webgpu-deep-dive", name: "WebGPU", description: "Modern GPU compute and graphics API for the browser, now baseline across engines.", quadrant: "Techniques", ring: "Assess", source: "YouTube", url: "#", stars: 9400, momentum: 53, tags: ["graphics"], first_seen: "2026-05-08", last_seen: "2026-05-23" },
  ],
};

function daysAgo(iso) {
  const d = new Date(iso + "T00:00:00");
  return Math.floor((Date.now() - d.getTime()) / 86400000);
}

function useRadarData(refreshKey = 0) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");
  useEffect(() => {
    let alive = true;
    // cache-bust on refresh so the browser doesn't serve a stale radar.json
    fetch("data/radar.json?v=" + refreshKey)
      .then((r) => { if (!r.ok) throw new Error("no file"); return r.json(); })
      .then((j) => { if (alive) { setData(j); setStatus("live"); } })
      .catch(() => { if (alive) { setData(SAMPLE); setStatus("sample"); } });
    return () => { alive = false; };
  }, [refreshKey]);
  return { data, status };
}

function Toggle({ on, set, label, color }) {
  return (
    <button onClick={() => set(!on)} style={{
      fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, letterSpacing: 1,
      padding: "6px 12px", cursor: "pointer", borderRadius: 3,
      border: "1px solid " + (on ? color : "#2a4060"),
      background: on ? color + "22" : "transparent",
      color: on ? color : "#5b7894",
    }}>
      {on ? "● " : "○ "}{label}
    </button>
  );
}

/* Shared filter pill — used by both Observatory and Dispatch. */
function Pill({ label, active, onClick, color }) {
  return (
    <button onClick={onClick} style={{
      border: "1.5px solid " + (active ? (color || "#1a1a1a") : "#d8d2c4"),
      background: active ? (color || "#1a1a1a") : "transparent",
      color: active ? "#fff" : "#6b6456",
      fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, letterSpacing: 1,
      padding: "5px 11px", borderRadius: 20, cursor: "pointer",
      marginRight: 6, marginBottom: 6,
    }}>{label}</button>
  );
}

/* ===================== RING EDITOR =====================
   Segmented ring picker used in Atlas modal and Observatory detail panel.
   Clicking a ring fires onSetRing immediately — no staging, no commands.
   The App handler POSTs to /api/promote and re-fetches radar.json on success. */
function RingEditor({ item, onSetRing, saveStatus }) {
  const saving = saveStatus?.activeid === item.id && saveStatus?.status === "saving";
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5,
        color: "#6b6456", letterSpacing: 1.5, marginBottom: 6,
      }}>MOVE TO RING</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {RINGS.map((r) => {
          const on = item.ring === r;
          return (
            <button key={r} onClick={() => !saving && onSetRing(item.id, r)}
              disabled={saving}
              style={{
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: 0.5,
                padding: "6px 12px", cursor: saving ? "wait" : "pointer", borderRadius: 4,
                border: "1.5px solid " + RING_INK[r],
                background: on ? RING_INK[r] : "transparent",
                color: on ? "#fff" : RING_INK[r], fontWeight: on ? 700 : 400,
                opacity: saving ? 0.6 : 1,
              }}>{r}</button>
          );
        })}
      </div>
      <div style={{
        marginTop: 7, fontFamily: "'IBM Plex Mono', monospace",
        fontSize: 10, color: "#9a9384", lineHeight: 1.5,
      }}>
        Click a ring to save immediately to disk.
      </div>
    </div>
  );
}

/* ===================== NOTES (artifact storage) =====================
   Notes live in the dashboard's per-user storage, NOT in radar.json.
   This keeps the file pipeline read-only for the dashboard and lets
   each viewer keep their own annotations. */
const _slug = (id) => id.replace(/[^a-zA-Z0-9]+/g, "_");

async function loadNote(id) {
  try {
    const r = await window.storage.get("note:" + _slug(id));
    return r?.value || "";
  } catch { return ""; }
}

async function saveNote(id, text) {
  const key = "note:" + _slug(id);
  try {
    if (text && text.trim()) {
      await window.storage.set(key, text);
    } else {
      await window.storage.delete(key);
    }
    return true;
  } catch (e) { console.error("note save failed", e); return false; }
}

/* ===================== OBSERVATORY (cream/serif sibling of Dispatch) =====================
   Same editorial visual language as Dispatch: cream paper, hard drop
   shadows, Georgia for body, IBM Plex Mono for meta. The radar plot
   stays as the centerpiece but adapts to the lighter palette. */
function Observatory({ data, status, onSetRing, saveStatus }) {
  const [active, setActive] = useState(null);
  const [ringFilter, setRingFilter] = useState("All");
  const [quadFilter, setQuadFilter] = useState("All");
  const [recentOnly, setRecentOnly] = useState(false);
  const [showDiscovered, setShowDiscovered] = useState(true);
  const [note, setNote] = useState("");
  const [noteStatus, setNoteStatus] = useState(""); // "" | "dirty" | "saved"

  const items = useMemo(() => data.items.filter((d) => {
    if (!showDiscovered && d.ring === "Discovered") return false;
    if (ringFilter !== "All" && d.ring !== ringFilter) return false;
    if (quadFilter !== "All" && d.quadrant !== quadFilter) return false;
    if (recentOnly && daysAgo(d.first_seen) > 7) return false;
    return true;
  }), [data, ringFilter, quadFilter, recentOnly, showDiscovered]);

  // geometry — sized to feel like a printed plate
  const size = 540, cx = size / 2, cy = size / 2;
  const ringRadii = { Adopt: 62, Trial: 112, Assess: 162, Hold: 210, Discovered: 258 };
  const ringInner = { Adopt: 14, Trial: 62, Assess: 112, Hold: 162, Discovered: 210 };

  const placed = useMemo(() => items.map((d) => {
    const qIdx = QUADRANTS.indexOf(d.quadrant);
    const inner = ringInner[d.ring] ?? 210;
    const outer = ringRadii[d.ring] ?? 258;
    let h = 0;
    for (let i = 0; i < d.id.length; i++) h = (h * 31 + d.id.charCodeAt(i)) % 100000;
    const frac = h / 100000;
    const ang = (qIdx * Math.PI) / 2 + 0.2 + frac * (Math.PI / 2 - 0.4);
    const rad = inner + 16 + ((h % 1000) / 1000) * Math.max(8, outer - inner - 30);
    return { ...d, x: cx + Math.cos(ang) * rad, y: cy - Math.sin(ang) * rad };
  }), [items]);

  const activeLive = active
    ? (data.items.find((x) => x.id === active.id) || active)
    : null;

  // load the note for the active item whenever it changes
  useEffect(() => {
    let alive = true;
    if (!active) { setNote(""); setNoteStatus(""); return; }
    loadNote(active.id).then((t) => { if (alive) { setNote(t); setNoteStatus(""); } });
    return () => { alive = false; };
  }, [active?.id]);

  const onSave = async () => {
    if (!active) return;
    const ok = await saveNote(active.id, note);
    setNoteStatus(ok ? "saved" : "error");
    if (ok) setTimeout(() => setNoteStatus(""), 2000);
  };

  // summary stats (computed on the unfiltered set so they don't lie)
  const total = data.items.length;
  const discCount = data.items.filter((d) => d.ring === "Discovered").length;
  const newCount = data.items.filter((d) => daysAgo(d.first_seen) <= 7).length;

  return (
    <div style={{
      fontFamily: "Georgia, 'Times New Roman', serif",
      background: "#f4f0e6", color: "#1a1a1a", minHeight: "100%", padding: "34px 38px",
    }}>
      {/* masthead — mirrors Dispatch */}
      <div style={{ borderBottom: "3px solid #1a1a1a", paddingBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <h1 style={{ margin: 0, fontSize: 44, fontWeight: 800, letterSpacing: -1, lineHeight: 1 }}>
            The Observatory
          </h1>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5,
            color: "#6b6456", letterSpacing: 1, textAlign: "right",
          }}>
            RADAR PLOT VIEW<br />
            {status === "live" ? "LIVE FEED" : "SAMPLE DATA"} — {data.generated}
          </span>
        </div>
      </div>

      {/* summary strip — counts always reflect the full dataset */}
      <div style={{
        display: "flex", gap: 28, margin: "14px 0 18px",
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#6b6456",
        letterSpacing: 1,
      }}>
        <Stat label="SIGNALS" value={total} />
        <Stat label="AWAITING REVIEW" value={discCount} color={RING_INK.Discovered} />
        <Stat label="NEW THIS WEEK" value={newCount} color={RING_INK.Trial} />
        <Stat label="SHOWN" value={placed.length} />
      </div>

      {/* filters — same pills/idiom as Dispatch */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ marginBottom: 4 }}>
          <Pill label="ALL RINGS" active={ringFilter === "All"} onClick={() => setRingFilter("All")} />
          {RINGS.map((r) => (
            <Pill key={r} label={r.toUpperCase()} active={ringFilter === r}
              onClick={() => setRingFilter(r)} color={RING_INK[r]} />
          ))}
        </div>
        <div style={{ marginBottom: 4 }}>
          <Pill label="ALL QUADRANTS" active={quadFilter === "All"} onClick={() => setQuadFilter("All")} />
          {QUADRANTS.map((q) => (
            <Pill key={q} label={q.toUpperCase()} active={quadFilter === q}
              onClick={() => setQuadFilter(q)} />
          ))}
        </div>
        <div>
          <Pill label={recentOnly ? "✓ NEW THIS WEEK" : "NEW THIS WEEK ONLY"}
            active={recentOnly} onClick={() => setRecentOnly(!recentOnly)} color={RING_INK.Trial} />
          <Pill label={showDiscovered ? "✓ DISCOVERED VISIBLE" : "DISCOVERED HIDDEN"}
            active={showDiscovered} onClick={() => setShowDiscovered(!showDiscovered)}
            color={RING_INK.Discovered} />
        </div>
      </div>

      {/* plot + detail panel */}
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
        {/* radar plate — sits on its own paper card */}
        <div style={{
          background: "#fffdf7", border: "1px solid #1a1a1a",
          boxShadow: "5px 5px 0 #1a1a1a", padding: 14, flex: "0 0 auto",
        }}>
          <svg width={size} height={size} style={{ display: "block" }}>
            {/* rings — thin dark hairlines on cream */}
            {RINGS.map((r) => (
              <g key={r}>
                <circle cx={cx} cy={cy} r={ringRadii[r]} fill="none"
                  stroke={r === "Discovered" ? RING_INK.Discovered : "#1a1a1a"}
                  strokeOpacity={r === "Discovered" ? 0.45 : 0.18}
                  strokeWidth="1"
                  strokeDasharray={r === "Discovered" ? "3 4" : "0"} />
                <text x={cx} y={cy - ringRadii[r] + 12} textAnchor="middle"
                  fill={RING_INK[r]}
                  style={{ fontFamily: "'IBM Plex Mono', monospace",
                           fontSize: 9.5, letterSpacing: 1.5, cursor: "pointer" }}
                  onClick={() => setRingFilter(ringFilter === r ? "All" : r)}>
                  {r.toUpperCase()}
                </text>
              </g>
            ))}
            {/* quadrant dividers */}
            <line x1={cx} y1={cy - 262} x2={cx} y2={cy + 262} stroke="#1a1a1a" strokeOpacity="0.18" />
            <line x1={cx - 262} y1={cy} x2={cx + 262} y2={cy} stroke="#1a1a1a" strokeOpacity="0.18" />
            {/* quadrant labels — clickable to filter */}
            {QUADRANTS.map((q, i) => {
              const pos = [
                { x: cx + 140, y: cy - 250 }, { x: cx - 140, y: cy - 250 },
                { x: cx - 140, y: cy + 258 }, { x: cx + 140, y: cy + 258 },
              ][i];
              const on = quadFilter === q;
              return (
                <text key={q} x={pos.x} y={pos.y} textAnchor="middle"
                  fill={on ? "#1a1a1a" : "#6b6456"}
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: 12, letterSpacing: 2, fontWeight: on ? 800 : 600,
                    cursor: "pointer",
                  }}
                  onClick={() => setQuadFilter(on ? "All" : q)}>
                  {q.toUpperCase()}
                </text>
              );
            })}
            {/* blips */}
            {placed.map((d) => {
              const on = active?.id === d.id;
              const isNew = daysAgo(d.first_seen) <= 7;
              return (
                <g key={d.id} style={{ cursor: "pointer" }}
                  onMouseEnter={() => setActive(d)} onClick={() => setActive(d)}>
                  {(d.ring === "Discovered" || isNew) && (
                    <circle cx={d.x} cy={d.y} r={on ? 14 : 9} fill="none"
                      stroke={RING_INK[d.ring]} strokeWidth="1" opacity="0.35" />
                  )}
                  <circle cx={d.x} cy={d.y} r={on ? 8 : 5}
                    fill={RING_INK[d.ring]}
                    stroke={on ? "#1a1a1a" : "#fffdf7"} strokeWidth={on ? 2 : 1.5} />
                </g>
              );
            })}
          </svg>
        </div>

        {/* detail card — same hard-shadow card language */}
        <div style={{ flex: "1 1 320px", minWidth: 300, maxWidth: 460 }}>
          {activeLive ? (
            <article style={{
              background: activeLive.ring === "Discovered" ? "#f6f1ff" : "#fffdf7",
              border: "1px solid #1a1a1a",
              boxShadow: activeLive.ring === "Discovered"
                ? "5px 5px 0 " + RING_INK.Discovered
                : "5px 5px 0 #1a1a1a",
              padding: "16px 18px", position: "relative",
            }}>
              <div style={{
                position: "absolute", top: -1, right: -1,
                background: RING_INK[activeLive.ring], color: "#fff",
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, letterSpacing: 1.5,
                padding: "4px 9px",
              }}>{activeLive.ring.toUpperCase()}</div>

              <div style={{
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5,
                color: "#6b6456", letterSpacing: 1.5, marginBottom: 6,
              }}>
                {activeLive.quadrant.toUpperCase()} · {activeLive.source.toUpperCase()}
                {activeLive.company ? " · " + activeLive.company.toUpperCase() : ""}
                {daysAgo(activeLive.first_seen) <= 7 && <span style={{ color: RING_INK.Trial }}> · NEW</span>}
              </div>

              <h2 style={{
                margin: "0 0 6px", fontSize: 22, fontWeight: 800,
                letterSpacing: -0.5, lineHeight: 1.1,
              }}>{activeLive.name}</h2>

              <p style={{ margin: "0 0 12px", fontSize: 13.5, lineHeight: 1.55, color: "#33312b" }}>
                {activeLive.description}
              </p>

              {/* meta row */}
              <div style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                borderTop: "1px solid #d8d2c4", borderBottom: "1px solid #d8d2c4",
                padding: "8px 0", marginBottom: 12,
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#6b6456",
              }}>
                <span>first seen {activeLive.first_seen}</span>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  m{activeLive.momentum}
                  <span style={{ display: "inline-block", width: 50, height: 5, background: "#e3ddcd" }}>
                    <span style={{
                      display: "block", height: "100%", width: activeLive.momentum + "%",
                      background: RING_INK[activeLive.ring],
                    }} />
                  </span>
                </span>
              </div>

              {/* ring editor — saves immediately to disk */}
              <RingEditor item={activeLive} onSetRing={onSetRing} saveStatus={saveStatus} />

              {/* notes editor */}
              <div style={{
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5,
                color: "#6b6456", letterSpacing: 1.5, marginBottom: 5,
              }}>NOTES</div>
              <textarea
                value={note}
                onChange={(e) => { setNote(e.target.value); setNoteStatus("dirty"); }}
                placeholder="why is this on the radar? what to try? what to watch?"
                style={{
                  width: "100%", boxSizing: "border-box", minHeight: 90,
                  fontFamily: "Georgia, serif", fontSize: 13, lineHeight: 1.5,
                  color: "#1a1a1a", background: "#fffaf0",
                  border: "1px solid #c9c0a8", padding: "8px 10px", resize: "vertical",
                }}
              />
              <div style={{ display: "flex", justifyContent: "space-between",
                alignItems: "center", marginTop: 6 }}>
                <span style={{
                  fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5,
                  color: noteStatus === "saved" ? RING_INK.Adopt
                       : noteStatus === "dirty" ? "#b8841d" : "#6b6456",
                  letterSpacing: 1,
                }}>
                  {noteStatus === "saved" ? "✓ SAVED"
                    : noteStatus === "dirty" ? "● UNSAVED"
                    : "STORED PER USER"}
                </span>
                <button onClick={onSave} style={{
                  background: "#1a1a1a", color: "#fff", border: "none",
                  padding: "6px 14px", cursor: "pointer",
                  fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, letterSpacing: 1.5,
                }}>SAVE NOTE</button>
              </div>
            </article>
          ) : (
            <div style={{
              fontFamily: "Georgia, serif", fontSize: 14,
              color: "#6b6456", fontStyle: "italic", padding: "18px 4px",
            }}>
              Hover or tap a blip on the radar to inspect a signal.
              Click a quadrant or ring label to filter.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* Small stat block for the summary strip. */
function Stat({ label, value, color }) {
  return (
    <div>
      <div style={{ fontSize: 22, fontWeight: 800, color: color || "#1a1a1a",
        fontFamily: "Georgia, serif", lineHeight: 1 }}>
        {value}
      </div>
      <div style={{ marginTop: 3 }}>{label}</div>
    </div>
  );
}

/* ===================== MOCKUP B — DISPATCH ===================== */
function Dispatch({ data, status }) {
  const [ringFilter, setRingFilter] = useState("All");
  const [quadFilter, setQuadFilter] = useState("All");
  const [recentOnly, setRecentOnly] = useState(false);

  const filtered = data.items.filter((d) =>
    (ringFilter === "All" || d.ring === ringFilter) &&
    (quadFilter === "All" || d.quadrant === quadFilter) &&
    (!recentOnly || daysAgo(d.first_seen) <= 7)
  ).sort((a, b) => {
    const ra = a.ring === "Discovered" ? 1 : 0;
    const rb = b.ring === "Discovered" ? 1 : 0;
    if (ra !== rb) return rb - ra;
    return b.momentum - a.momentum;
  });

  const discCount = data.items.filter((d) => d.ring === "Discovered").length;
  const newCount = data.items.filter((d) => daysAgo(d.first_seen) <= 7).length;

  return (
    <div style={{
      fontFamily: "Georgia, 'Times New Roman', serif",
      background: "#f4f0e6", color: "#1a1a1a", minHeight: "100%", padding: "34px 38px",
    }}>
      <div style={{ borderBottom: "3px solid #1a1a1a", paddingBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <h1 style={{ margin: 0, fontSize: 44, fontWeight: 800, letterSpacing: -1, lineHeight: 1 }}>
            The Dispatch
          </h1>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5,
            color: "#6b6456", letterSpacing: 1, textAlign: "right",
          }}>
            TECHNOLOGY RADAR<br />
            {status === "live" ? "LIVE FEED" : "SAMPLE DATA"} — {data.generated}
          </span>
        </div>
      </div>
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: "#6b6456",
        letterSpacing: 1, margin: "10px 0 20px",
      }}>
        {filtered.length} of {data.items.length} shown ·
        <span style={{ color: RING_INK.Discovered }}> {discCount} awaiting review</span> ·
        {newCount} new this week
      </div>

      <div style={{ marginBottom: 22 }}>
        <div style={{ marginBottom: 4 }}>
          <Pill label="ALL RINGS" active={ringFilter === "All"} onClick={() => setRingFilter("All")} />
          {RINGS.map((r) => (
            <Pill key={r} label={r.toUpperCase()} active={ringFilter === r}
              onClick={() => setRingFilter(r)} color={RING_INK[r]} />
          ))}
        </div>
        <div style={{ marginBottom: 4 }}>
          <Pill label="ALL QUADRANTS" active={quadFilter === "All"} onClick={() => setQuadFilter("All")} />
          {QUADRANTS.map((q) => (
            <Pill key={q} label={q.toUpperCase()} active={quadFilter === q}
              onClick={() => setQuadFilter(q)} />
          ))}
        </div>
        <div>
          <Pill label={recentOnly ? "✓ NEW THIS WEEK" : "NEW THIS WEEK ONLY"}
            active={recentOnly} onClick={() => setRecentOnly(!recentOnly)} color="#1d6fb8" />
        </div>
      </div>

      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(268px, 1fr))", gap: 18,
      }}>
        {filtered.map((d, i) => {
          const isNew = daysAgo(d.first_seen) <= 7;
          const isDisc = d.ring === "Discovered";
          return (
            <article key={d.id} style={{
              background: isDisc ? "#f6f1ff" : "#fffdf7",
              border: "1px solid #1a1a1a",
              boxShadow: isDisc ? "5px 5px 0 " + RING_INK.Discovered : "5px 5px 0 #1a1a1a",
              padding: "17px 17px 15px", position: "relative",
            }}>
              <div style={{
                position: "absolute", top: -1, right: -1,
                background: RING_INK[d.ring], color: "#fff",
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, letterSpacing: 1.5,
                padding: "4px 9px",
              }}>{d.ring.toUpperCase()}</div>

              <div style={{
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5,
                color: "#6b6456", letterSpacing: 1.5, marginBottom: 6,
              }}>
                № {String(i + 1).padStart(2, "0")} — {d.quadrant.toUpperCase()}
                {isNew && <span style={{ color: "#1d6fb8" }}> · NEW</span>}
              </div>

              <h2 style={{
                margin: "0 0 8px", fontSize: 21, fontWeight: 800,
                letterSpacing: -0.5, lineHeight: 1.1,
              }}>{d.name}</h2>

              <p style={{ margin: "0 0 13px", fontSize: 13.5, lineHeight: 1.55, color: "#33312b" }}>
                {d.description}
              </p>

              <div style={{
                borderTop: "1px solid #d8d2c4", paddingTop: 9,
                display: "flex", justifyContent: "space-between", alignItems: "center",
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, color: "#6b6456",
              }}>
                <span>{d.source}{d.stars ? ` · ★${(d.stars / 1000).toFixed(1)}k` : ""}</span>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  m{d.momentum}
                  <span style={{ display: "inline-block", width: 40, height: 5, background: "#e3ddcd" }}>
                    <span style={{
                      display: "block", height: "100%", width: d.momentum + "%",
                      background: RING_INK[d.ring],
                    }} />
                  </span>
                </span>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}


/* ===================== ATLAS — radar + list combined =====================
   The default view. Same editorial language as Observatory and Dispatch.
   Layout:
     - radar plate sticks to the left (spatial context)
     - sortable card list scrolls on the right (scannable detail)
     - click anything -> modal with full detail + ring editor + notes
   Hovering either side highlights the matching item on the other. */
function Atlas({ data, status, onSetRing, saveStatus }) {
  const [active, setActive] = useState(null);      // selected -> modal
  const [hoverId, setHoverId] = useState(null);    // cross-highlight
  const [ringFilter, setRingFilter] = useState("All");
  const [quadFilter, setQuadFilter] = useState("All");
  const [recentOnly, setRecentOnly] = useState(false);
  const [showDiscovered, setShowDiscovered] = useState(true);
  const [sortBy, setSortBy] = useState("default");
  const [note, setNote] = useState("");
  const [noteStatus, setNoteStatus] = useState(""); // "" | "dirty" | "saved"

  // shared filter applied to both halves
  const filtered = useMemo(() => data.items.filter((d) => {
    if (!showDiscovered && d.ring === "Discovered") return false;
    if (ringFilter !== "All" && d.ring !== ringFilter) return false;
    if (quadFilter !== "All" && d.quadrant !== quadFilter) return false;
    if (recentOnly && daysAgo(d.first_seen) > 7) return false;
    return true;
  }), [data, ringFilter, quadFilter, recentOnly, showDiscovered]);

  // sort options for the list (radar is unaffected — spatial already)
  const sorted = useMemo(() => {
    const arr = [...filtered];
    const ringIdx = { Adopt: 0, Trial: 1, Assess: 2, Hold: 3, Discovered: 4 };
    switch (sortBy) {
      case "momentum":
        return arr.sort((a, b) => b.momentum - a.momentum);
      case "newest":
        return arr.sort((a, b) => (b.first_seen || "").localeCompare(a.first_seen || ""));
      case "name":
        return arr.sort((a, b) => a.name.localeCompare(b.name));
      case "ring":
        return arr.sort((a, b) => {
          const r = ringIdx[a.ring] - ringIdx[b.ring];
          return r !== 0 ? r : b.momentum - a.momentum;
        });
      default: /* "default" = Discovered first, then momentum */
        return arr.sort((a, b) => {
          const ra = a.ring === "Discovered" ? 1 : 0;
          const rb = b.ring === "Discovered" ? 1 : 0;
          if (ra !== rb) return rb - ra;
          return b.momentum - a.momentum;
        });
    }
  }, [filtered, sortBy]);

  const activeLive = active
    ? (data.items.find((x) => x.id === active.id) || active)
    : null;

  // notes load + modal lifecycle
  useEffect(() => {
    let alive = true;
    if (!active) { setNote(""); setNoteStatus(""); return; }
    loadNote(active.id).then((t) => { if (alive) { setNote(t); setNoteStatus(""); } });
    return () => { alive = false; };
  }, [active?.id]);

  // close modal on Escape
  useEffect(() => {
    if (!active) return;
    const onKey = (e) => { if (e.key === "Escape") setActive(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active]);

  const onSave = async () => {
    if (!active) return;
    const ok = await saveNote(active.id, note);
    setNoteStatus(ok ? "saved" : "error");
    if (ok) setTimeout(() => setNoteStatus(""), 2000);
  };

  // radar geometry
  const size = 520, cx = size / 2, cy = size / 2;
  const ringRadii = { Adopt: 58, Trial: 106, Assess: 154, Hold: 202, Discovered: 248 };
  const ringInner = { Adopt: 12, Trial: 58, Assess: 106, Hold: 154, Discovered: 202 };

  const placed = useMemo(() => filtered.map((d) => {
    const qIdx = QUADRANTS.indexOf(d.quadrant);
    const inner = ringInner[d.ring] ?? 202;
    const outer = ringRadii[d.ring] ?? 248;
    let h = 0;
    for (let i = 0; i < d.id.length; i++) h = (h * 31 + d.id.charCodeAt(i)) % 100000;
    const frac = h / 100000;
    const ang = (qIdx * Math.PI) / 2 + 0.2 + frac * (Math.PI / 2 - 0.4);
    const rad = inner + 16 + ((h % 1000) / 1000) * Math.max(8, outer - inner - 30);
    return { ...d, x: cx + Math.cos(ang) * rad, y: cy - Math.sin(ang) * rad };
  }), [filtered]);

  // summary stats — full dataset, not filtered (don't lie about totals)
  const total = data.items.length;
  const discCount = data.items.filter((d) => d.ring === "Discovered").length;
  const newCount = data.items.filter((d) => daysAgo(d.first_seen) <= 7).length;

  return (
    <div style={{
      fontFamily: "Georgia, 'Times New Roman', serif",
      background: "#f4f0e6", color: "#1a1a1a", minHeight: "100%", padding: "30px 34px",
    }}>
      {/* masthead */}
      <div style={{ borderBottom: "3px solid #1a1a1a", paddingBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <h1 style={{ margin: 0, fontSize: 44, fontWeight: 800, letterSpacing: -1, lineHeight: 1 }}>
            The Atlas
          </h1>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5,
            color: "#6b6456", letterSpacing: 1, textAlign: "right",
          }}>
            TECHNOLOGY RADAR<br />
            {status === "live" ? "LIVE FEED" : "SAMPLE DATA"} — {data.generated}
          </span>
        </div>
      </div>

      {/* edit mode hint */}
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5,
        color: "#6b6456", letterSpacing: 0.5, margin: "10px 0 0",
      }}>
        Click any card to open the detail panel and move it between rings.
        Changes save to disk immediately.
      </div>

      {/* summary strip */}
      <div style={{
        display: "flex", gap: 28, margin: "12px 0 16px",
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#6b6456",
        letterSpacing: 1,
      }}>
        <Stat label="SIGNALS" value={total} />
        <Stat label="AWAITING REVIEW" value={discCount} color={RING_INK.Discovered} />
        <Stat label="NEW THIS WEEK" value={newCount} color={RING_INK.Trial} />
        <Stat label="SHOWN" value={filtered.length} />
      </div>

      {/* filters + sort */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 4 }}>
          <Pill label="ALL RINGS" active={ringFilter === "All"} onClick={() => setRingFilter("All")} />
          {RINGS.map((r) => (
            <Pill key={r} label={r.toUpperCase()} active={ringFilter === r}
              onClick={() => setRingFilter(r)} color={RING_INK[r]} />
          ))}
        </div>
        <div style={{ marginBottom: 4 }}>
          <Pill label="ALL QUADRANTS" active={quadFilter === "All"} onClick={() => setQuadFilter("All")} />
          {QUADRANTS.map((q) => (
            <Pill key={q} label={q.toUpperCase()} active={quadFilter === q}
              onClick={() => setQuadFilter(q)} />
          ))}
        </div>
        <div style={{ marginBottom: 4 }}>
          <Pill label={recentOnly ? "✓ NEW THIS WEEK" : "NEW THIS WEEK ONLY"}
            active={recentOnly} onClick={() => setRecentOnly(!recentOnly)} color={RING_INK.Trial} />
          <Pill label={showDiscovered ? "✓ DISCOVERED VISIBLE" : "DISCOVERED HIDDEN"}
            active={showDiscovered} onClick={() => setShowDiscovered(!showDiscovered)}
            color={RING_INK.Discovered} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5,
            color: "#6b6456", letterSpacing: 1.5,
          }}>SORT</span>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} style={{
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 11,
            background: "#fffdf7", border: "1.5px solid #1a1a1a", color: "#1a1a1a",
            padding: "5px 28px 5px 10px", cursor: "pointer",
            appearance: "none", borderRadius: 0,
          }}>
            <option value="default">Discovered first, then momentum</option>
            <option value="momentum">Momentum (high → low)</option>
            <option value="newest">Recently discovered</option>
            <option value="name">Name (A → Z)</option>
            <option value="ring">By ring</option>
          </select>
        </div>
      </div>

      {/* main split — radar (sticky-ish, left) and list (scroll, right) */}
      <div style={{ display: "flex", gap: 22, alignItems: "flex-start", flexWrap: "wrap" }}>
        {/* radar plate */}
        <div style={{
          background: "#fffdf7", border: "1px solid #1a1a1a",
          boxShadow: "5px 5px 0 #1a1a1a", padding: 12,
          flex: "0 0 auto", position: "sticky", top: 12, alignSelf: "flex-start",
        }}>
          <svg width={size} height={size} style={{ display: "block" }}>
            {RINGS.map((r) => (
              <g key={r}>
                <circle cx={cx} cy={cy} r={ringRadii[r]} fill="none"
                  stroke={r === "Discovered" ? RING_INK.Discovered : "#1a1a1a"}
                  strokeOpacity={r === "Discovered" ? 0.45 : 0.18}
                  strokeWidth="1"
                  strokeDasharray={r === "Discovered" ? "3 4" : "0"} />
                <text x={cx} y={cy - ringRadii[r] + 12} textAnchor="middle"
                  fill={RING_INK[r]}
                  style={{ fontFamily: "'IBM Plex Mono', monospace",
                           fontSize: 9.5, letterSpacing: 1.5, cursor: "pointer" }}
                  onClick={() => setRingFilter(ringFilter === r ? "All" : r)}>
                  {r.toUpperCase()}
                </text>
              </g>
            ))}
            <line x1={cx} y1={cy - 252} x2={cx} y2={cy + 252} stroke="#1a1a1a" strokeOpacity="0.18" />
            <line x1={cx - 252} y1={cy} x2={cx + 252} y2={cy} stroke="#1a1a1a" strokeOpacity="0.18" />
            {QUADRANTS.map((q, i) => {
              const pos = [
                { x: cx + 130, y: cy - 240 }, { x: cx - 130, y: cy - 240 },
                { x: cx - 130, y: cy + 248 }, { x: cx + 130, y: cy + 248 },
              ][i];
              const on = quadFilter === q;
              return (
                <text key={q} x={pos.x} y={pos.y} textAnchor="middle"
                  fill={on ? "#1a1a1a" : "#6b6456"}
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: 12, letterSpacing: 2, fontWeight: on ? 800 : 600,
                    cursor: "pointer",
                  }}
                  onClick={() => setQuadFilter(on ? "All" : q)}>
                  {q.toUpperCase()}
                </text>
              );
            })}
            {placed.map((d) => {
              const isHover = hoverId === d.id;
              const isNew = daysAgo(d.first_seen) <= 7;
              return (
                <g key={d.id} style={{ cursor: "pointer" }}
                  onMouseEnter={() => setHoverId(d.id)}
                  onMouseLeave={() => setHoverId(null)}
                  onClick={() => setActive(d)}>
                  {(d.ring === "Discovered" || isNew || isHover) && (
                    <circle cx={d.x} cy={d.y} r={isHover ? 14 : 9} fill="none"
                      stroke={RING_INK[d.ring]} strokeWidth={isHover ? 1.5 : 1}
                      opacity={isHover ? 0.7 : 0.35} />
                  )}
                  <circle cx={d.x} cy={d.y} r={isHover ? 7 : 5}
                    fill={RING_INK[d.ring]}
                    stroke={isHover ? "#1a1a1a" : "#fffdf7"}
                    strokeWidth={isHover ? 2 : 1.5} />
                </g>
              );
            })}
          </svg>
        </div>

        {/* card list */}
        <div style={{ flex: "1 1 460px", minWidth: 320 }}>
          {sorted.length === 0 ? (
            <div style={{
              fontFamily: "Georgia, serif", fontSize: 14, fontStyle: "italic",
              color: "#6b6456", padding: 20,
            }}>No signals match the current filters.</div>
          ) : (
            <div style={{
              display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
              gap: 14,
            }}>
              {sorted.map((d, i) => {
                const isNew = daysAgo(d.first_seen) <= 7;
                const isDisc = d.ring === "Discovered";
                const isHover = hoverId === d.id;
                return (
                  <article key={d.id}
                    onMouseEnter={() => setHoverId(d.id)}
                    onMouseLeave={() => setHoverId(null)}
                    onClick={() => setActive(d)}
                    style={{
                      background: isDisc ? "#f6f1ff" : "#fffdf7",
                      border: "1px solid #1a1a1a",
                      boxShadow: isHover
                        ? "7px 7px 0 " + (isDisc ? RING_INK.Discovered : "#1a1a1a")
                        : "4px 4px 0 " + (isDisc ? RING_INK.Discovered : "#1a1a1a"),
                      padding: "14px 14px 12px", position: "relative",
                      cursor: "pointer", transition: "box-shadow .12s",
                    }}>
                    <div style={{
                      position: "absolute", top: -1, right: -1,
                      background: RING_INK[d.ring], color: "#fff",
                      fontFamily: "'IBM Plex Mono', monospace", fontSize: 9, letterSpacing: 1.5,
                      padding: "3px 8px",
                    }}>{d.ring.toUpperCase()}</div>
                    <div style={{
                      fontFamily: "'IBM Plex Mono', monospace", fontSize: 9,
                      color: "#6b6456", letterSpacing: 1.5, marginBottom: 5,
                    }}>
                      № {String(i + 1).padStart(2, "0")} — {d.quadrant.toUpperCase()}
                      {isNew && <span style={{ color: RING_INK.Trial }}> · NEW</span>}
                    </div>
                    <h2 style={{
                      margin: "0 0 6px", fontSize: 18, fontWeight: 800,
                      letterSpacing: -0.4, lineHeight: 1.15,
                    }}>{d.name}</h2>
                    <p style={{ margin: "0 0 10px", fontSize: 12.5, lineHeight: 1.5,
                      color: "#33312b", display: "-webkit-box",
                      WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden",
                    }}>{d.description}</p>
                    <div style={{
                      borderTop: "1px solid #d8d2c4", paddingTop: 7,
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      fontFamily: "'IBM Plex Mono', monospace", fontSize: 9, color: "#6b6456",
                    }}>
                      <span>{d.source}{d.company ? " · " + d.company : ""}</span>
                      <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        m{d.momentum}
                        <span style={{ display: "inline-block", width: 32, height: 4, background: "#e3ddcd" }}>
                          <span style={{
                            display: "block", height: "100%", width: d.momentum + "%",
                            background: RING_INK[d.ring],
                          }} />
                        </span>
                      </span>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* modal — detail + ring editor + notes */}
      {activeLive && (
        <div onClick={() => setActive(null)} style={{
          position: "fixed", inset: 0, background: "rgba(20,18,12,0.55)",
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: 20, zIndex: 50,
        }}>
          <article onClick={(e) => e.stopPropagation()} style={{
            background: activeLive.ring === "Discovered" ? "#f6f1ff" : "#fffdf7",
            border: "1px solid #1a1a1a",
            boxShadow: "8px 8px 0 " + (activeLive.ring === "Discovered" ? RING_INK.Discovered : "#1a1a1a"),
            padding: "20px 22px", position: "relative",
            width: "100%", maxWidth: 540, maxHeight: "90vh", overflowY: "auto",
            fontFamily: "Georgia, serif",
          }}>
            <button onClick={() => setActive(null)} aria-label="Close" style={{
              position: "absolute", top: 8, right: 8,
              background: "transparent", border: "none", cursor: "pointer",
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 18, color: "#6b6456",
              padding: "2px 8px", lineHeight: 1,
            }}>×</button>

            <div style={{
              position: "absolute", top: -1, left: 22,
              background: RING_INK[activeLive.ring], color: "#fff",
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, letterSpacing: 1.5,
              padding: "4px 9px",
            }}>{activeLive.ring.toUpperCase()}</div>

            <div style={{ height: 18 }} />

            <div style={{
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5,
              color: "#6b6456", letterSpacing: 1.5, marginBottom: 6,
            }}>
              {activeLive.quadrant.toUpperCase()} · {activeLive.source.toUpperCase()}
              {activeLive.company ? " · " + activeLive.company.toUpperCase() : ""}
              {daysAgo(activeLive.first_seen) <= 7 && <span style={{ color: RING_INK.Trial }}> · NEW</span>}
            </div>

            <h2 style={{
              margin: "0 0 8px", fontSize: 26, fontWeight: 800,
              letterSpacing: -0.5, lineHeight: 1.1,
            }}>{activeLive.name}</h2>

            <p style={{ margin: "0 0 14px", fontSize: 14.5, lineHeight: 1.55, color: "#33312b" }}>
              {activeLive.description}
            </p>

            {activeLive.url && activeLive.url !== "#" && (
              <a href={activeLive.url} target="_blank" rel="noreferrer" style={{
                display: "inline-block", fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 10.5, color: "#1a1a1a", letterSpacing: 1,
                borderBottom: "1px solid #1a1a1a", textDecoration: "none",
                marginBottom: 12,
              }}>OPEN SOURCE ↗</a>
            )}

            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              borderTop: "1px solid #d8d2c4", borderBottom: "1px solid #d8d2c4",
              padding: "8px 0", marginBottom: 14,
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#6b6456",
            }}>
              <span>first seen {activeLive.first_seen}</span>
              <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                m{activeLive.momentum}
                <span style={{ display: "inline-block", width: 56, height: 5, background: "#e3ddcd" }}>
                  <span style={{
                    display: "block", height: "100%", width: activeLive.momentum + "%",
                    background: RING_INK[activeLive.ring],
                  }} />
                </span>
              </span>
            </div>

            {/* ring editor — saves immediately to disk */}
            <RingEditor item={activeLive} onSetRing={onSetRing} saveStatus={saveStatus} />

            <div style={{
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5,
              color: "#6b6456", letterSpacing: 1.5, marginBottom: 5,
            }}>NOTES</div>
            <textarea
              value={note}
              onChange={(e) => { setNote(e.target.value); setNoteStatus("dirty"); }}
              placeholder="why is this on the radar? what to try? what to watch?"
              style={{
                width: "100%", boxSizing: "border-box", minHeight: 110,
                fontFamily: "Georgia, serif", fontSize: 13.5, lineHeight: 1.5,
                color: "#1a1a1a", background: "#fffaf0",
                border: "1px solid #c9c0a8", padding: "9px 11px", resize: "vertical",
              }}
            />
            <div style={{ display: "flex", justifyContent: "space-between",
              alignItems: "center", marginTop: 7 }}>
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5,
                color: noteStatus === "saved" ? RING_INK.Adopt
                     : noteStatus === "dirty" ? "#b8841d" : "#6b6456",
                letterSpacing: 1,
              }}>
                {noteStatus === "saved" ? "✓ SAVED"
                  : noteStatus === "dirty" ? "● UNSAVED"
                  : "STORED PER USER"}
              </span>
              <button onClick={onSave} style={{
                background: "#1a1a1a", color: "#fff", border: "none",
                padding: "6px 14px", cursor: "pointer",
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, letterSpacing: 1.5,
              }}>SAVE NOTE</button>
            </div>
          </article>
        </div>
      )}
    </div>
  );
}

/* ===================== SHELL ===================== */
export default function App() {
  const [view, setView] = useState("atlas");
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, status } = useRadarData(refreshKey);

  // {status: "idle"|"saving"|"saved"|"error", activeid: "", name: ""}
  const [saveStatus, setSaveStatus] = useState({ status: "idle", activeid: "", name: "" });

  const onSetRing = async (id, ring) => {
    setSaveStatus({ status: "saving", activeid: id, name: "" });
    try {
      const r = await fetch("/api/promote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, ring }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || "save failed");
      setSaveStatus({ status: "saved", activeid: id, name: j.name });
      setRefreshKey((k) => k + 1);
      setTimeout(() => setSaveStatus({ status: "idle", activeid: "", name: "" }), 2000);
    } catch (e) {
      setSaveStatus({ status: "error", activeid: id, name: e.message });
    }
  };

  if (!data) {
    return (
      <div style={{
        minHeight: "100vh", background: "#060d18", color: "#5b7894",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: "monospace", fontSize: 13,
      }}>loading radar…</div>
    );
  }

  return (
    <div style={{
      minHeight: "100vh", background: "#000",
    }}>
      <div style={{
        display: "flex", gap: 0, background: "#1a1a1a", padding: "10px 14px",
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace", alignItems: "center",
        flexWrap: "wrap",
      }}>
        <span style={{ color: "#777", fontSize: 11, letterSpacing: 1, marginRight: 14 }}>
          VIEW:
        </span>
        {[
          { id: "atlas", label: "ATLAS" },
          { id: "observatory", label: "OBSERVATORY" },
          { id: "dispatch", label: "DISPATCH" },
        ].map((m) => (
          <button key={m.id} onClick={() => setView(m.id)} style={{
            background: view === m.id ? "#fff" : "transparent",
            color: view === m.id ? "#000" : "#999",
            border: "1px solid " + (view === m.id ? "#fff" : "#444"),
            padding: "6px 14px", marginRight: 8, fontSize: 11, letterSpacing: 1,
            cursor: "pointer", fontFamily: "inherit",
          }}>{m.label}</button>
        ))}
        <span style={{
          fontSize: 10.5, letterSpacing: 1, padding: "4px 9px", borderRadius: 3,
          background: "#1d6fb8", color: "#fff", marginRight: 6,
        }}>EDIT MODE</span>
        {saveStatus.status !== "idle" && (
          <span style={{
            fontSize: 10.5, letterSpacing: 1, padding: "4px 9px", borderRadius: 3,
            color: "#1a1a1a",
            background: saveStatus.status === "saving" ? "#fbbf24"
                      : saveStatus.status === "saved"  ? "#4ade80"
                      : "#f87171",
          }}>
            {saveStatus.status === "saving" ? "SAVING..."
             : saveStatus.status === "saved"  ? `✓ ${saveStatus.name}`
             : `✗ ${saveStatus.name}`}
          </span>
        )}
        <span style={{
          marginLeft: "auto", fontSize: 10, letterSpacing: 1,
          color: status === "live" ? "#4ade80" : "#fbbf24",
        }}>
          {status === "live" ? "● radar.json loaded" : "● sample data (radar.json not found)"}
        </span>
      </div>

      {view === "atlas"
        ? <Atlas data={data} status={status} onSetRing={onSetRing} saveStatus={saveStatus} />
        : view === "observatory"
        ? <Observatory data={data} status={status} onSetRing={onSetRing} saveStatus={saveStatus} />
        : <Dispatch data={data} status={status} />}
    </div>
  );
}
