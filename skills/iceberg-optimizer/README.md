# iceberg-optimizer

A [Claude Code](https://claude.com/claude-code) skill that diagnoses an Apache
Iceberg table and produces a ranked, **cost-aware** maintenance and layout plan —
compaction (bin-pack / sort / z-order), partition evolution, snapshot expiry,
orphan-file and manifest cleanup, sort orders, and bloom filters — plus a run
schedule.

What makes it different from a static runbook: it **observes before it asks,
asks before it decides, and simulates before it recommends.**

1. **Profile** the table's physical state from its metadata tables.
2. **Reconstruct the workload** — derive ingestion shape (write cadence, file
   size at write, partition fan-out, late data, mutability) from metadata, then
   interview only for the intent metadata can't reveal (latency / freshness SLAs,
   query frequency, cost priority, time-travel needs).
3. **Decide** with a joint framework that gates every action on intent — so a
   cold, rarely-queried table is told to do *nothing* rather than handed a
   pointless compaction job.
4. **Simulate** Do-nothing / Light / Targeted-sort / Aggressive / Storage-min
   scenarios across query latency, query cost, maintenance cost, and storage
   cost, driven by the table's real numbers, so you optimize for the axis you
   care about.
5. **Plan** with exact, engine-specific commands (Spark, Trino, AWS Glue, Flink)
   and a schedule.

## Install

Copy the skill into your Claude Code skills directory:

```bash
cp -r skills/iceberg-optimizer ~/.claude/skills/        # user-level, or
cp -r skills/iceberg-optimizer <your-repo>/.claude/skills/   # project-level
```

Then ask Claude Code to "optimize my Iceberg table" (or profile it, design a
maintenance schedule, decide whether it's worth compacting, etc.).

## The scripts (stdlib-only; `sqlglot` optional)

```bash
# 1. Profile from exported metadata tables
python scripts/profile_table.py --snapshots snap.json --files files.json \
    [--partitions parts.json] [--manifests mans.json] --out profile.json

# 2. Reconstruct read access patterns from query logs
python scripts/parse_query_log.py --trino-queries q.json \
    --table cat.db.tbl --out workload.json
#   (or --sql-file q.sql, or --spark-eventlog app.log)

# 3. Simulate scenarios across the four cost axes
python scripts/simulate.py --profile profile.json --workload workload.json \
    --queries-per-month 50000 --priority total
```

Inputs are exports of the table's Iceberg metadata tables and query history — the
skill never connects to your warehouse. The simulator's cost model is transparent
and every assumption is printed and overridable via `--assumptions`; treat its
output as directional, not a benchmark.

## Layout

```
SKILL.md                          orchestrator: the 5-phase flow
references/metadata-tables.md     metadata table schemas + diagnostic queries
references/workload-interview.md  derive-then-ask question bank
references/decision-framework.md  joint scoring rules + intent gates
references/procedures.md          verified Spark/Trino/Glue/Flink syntax
references/scheduling.md          archetype→schedule matrix + triggers
scripts/                          profile_table · parse_query_log · simulate
```
