# 🗺️ Docker Backup Guard — Roadmap

> **Current version:** v1.2.0 | **Last updated:** 2026-06-25
>
> This roadmap is a living document. Priorities shift based on user feedback and real-world usage.

---

## 📊 What We've Built So Far

### v1.0.x — Foundation (Released ✅)
- Docker container discovery via labels (`backup.enable=true`)
- Stop → Copy → Start snapshot workflow
- AES-256 7z encryption
- Rclone cloud sync (40+ providers)
- Streamlit web UI with login
- Portainer API backup
- Gotify notifications
- Healthcheck.io / Uptime Kuma ping support
- EN/TR/DE multilingual support

### v1.1.0 — Reliability (Released ✅)
- Docker socket proxy for security
- Scheduler with `.env` hot-reload
- Setup wizard for first-run experience
- Settings editor with edit-mode toggle
- Log viewer with deque-based tail
- Retry logic for container stop/start ops
- Test suite foundation

### v1.2.0 — Performance (Released ✅)
- Module-level `frozenset` constants → O(1) membership lookups
- `os.scandir()` → O(1) empty directory checks
- Bulk container fetch → eliminates N+1 API calls
- Heartbeat URL pre-calculation → >99% CPU reduction in scheduler loop
- `ThreadPoolExecutor` → parallel container stop/start
- `requests.Session` → connection pooling for API calls
- Chunked Docker API requests → no URI length limits
- Immutable tuples in hot paths → zero allocation overhead

---

## 🎯 v2.0.0 — "The Restore Release"

> **Theme:** Backup is half the job. Restore completes it.
>
> **Target:** Q3 2026 | **Effort:** ~6-8 weeks

### 2.1 🔄 Automated Restore Wizard
**Priority: 🔴 Critical | Effort: L**

**Why:** The #1 missing feature. Users currently must manually download, decrypt, extract, and copy files. This turns a 10-minute disaster into a 2-hour panic.

**Technical Design:**
```
UI Flow:
  1. "Restore" tab → list available backups (local + cloud via rclone ls)
  2. Select backup → show metadata (date, size, containers included)
  3. Preview step → show which volumes/containers will be affected
  4. Dry-run toggle → simulate without writing
  5. Execute → stop containers → extract 7z → rsync files → start containers
  6. Result summary → what was restored, any warnings

Engine additions:
  - BackupIndex class: scans /backups/*.7z + rclone remote for available archives
  - RestoreEngine.restore_from_archive(archive_path, target_containers, dry_run=False)
  - Volume mapping: maps archive paths back to Docker volume/bind mount destinations
  - Safety: never overwrite newer files without confirmation
  - Rollback: if restore fails mid-way, revert to pre-restore state
```

**Acceptance Criteria:**
- [ ] User can browse local and cloud backups from the UI
- [ ] User can restore a full backup or select specific containers
- [ ] Dry-run mode shows exactly what will happen before execution
- [ ] Containers are automatically stopped/started during restore
- [ ] Restore operation is logged with full audit trail

---

### 2.2 📦 Backup History & Metrics
**Priority: 🟠 High | Effort: M**

**Why:** `backup_state.json` only stores the *last* backup. No history, no trends, no way to know if backups are growing or failing over time.

**Technical Design:**
```
Database: SQLite (zero-config, single file, no server)
Location: /backups/backup_history.db

Schema:
  backups (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,        -- 'success' | 'failed' | 'skipped'
    size_bytes INTEGER,
    container_count INTEGER,
    duration_seconds REAL,
    archive_name TEXT,
    compression_ratio REAL,      -- original_size / compressed_size
    error_message TEXT,
    triggered_by TEXT             -- 'scheduler' | 'manual' | 'api'
  )

  backup_containers (
    backup_id INTEGER REFERENCES backups(id),
    container_name TEXT,
    container_id TEXT,
    volumes_backed_up INTEGER,
    status TEXT
  )

UI additions:
  - Time-series chart: backup size over time (last 30/90/365 days)
  - Success rate gauge: 95% → green, <80% → red
  - Storage projection: "At current growth rate, 7-day retention = ~X GB"
  - Table view: sortable, filterable backup history
```

**Acceptance Criteria:**
- [ ] Every backup run creates a history record in SQLite
- [ ] Dashboard shows size trend chart and success rate
- [ ] User can filter history by date range, status, container
- [ ] Old history records are cleaned up according to retention policy

---

### 2.3 🔔 Apprise Notification Integration
**Priority: 🟠 High | Effort: S**

**Why:** Gotify-only notification limits the audience. Apprise adds 50+ providers with minimal code changes.

**Technical Design:**
```
New dependency: apprise>=1.9.0

Config additions in .env / UI:
  NOTIFICATION_PROVIDER = "gotify" | "apprise" | "both"
  APPRISE_URL = "discord://webhook_id/webhook_token"
  APPRISE_URL_2 = "tgram://bot_token/chat_id"  (optional secondary)

Implementation:
  - NotificationManager class wrapping Gotify + Apprise
  - send_notification(title, message, priority) dispatches to configured providers
  - Backward compatible: existing Gotify config continues to work unchanged
  - UI: dropdown to select provider + help text with common Apprise URL formats
```

**Acceptance Criteria:**
- [ ] User can configure Apprise URL from Settings UI
- [ ] Notifications are sent to both Gotify and Apprise if both configured
- [ ] Connection test button works for Apprise providers
- [ ] Existing Gotify-only users see no change in behavior

---

## 🏗️ v2.1.0 — "Production Ready"

> **Theme:** Quality, testing, operations.
>
> **Target:** Q4 2026 | **Effort:** ~4-6 weeks

### 2.4 🧪 CI/CD Pipeline & Test Coverage
**Priority: 🟠 High | Effort: M**

**Why:** No CI means regressions slip through. No automated Docker builds means manual releases.

**Technical Design:**
```yaml
.github/workflows/ci.yml:
  - Lint: ruff check app/ tests/
  - Type check: mypy app/ (strict mode, gradual rollout)
  - Unit tests: pytest --cov=app --cov-report=html (with Docker mocking)
  - Integration tests: docker-compose up, run backup, verify output
  - Security scan: trivy fs --severity HIGH,CRITICAL .

.github/workflows/release.yml:
  - On tag push (v*):
    - Build multi-arch image (linux/amd64, linux/arm64, linux/arm/v7)
    - Push to ghcr.io/exoss/docker-backup-guard:$TAG + :latest
    - Generate SBOM (spdx)
    - Create GitHub Release with changelog

Test coverage targets:
  - engine.py: >80% (core logic)
  - api_handlers.py: >70%
  - security.py: 100% (crypto must be flawless)
  - ui.py: >50% (harder to test, focus on critical paths)
```

**Acceptance Criteria:**
- [ ] PRs cannot merge without passing CI
- [ ] Multi-arch images built and pushed automatically on release
- [ ] Test coverage report generated per PR
- [ ] Security scan runs weekly + on dependency changes

---

### 2.5 📋 Backup Exclusions (per-volume patterns)
**Priority: 🟡 Medium | Effort: L**

**Why:** Backing up `node_modules`, `.cache`, AI model weights wastes time and space. Users need control.

**Technical Design:**
```
Config sources (merged, later overrides earlier):
  1. Global: BACKUP_EXCLUDE_GLOBAL in .env (comma-separated globs)
  2. Per-container: Docker label backup.exclude (comma-separated globs)
  3. Per-volume: UI-managed exclusion list per container volume

Engine changes:
  - Replace cp -rp with rsync -a --exclude={pattern} --exclude={pattern}...
  - Add rsync to Dockerfile
  - Exclusion preview: rsync --dry-run --stats to estimate savings
  - Log: "Skipped 342 files (1.2 GB) matching exclude patterns"

UI additions:
  - Per-container "Exclusions" expander in Action Center
  - Quick-preset buttons: [node_modules] [.cache] [.venv] [__pycache__] [.git]
  - Custom pattern input with glob syntax validation
  - Preview button: shows how many files/bytes would be excluded
```

**Acceptance Criteria:**
- [ ] Users can define global and per-container exclusion patterns
- [ ] UI provides quick-preset buttons for common patterns
- [ ] Preview mode shows estimated savings before applying
- [ ] Exclusions are logged per backup run

---

## 🔮 v3.0.0 — "Enterprise Features"

> **Theme:** Scale, multi-node, advanced recovery.
>
> **Target:** 2027 | **Effort:** ~12 weeks

### 3.1 🗄️ Zero-Downtime Database Backups
**Priority: 🟡 Medium | Effort: XL**

**Why:** Stopping a Postgres container for backup causes ~10-30s downtime. Database-aware hot backups eliminate this.

**Technical Design:**
```
Container labeling:
  backup.type = "postgres" | "mysql" | "mongo" | "volume" (default)
  backup.db_user = "postgres"          (optional, auto-detected)
  backup.db_name = "mydb"              (optional, dumps all if omitted)

Engine modules:
  - DatabaseBackupBase (abstract): dump(), restore(), test_connection()
  - PostgresBackup: docker exec {container} pg_dump -U {user} {db} > /tmp/dump.sql
  - MySQLBackup: docker exec {container} mysqldump -u {user} -p{pass} {db}
  - MongoBackup: docker exec {container} mongodump --archive

Flow:
  1. Detect backup.type label
  2. If database type: run dump inside container → stream to host temp file
  3. Include dump file in 7z alongside volume data
  4. On restore: extract dump → docker exec {container} psql/ mysql < dump.sql

Safety:
  - Verify dump integrity before declaring success
  - Timeout per dump (default 30 min, configurable)
  - Lock-free where possible (--no-lock for MySQL, --no-owner for Postgres)
```

**Acceptance Criteria:**
- [ ] Postgres, MySQL, MongoDB hot backups working
- [ ] Backup does not stop the database container
- [ ] Dump integrity verified after creation
- [ ] Restore correctly replays the dump into the container

---

### 3.2 🔄 Incremental Backups via Restic
**Priority: 🟡 Medium | Effort: XL**

**Why:** Full 7z snapshots every day waste storage and bandwidth. Incremental backups store only changes.

**Technical Design:**
```
Mode toggle (per backup strategy):
  MODE = "full" (current 7z behavior) | "incremental" (restic)

Restic integration:
  - Initialize restic repository on first run
  - Each backup = restic snapshot with tags (container name, timestamp)
  - Retention policy: restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6
  - Encryption: restic's built-in AES-256 (or repo-level key from BACKUP_PASSWORD)

Benefits over current approach:
  - 90%+ storage reduction for typical workloads
  - 10-50x faster backups after initial snapshot
  - Deduplication across containers and over time
  - Built-in integrity verification (restic check)

Migration path:
  - Both modes coexist — user chooses per backup
  - Full mode remains default for simplicity
  - Incremental mode requires restic binary in Docker image
```

**Acceptance Criteria:**
- [ ] Restic repository initialization from UI
- [ ] Incremental backup runs correctly, storing only changed data
- [ ] Restore from incremental backup works (restic mount + rsync)
- [ ] Storage savings measurable and displayed in dashboard

---

### 3.3 🖥️ Multi-Node / Agent Mode
**Priority: 🟢 Low (Future) | Effort: XXL**

**Why:** Users with multiple Docker hosts currently need separate DBG instances. An agent mode enables centralized management.

**Concept:**
```
                    ┌─────────────────┐
                    │  DBG Controller  │  ← Central UI + scheduler
                    │  (Web UI + API)  │
                    └──────┬──────────┘
                           │ HTTPS + API key
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ DBG Agent│ │ DBG Agent│ │ DBG Agent│  ← Per-host backup workers
        │ (Docker) │ │ (Docker) │ │ (Docker) │
        └──────────┘ └──────────┘ └──────────┘
        Host A       Host B       Host C

  - Agent: lightweight container, only runs engine.py + rclone
  - Controller: full UI, delegates backup jobs to agents
  - Communication: REST API with token auth over HTTPS
  - Fleet dashboard: all hosts status in single view
```

---

## 🧹 Continuous Improvements (Ongoing)

These are smaller items worked on between major releases:

| # | Item | Impact |
|---|------|--------|
| 1 | **Backup verification:** `7z t` integrity check after compression | Catches silent corruption |
| 2 | **Email summary:** Weekly digest of backup status to configured email | Situational awareness |
| 3 | **Backup size estimation:** Show estimated size before starting | User confidence |
| 4 | **Pre/post backup hooks:** Run custom scripts before/after backup | Flexibility |
| 5 | **Docker healthcheck endpoint:** `/health` API returning JSON status | Monitoring integration |
| 6 | **ARMv6 (Raspberry Pi Zero) support:** Test and document | Wider hardware |
| 7 | **Dark mode:** Streamlit theme toggle | UX polish |
| 8 | **Backup tags/labels:** User-defined tags for backup categorization | Organization |
| 9 | **Encryption key backup reminder:** Nag if key not backed up | Disaster recovery |
| 10 | **Log structured logging:** JSON log format option | Log aggregation tools |

---

## 📅 Timeline Summary

```
2026 Q2 ─ v1.2.0 ✅ Performance optimizations (CURRENT)
2026 Q3 ─ v2.0.0 🎯 Restore wizard + History + Apprise
2026 Q4 ─ v2.1.0 🏗️ CI/CD + Test coverage + Exclusions
2027 Q1 ─ v2.2.0 🗄️ Database hot backups
2027 Q2 ─ v3.0.0 🔄 Incremental backups (Restic)
2027 Q3+ ─ v3.x   🖥️ Multi-node / Advanced analytics
```

---

## 🗳️ How Priorities Are Set

1. **User feedback:** GitHub issues + discussions weigh heaviest
2. **Breaking changes:** Security fixes jump to top of queue
3. **Effort/Impact ratio:** Low-effort, high-impact features ship first
4. **Dependency requests:** If a feature unblocks another, it gets priority

---

> **Want to influence this roadmap?** Open a [GitHub Issue](https://github.com/exoss/docker-backup-guard/issues) with the `enhancement` label or 👍 an existing feature request.
