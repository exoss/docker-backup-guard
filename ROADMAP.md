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

---

## 🔮 Long-Term Vision (v2.0.0)

### 5. 🔄 Incremental Backups (Restic Integration)
*   **Goal:** Switch from full snapshots to incremental backups to save space and bandwidth.
*   **Technology:** Evaluate integrating `Restic` or `BorgBackup` alongside Rclone.

### 6.  Advanced Analytics
*   **Goal:** Visual charts showing backup size growth over time, success rates, and storage predictions.
