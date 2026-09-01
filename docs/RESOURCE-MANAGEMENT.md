# Reflow Resource Management Reference

## 1. Managed Temporary Storage & Cleanup
Reflow maintains temporary files inside `storage/tmp/`. Each temporary artifact is registered in `TmpFileRecord` with:
- `owner`: System component or user process initiating the temp allocation.
- `created_at`: Generation timestamp.
- `expires_at`: Expiration timestamp (Default: +24h).

### Triggering Cleanup:
- **API**: `POST /api/system/storage/cleanup`
- **CLI / Daemon**: Invokes `TmpStorageService.purge_expired_tmp_files(db)`

---

## 2. Disk Space Pre-flight Reservation
Before accepting a heavy media render job, `ResourceManager` performs a pre-flight disk check:
- Validates available free disk space > 0.5 GB and > estimated job output size.
- Temporarily reserves estimated output space until job finishes or fails.
- Rejects job safely with HTTP 503 `INSUFFICIENT_DISK_SPACE` if disk threshold is breached.

---

## 3. Real Telemetry Data
The `/system` telemetry dashboard consumes `GET /api/system/performance`, reporting actual hardware metrics:
- **CPU**: Logical core count, real CPU load %.
- **Memory**: Total MB, used MB, available MB, usage %.
- **Disk**: Total GB, used GB, free GB, reserved GB.
- **Database Pool**: Active connection pool size, checked in, checked out, overflow.
- **Queue**: Active depth, max queue depth, oldest job age, jobs grouped by status/type.
