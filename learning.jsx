const { useState, useMemo, useEffect } = React;

/* ============================================================
   LEARNING LIBRARY — CONTENT RADAR
   Atlas-style companion to the tech radar dashboard: a radar plot
   (snapshot of everything at once) pinned beside a scrollable, readable
   card list — same idea as dashboard.jsx's Atlas view, adapted so a
   glance replaces "quadrant" with "topic" and "ring" with consumption
   status (Discovered → Reading → Read).

   Holds mixed learning content — books, articles, and videos — in one
   list, each item carrying a `type`. Reuses the same curated TOPICS
   vocabulary as radar_core.TOPICS / dashboard.jsx, so an item and a
   technology can share a topic tag (e.g. both tagged "RAG" or "Quant").

   Reads data/learning.json: { generated, items: [...] }. Falls back to
   the SAMPLE list below if the file can't be fetched (e.g. opening
   learning.html directly from disk).
   ============================================================ */

const TOPICS = ["AI", "ML", "Agents", "Skills", "Prompts", "Trading", "Quant", "RAG", "Data Feeds"];

// Status radius order mirrors the tech radar: the most "resolved" state
// sits innermost (Read ~ Adopted), the inbox sits outermost (Discovered).
const STATUS_ORDER = ["Read", "Reading", "Discovered"];
const STATUS_COLOR = { Discovered: "#6d4fc4", Reading: "#1d6fb8", Read: "#1a7f4b" };
const STATUS_BG = { Discovered: "#f6f1ff", Reading: "#eef6ff", Read: "#eefbf3" };
const STATUS_LABEL = { Discovered: "Discovered", Reading: "In Progress", Read: "Done" };

// Content types. A small glyph + label brands each card so books,
// articles and videos are distinguishable at a glance without color
// (color is reserved for status, as on the tech radar).
const TYPES = ["book", "article", "video"];
const TYPE_LABEL = { book: "Book", article: "Article", video: "Video" };
const TYPE_ICON = { book: "▣", article: "❡", video: "▶" };

/* Fallback sample — used if data/learning.json can't be fetched. */
const SAMPLE = {
  generated: "2026-07-03",
  items: [
    { id: "ddia", type: "book", title: "Designing Data-Intensive Applications", author: "Martin Kleppmann", year: 2017, status: "Read", topics: ["Data Feeds", "Skills"], pages: 616, rating: 5, finished: "2026-03-02", blurb: "The reference for how reliable, scalable systems actually store and move data — replication, partitioning, and the tradeoffs behind every database pitch deck." },
    { id: "afml", type: "book", title: "Advances in Financial Machine Learning", author: "Marcos López de Prado", year: 2018, status: "Reading", topics: ["Quant", "ML", "Trading"], pages: 400, pages_read: 210, started: "2026-06-01", blurb: "Why most backtests lie, and a rebuild of the ML pipeline for finance from labeling to cross-validation." },
    { id: "attention", type: "article", title: "Attention Is All You Need", author: "Vaswani et al.", source: "arXiv", url: "https://arxiv.org/abs/1706.03762", year: 2017, status: "Read", topics: ["ML", "AI"], minutes: 40, rating: 5, finished: "2025-08-11", blurb: "The transformer paper. Worth reading in the original once — every later 'attention' explainer is a gloss on this." },
    { id: "karpathy-gpt", type: "video", title: "Let's build GPT: from scratch, in code, spelled out", author: "Andrej Karpathy", source: "YouTube", url: "https://www.youtube.com/watch?v=kCc8FmEb1nY", year: 2023, status: "Reading", topics: ["ML", "AI"], duration: "1h 56m", started: "2026-07-10", blurb: "Hands-on build of a GPT from the ground up — the clearest walk from bigram model to a working transformer you can find." },
  ],
};

function daysAgo(iso) {
  const d = new Date(iso + "T00:00:00");
  return Math.floor((Date.now() - d.getTime()) / 86400000);
}

/* The date an item was last "touched" by its current status — used for
   the default sort and the "recently touched" sort option. */
function touchedDate(b) { return b.finished || b.started || b.added || "0000-00-00"; }

/* Human "length" label per content type — pages for books, read-time for
   articles, runtime for videos. Returns "" if the item carries no length. */
function lengthLabel(b) {
  if (b.type === "book") return b.pages ? b.pages + "p" : "";
  if (b.type === "article") return b.minutes ? b.minutes + " min read" : "";
  if (b.type === "video") return b.duration || "";
  return "";
}

/* Byline under the title: creator, then source (publication / channel) for
   articles and videos, then year. Books just show author · year. */
function byline(b) {
  const parts = [b.author];
  if (b.source && b.type !== "book") parts.push(b.source);
  if (b.year) parts.push(b.year);
  return parts.filter(Boolean).join(" · ");
}

/* Deterministic pseudo-random hash from a string, used to jitter an item's
   position within its radar sector/ring band (same trick dashboard.jsx
   uses to spread blips without overlapping). */
function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 100000;
  return h;
}

/* ===================== FUZZY SEARCH =====================
   Same lightweight subsequence match as dashboard.jsx's Atlas search:
   query characters must appear in order in the target, but need not be
   contiguous or exact. An exact substring scores highest; denser, earlier
   runs score higher than sparse ones. */
function fuzzyScore(query, text) {
  if (!query) return 0;
  const q = query.toLowerCase(), t = (text || "").toLowerCase();
  if (t.includes(q)) return 100 + q.length;
  let qi = 0, score = 0, streak = 0;
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) { score += 1 + streak * 2; streak++; qi++; }
    else streak = 0;
  }
  return qi === q.length ? score : -1;
}

// Best weighted match across an item's searchable fields, or -1 if the query
// matches none of them. 0 (no query) means "everything matches".
function itemScore(query, b) {
  if (!query) return 0;
  const fields = [
    [b.title, 3], [(b.topics || []).join(" "), 2.2], [b.author, 1.5],
    [b.source, 1.2], [b.blurb, 1],
  ];
  let best = -1;
  for (const [text, weight] of fields) {
    const s = fuzzyScore(query, text || "");
    if (s >= 0) best = Math.max(best, s * weight);
  }
  return best;
}

function useLearningData() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");
  useEffect(() => {
    let alive = true;
    fetch("data/learning.json")
      .then((r) => { if (!r.ok) throw new Error("no file"); return r.json(); })
      .then((j) => { if (alive) { setData(j); setStatus("live"); } })
      .catch(() => { if (alive) { setData(SAMPLE); setStatus("sample"); } });
    return () => { alive = false; };
  }, []);
  return { data, status };
}

/* Shared filter pill — same idiom as dashboard.jsx's Pill. */
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

function TopicChips({ topics }) {
  if (!topics || !topics.length) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
      {topics.map((t) => (
        <span key={t} style={{
          fontFamily: "'IBM Plex Mono', monospace", fontSize: 8.5, letterSpacing: 1,
          color: "#1a1a1a", background: "#efe9da",
          border: "1px solid #d8d2c4", padding: "2px 7px", borderRadius: 20,
        }}>{t.toUpperCase()}</span>
      ))}
    </div>
  );
}

/* Small type tag (glyph + label) — brands a card/modal as book/article/video
   without leaning on color, which stays reserved for reading status. */
function TypeTag({ type }) {
  return (
    <span style={{
      fontFamily: "'IBM Plex Mono', monospace", fontSize: 9, letterSpacing: 1.2,
      color: "#1a1a1a", background: "#efe9da", border: "1px solid #d8d2c4",
      padding: "2px 7px", borderRadius: 3, textTransform: "uppercase",
      whiteSpace: "nowrap",
    }}>{TYPE_ICON[type] || "▣"} {TYPE_LABEL[type] || type}</span>
  );
}

function Stat({ label, value, color }) {
  return (
    <div>
      <div style={{ fontSize: 22, fontWeight: 800, color: color || "#1a1a1a",
        fontFamily: "Georgia, serif", lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>
        {value}
      </div>
      <div style={{ marginTop: 3 }}>{label}</div>
    </div>
  );
}

function Stars({ rating }) {
  if (!rating) return null;
  return <span style={{ color: "#b8841d", letterSpacing: 1 }}>{"★".repeat(rating)}{"☆".repeat(5 - rating)}</span>;
}

function ProgressBar({ pct, color, width = 44 }) {
  return (
    <span style={{
      display: "inline-block", width, height: 5, background: "rgba(0,0,0,0.08)",
      borderRadius: 3, overflow: "hidden", verticalAlign: "middle", marginLeft: 5,
    }}>
      <span style={{ display: "block", height: "100%", width: pct + "%", background: color }} />
    </span>
  );
}

/* External link chip — opens an article/video (or a book's page) in a new
   tab. stopPropagation so clicking it doesn't also open the detail modal. */
function OpenLink({ url, small }) {
  if (!url) return null;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
      style={{
        fontFamily: "'IBM Plex Mono', monospace", fontSize: small ? 9.5 : 10.5,
        letterSpacing: 1, color: "#1d6fb8", textDecoration: "none",
        borderBottom: "1px solid rgba(29,111,184,0.4)", whiteSpace: "nowrap",
      }}>OPEN ↗</a>
  );
}

function CardFoot({ b }) {
  const len = lengthLabel(b);
  if (b.status === "Reading") {
    if (b.type === "book" && b.pages_read && b.pages) {
      const pct = Math.round((b.pages_read / b.pages) * 100);
      return (<><span>started {b.started}</span><span>{b.pages_read}/{b.pages}p<ProgressBar pct={pct} color={STATUS_COLOR.Reading} /></span></>);
    }
    return (<><span>started {b.started}</span><span>{b.url ? <OpenLink url={b.url} small /> : len}</span></>);
  }
  if (b.status === "Read") {
    return (<><span>finished {b.finished}</span>{b.rating ? <Stars rating={b.rating} /> : (b.url ? <OpenLink url={b.url} small /> : <span>{len}</span>)}</>);
  }
  return (<><span>{b.added ? `added ${b.added} · ${daysAgo(b.added)}d ago` : len}</span><span>{b.url ? <OpenLink url={b.url} small /> : len}</span></>);
}

/* ===================== RADAR PLOT =====================
   Rings encode consumption status (Read innermost, Discovered outermost —
   the same "most resolved sits closest to center" logic as the tech
   radar's Adopted→Archived ordering). Sectors encode topic, one per
   entry in TOPICS, instead of the tech radar's 4 quadrants. */
function RadarPlot({ items, statusFilter, setStatusFilter, topicFilter, setTopicFilter, hoverId, setHoverId, onSelect }) {
  // Extra horizontal/vertical margin (beyond the label radius) so topic
  // labels near 0°/180°/90°/270° have room for their full text instead of
  // clipping against the SVG edge — works for any topic count, odd or even.
  const width = 600, height = 560, cx = 300, cy = 280;
  const ringR = { Read: 68, Reading: 148, Discovered: 214 };
  const ringInner = { Read: 12, Reading: 68, Discovered: 148 };
  const labelR = 228;
  const sectorSpan = (Math.PI * 2) / TOPICS.length;

  const placed = useMemo(() => items.map((b) => {
    const topicIdx = Math.max(0, TOPICS.indexOf((b.topics || [])[0]));
    const inner = ringInner[b.status] ?? 148;
    const outer = ringR[b.status] ?? 214;
    const h = hashStr(b.id);
    const pad = sectorSpan * 0.16;
    const frac = (h % 1000) / 1000;
    const ang = topicIdx * sectorSpan + pad + frac * (sectorSpan - pad * 2);
    const radFrac = ((h >> 3) % 1000) / 1000;
    const rad = inner + 14 + radFrac * Math.max(8, outer - inner - 24);
    return { ...b, x: cx + Math.cos(ang) * rad, y: cy - Math.sin(ang) * rad };
  }), [items]);

  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      {STATUS_ORDER.map((key) => (
        <g key={key}>
          <circle cx={cx} cy={cy} r={ringR[key]} fill="none"
            stroke={key === "Discovered" ? STATUS_COLOR.Discovered : "#1a1a1a"}
            strokeOpacity={key === "Discovered" ? 0.45 : 0.18}
            strokeWidth="1"
            strokeDasharray={key === "Discovered" ? "3 4" : "0"} />
          <text x={cx} y={cy - ringR[key] + 12} textAnchor="middle"
            fill={STATUS_COLOR[key]}
            style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, letterSpacing: 1.5, cursor: "pointer" }}
            onClick={() => setStatusFilter(statusFilter === key ? "All" : key)}>
            {STATUS_LABEL[key].toUpperCase()}
          </text>
        </g>
      ))}
      {/* sector spokes — one per topic boundary, radiating from center. Not
          paired into diameters, so this works whether TOPICS has an odd or
          even number of entries (it's grown before, e.g. "Data Feeds"). */}
      {TOPICS.map((_, i) => {
        const ang = i * sectorSpan;
        return (
          <line key={i}
            x1={cx} y1={cy}
            x2={cx + Math.cos(ang) * 220} y2={cy - Math.sin(ang) * 220}
            stroke="#1a1a1a" strokeOpacity="0.14" />
        );
      })}
      {TOPICS.map((t, i) => {
        const mid = i * sectorSpan + sectorSpan / 2;
        const x = cx + Math.cos(mid) * labelR;
        const y = cy - Math.sin(mid) * labelR;
        const cosv = Math.cos(mid);
        const anchor = cosv > 0.35 ? "start" : cosv < -0.35 ? "end" : "middle";
        const on = topicFilter === t;
        return (
          <text key={t} x={x} y={y + 3} textAnchor={anchor}
            fill={on ? "#1a1a1a" : "#6b6456"}
            style={{
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, letterSpacing: 1,
              fontWeight: on ? 800 : 600, cursor: "pointer",
            }}
            onClick={() => setTopicFilter(topicFilter === t ? "All" : t)}>
            {t.toUpperCase()}
          </text>
        );
      })}
      {placed.map((b) => {
        const isHover = hoverId === b.id;
        const color = STATUS_COLOR[b.status];
        return (
          <g key={b.id} style={{ cursor: "pointer" }}
            onMouseEnter={() => setHoverId(b.id)} onMouseLeave={() => setHoverId(null)}
            onClick={() => onSelect(b)}>
            {(b.status === "Discovered" || isHover) && (
              <circle cx={b.x} cy={b.y} r={isHover ? 13 : 9} fill="none"
                stroke={color} strokeWidth={isHover ? 1.5 : 1} opacity={isHover ? 0.7 : 0.35} />
            )}
            <circle cx={b.x} cy={b.y} r={isHover ? 7 : 5} fill={color}
              stroke={isHover ? "#1a1a1a" : "#fffdf7"} strokeWidth={isHover ? 2 : 1.5} />
          </g>
        );
      })}
    </svg>
  );
}

function ItemCard({ b, hoverId, setHoverId, onSelect }) {
  const isHover = hoverId === b.id;
  return (
    <article
      onMouseEnter={() => setHoverId(b.id)} onMouseLeave={() => setHoverId(null)}
      onClick={() => onSelect(b)}
      style={{
        background: "#fffdf7", border: "1px solid #1a1a1a",
        boxShadow: isHover ? `7px 7px 0 ${STATUS_COLOR[b.status]}` : `4px 4px 0 ${STATUS_COLOR[b.status]}`,
        padding: "14px 14px 12px", position: "relative", cursor: "pointer",
        transition: "box-shadow .12s, transform .12s",
        transform: isHover ? "translate(-2px, -2px)" : "none",
      }}>
      <div style={{
        position: "absolute", top: -1, right: -1,
        background: STATUS_COLOR[b.status], color: "#fff",
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 9, letterSpacing: 1.5,
        padding: "3px 8px", textTransform: "uppercase",
      }}>{STATUS_LABEL[b.status]}</div>
      <div style={{ marginBottom: 6 }}><TypeTag type={b.type} /></div>
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 9, color: "#6b6456",
        letterSpacing: 1.2, marginBottom: 5, textTransform: "uppercase", paddingRight: 70,
      }}>{byline(b)}</div>
      <h3 style={{ margin: "0 0 6px", fontSize: 17, fontWeight: 800, letterSpacing: -0.3, lineHeight: 1.2 }}>
        {b.title}
      </h3>
      <p style={{
        margin: "0 0 10px", fontSize: 12.5, lineHeight: 1.5, color: "#33312b",
        display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden",
      }}>{b.blurb}</p>
      <TopicChips topics={b.topics} />
      <div style={{
        borderTop: "1px solid #d8d2c4", paddingTop: 8,
        display: "flex", justifyContent: "space-between", alignItems: "center",
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, color: "#6b6456",
      }}><CardFoot b={b} /></div>
    </article>
  );
}

function DetailModal({ item, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (!item) return null;
  const b = item;
  const len = lengthLabel(b);
  return (
    <div onClick={onClose} style={{
      position: "fixed", inset: 0, background: "rgba(20,18,12,0.55)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: 20, zIndex: 50,
    }}>
      <article onClick={(e) => e.stopPropagation()} style={{
        background: "#fffdf7", border: "1px solid #1a1a1a",
        boxShadow: `8px 8px 0 ${STATUS_COLOR[b.status]}`,
        padding: "22px 24px", position: "relative",
        width: "100%", maxWidth: 520, maxHeight: "86vh", overflowY: "auto",
        fontFamily: "Georgia, serif",
      }}>
        <button onClick={onClose} aria-label="Close" style={{
          position: "absolute", top: 8, right: 10,
          background: "transparent", border: "none", cursor: "pointer",
          fontFamily: "'IBM Plex Mono', monospace", fontSize: 20, color: "#6b6456",
          padding: "4px 8px", lineHeight: 1,
        }}>×</button>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 14, flexWrap: "wrap" }}>
          <span style={{
            display: "inline-block", color: "#fff", background: STATUS_COLOR[b.status],
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, letterSpacing: 1.5,
            padding: "4px 9px", textTransform: "uppercase",
          }}>{STATUS_LABEL[b.status]}</span>
          <TypeTag type={b.type} />
        </div>
        <h2 style={{ margin: "0 0 4px", fontSize: 26, letterSpacing: -0.5, lineHeight: 1.1 }}>{b.title}</h2>
        <div style={{ fontSize: 12.5, color: "#6b6456", fontStyle: "italic", marginBottom: 12 }}>
          {byline(b)}
        </div>
        <p style={{ fontSize: 14.5, lineHeight: 1.6, color: "#33312b", margin: "0 0 14px" }}>{b.blurb}</p>
        {b.url && (
          <div style={{ margin: "0 0 14px" }}><OpenLink url={b.url} /></div>
        )}
        <TopicChips topics={b.topics} />
        <div style={{
          display: "flex", justifyContent: "space-between", borderTop: "1px solid #d8d2c4",
          paddingTop: 10, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#6b6456",
        }}>
          {b.status === "Reading" && (
            b.type === "book" && b.pages_read && b.pages
              ? <span>started {b.started} · {b.pages_read}/{b.pages} pages ({Math.round((b.pages_read / b.pages) * 100)}%)</span>
              : <span>started {b.started}{len ? ` · ${len}` : ""}</span>
          )}
          {b.status === "Read" && (
            <><span>finished {b.finished}{len ? ` · ${len}` : ""}</span><Stars rating={b.rating} /></>
          )}
          {b.status === "Discovered" && (
            <span>{b.added ? `added ${b.added}` : "queued"}{len ? ` · ${len}` : ""}</span>
          )}
        </div>
      </article>
    </div>
  );
}

/* ===================== SHELL ===================== */
function LearningApp() {
  const { data, status } = useLearningData();
  const [statusFilter, setStatusFilter] = useState("All");
  const [topicFilter, setTopicFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  const [sortBy, setSortBy] = useState("default");
  const [searchQuery, setSearchQuery] = useState("");
  const [hoverId, setHoverId] = useState(null);
  const [active, setActive] = useState(null);

  // typing a query auto-switches to relevance sort, but only away from the
  // default (doesn't clobber a sort the user picked on purpose)
  const onSearchChange = (v) => {
    setSearchQuery(v);
    if (v.trim() && sortBy === "default") setSortBy("relevance");
  };

  // tolerate both the new {items} shape and any stale {books} file
  const allItems = useMemo(() => (data ? (data.items || data.books || []) : []), [data]);

  const filtered = useMemo(() => {
    return allItems.filter((b) =>
      (statusFilter === "All" || b.status === statusFilter) &&
      (topicFilter === "All" || (b.topics || []).includes(topicFilter)) &&
      (typeFilter === "All" || b.type === typeFilter)
    );
  }, [allItems, statusFilter, topicFilter, typeFilter]);

  // fuzzy-score against the search box; a query drops non-matches entirely
  const query = searchQuery.trim();
  const scored = useMemo(() => {
    const withScores = filtered.map((b) => ({ b, score: itemScore(query, b) }));
    return query ? withScores.filter((x) => x.score >= 0) : withScores;
  }, [filtered, query]);

  // item list after search, used for both the radar plot and the card list
  const searched = useMemo(() => scored.map((x) => x.b), [scored]);

  const sorted = useMemo(() => {
    const arr = [...scored];
    const rank = { Discovered: 0, Reading: 0, Read: 1 };
    const statusIdx = { Discovered: 0, Reading: 1, Read: 2 };
    switch (sortBy) {
      case "relevance":
        return arr.sort((a, b) => query ? b.score - a.score : touchedDate(b.b).localeCompare(touchedDate(a.b))).map((x) => x.b);
      case "title": return arr.sort((a, b) => a.b.title.localeCompare(b.b.title)).map((x) => x.b);
      case "status": return arr.sort((a, b) => statusIdx[a.b.status] - statusIdx[b.b.status] || a.b.title.localeCompare(b.b.title)).map((x) => x.b);
      case "recent": return arr.sort((a, b) => touchedDate(b.b).localeCompare(touchedDate(a.b))).map((x) => x.b);
      default:
        return arr.sort((a, b) => {
          const ra = rank[a.b.status], rb = rank[b.b.status];
          return ra !== rb ? ra - rb : touchedDate(b.b).localeCompare(touchedDate(a.b));
        }).map((x) => x.b);
    }
  }, [scored, sortBy, query]);

  if (!data) {
    return (
      <div style={{
        minHeight: "100vh", background: "#060d18", color: "#5b7894",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: "monospace", fontSize: 13,
      }}>loading learning library…</div>
    );
  }

  const counts = { Discovered: 0, Reading: 0, Read: 0 };
  allItems.forEach((b) => { if (counts[b.status] !== undefined) counts[b.status]++; });
  const typeCounts = { book: 0, article: 0, video: 0 };
  allItems.forEach((b) => { if (typeCounts[b.type] !== undefined) typeCounts[b.type]++; });

  return (
    <div style={{ minHeight: "100vh", background: "#000" }}>
      {/* top bar — one shared tab group with dashboard.jsx: ATLAS / INDEX live
          on the radar page, LEARNING is the active tab here */}
      <div style={{
        display: "flex", gap: 0, background: "#1a1a1a", padding: "10px 14px",
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace", alignItems: "center",
        flexWrap: "wrap",
      }}>
        <span style={{ color: "#777", fontSize: 11, letterSpacing: 1, marginRight: 14 }}>
          VIEW:
        </span>
        <a href="index.html#atlas" style={{
          background: "transparent", color: "#999", border: "1px solid #444",
          textDecoration: "none", padding: "6px 14px", marginRight: 8,
          fontSize: 11, letterSpacing: 1,
        }}>ATLAS</a>
        <a href="index.html#index" style={{
          background: "transparent", color: "#999", border: "1px solid #444",
          textDecoration: "none", padding: "6px 14px", marginRight: 8,
          fontSize: 11, letterSpacing: 1,
        }}>INDEX</a>
        <span style={{
          background: "#fff", color: "#000", border: "1px solid #fff",
          padding: "6px 14px", fontSize: 11, letterSpacing: 1,
        }}>LEARNING</span>
        <a href="similarity.html" style={{
          background: "transparent", color: "#999", border: "1px solid #444",
          textDecoration: "none", padding: "6px 14px", marginLeft: 8,
          fontSize: 11, letterSpacing: 1,
        }}>SIMILARITY</a>
        <a href="projects.html" style={{
          background: "transparent", color: "#999", border: "1px solid #444",
          textDecoration: "none", padding: "6px 14px", marginLeft: 8,
          fontSize: 11, letterSpacing: 1,
        }}>PROJECTS</a>
        <a href="people.html" style={{
          background: "transparent", color: "#999", border: "1px solid #444",
          textDecoration: "none", padding: "6px 14px", marginLeft: 8,
          fontSize: 11, letterSpacing: 1,
        }}>PEOPLE</a>
        <span style={{
          marginLeft: "auto", fontSize: 10, letterSpacing: 1,
          color: status === "live" ? "#4ade80" : "#fbbf24",
        }}>
          {status === "live" ? "● learning.json loaded" : "● sample data (learning.json not found)"}
        </span>
      </div>

      <div style={{
        fontFamily: "Georgia, 'Times New Roman', serif",
        background: "#f4f0e6", color: "#1a1a1a", minHeight: "100%", padding: "30px 34px 60px",
      }}>
        {/* masthead */}
        <div style={{ borderBottom: "3px solid #1a1a1a", paddingBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 10 }}>
            <h1 style={{ margin: 0, fontSize: 44, fontWeight: 800, letterSpacing: -1, lineHeight: 1 }}>
              The Learning Library
            </h1>
            <span style={{
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5,
              color: "#6b6456", letterSpacing: 1, textAlign: "right",
            }}>
              BOOKS · ARTICLES · VIDEOS — ATLAS VIEW<br />
              {data.generated}
            </span>
          </div>
        </div>

        {/* fuzzy search */}
        <div style={{ margin: "14px 0 4px" }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search — try a typo, a partial word, a topic, an author, or a source…"
            style={{
              width: "100%", boxSizing: "border-box", fontFamily: "Georgia, serif", fontSize: 15,
              padding: "10px 14px", border: "1.5px solid #1a1a1a", background: "#fffdf7",
              color: "#1a1a1a",
            }}
          />
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, color: "#9a9384",
            letterSpacing: 0.5, marginTop: 4,
          }}>
            Fuzzy match across title, author, source, blurb and topics — finds partial or misspelled terms too.
          </div>
        </div>

        {/* summary stat strip */}
        <div style={{
          display: "flex", gap: 28, margin: "12px 0 16px",
          fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#6b6456", letterSpacing: 1,
          flexWrap: "wrap",
        }}>
          <Stat label="TOTAL ITEMS" value={allItems.length} />
          <Stat label="BOOKS" value={typeCounts.book} />
          <Stat label="ARTICLES" value={typeCounts.article} />
          <Stat label="VIDEOS" value={typeCounts.video} />
          <Stat label="DISCOVERED" value={counts.Discovered} color={STATUS_COLOR.Discovered} />
          <Stat label="IN PROGRESS" value={counts.Reading} color={STATUS_COLOR.Reading} />
          <Stat label="DONE" value={counts.Read} color={STATUS_COLOR.Read} />
          <Stat label="SHOWN" value={sorted.length} />
        </div>

        {/* filters + sort */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 4 }}>
            <Pill label="ALL TYPES" active={typeFilter === "All"} onClick={() => setTypeFilter("All")} />
            {TYPES.map((t) => (
              <Pill key={t} label={TYPE_LABEL[t].toUpperCase()} active={typeFilter === t}
                onClick={() => setTypeFilter(typeFilter === t ? "All" : t)} />
            ))}
          </div>
          <div style={{ marginBottom: 4 }}>
            <Pill label="ALL STATUS" active={statusFilter === "All"} onClick={() => setStatusFilter("All")} />
            {STATUS_ORDER.map((key) => (
              <Pill key={key} label={STATUS_LABEL[key].toUpperCase()} active={statusFilter === key}
                onClick={() => setStatusFilter(statusFilter === key ? "All" : key)} color={STATUS_COLOR[key]} />
            ))}
          </div>
          <div style={{ marginBottom: 4 }}>
            <Pill label="ALL TOPICS" active={topicFilter === "All"} onClick={() => setTopicFilter("All")} />
            {TOPICS.map((t) => (
              <Pill key={t} label={t.toUpperCase()} active={topicFilter === t}
                onClick={() => setTopicFilter(topicFilter === t ? "All" : t)} />
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: "#6b6456", letterSpacing: 1.5 }}>SORT</span>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} style={{
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 11,
              background: "#fffdf7", border: "1.5px solid #1a1a1a", color: "#1a1a1a",
              padding: "5px 28px 5px 10px", cursor: "pointer", appearance: "none", borderRadius: 0,
            }}>
              <option value="default">Discovered &amp; in progress first, then recent</option>
              <option value="relevance">Search relevance</option>
              <option value="status">By status</option>
              <option value="title">Title (A → Z)</option>
              <option value="recent">Most recently touched</option>
            </select>
          </div>
        </div>

        {/* main split — radar (sticky, snapshot of everything) + scrollable list */}
        <div style={{ display: "flex", gap: 22, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div style={{
            background: "#fffdf7", border: "1px solid #1a1a1a",
            boxShadow: "5px 5px 0 #1a1a1a", padding: 12,
            flex: "0 0 auto", position: "sticky", top: 12, alignSelf: "flex-start",
          }}>
            <RadarPlot items={searched} statusFilter={statusFilter} setStatusFilter={setStatusFilter}
              topicFilter={topicFilter} setTopicFilter={setTopicFilter}
              hoverId={hoverId} setHoverId={setHoverId} onSelect={setActive} />
            <div style={{
              fontSize: 10, color: "#6b6456", letterSpacing: 0.5, textAlign: "center",
              marginTop: 8, maxWidth: 470, fontFamily: "'IBM Plex Mono', monospace",
            }}>click a ring or topic label to filter · hover a dot to spotlight its card</div>
          </div>

          <div style={{ flex: "1 1 460px", minWidth: 300 }}>
            {sorted.length === 0 ? (
              <div style={{ fontFamily: "Georgia, serif", fontSize: 14, fontStyle: "italic", color: "#6b6456", padding: 20 }}>
                No items match the current filters.
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 14 }}>
                {sorted.map((b) => (
                  <ItemCard key={b.id} b={b} hoverId={hoverId} setHoverId={setHoverId} onSelect={setActive} />
                ))}
              </div>
            )}
          </div>
        </div>

        <footer style={{
          marginTop: 32, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10,
          color: "#6b6456", letterSpacing: 0.5, textAlign: "center",
        }}>click any item — dot or card — to open its full entry</footer>
      </div>

      <DetailModal item={active} onClose={() => setActive(null)} />
    </div>
  );
}
