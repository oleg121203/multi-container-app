# Restore from backup — Vector DB and Redis

Severity: P1

Scope: restore Qdrant/Milvus data from object storage and restore Redis from RDB/AOF snapshot.

Prerequisites:

- Access to object storage (S3 or compatible) with backups.
- Credentials for cluster admin and access to `kubectl` for the target cluster/env.

Steps: Qdrant (example)

1. Scale down writers/clients that may write to DB to avoid data races.
2. Create a temporary restore pod with access to the persistent volume.
3. Download backup from S3: `aws s3 cp s3://my-bucket/qdrant-backups/2025-08-22.tar.gz /tmp/restore/`.
4. Extract and restore using qdrant import utilities or replace PVC data (follow vendor docs).
5. Verify collection count and sample vectors: run a small query.
6. Scale services back up and monitor metrics and logs.

Steps: Redis (example)

1. If Redis is deployed as a StatefulSet, create a backup pod that mounts the same PVC or a new PVC and copy RDB/AOF into the volume.
2. Stop Redis (or scale to single node) and replace dump.rdb / appendonly.aof with the snapshot.
3. Start Redis and monitor replication and error logs.

Validation:

- Run health checks: RAG queries return expected sample results.
- Verify Prometheus metrics show stable traffic and no high error rates.

Backup cadence (recommended):

- Vector DB: daily incremental + weekly full; retain ≥30 days on S3-compatible storage.
- Redis: RDB every 15 minutes or AOF continuous; daily snapshot to external storage.

Recovery drills:

- Monthly: perform restore into sandbox/CI environment, run smoke RAG queries and basic load (100 queries) to confirm integrity and performance.

Postmortem:

- Document root cause and timeline in the incident runbook file.
- Consider automating restore in CI sandbox for periodic drills.

References:

- Qdrant backup docs: [Qdrant docs](https://qdrant.tech/documentation/)
- Redis persistence: [Redis persistence docs](https://redis.io/docs/manual/persistence/)
