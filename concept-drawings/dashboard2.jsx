import React, { useState, useMemo, useEffect } from "react";

/* ============================================================
   TECHNOLOGY RADAR DASHBOARD
   Reads the runner's data/radar.json. Two views:
     A · Observatory — dark polar radar plot
     B · Dispatch    — light editorial briefing grid
   Both include the "Discovered" ring (the runner's inbox).
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

function useRadarData() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");
  useEffect(() => {
    let alive = true;
    fetch("data/radar.json")
      .then((r) => { if (!r.ok) throw new Error("no file"); return r.json(); })
      .then((j) => { if (alive) { setData(j); setStatus("live"); } })
      .catch(() => { if (alive) { setData(SAMPLE); setStatus("sample"); } });
    return () => { alive = false; };
  }, []);
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

/* ===================== MOCKUP A — OBSERVATORY ===================== */
function Observatory({ data, status }) {
  const [active, setActive] = useState(null);
  const [showDiscovered, setShowDiscovered] = useState(true);
  const [recentOnly, setRecentOnly] = useState(false);

  const items = useMemo(() => data.items.filter((d) => {
    if (!showDiscovered && d.ring === "Discovered") return false;
    if (recentOnly && daysAgo(d.first_seen) > 7) return false;
    return true;
  }), [data, showDiscovered, recentOnly]);

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

  const newCount = data.items.filter((d) => daysAgo(d.first_seen) <= 7).length;
  const discCount = data.items.filter((d) => d.ring === "Discovered").length;

  return (
    <div style={{
      fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      background: "radial-gradient(ellipse at 50% 28%, #10243a 0%, #060d18 72%)",
      color: "#cfe3f5", minHeight: "100%", padding: "30px 28px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h1 style={{ margin: 0, fontSize: 26, letterSpacing: 4, fontWeight: 600, color: "#e8f3ff" }}>
          OBSERVATORY
        </h1>
        <span style={{ fontSize: 11, color: "#5b7894", letterSpacing: 2 }}>
          {status === "live" ? "LIVE" : "SAMPLE"} · {data.generated} · {data.items.length} SIGNALS
        </span>
      </div>
      <div style={{ height: 1, background: "linear-gradient(90deg,#1f4060,transparent)", margin: "12px 0 18px" }} />

      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <Toggle on={showDiscovered} set={setShowDiscovered}
          label={`SHOW DISCOVERED (${discCount})`} color="#a78bfa" />
        <Toggle on={recentOnly} set={setRecentOnly}
          label={`NEW THIS WEEK (${newCount})`} color="#38bdf8" />
      </div>

      <div style={{ display: "flex", gap: 26, flexWrap: "wrap" }}>
        <svg width={size} height={size} style={{ flex: "0 0 auto" }}>
          <defs>
            <radialGradient id="oglow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#1c4a6e" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#1c4a6e" stopOpacity="0" />
            </radialGradient>
          </defs>
          <circle cx={cx} cy={cy} r={ringRadii.Discovered} fill="url(#oglow)" />
          {RINGS.map((r) => (
            <g key={r}>
              <circle cx={cx} cy={cy} r={ringRadii[r]} fill="none"
                stroke={r === "Discovered" ? "#3b3a5c" : "#22405c"}
                strokeWidth="1" strokeDasharray={r === "Discovered" ? "3 4" : "0"} />
              <text x={cx} y={cy - ringRadii[r] + 13} textAnchor="middle"
                fill={RING_COLOR[r]} fontSize="9.5" letterSpacing="1.5" opacity="0.85">
                {r.toUpperCase()}
              </text>
            </g>
          ))}
          <line x1={cx} y1={cy - 262} x2={cx} y2={cy + 262} stroke="#22405c" />
          <line x1={cx - 262} y1={cy} x2={cx + 262} y2={cy} stroke="#22405c" />
          {QUADRANTS.map((q, i) => {
            const pos = [
              { x: cx + 140, y: cy - 248 }, { x: cx - 140, y: cy - 248 },
              { x: cx - 140, y: cy + 258 }, { x: cx + 140, y: cy + 258 },
            ][i];
            return (
              <text key={q} x={pos.x} y={pos.y} textAnchor="middle"
                fill="#6f8cab" fontSize="12" letterSpacing="2" fontWeight="600">
                {q.toUpperCase()}
              </text>
            );
          })}
          {placed.map((d) => {
            const on = active?.id === d.id;
            const isNew = daysAgo(d.first_seen) <= 7;
            return (
              <g key={d.id} style={{ cursor: "pointer" }}
                onMouseEnter={() => setActive(d)} onClick={() => setActive(d)}>
                {(d.ring === "Discovered" || isNew) && (
                  <circle cx={d.x} cy={d.y} r={on ? 15 : 10} fill="none"
                    stroke={RING_COLOR[d.ring]} strokeWidth="1" opacity="0.45" />
                )}
                <circle cx={d.x} cy={d.y} r={on ? 9 : 5.2}
                  fill={RING_COLOR[d.ring]}
                  stroke={on ? "#e8f3ff" : "#0a1626"} strokeWidth="2" />
              </g>
            );
          })}
        </svg>

        <div style={{ flex: "1 1 280px", minWidth: 280 }}>
          {active ? (
            <div style={{
              border: "1px solid #234060", background: "#0c1c2e",
              padding: "16px 18px", borderRadius: 4, marginBottom: 14,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 17, color: "#e8f3ff", fontWeight: 600 }}>{active.name}</span>
                <span style={{
                  fontSize: 9.5, padding: "3px 8px", borderRadius: 3,
                  background: RING_COLOR[active.ring] + "22", color: RING_COLOR[active.ring],
                  letterSpacing: 1,
                }}>{active.ring.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: 10.5, color: "#5b7894", margin: "5px 0 10px", letterSpacing: 1 }}>
                {active.quadrant} · via {active.source} · first seen {active.first_seen}
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.6, color: "#acc6dd", margin: 0 }}>
                {active.description}
              </p>
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 9.5, color: "#5b7894", letterSpacing: 1, marginBottom: 4 }}>
                  MOMENTUM {active.momentum}
                </div>
                <div style={{ background: "#16304a", height: 6, borderRadius: 3 }}>
                  <div style={{
                    width: active.momentum + "%", height: "100%", borderRadius: 3,
                    background: "linear-gradient(90deg,#38bdf8,#4ade80)",
                  }} />
                </div>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 12, color: "#5b7894", marginBottom: 14, fontStyle: "italic" }}>
              ▸ Hover or tap a blip to inspect a signal.
            </div>
          )}
          <div style={{ fontSize: 9.5, color: "#5b7894", letterSpacing: 2, marginBottom: 8 }}>
            SIGNALS ({placed.length})
          </div>
          <div style={{ maxHeight: 280, overflowY: "auto" }}>
            {placed.map((d) => (
              <div key={d.id} onMouseEnter={() => setActive(d)} onClick={() => setActive(d)}
                style={{
                  display: "flex", justifyContent: "space-between", padding: "7px 10px",
                  cursor: "pointer", borderLeft: "2px solid " + RING_COLOR[d.ring],
                  background: active?.id === d.id ? "#13283e" : "transparent",
                  marginBottom: 2, fontSize: 12,
                }}>
                <span style={{ color: "#cfe3f5" }}>{d.name}</span>
                <span style={{ color: "#5b7894" }}>{d.ring}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
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

  const Pill = ({ label, active, onClick, color }) => (
    <button onClick={onClick} style={{
      border: "1.5px solid " + (active ? (color || "#1a1a1a") : "#d8d2c4"),
      background: active ? (color || "#1a1a1a") : "transparent",
      color: active ? "#fff" : "#6b6456",
      fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, letterSpacing: 1,
      padding: "5px 11px", borderRadius: 20, cursor: "pointer",
      marginRight: 6, marginBottom: 6,
    }}>{label}</button>
  );

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

/* ===================== SHELL ===================== */
export default function App() {
  const [view, setView] = useState("observatory");
  const { data, status } = useRadarData();

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
    <div style={{ minHeight: "100vh", background: "#000" }}>
      <div style={{
        display: "flex", gap: 0, background: "#1a1a1a", padding: "10px 14px",
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace", alignItems: "center",
        flexWrap: "wrap",
      }}>
        <span style={{ color: "#777", fontSize: 11, letterSpacing: 1, marginRight: 14 }}>
          VIEW:
        </span>
        {[
          { id: "observatory", label: "A · OBSERVATORY" },
          { id: "dispatch", label: "B · DISPATCH" },
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
          marginLeft: "auto", fontSize: 10, letterSpacing: 1,
          color: status === "live" ? "#4ade80" : "#fbbf24",
        }}>
          {status === "live" ? "● radar.json loaded" : "● sample data (radar.json not found)"}
        </span>
      </div>

      {view === "observatory"
        ? <Observatory data={data} status={status} />
        : <Dispatch data={data} status={status} />}
    </div>
  );
}
