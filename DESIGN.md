# Restore Container v1.1.0 Design Document

## 1. Executive Summary
This document outlines the architecture for the "Restore Container" v1.1.0 upgrade. The primary goal is to transition from a monolithic backup strategy to a **Hybrid Backup Architecture**. This allows for granular, project-specific scheduling (e.g., Dockmost daily, Gotify weekly) alongside full-system "Doomsday" disaster recovery. The UI will be optimized for performance using a "Filter & Fetch" pattern and secured with a password-gated confirmation mechanism.

## 2. Architecture: Hybrid Backup Strategy
The system will support three concurrent backup modes:

### A. Granular Project Backups (Primary)
- **Scope:** Single Docker Compose project (e.g., `dockmost`, `n8n`).
- **Mechanism:** 
  1. Identify containers via `com.docker.compose.project` label.
  2. Stop specific project containers.
  3. Archive volumes linked to that project.
  4. Encrypt & Upload.
  5. Restart containers.
- **Scheduling:** Independent cron schedules per project (defined in UI/`.env`).

### B. Disaster Recovery ("Doomsday" Backup)
- **Scope:** All volumes, Docker configurations, and environment files.
- **Mechanism:** Full system freeze -> Bulk compression -> Encryption -> Upload.
- **Scheduling:** Dedicated global schedule (e.g., Monthly or Weekly).

### C. Portainer Configuration
- **Scope:** Portainer metadata and internal database.
- **Mechanism:** Portainer API call.
- **Trigger:** Scheduled or pre-hook for Disaster Recovery.

## 3. Security: Password-Gated Confirmation
To prevent accidental data loss or unauthorized restores, critical actions require dual authentication.

- **Workflow:**
  1. User clicks "Restore" or "Delete".
  2. System prompts: *"Are you sure?"* (Soft Confirmation).
  3. System prompts: *"Enter BACKUP_PASSWORD to confirm"* (Hard Confirmation).
  4. Logic validates input against `BACKUP_PASSWORD` hash in `.env`.
  5. Action executes only upon success.

## 4. UI/UX Design (Streamlit)

### Performance: "Filter & Fetch" Pattern
Listing thousands of cloud backup files causes UI freezes. We will adopt a lazy-loading strategy:
1. **Initial State:** Empty list or last 5 recent backups.
2. **User Action:** Selects `Project Name` and `Date Range` in Sidebar.
3. **Action:** Clicks "Search Backups".
4. **Backend:** Queries Rclone/Cloud API with filters.
5. **Display:** Results populate the table.

### Caching Strategy
- Use `st.session_state` to cache API responses.
- **Manual Control:** A "Clear Cache / Refresh" button in the sidebar to force a re-fetch from the cloud provider.

### Scheduler Dashboard
A new "Automation" page will replace the simple toggle:
| Project Name | Schedule (Cron) | Last Backup | Next Backup | Status |
| :--- | :--- | :--- | :--- | :--- |
| `dockmost` | `0 3 * * *` (Daily) | 2h ago | 22h left | [Toggle] |
| `gotify` | `0 4 * * 0` (Weekly) | 1d ago | 6d left | [Toggle] |

## 5. Backend Modularization Plan
Refactor `engine.py` to decouple monolithic logic.

### New Module Structure
- **`managers/backup_manager.py`**: Orchestrator for routing requests.
- **`managers/project_backup.py`**: Handles logic for single-project isolation (Stop -> Tar -> Start).
- **`managers/system_backup.py`**: Handles Disaster Recovery logic.
- **`services/scheduler_service.py`**: Updated to handle a dynamic list of jobs instead of a single global timer.

## 6. Data Flow
1. **Scheduler** reads config -> Triggers `ProjectBackup.run("dockmost")`.
2. **Engine** locks project -> Performs Backup -> Updates `history.json`.
3. **UI** polls `history.json` or query Cloud API (on demand) -> Updates Dashboard.
