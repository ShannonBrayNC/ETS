# Backup And Restore

## SQLite Alpha Backup

For alpha SQLite deployments, stop writes or place the service in maintenance
mode before copying the database file.

```powershell
Copy-Item .data\ets.db .backup\ets-$(Get-Date -Format yyyyMMddHHmmss).db
```

## Restore Validation

After restore:

1. Start ETS with `ETS_STORAGE_PROVIDER=sqlite` and `ETS_SQLITE_PATH` pointing
   at the restored file.
2. Check `GET /ready`.
3. Check `GET /api/v1/log/head`.
4. Fetch a known inclusion proof and verify it.
5. Compare the restored tree head with the pre-backup checkpoint.

## PostgreSQL Target

Future production deployments should use managed PostgreSQL backups with point in
time recovery. Target RPO and RTO should be selected by the evidence retention
policy; initial suggested targets are RPO 15 minutes and RTO 4 hours.

## Disaster Recovery Notes

Restoring an older database can create rollback risk. Clients should compare
trusted checkpoints and require consistency proofs after restore.
