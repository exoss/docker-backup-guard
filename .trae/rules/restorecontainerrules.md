# Critical Instructions
- **Stack:** Python (Docker-py, Rclone-wrapper, Streamlit).
- **Target:** Raspberry Pi (ARM64/AMD64). Lightweight & Dockerized.
- **Workflow:** If .env is missing, boot into Streamlit Setup Wizard. Mask secrets in UI.

# Backup Logic
- **Labels:** Process ONLY containers with `backup.enable=true`.
- **Sequence:** Stop containers -> Portainer API Backup -> Tar/GZ Compress -> AES-256 Encrypt -> Rclone Sync -> Restart containers.
- **Retention:** Auto-delete local/remote backups older than `RETENTION_DAYS`.

# Safety & Monitoring
- **Error Handling:** Use try-except for all steps. Notify via Gotify & Healthcheck URL on Success/Fail.
- **Security:** Never log plain-text passwords. Use `/var/run/docker.sock` with minimal privileges.
- **Environment:** Default TZ: `Europe/Berlin`. Config via `.env`.

# UI Requirements
- Minimalist dashboard: Manual backup trigger, status overview, and live logs.
- Split code into modules: `engine.py`, `ui.py`, `api_handlers.py`.