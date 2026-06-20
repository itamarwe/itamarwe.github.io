# Maintenance procedures — routing index

This file is now a routing index only. Full procedures live in `engines/`.

## Operation order (always)

compact → expire snapshots → remove orphans → rewrite manifests

**Why:**
- Compact first: expiring snapshots can make delete files unreachable, permanently
  losing the ability to physically remove rows via future compaction.
- Expire before orphan cleanup: orphan removal run too early can delete files still
  referenced by unexpired snapshots.

## Engine routing

| Engine | Procedure file |
|---|---|
| Spark (standalone, Databricks, EMR, local) | `engines/spark.md` |
| AWS Glue / Amazon EMR | `engines/glue.md` (supplements `engines/spark.md`) |
| Trino | `engines/trino.md` |
| Snowflake (managed or external) | `engines/snowflake.md` |
| Flink / Kafka Connect (write-time only) | `engines/ingestion.md` |

## Capability matrix

| Operation | Spark | Trino | Snowflake (managed) | Snowflake (external) |
|---|---|---|---|---|
| Bin-pack compaction | ✓ | ✓ | Auto + COMPACT | ✗ (use Spark) |
| Sort compaction | ✓ | ✗ | ✗ | ✗ |
| Z-order compaction | ✓ | ✗ | ✗ | ✗ |
| Expire snapshots | ✓ | ✓ | ✓ | ✗ (use Spark) |
| Remove orphan files | ✓ | ✓ | Auto | ✗ (use Spark) |
| Rewrite manifests (consolidate) | ✓ | ✓ | — | ✗ |
| Rewrite manifests (cluster by partition) | ✓ | ✗ | — | ✗ |
| Rewrite position delete files | ✓ | ✗ | — | ✗ |
| Format version upgrade | ✓ | ✓ | ✓ | ✗ |
| Write-time sort order | ✓ | ✓ | Clustering key | — |
| GDPR row deletion | ✓ | ✓ | ✓ | Run in Spark; REFRESH |

Load the specific engine file from `engines/` for the exact syntax.
