# NFR: Database Backup

## Scope
PostgreSQL database backup: scheduled dump, compression, S3 upload, retention cleanup.
Applies to production deployment via Docker Compose.

## Rules

### Deployment approach
- Dedicated `backup` service in `docker-compose.yml` — no server-level cron required
- Service built from same repo, restarts `unless-stopped`
- Scheduler implemented as Python process inside container (library: `schedule` or `APScheduler`)
- No separate cron daemon or `supercronic` required

### Configuration
- Backup credentials stored in `.env.backup` — separate from main `.env`
- `.env.backup` declared with `required: false` (Docker Compose ≥ v2.24):
  ```yaml
  env_file:
    - .env
    - path: .env.backup
      required: false
  ```
- If `.env.backup` absent: backup service starts dormant — logs "Backup not configured, skipping" each scheduled run, no crash
- If `.env.backup` present: backup activates automatically on next container restart

Required vars in `.env.backup`:

| Var | Example value |
|-----|---------------|
| `S3_ENDPOINT_URL` | `https://s3.twcstorage.ru` |
| `S3_BUCKET` | `9fa23c1c-29cabc89-8d4e-4c7c-81ca-0867885630c4` |
| `S3_ACCESS_KEY` | *(key value)* |
| `S3_SECRET_KEY` | *(secret value)* |
| `S3_REGION` | `ru-1` |
| `S3_PREFIX` | `backups/` (default) |

### Schedule
- Runs daily at **02:00 Asia/Yekaterinburg (UTC+5)** — matches bot timezone
- Implemented as blocking sleep loop: computes seconds until next 02:00, sleeps, runs

### Backup process
1. Run `pg_dump` against `db` service via internal Docker network
2. Compress output with gzip
3. Name file: `backup_YYYY-MM-DD.sql.gz`
4. Upload to S3: `{S3_PREFIX}backup_YYYY-MM-DD.sql.gz`
5. On success: log filename and S3 path
6. On failure: log error with traceback; no automatic retry (next run tomorrow)

### Retention policy
Applied after each successful upload. Retention evaluates all objects under `S3_PREFIX`:

| Age of backup | Action |
|---------------|--------|
| ≤ 14 days | Keep |
| 15 days – 6 months | Keep only if date is 1st of month; delete others |
| > 6 months | Delete |

Retention runs against backup filenames only (pattern: `backup_YYYY-MM-DD.sql.gz`).
Unrecognized filenames in `S3_PREFIX` are skipped silently.

### Secrets
- `.env.backup` never committed to git — add to `.gitignore`
- S3 credentials not logged, not stored anywhere except `.env.backup`

## Open questions
- [ ] On upload failure: log to stdout only (current), or active alert via Max message to owner?
- [ ] Restore procedure: not in spec scope. Document separately before first production incident.
