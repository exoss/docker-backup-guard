# Docker Backup Guard

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Rclone](https://img.shields.io/badge/Rclone-333333?style=for-the-badge&logo=rclone&logoColor=white)
![Version](https://img.shields.io/badge/version-v1.2.3-blue?style=for-the-badge)

**Docker Backup Guard** is a robust, user-friendly backup automation tool for Docker containers. It combines a modern web interface with powerful background workers to ensure your data is safe, encrypted, and synced to the cloud.

Designed for **Raspberry Pi** and Linux servers, it supports both **Volume/Bind Mount backups** and **Portainer Configuration backups**.

## 🚀 Key Features

### 📦 Backup & Restore
*   **Smart Volume Detection:** Automatically finds volumes and bind mounts for containers labeled with `backup.enable=true`.
*   **Portainer API Integration:** Specifically designed to backup Portainer configurations via its API, avoiding database corruption risks.
*   **Atomic Snapshots:** Stops containers briefly to copy data, then restarts them immediately to minimize downtime before compression begins.
*   **AES-256 Encryption:** All backups are compressed and encrypted using standard libraries.
*   **Cloud Sync:** Built-in **Rclone** support to sync backups to Google Drive, S3, Dropbox, and 40+ other providers.

### 🖥️ Modern Web UI
*   **Dashboard:** View system status, last backup stats, and protected container list.
*   **Settings Editor:** Configure schedules, retention policies, and cloud settings directly from the browser.
*   **Rclone Config Editor:** Edit your `rclone.conf` file directly within the app (supports directory detection fixes).
*   **Action Center:** Manually trigger backups for specific containers or run a full system backup.
*   **Logs & Monitoring:** View real-time system logs and clear them with a single click.
*   **Multilingual:** Fully localized in **English**, **Türkçe**, and **Deutsch**.

### 🤖 Automation & Security
*   **Scheduled Backups:** Built-in scheduler runs daily backups at your specified time.
*   **Notifications:** Integrated **Gotify** support for success/failure alerts.
*   **Healthchecks:** Supports **Uptime Kuma** / Healthcheck.io pings to monitor backup job heartbeat.
*   **Secure:** Encrypted `.env` storage for sensitive tokens. Password-protected Web UI.

---

## 🛠️ Installation

### 1. Prepare your environment
Create a directory for the project:
```bash
mkdir -p docker-backup-guard/backups
mkdir -p docker-backup-guard/logs
touch docker-backup-guard/rclone.conf
cd docker-backup-guard
```

### 2. Docker Compose
Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  backup-guard:
    image: ghcr.io/exoss/docker-backup-guard:latest # Or build locally
    container_name: docker-backup-guard
    restart: unless-stopped
    ports:
      - "8501:8501"
    volumes:
      # Application State & Config
      - ./app/.env:/app/.env                 # Stores configuration
      - ./backups:/backups                   # Local backup storage
      - ./logs:/app/logs                     # Logs
      
      # Rclone Configuration (IMPORTANT: Do NOT use :ro if you want to edit via UI)
      - ./rclone.conf:/app/rclone.conf
      
      # Docker Socket (Required to control containers)
      # - /var/run/docker.sock:/var/run/docker.sock # (Insecure, see below for Socket Proxy)
      
      # Host Filesystem Access (Required to read volumes)
      - /:/hostfs:ro
      - /var/lib/docker/volumes:/var/lib/docker/volumes:ro
    environment:
      - TZ=Europe/Berlin
      - DOCKER_HOST=tcp://socket-proxy:2375 # Use Socket Proxy
    depends_on:
      - socket-proxy
    networks:
      - backup-net

  # Secure Docker Socket Proxy
  socket-proxy:
    image: tecnativa/docker-socket-proxy
    container_name: docker-socket-proxy
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - CONTAINERS=1 # Allow listing
      - POST=1       # Allow start/stop
      - IMAGES=1     # Allow image inspection
    networks:
      - backup-net

networks:
  backup-net:
    driver: bridge
```

### 3. Start the Container
```bash
docker-compose up -d
```

### 4. Initial Setup
1.  Open your browser and navigate to `http://YOUR_SERVER_IP:8501`.
2.  You will be greeted by the **Setup Wizard**.
3.  Enter your **Portainer URL & Token** (if using Portainer).
4.  Set a **Backup Password** (used for encryption).
5.  Configure **Rclone** (paste your config content directly in the UI).
6.  Save & Restart.

---

## ⚙️ Configuration

### Label Your Containers
To tell Docker Backup Guard which containers to backup, simply add the label `backup.enable=true` to them in your `docker-compose.yml` or via Portainer.

```yaml
services:
  my-database:
    image: postgres:14
    labels:
      - "backup.enable=true"
```

### Environment Variables
The application manages these automatically via the UI, but you can manually edit `.env/config.env`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `BACKUP_PASSWORD` | Password for AES-256 backup encryption (required) | — |
| `PORTAINER_URL` | Portainer server URL (optional, for API backup) | — |
| `PORTAINER_TOKEN` | Portainer API access token | — |
| `GOTIFY_URL` | Gotify server URL for push notifications | — |
| `GOTIFY_TOKEN` | Gotify app token | — |
| `HEALTHCHECK_URL` | Healthcheck.io or Uptime Kuma push URL | — |
| `VERIFY_SSL` | `true` / `false` for strict TLS certificate verification on outbound monitoring/API requests | `false` |
| `HEARTBEAT_URL` | Uptime Kuma push URL for periodic "system alive" pings | — |
| `HEARTBEAT_INTERVAL` | Minutes between heartbeat pings (0 = disabled) | `0` |
| `SCHEDULE_ENABLE` | `true` / `false` to enable daily backups | `false` |
| `SCHEDULE_TIME` | Time of day to run backup (24h format) | `03:00` |
| `RETENTION_DAYS` | Number of days to keep local and cloud backups | `7` |
| `TZ` | Timezone for scheduler | `Europe/Berlin` |
| `LANGUAGE` | UI language: `en`, `tr`, or `de` | `en` |
| `WEB_UI_USERNAME` | Web dashboard login username | `admin` |
| `WEB_UI_PASSWORD` | Web dashboard login password | `admin` |
| `RCLONE_CONFIG_PATH` | Path to rclone configuration file | `/app/rclone.conf` |
| `RCLONE_REMOTE_NAME` | Name of the remote in `rclone.conf` | `remote` |
| `RCLONE_DESTINATION` | Cloud destination path for backups | `backups` |

---

## ☁️ Cloud Sync (Rclone) setup
If you don't have an `rclone.conf` yet:
1.  **Use the UI:** The Settings tab includes an editor where you can paste a config generated on another machine (Windows/Mac).
2.  **Generate Locally:** Run `rclone config` on your PC, follow the steps for Google Drive/S3/Dropbox, and copy the output to the Web UI.

**Note:** If you see a "Permission denied" error when saving Rclone config in the UI, ensure your `docker-compose.yml` does **not** have `:ro` (read-only) on the `rclone.conf` volume mount.

---

## 🛡️ Security
*   **Web UI Access:** Protected by a login screen (default credentials set during setup).
*   **Encryption:** Sensitive environment variables (Tokens, Passwords) are encrypted at rest using `Fernet` (symmetric encryption).
*   **Backup Encryption:** Archives are encrypted with AES-256. You **must** remember your backup password to restore data!
*   **TLS Verification:** You can enable strict certificate validation for Portainer, heartbeat, and healthcheck requests with `VERIFY_SSL=true`.

---

## 📜 Logs & Troubleshooting
*   Logs are viewable in the **Logs** tab of the dashboard.
*   You can clear logs using the **"Clear Logs"** button to free up space.
*   Common Issue: *Rclone config path is a directory*. The app automatically detects this Docker misconfiguration and writes to `rclone.conf` inside that directory.

---

## ⚡ Performance (v1.2.0)
*   **O(1) membership lookups:** Module-level `frozenset` constants eliminate repeated list allocations in hot paths.
*   **Bulk container fetch:** Single Docker API call replaces N+1 per-container reloads, chunked into batches of 30 to avoid URI limits.
*   **Heartbeat pre-calculation:** URL parsing moved from every periodic tick to config-load time (>99% CPU reduction).
*   **Parallel stop/start:** `ThreadPoolExecutor` parallelizes container operations, reducing downtime for multi-container stacks.
*   **Connection pooling:** `requests.Session` with HTTP adapter reuse for Gotify/Portainer API calls.
*   **Immutable tuples:** Hot-path membership checks use tuples instead of inline lists.

---

## 📁 Project Structure
```
.
├── app/
│   ├── engine.py              # Core backup/restore logic
│   ├── api_handlers.py        # Portainer & Gotify API client
│   ├── scheduler_service.py   # Background scheduler + heartbeat
│   ├── ui.py                  # Streamlit web dashboard
│   ├── security.py            # Fernet encryption utilities
│   ├── languages.py           # i18n translations (en/tr/de)
│   └── tests/
├── tests/                     # Unit tests
├── main.py                    # Streamlit entry point
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh              # Launches scheduler + web UI
├── requirements.txt
└── .env.example               # Environment config template
```

---

**License:** MIT
