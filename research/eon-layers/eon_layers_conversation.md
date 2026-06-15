# EON — Data-for-AI Layers: conversation log

Working session that produced `eon_layers_manim.py` and the two rendered videos.

---

## 1. Source

User provided a diarized Hebrew transcript of Geekonomy podcast episode #1209 with Dr. Asaf Natanzon (Chief Architect at EON) and asked:

> I want to summarize what EON did here to make data accessible for AI.

## 2. First summary

EON started as a cloud backup company but discovered the artifact they produce — a normalized, queryable copy of every piece of organizational data — is exactly what AI needs. Asaf called it "the new Library of Alexandria."

The pipeline:
1. **Agentless discovery** via IAM role — enumerate every resource, auto-classify what's inside (PII, prod, DB engines, etc.)
2. **Snapshot → scan → re-encode** — cloud-native snapshots are opaque blobs; EON rewrites them into queryable format in S3
3. **Tabular format: Parquet + Apache Iceberg** — databases extracted to Parquet, exposed as Iceberg tables with time-travel snapshots
4. **Zero-ETL data lake as a side effect** — every backed-up source lands in the same Iceberg lake → unified multi-cloud/multi-SaaS data lake for free

On top of that, the AI-specific layer:
5. **Joinability detection** — min-hash for physical overlap + LLM for semantics
6. **RAG / index over tables** — LLM-generated table descriptions, sample values, foreign keys, joinability cluster
7. **NL2SQL that scales** — joinability graph + table-cluster RAG + interactive UI for hundreds-of-thousands-of-tables scale
8. **Gemini integration** — Google Next launch partner; Gemini in GCP console can query the backup estate directly

The backup is the AI substrate. EON is splitting into two product lines: backup-buyer (restore-centric) and data-team (zero-ETL lake + NL2SQL).

## 3. User asked for focus on four layers

> I was referring to:
> 1. Joinability detection
> 2. Semantic analysis by LLM
> 3. RAG over tables
> 4. How NL2SQL uses the previous layers

### Layer 1 — Joinability detection

The problem: same logical entity shows up in many sources under different column names, sometimes in schemas that don't exist (raw Mongo JSON). Before cross-source queries, you need to know what joins what.

Naive approaches fail:
- LLM-only on column names → hallucinates joins on look-alike UUIDs
- Brute-force intersection on billions of rows → too expensive

EON's combined physical + semantic check:
- **Physical overlap** estimated cheaply with **min-hash** — two columns of 1B values intersecting at 10% detected without scanning 2B values
- **Semantic check** on top — LLM looks at column names, sampled values, surrounding columns to confirm the semantics match (so a 1..N integer counter doesn't get joined to another unrelated 1..N counter just because they "intersect" 100%)

Output: a graph of which columns in which tables are actually joinable, with confidence scores.

### Layer 2 — Semantic analysis by LLM

Runs at ingest time, per table, and produces the metadata everything else is built on.

For each table, EON feeds the LLM:
- Column names
- **Sampled rows** (bounded count that fits in prompt budget — not random)
- Source DB, environment
- Detected foreign keys (when present, a hard signal)
- **Joinability candidates from Layer 1** ("this column overlaps with that one — what can you infer?")

LLM outputs a structured description: what each column means, what the table represents, how it relates to other tables. Works even for schemaless Mongo collections — the LLM does schema *inference* from sampled JSON.

The key point: an LLM hooked directly to a database has only the semantic signal. EON's advantage is feeding the LLM the **physical-overlap evidence too** — descriptions encode real relationships, not guessed ones.

### Layer 3 — RAG over tables

**Each table is indexed.** The index entry for table T contains:
- Table name and origin
- Per-column descriptions (from Layer 2)
- Sample values
- Cluster of related/joinable tables (from Layer 1)
- Contextual metadata (source DB, environment)

Two things sit on top:
- **Search:** "what tables do we have about X?" → relevant cluster
- **Clustering:** tables sharing joinable columns are grouped; a query about "users and their orders" resolves to a small connected subgraph, not a flat list of a million tables

The RAG is an *index over table metadata and relationships*, not over raw rows.

### Layer 4 — NL2SQL

Off-the-shelf NL2SQL handles ~100 tables; collapses at a million. EON customers have hundreds of thousands of tables.

Flow:
1. **Retrieve the relevant cluster** — RAG (Layer 3) returns candidate tables. A 1M-table problem collapses to a 10-table problem.
2. **Interactive confirmation** — UI shows the proposed cluster, user can correct it. Not "fire and forget."
3. **Generate SQL using joinability hints** — LLM is given the joinability graph (Layer 1) as ground truth. Instead of guessing `ON a.user_id = b.user_id`, it's told "these two columns physically overlap 94%, join on these."
4. **Iceberg time-travel** for fresh vs historical questions — LLM picks the right snapshot for "today's state" or "trend over time."

**RAG narrows the search space, joinability ensures the joins are real, semantic descriptions let the LLM generate correct SQL, and the interactive layer catches what's still wrong.** Each layer handles a failure mode the next can't fix.

## 4. 3b1b / Manim animation

User asked for a loopable Manim-style animation demonstrating the four layers. I produced `eon_layers_manim.py` — a single self-contained Manim CE script with one `EONLayers` class. ~55 seconds, 68 animations.

Beats:
- **Intro:** "Making organizational data AI-queryable" fades from black
- **Layer 1:** two tables (RDS users / Mongo events), naive "UUID guess" gets a red ✗, min-hash sketches appear under each, double-arrow + `≈ 0.94 Jaccard` resolves with *"physical overlap, not a guess"*
- **Layer 2:** orders_2024 table + four inputs (with joinability hints highlighted) feed an LLM hex that pulses and emits a structured description, with `uid → users.id (FK, 94%)` highlighted to show the carry-through from Layer 1
- **Layer 3:** 24 table icons morph into coloured dots in a circular "table index"; clusters form (users / events / orders / billing); a query becomes a yellow dot, curves into the orders cluster, ring highlights neighbours
- **Layer 4:** three columns — retrieved cluster of 3 tables → weighted join graph (bright 0.94 / dim 0.12) → generated SQL with `ON o.uid = u.id` highlighted → `user confirms cluster ✓` at the end
- **Outro:** four-line recap fades to black → loops to intro

3b1b palette: dark BG (#0E1116), blue/teal/yellow/orange accents.

## 5. RAG framing correction

> The RAG as I understand it is for tables, not for documents — so when a user wants to query something it finds the right tables to query using the semantic layer and the "joinability/similarity" graph.

Fixed by:
- **Subtitle reframed:** "an index of **tables** — by **meaning** + **joinability**" (with `meaning` in Layer 2's teal and `joinability` in Layer 1's blue), making explicit that this layer is built on top of the prior two
- **"embedding space" → "table index"** — kills the document confusion
- **Joinability edges drawn inside each cluster** (faint yellow, the same yellow as Layer 1's Jaccard arrow), so the cluster visually *is* a subgraph of the joinability graph
- **"tables to query →"** label appears next to the highlighted cluster — handoff to Layer 4 is now explicit

## 6. Aspect-ratio variants

User asked for:
- **Twitter / X:** 16:9 at 1920×1080
- **LinkedIn:** 4:5 at 1080×1350

The original `EONLayers` scene is laid out horizontally and renders fine at 16:9. For 4:5 I added an `EONLayersTall` subclass that inherits all helpers and the intro/outro and overrides each layer method with a vertical re-flow that fits the 6.4-wide × 8-tall scene frame:

- **Layer 1:** tables stacked top/bottom, sketches and Jaccard arrow run vertically between them
- **Layer 2:** table + inputs at the top feeding into a centered LLM hex, output box below
- **Layer 3:** 3×8 grid of table icons on top, "table index" circle on the bottom — joinability edges and `tables to query →` annotation preserved
- **Layer 4:** three steps stacked top-to-bottom (cluster → join graph → SQL), confirmation at the bottom

Final renders:

| Platform | File | Resolution | FPS | Duration |
|---|---|---|---|---|
| Twitter / X (16:9) | `eon_layers_16x9_1920x1080.mp4` | 1920×1080 | 60 | 63.5 s |
| LinkedIn (4:5)    | `eon_layers_4x5_1080x1350.mp4`  | 1080×1350 | 30 | 61.6 s |

Both fade in and out from black, so they loop cleanly.

## 7. Re-rendering

```bash
pip install manim

# 16:9 — Twitter / X / YouTube — 1920x1080
manim -qh eon_layers_manim.py EONLayers

# 4:5 — LinkedIn feed — 1080x1350
manim --resolution 1080,1350 -qm eon_layers_manim.py EONLayersTall

# Loopable GIF
manim -qm --format gif eon_layers_manim.py EONLayers
```
