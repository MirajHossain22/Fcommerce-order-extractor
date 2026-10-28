# Pilot operations and deployment preparation

This repository is ready for the next deployment setup step, not already hosted. No hosting account, public hostname, or persistent volume has been selected. The local flow and recovery checks use synthetic data. The Docker engine was unavailable during this batch, so the image has not been built or tested.

## 1. Keep a recoverable database

Run these PowerShell commands from the repository root. Choose a different backup filename for every run:

```powershell
$env:PYTHONPATH = "backend"
New-Item -ItemType Directory -Force backups
.\.venv\Scripts\python.exe -m app.backup backup orders.sqlite3 backups/orders-before-pilot.sqlite3
.\.venv\Scripts\python.exe -m app.backup verify backups/orders-before-pilot.sqlite3
```

The tool uses SQLite's backup API, so committed WAL data is included and the application can stay running during backup. It checks database integrity, required tables, order records, and link references. It refuses missing sources, an existing destination, and identical source/destination paths. It operates on the current schema; start the app to migrate older databases before using this tool. A migration backup of an older database should be taken separately before that first start.

Backups contain customer data and private links. Keep them on restricted storage, outside the public static directory; `backups/` is ignored by Git. Move a copy to protected storage outside the app host, and test restoration before relying on that copy. Neither this tool nor the Dockerfile schedules backups automatically.

## 2. Restore without overwriting the live file

```powershell
.\.venv\Scripts\python.exe -m app.backup restore backups/orders-before-pilot.sqlite3 orders-restored.sqlite3
.\.venv\Scripts\python.exe -m app.backup verify orders-restored.sqlite3
```

Restore writes to a **new path only**. It preserves orders, courier details, checkout receipts, and buyer tracking links from the snapshot, but clears browser seller sessions so sellers must sign in again. Configured seller keys remain in environment/secret configuration, not in the backup.

Stop the current server before switching `DATABASE_PATH` to the restored file's absolute path. Keep the old database for rollback; do not delete or overwrite it. Restart the server, sign in, and verify an order, receipt, and tracking page. A snapshot does not include orders or status changes made after it was taken; reconcile those separately before resuming sales. Restoring also reinstates link state as of the snapshot.

Automated checks cover backup while a WAL connection remains open, restore into a new database, receipt replay after restore, session invalidation, corruption/orphan rejection, and refusal to overwrite files. These checks do not replace a recovery drill on the selected host.

## 3. Configure a persistent pilot instance

The pilot launcher is `python -m app.serve` with `PYTHONPATH=backend`. Unlike the local development command, it reads deployment settings from the **process environment**, not `.env`:

| Setting | Required configuration |
| --- | --- |
| `DATABASE_PATH` | Absolute path on a persistent local disk; parent directory must exist and be writable by the app user. |
| `ALLOWED_HOSTS` | Comma-separated exact public hostnames, without schemes/ports. Wildcards are rejected. Include any hostname used by health probes. |
| `SELLER_API_KEYS` | JSON secret-key-to-seller-ID mapping from the host's secret store. Keys must be at least 32 characters; generate random keys as described in `BACKEND_CHECKOUT.md`. |
| `HOST` | Defaults to `127.0.0.1`; the container sets `0.0.0.0` internally. |
| `PORT` | Defaults to `8000`. |
| `FORWARDED_ALLOW_IPS` | Defaults to `127.0.0.1`. Set the exact trusted reverse-proxy addresses; do not trust arbitrary internet clients. |

Use one application instance and one worker for this SQLite pilot. Do not use an ephemeral filesystem or a shared network filesystem for the live database. Keep health checks on `GET /healthz`; it returns 503 if the order table cannot be read and does not recreate a missing file. It checks storage reads, not AI quota, backup freshness, or write capacity.

The launcher disables access logs so checkout/tracking tokens are not routinely written into request logs. Configure any reverse proxy to omit or redact these paths too. The app rejects unexpected Host headers. The HTTPS reverse proxy must preserve the original Host and provide a trusted forwarded scheme so secure session cookies and origin checks work.

## 4. Container starter

The Dockerfile runs as a non-root user, copies only application code/static assets, and expects persistent storage mounted at `/data`. `.dockerignore` excludes `.env`, Git metadata, databases, backups, and the local virtual environment from the build context. Configure secrets at runtime; do not bake them into an image.

When Docker is available:

```powershell
docker build -t fcommerce-order-desk .
docker volume create fcommerce-orders
docker run --name fcommerce-order-desk -p 127.0.0.1:8000:8000 --mount source=fcommerce-orders,target=/data --env SELLER_API_KEYS --env ALLOWED_HOSTS --env FORWARDED_ALLOW_IPS fcommerce-order-desk
```

Set the named environment variables first. If using a bind mount instead of a named volume, give container UID 10001 write access to the mounted directory. This image is a starting configuration; build, startup, volume permissions, and restart persistence must be verified on the actual host. Dependencies currently use the repository's version ranges, not a reproducible lockfile.

## 5. Finish the hosted pilot

- [ ] Choose the host, domain, persistent disk, and backup destination.
- [ ] Build/start the app and verify persistent data after a restart or container replacement.
- [ ] Configure real HTTPS, HTTP-to-HTTPS redirection, exact hosts, and trusted proxy addresses.
- [ ] Verify login, Secure session cookies, logout, checkout sharing across devices, confirmation retries, courier display, and tracking through the public origin.
- [ ] Verify rejected cross-origin writes and seller isolation through the proxy.
- [ ] Run a backup/restore drill using a separate destination; record recovery time and retained order count.
- [ ] Set backup ownership/schedule, request-abuse controls, and an incident contact before real customer traffic.
- [ ] Invite a small seller/buyer group and record checkout completion time, abandonment, corrected details, duplicates, and status enquiries without collecting unnecessary contact data in analytics.

Live AI quality is still unverified. Manual checkout works independently of the AI provider. Courier information is entered by sellers; no courier booking or automatic delivery feed is implemented.
