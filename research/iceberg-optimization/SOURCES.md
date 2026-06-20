# Sources

The recommendations in this book are synthesized from the Apache Iceberg
documentation, vendor/platform docs, practitioner writing, and one long-form
source supplied for this research. Numeric rules of thumb are community/vendor
defaults current as of mid-2026; validate against your own optimization profile.

## Supplied source

- *Architecting an Apache Iceberg Lakehouse* (manuscript, dated 2026-06-18) —
  esp. ch. 5 (ingestion layer), ch. 9 (maintenance: small files, colocation,
  metadata sprawl, MOR, compaction, snapshot expiration, COW vs MOR retention,
  GDPR), and the metadata-tables appendix. Used for compaction options, COW/MOR
  retention guidance, expiration cadence (daily COW / hourly MOR), dangling
  deletes, branch/tag retention, and the ingestion-tool survey.

## Apache Iceberg internals & procedures

- Apache Iceberg docs — Spark procedures (`rewrite_data_files`,
  `expire_snapshots`, `remove_orphan_files`, `rewrite_manifests`,
  `rewrite_position_delete_files`): https://iceberg.apache.org/docs/latest/spark-procedures/
- Dremio — *Compaction in Apache Iceberg* / *Maintaining Iceberg Tables*:
  https://www.dremio.com/blog/compaction-in-apache-iceberg-fine-tuning-your-iceberg-tables-data-files/
  · https://www.dremio.com/blog/maintaining-iceberg-tables-compaction-expiring-snapshots-and-more/
- Dremio — *Row-Level Changes: Copy-On-Write vs Merge-On-Read*:
  https://www.dremio.com/blog/row-level-changes-on-the-lakehouse-copy-on-write-vs-merge-on-read-in-apache-iceberg/
- AWS Prescriptive Guidance — *Optimizing write performance* (distribution mode,
  target file size): https://docs.aws.amazon.com/prescriptive-guidance/latest/apache-iceberg-on-aws/best-practices-write.html
- Cloudera — *Optimization Strategies for Iceberg Tables*:
  https://www.cloudera.com/blog/technical/optimization-strategies-for-iceberg-tables.html
- IOMETE — *The Iceberg Maintenance Runbook*:
  https://iomete.com/resources/blog/iceberg-maintenance-runbook
- Alex Merced — Iceberg metadata tables / maintenance masterclass:
  https://iceberglakehouse.com/posts/2026-04-29-iceberg-masterclass-10/

## Platform docs

- Databricks — *Predictive optimization for Unity Catalog managed tables*:
  https://docs.databricks.com/aws/en/optimizations/predictive-optimization
- Databricks — *Liquid clustering*:
  https://docs.databricks.com/aws/en/tables/clustering
- Databricks — *Unity Catalog and the next era of Apache Iceberg* (managed
  Iceberg GA, v3): https://www.databricks.com/blog/unity-catalog-and-next-era-apache-icebergtm
- Snowflake — *Manage Apache Iceberg tables* (managed vs external, automatic
  maintenance): https://docs.snowflake.com/en/user-guide/tables-iceberg-manage
- Snowflake — Iceberg tables architecture & 2026 features (Table Optimization
  Service, v3 preview): https://www.flexera.com/blog/finops/snowflake-iceberg-table/
- dbt — *Snowflake and Apache Iceberg* / Snowflake configs:
  https://docs.getdbt.com/docs/mesh/iceberg/snowflake-iceberg-support
  · https://docs.getdbt.com/reference/resource-configs/snowflake-configs
- dbt — Spark configs (Iceberg): https://docs.getdbt.com/reference/resource-configs/spark-configs
- Apache NiFi — `PutIceberg` processor:
  https://docs.cloudera.com/cfm/4.10.0/nifi-components-cfm/docs/nifi-docs/components/org.apache.nifi/nifi-iceberg-processors-nar/x/org.apache.nifi.processors.iceberg.PutIceberg/index.html
- Apache Iceberg — Flink writes / sink (checkpoint↔commit, deletes):
  https://iceberg.apache.org/docs/latest/flink-writes/
  · upsert/equality-delete pitfall: https://github.com/apache/iceberg/issues/15305

## Small-file & streaming references

- Dremio — *Minimizing Iceberg Table Management with Smart Writing*:
  https://www.dremio.com/blog/minimizing-iceberg-table-management-with-smart-writing/
- Ancestry Eng. — *Solving the Small File Problem in Iceberg Tables*:
  https://medium.com/ancestry-product-and-technology/solving-the-small-file-problem-in-iceberg-tables-6c31a295f724
- OLake — *Merge-on-Read vs Copy-on-Write*: https://olake.io/iceberg/mor-vs-cow/
