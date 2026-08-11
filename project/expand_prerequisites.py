"""
Expand prerequisite (`prereq_of`) edges in knowledge_graph.pkl to cover the full
concept set, instead of just the 13-concept test batch M3 originally ran this on.

WHY THIS EXISTS
---------------
M3 (M3_GraphRAG_Construction.ipynb) extracted 313 concepts from the full course
corpus, but only ever ran the LLM-based `detect_prerequisite()` pairwise check on
a 5-page/13-concept TEST sample (cell 11 + cell 13) before moving on to full-scale
concept extraction (cell 19). It never re-ran prerequisite detection at full scale
-- doing so naively is ~48,800 pairs (313 choose 2), each needing an LLM call,
which would take way too long.

This script prunes that down to a tractable candidate set using two cheap,
explainable heuristics (no LLM calls needed for pruning):

  1. Co-occurrence: any two concepts explained by the same resource (page) are
     automatically candidates -- they were extracted from the same material and
     are topically related.
  2. Difficulty-tier + text-similarity: for each concept, only consider
     same-or-lower-difficulty-tier concepts as potential prerequisites (you
     don't need an "advanced" concept to understand a "beginner" one), ranked
     by Jaccard similarity of title/definition/alias words, keeping each
     concept's top-K most similar candidates.

On the current graph this produces ~3,400 candidate pairs (vs ~48,800 for the
full cross product) -- roughly a 1-2 hour run against a GPU-backed Ollama
instance instead of a 1-2 day one.

USAGE
-----
Run this INSIDE the dev container (it needs to reach the `ollama` and `mongo`
compose services by hostname, and needs networkx/pymongo/requests, all already
in the Dockerfile):

    docker compose exec dev python3 expand_prerequisites.py

It is resumable: progress is checkpointed to prereq_checkpoint.json after every
pair, so if it's interrupted (Ctrl+C, connection drop, etc.) just re-run the
same command and it'll pick up where it left off instead of re-querying pairs
it already has answers for.

The original knowledge_graph.pkl is backed up once (on first run) to
knowledge_graph_original_backup.pkl before anything is overwritten.
"""

import itertools
import json
import os
import pickle
import re
import shutil
import time
from collections import defaultdict

import networkx as nx
import requests

GRAPH_PATH = "/workspace/knowledge_graph.pkl"
BACKUP_PATH = "/workspace/knowledge_graph_original_backup.pkl"
CHECKPOINT_PATH = "/workspace/prereq_checkpoint.json"

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL = "qwen2.5:7b"

TOP_K = 15          # candidates per concept from text similarity
SAVE_EVERY = 25      # checkpoint + graph snapshot every N pairs
REQUEST_TIMEOUT = 60

TIER_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}
STOPWORDS = set(
    "a an the of for and to in on with is are as by using use used it its "
    "this that from into over via or vs".split()
)


def tier(graph, node):
    return TIER_ORDER.get(graph.nodes[node].get("difficulty", "intermediate"), 1)


def bag_of_words(graph, node):
    d = graph.nodes[node]
    text = " ".join(
        [d.get("title", ""), d.get("definition") or "", " ".join(d.get("aliases") or [])]
    )
    words = re.findall(r"[a-z0-9]+", text.lower())
    return set(w for w in words if w not in STOPWORDS and len(w) > 2)


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def build_candidate_pairs(graph):
    """Returns a set of (concept_a, concept_b) tuples, sorted alphabetically,
    where concept_a is intended as the potential prerequisite (asked first)."""
    concepts = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "concept"]
    bows = {n: bag_of_words(graph, n) for n in concepts}

    # 1. Co-occurrence: concepts sharing an "explains" resource
    res_to_concepts = defaultdict(set)
    for u, v, data in graph.edges(data=True):
        if data.get("relation") == "explains":
            if graph.nodes[u].get("node_type") == "resource":
                res_to_concepts[u].add(v)
            else:
                res_to_concepts[v].add(u)

    cooccurring = set()
    for concepts_in_res in res_to_concepts.values():
        for a, b in itertools.combinations(sorted(concepts_in_res), 2):
            cooccurring.add((a, b))

    # 2. Top-K similarity within same-or-lower difficulty tier
    similarity_pairs = set()
    for c in concepts:
        tc = tier(graph, c)
        scored = []
        for other in concepts:
            if other == c:
                continue
            if tier(graph, other) <= tc:
                score = jaccard(bows[c], bows[other])
                if score > 0:
                    scored.append((score, other))
        scored.sort(reverse=True)
        for _, other in scored[:TOP_K]:
            # 'other' is the candidate prerequisite for 'c'
            similarity_pairs.add(tuple(sorted((other, c))))

    all_pairs = cooccurring | similarity_pairs

    # Drop pairs that already have an edge (either direction) in the graph --
    # don't re-spend an LLM call re-deciding something we already know.
    existing_prereq = set()
    for u, v, data in graph.edges(data=True):
        if data.get("relation") == "prereq_of":
            existing_prereq.add((u, v))
            existing_prereq.add((v, u))

    pruned = {p for p in all_pairs if p not in existing_prereq}
    return pruned, concepts


def query_ollama(prompt, temperature=0.1, max_tokens=10):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except requests.RequestException as e:
        print(f"    Ollama request failed: {e}")
    return None


def detect_prerequisite(graph, concept_a, concept_b):
    """Ask: must a student understand concept_a BEFORE concept_b?"""
    a = graph.nodes[concept_a]
    b = graph.nodes[concept_b]
    prompt = f"""You are an AI education expert. Determine if one concept is a prerequisite for another.

Concept A: {a.get('title', concept_a)}
Definition: {a.get('definition', 'N/A')}

Concept B: {b.get('title', concept_b)}
Definition: {b.get('definition', 'N/A')}

Question: Must a student understand "{a.get('title', concept_a)}" BEFORE learning "{b.get('title', concept_b)}"?

Answer with ONLY one word: "yes" or "no"
"""
    response = query_ollama(prompt)
    if response and "yes" in response.strip().lower():
        return True
    return False


def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    return {"decisions": {}}


def save_checkpoint(state):
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(state, f)


def validate_and_fix_dag(graph):
    prereq_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("relation") == "prereq_of"]
    prereq_graph = nx.DiGraph()
    prereq_graph.add_edges_from(prereq_edges)

    removed = []
    while True:
        try:
            cycle = nx.find_cycle(prereq_graph)
        except nx.NetworkXNoCycle:
            break
        u, v = cycle[-1][0], cycle[-1][1]
        prereq_graph.remove_edge(u, v)
        if graph.has_edge(u, v):
            graph.remove_edge(u, v)
        removed.append((u, v))

    if removed:
        print(f"Removed {len(removed)} edges to break cycles:")
        for u, v in removed:
            print(f"  {graph.nodes[u].get('title', u)} -> {graph.nodes[v].get('title', v)}")
    else:
        print("No cycles found -- DAG is valid.")
    return len(removed)


def main():
    if not os.path.exists(BACKUP_PATH):
        shutil.copy(GRAPH_PATH, BACKUP_PATH)
        print(f"Backed up original graph to {BACKUP_PATH}")

    with open(GRAPH_PATH, "rb") as f:
        graph = pickle.load(f)

    starting_prereq_count = sum(
        1 for _, _, d in graph.edges(data=True) if d.get("relation") == "prereq_of"
    )
    print(f"Loaded graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges "
          f"({starting_prereq_count} existing prereq_of edges)")

    candidate_pairs, concepts = build_candidate_pairs(graph)
    print(f"Concepts: {len(concepts)}")
    print(f"Candidate pairs to check: {len(candidate_pairs)} "
          f"(vs {len(concepts) * (len(concepts) - 1) // 2} for full cross product)")

    state = load_checkpoint()
    decisions = state["decisions"]

    remaining = [p for p in sorted(candidate_pairs) if f"{p[0]}|{p[1]}" not in decisions]
    print(f"Already checked (from checkpoint): {len(candidate_pairs) - len(remaining)}")
    print(f"Remaining to check: {len(remaining)}")

    start_time = time.time()
    new_edges = 0

    for i, (a, b) in enumerate(remaining, 1):
        key = f"{a}|{b}"
        is_prereq = detect_prerequisite(graph, a, b)
        decisions[key] = is_prereq

        if is_prereq:
            graph.add_edge(a, b, relation="prereq_of")
            new_edges += 1

        if i % 10 == 0 or i == len(remaining):
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta_min = (len(remaining) - i) / rate / 60 if rate > 0 else float("inf")
            print(f"[{i}/{len(remaining)}] checked, {new_edges} new edges so far "
                  f"({rate:.2f} pairs/sec, ETA {eta_min:.1f} min)")

        if i % SAVE_EVERY == 0:
            save_checkpoint(state)
            with open(GRAPH_PATH, "wb") as f:
                pickle.dump(graph, f)

    save_checkpoint(state)

    print(f"\nDone checking pairs. Added {new_edges} new prereq_of edges.")
    validate_and_fix_dag(graph)

    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(graph, f)

    final_prereq_count = sum(
        1 for _, _, d in graph.edges(data=True) if d.get("relation") == "prereq_of"
    )
    print(f"\nFinal graph saved: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    print(f"prereq_of edges: {starting_prereq_count} -> {final_prereq_count}")


if __name__ == "__main__":
    main()
