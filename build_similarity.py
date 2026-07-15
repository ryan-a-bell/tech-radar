#!/usr/bin/env python3
"""
build_similarity.py — precompute a semantic similarity matrix for the
Tool Similarity page (web/similarity.html).

  python build_similarity.py

Writes data/similarity.json: a dense cosine-similarity matrix over every
non-archived tool's description, keyed by item id. When this file is present
the similarity page uses it instead of its built-in, in-browser TF-IDF — so
you get true semantic links (competitors that describe themselves with
different words) rather than just shared vocabulary.

Backends, in order of preference (whatever is installed wins):
  1. sentence-transformers  (local MiniLM — no API key, highest quality)
  2. model2vec              (static/distilled embeddings — semantic, no torch,
                             lightweight; great when torch isn't available)
  3. scikit-learn TF-IDF     (lexical, but stemmed/tuned)
  4. pure-python TF-IDF      (always available; mirrors the JS fallback)

The similarity page works fine WITHOUT running this — it just falls back to
its own client-side TF-IDF. This script is the quality upgrade path.

Output shape:
  { "method": "embeddings:all-MiniLM-L6-v2",
    "generated": "2026-07-13",
    "ids":     ["manual:github:...", ...],
    "matrix":  [[1.0, 0.31, ...], ...] }   # rounded to 3 dp
"""

import datetime as _dt
import glob
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS_DIR = os.path.join(HERE, "data", "items")
OUT = os.path.join(HERE, "data", "similarity.json")
PROJ_OUT = os.path.join(HERE, "data", "project_similarity.json")


def load_items():
    items = []
    for path in sorted(glob.glob(os.path.join(ITEMS_DIR, "**", "*.json"), recursive=True)):
        with open(path, encoding="utf-8") as f:
            it = json.load(f)
        if it.get("ring") == "Archived":
            continue
        items.append(it)
    return items


def doc_text(it):
    parts = [
        it.get("description") or "",
        it.get("name") or "",
        it.get("company") or "",
        " ".join(it.get("tags") or []),
        " ".join(it.get("topics") or []),
    ]
    return " ".join(parts).strip()


# --- backend 1: sentence-transformers --------------------------------------
def embed_sentence_transformers(texts):
    from sentence_transformers import SentenceTransformer  # type: ignore
    import numpy as np

    model = SentenceTransformer("all-MiniLM-L6-v2")
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    sim = np.clip(vecs @ vecs.T, -1.0, 1.0)
    return sim, "embeddings:all-MiniLM-L6-v2"


# --- backend 2: model2vec (static/distilled embeddings, no torch) ----------
def embed_model2vec(texts):
    from model2vec import StaticModel  # type: ignore
    import numpy as np

    # potion-retrieval-32M is tuned for retrieval/similarity — best separation
    # of the distilled static models, and still loads in seconds without torch.
    name = "minishlab/potion-retrieval-32M"
    model = StaticModel.from_pretrained(name)
    vecs = model.encode(texts, show_progress_bar=True)
    vecs = np.asarray(vecs, dtype="float32")
    vecs /= (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
    sim = np.clip(vecs @ vecs.T, -1.0, 1.0)
    return sim, "embeddings:potion-retrieval-32M"


# --- backend 3: scikit-learn TF-IDF ----------------------------------------
def embed_sklearn(texts):
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2)
    X = vec.fit_transform(texts)
    sim = cosine_similarity(X)
    return sim, "tf-idf:sklearn"


# --- backend 3: pure-python TF-IDF -----------------------------------------
def embed_pure(texts):
    import re
    from collections import Counter

    stop = set(
        "a an the and or of for to in on with without from by is are be this that it its "
        "as at into your you our their they we can will use used using via based".split()
    )

    def tok(s):
        return [t for t in re.split(r"[^a-z0-9+#]+", s.lower())
                if len(t) >= 2 and t not in stop and not t.isdigit()]

    docs = [Counter(tok(t)) for t in texts]
    n = len(docs)
    df = Counter()
    for d in docs:
        df.update(d.keys())

    vecs = []
    for d in docs:
        v, norm = {}, 0.0
        for term, c in d.items():
            idf = math.log((1 + n) / (1 + df[term])) + 1
            w = (1 + math.log(c)) * idf
            v[term] = w
            norm += w * w
        norm = math.sqrt(norm) or 1.0
        vecs.append({t: w / norm for t, w in v.items()})

    sim = [[0.0] * n for _ in range(n)]
    for i in range(n):
        sim[i][i] = 1.0
        vi = vecs[i]
        for j in range(i + 1, n):
            vj = vecs[j]
            a, b = (vi, vj) if len(vi) < len(vj) else (vj, vi)
            dot = sum(w * b.get(t, 0.0) for t, w in a.items())
            sim[i][j] = sim[j][i] = dot
    return sim, "tf-idf:python"


def choose_backend(texts):
    for fn, name in ((embed_sentence_transformers, "sentence-transformers"),
                     (embed_model2vec, "model2vec"),
                     (embed_sklearn, "scikit-learn"),
                     (embed_pure, "pure-python")):
        try:
            sim, method = fn(texts)
            print(f"backend: {name} -> {method}")
            return sim, method
        except ImportError:
            continue
    raise RuntimeError("no similarity backend available")


def to_lists(sim):
    # accept numpy arrays or python lists; round to keep the file small
    try:
        return [[round(float(x), 3) for x in row] for row in sim]
    except TypeError:
        return [[round(float(x), 3) for x in list(row)] for row in list(sim)]


def _row_floats(sim, i):
    """One row of a numpy-or-list similarity matrix as python floats."""
    r = sim[i]
    try:
        return [float(x) for x in r]
    except TypeError:
        return [float(x) for x in list(r)]


def project_doc_text(p):
    """Embedding text for a project record from build_projects."""
    return " ".join([
        p.get("name") or "",
        p.get("blurb") or "",
        p.get("body") or "",
        " ".join(p.get("topics") or []),
    ]).strip()


def build_project_similarity(items):
    """Embed projects + tools in one space and write data/project_similarity.json:
    for each project, its cosine similarity to every non-archived tool. This is
    what powers the PROJECTS tab's "recommended tools". Skipped if there are no
    projects. The tool-vs-tool similarity.json is left untouched.
    """
    try:
        import build_projects
    except Exception as e:  # pragma: no cover - defensive
        print(f"skipping project_similarity.json — build_projects unavailable ({e})")
        return
    projects = build_projects.build_project_records()
    if not projects:
        print("no projects — skipping project_similarity.json")
        return

    tool_texts = [doc_text(it) for it in items]
    proj_texts = [project_doc_text(p) for p in projects]
    n_tools = len(tool_texts)
    print(f"embedding {len(projects)} projects against {n_tools} tools")
    # one shared space so a project vector and a tool vector are comparable
    sim, method = choose_backend(tool_texts + proj_texts)

    tool_ids = [it["id"] for it in items]
    proj_scores = {}
    for pi, p in enumerate(projects):
        row = _row_floats(sim, n_tools + pi)
        proj_scores[p["id"]] = [round(row[j], 3) for j in range(n_tools)]

    payload = {
        "method": method,
        "generated": _dt.date.today().isoformat(),
        "tool_ids": tool_ids,
        "projects": proj_scores,
    }
    with open(PROJ_OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    size_kb = os.path.getsize(PROJ_OUT) / 1024
    print(f"wrote {PROJ_OUT}  ({len(projects)} projects x {n_tools} tools, "
          f"{size_kb:.0f} KB, method={method})")
    print("the PROJECTS tab will now use this instead of client-side TF-IDF.")


def main():
    items = load_items()
    texts = [doc_text(it) for it in items]
    print(f"loaded {len(items)} non-archived tools")
    sim, method = choose_backend(texts)
    payload = {
        "method": method,
        "generated": _dt.date.today().isoformat(),
        "ids": [it["id"] for it in items],
        "matrix": to_lists(sim),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    size_kb = os.path.getsize(OUT) / 1024
    print(f"wrote {OUT}  ({len(items)}x{len(items)} matrix, {size_kb:.0f} KB, method={method})")
    print("the similarity page will now use this instead of client-side TF-IDF.")

    # project -> tool recommendations (semantic upgrade for the PROJECTS tab)
    build_project_similarity(items)


if __name__ == "__main__":
    main()
