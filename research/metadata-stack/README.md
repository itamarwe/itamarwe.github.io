# Five-layer data stack — figure source

Source behind the post
[*The Five Layers Between Your Data and an AI Agent That Doesn't Hallucinate*](../../content/posts/2026-06-17-the-five-layer-stack-for-ai-agents.md).

The post is a visual restatement of [Sanjeev Mohan's FAQ on metadata,
semantics, taxonomy, ontology, knowledge graphs, and
context](https://sanjmo.medium.com/faq-on-metadata-semantics-taxonomy-ontology-knowledge-graphs-and-context-c4a53bfda395),
which frames those terms as an interdependent five-layer stack:

1. **Metadata** — data about data; makes assets findable, governable, trustworthy
2. **Ontology** — entities, attributes, and the legal relationships between them
3. **Knowledge graph** — the ontology populated with real, connected instances
4. **Semantic layer** — one canonical metric definition, served to every consumer
5. **Context layer** — the runtime assembly of the right signals per decision

A single running example — a customer (Jane) who bought a MacBook Air, and a
support agent helping her — threads through all five figures.

## Layout

```
sim/
  make_summary.py    matplotlib generator for the lead / OG card
                     (five-layers.png, 1200x630) — the whole stack on one image.
  make_sections.py   matplotlib generator for the five per-section figures
                     (metadata / ontology / knowledge-graph / semantic-layer /
                     context-layer .png, 1100x560 each), one above each section.
```

The committed assets live in `public/img/metadata-stack/`.

## Honesty note

These are **illustrative** diagrams, not output from any live system. The entity
names, serial numbers, the "12,847 active customers" figure, and the
per-consumer mismatch are hand-picked to make each layer's point clearly.

## Regenerate

```bash
python research/metadata-stack/sim/make_summary.py    # -> five-layers.png
python research/metadata-stack/sim/make_sections.py   # -> the five section figures
```

Needs `numpy` and `matplotlib` (the dark 3blue1brown palette is matched to the
other posts' visuals).
