# Backup & Restore Runbook (INFRA-BACKUP-001)

> Status: **runbook authored, cron not yet wired**. Operator must apply the
> compose snippet and S3 lifecycle policy below to close out the finding.

## Scope

Daily logical backup of Postgres 15 to S3 + 30-day retention via lifecycle.
Quarterly restore drill into a throwaway environment.

## Backup container (compose snippet)

Add the following service to `docker-compose.prod.yml` (or a
private overlay) once AWS credentials are configured:

```yaml
  pg-backup:
    image: postgres:15-alpine
    restart: unless-stopped
    env_file: ../../.env
    environment:
      - PGHOST=postgres
      - PGUSER=${POSTGRES_USER:-postgres}
      - PGDATABASE=${POSTGRES_DB:-finance_tracker}
      - AWS_ACCESS_KEY_ID
      - AWS_SECRET_ACCESS_KEY
      - AWS_DEFAULT_REGION
      - BACKUP_BUCKET=${BACKUP_BUCKET:?must be set}
    entrypoint: ["sh", "-c"]
    command:
      - |
        apk add --no-cache aws-cli >/dev/null
        echo "0 2 * * * /backup.sh >> /var/log/backup.log 2>&1" | crontab -
        crond -f -L /var/log/cron.log
    volumes:
      - ../70-runbooks/scripts/backup.sh:/backup.sh:ro
    networks: [finance-internal]
    depends_on:
      postgres: { condition: service_healthy }
```

## `scripts/backup.sh` (reference)

```bash
#!/bin/sh
set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
KEY="postgres/$(date -u +%Y/%m/%d)/finance-${TS}.sql.gz"
pg_dump --no-owner --format=plain | gzip -9 \
  | aws s3 cp - "s3://${BACKUP_BUCKET}/${KEY}" \
      --storage-class STANDARD_IA \
      --metadata "host=${PGHOST},db=${PGDATABASE}"
echo "uploaded ${KEY}"
```

Cron is `0 2 * * *` (02:00 UTC). Retention is enforced server-side via the
S3 lifecycle policy below — the script itself does not delete.

## S3 lifecycle policy

```json
{
  "Rules": [
    {
      "ID": "expire-daily-30d",
      "Status": "Enabled",
      "Filter": { "Prefix": "postgres/" },
      "Expiration": { "Days": 30 }
    },
    {
      "ID": "monthly-retention-12m",
      "Status": "Enabled",
      "Filter": { "Prefix": "postgres-monthly/" },
      "Expiration": { "Days": 365 }
    }
  ]
}
```

Apply via `aws s3api put-bucket-lifecycle-configuration`. Optionally enable
versioning + Object Lock (governance mode) for compliance.

## Restore drill (quarterly)

1. Spin up an isolated stack:
   ```bash
   COMPOSE_PROJECT_NAME=ftrestore \
     docker compose -f docker-compose.prod.yml up -d postgres
   ```
2. Pick the most recent dump and stream it back:
   ```bash
   aws s3 cp "s3://${BACKUP_BUCKET}/postgres/$(date -u +%Y/%m/%d)/" - --recursive \
     | gunzip \
     | docker exec -i ftrestore-postgres-1 psql -U postgres -d finance_tracker
   ```
3. Run the smoke test suite against the restored DB:
   ```bash
   make -f Makefile audit-test-backend
   ```
4. Tear down:
   ```bash
   docker compose -p ftrestore down -v
   ```
5. Record the drill in `docs/audit/snapshot/restore-drills.md`
   (date, dump key, runtime, success/fail).

## Alarms

- CloudWatch alarm: object count in `postgres/` prefix < 1 in last 36 h.
- CloudWatch alarm: most recent object age > 30 h.
- Page on either alarm.

## Open work (user action required)

- [ ] Provision IAM user with `s3:PutObject` only on the backup prefix.
- [ ] Set `BACKUP_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` in
      production `.env`.
- [ ] Apply the lifecycle JSON to the bucket.
- [ ] Schedule the first quarterly restore drill.
