# Project Roadmap

This document outlines the planned development path for **Docker Backup Guard**. The focus is on enhancing reliability, expanding notification capabilities, and providing a robust Disaster Recovery solution.

## 🚀 Short-Term Goals (v1.1.0)

### 1. 🚨 Automated Restore Wizard (Disaster Recovery)
**Priority: Critical**
*   **Goal:** Enable users to restore containers directly from the web interface without manual file handling.
*   **Features:**
    *   **Backup Selection:** Browse available backups (local/cloud) by date.
    *   **One-Click Restore:** Automatically download, decrypt, extract, and place files in the correct volumes.
    *   **Container Management:** Automatically stop relevant containers before restore and restart them afterwards.
    *   **Safety Check:** Verification step to prevent accidental overwrites.

### 2. 📢 Advanced Notification System (Apprise)
**Priority: High**
*   **Goal:** Support a wider range of notification platforms beyond Gotify.
*   **Implementation:** Integrate the `Apprise` library.
*   **Supported Platforms:** Telegram, Discord, Slack, Microsoft Teams, Email (SMTP), Pushover, and 50+ others.
*   **UI Update:** Redesign the notification settings to allow selecting a provider and entering a unified configuration URL.

### 3. 🧹 Backup Exclusions (Per-Volume/Path)
**Priority: High**
*   **Goal:** Allow excluding non-critical/heavy paths (e.g., AI models, caches) from backups to save time and space.
*   **Config:**
    *   Global: `config/excludes.json` and optional `BACKUP_EXCLUDES` for quick patterns.
    *   Per-project/container: UI-managed list and Docker label `backup.exclude` (comma-separated glob patterns).
    *   Pattern Syntax: Glob-style (`**`, `*`), applied relative to each source path; works for bind mounts and named volumes.
*   **Engine:**
    *   Replace `cp` with `rsync -a` and `--exclude` rules; add `--dry-run` for preview.
    *   Install `rsync` in Docker image; keep performance-friendly defaults.
    *   Log excluded counts and write summary to `backup_state.json`.
*   **UI:**
    *   “Exclusions” panel per project: list volumes, add/remove patterns, quick presets (e.g., OpenWebUI models, node_modules).
    *   Preview button to simulate excludes and show estimated size/time impact.
*   **Safety:**
    *   Block patterns that exclude entire volumes; warn if >80% of files would be excluded.
    *   Protect critical paths (Docker metadata, .env, compose labels).
*   **Acceptance Criteria:** Users can define, preview, and persist exclusions; backups skip those paths; logs and state reflect exclusions.

---

## 🛠️ Mid-Term Goals (v1.2.0)

### 3. 🗄️ Zero-Downtime Database Backups
**Priority: High**
*   **Goal:** Perform backups of databases without stopping the containers (Hot Backup).
*   **Implementation:**
    *   **Database Modules:** Create specific handlers for MySQL, PostgreSQL, and MongoDB.
    *   **Execution:** Use `docker exec` to trigger native dump tools (`mysqldump`, `pg_dump`) directly to a stream.
    *   **Configuration:** Allow users to tag containers with specific database types (e.g., `backup.type=postgres`).

### 4. ☁️ Cloud File Browser & Manager
**Priority: Medium**
*   **Goal:** Manage remote backups directly from the Dashboard.
*   **Features:**
    *   **File Listing:** List files stored in the configured Rclone remote (Google Drive, S3, etc.).
    *   **Metadata:** Show file sizes and modification dates.
    *   **Management:** Allow deleting old or unnecessary backups from the cloud interface.

### 5. 🔐 Portainer Backup Encryption Toggle
**Priority: High**
*   **Goal:** Make Portainer-side encryption optional via environment variable to avoid double encryption.
*   **Config:** `PORTAINER_ENCRYPT=true|false` (default: `false`)
*   **Behavior:**
    *   When `false`: Do not send password to Portainer API; outer 7z uses `BACKUP_PASSWORD`.
    *   When `true`: Send `BACKUP_PASSWORD` to Portainer API; outer 7z can remain enabled.
*   **UI:** Add toggle to Settings with tooltip explaining trade-offs.
*   **Migration:** Existing setups continue with single encryption by default.

---

## 🔮 Long-Term Vision (v2.0.0)

### 5. 🔄 Incremental Backups (Restic Integration)
*   **Goal:** Switch from full snapshots to incremental backups to save space and bandwidth.
*   **Technology:** Evaluate integrating `Restic` or `BorgBackup` alongside Rclone.

### 6.  Advanced Analytics
*   **Goal:** Visual charts showing backup size growth over time, success rates, and storage predictions.
