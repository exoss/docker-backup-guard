# Restore Container

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Rclone](https://img.shields.io/badge/Rclone-333333?style=for-the-badge&logo=rclone&logoColor=white)

**Restore Container** is a lightweight, secure, and user-friendly backup solution designed for Docker environments. Optimized for Raspberry Pi (ARM64) and generic Linux servers (AMD64), it provides an all-in-one interface to manage container backups, encryption, and cloud synchronization.

![Dashboard Screenshot](https://via.placeholder.com/800x400?text=Dashboard+Screenshot+Placeholder)

## 🚀 Features

*   **Smart Volume Detection:** Automatically identifies and backs up volumes and bind mounts of containers labeled with `backup.enable=true`.
*   **Security First:** Uses **AES-256** encryption (Fernet) to secure your data before it leaves the server.
*   **Cloud Sync:** Integrated **Rclone** support to sync encrypted backups to Google Drive, Dropbox, S3, or any other cloud provider.
*   **Multi-Language Support:** Fully localized UI in **English**, **Türkçe**, and **Deutsch**.
*   **Notifications:** Real-time status updates via **Gotify**.
*   **Setup Wizard:** User-friendly initial setup wizard to configure environment variables without touching the terminal.

## 🛠️ Installation

### Prerequisites

*   Docker & Docker Compose installed on your host.
*   An Rclone configuration file (`rclone.conf`) ready.

### Quick Start

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/restore-container.git
    cd restore-container
    ```

2.  **Prepare your Rclone config:**
    Place your `rclone.conf` file in a known location (e.g., `./config/rclone/rclone.conf`).

3.  **Run with Docker Compose:**
    ```yaml
    version: '3.8'

    services:
      restore-container:
        build: .
        container_name: restore_container
        restart: unless-stopped
        ports:
          - "8501:8501"
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock
          - ./backups:/backups
          - ./.env:/app/.env
          - ./config/rclone:/config/rclone:ro
        environment:
          - TZ=Europe/Berlin
    ```

    ```bash
    docker-compose up -d --build
    ```

4.  **Access the UI:**
    Open your browser and navigate to `http://localhost:8501`.

## 📖 Usage

### 1. Label Your Containers
To enable backup for a specific container, simply add the following label to its `docker-compose.yml` or run command:

```yaml
labels:
  - "backup.enable=true"
```

### 2. Configure via Wizard
On first launch, you will be greeted by the **Setup Wizard**. Here you can configure:
*   **Portainer & Gotify** credentials.
*   **Backup Password** (Crucial for encryption!).
*   **Retention Policy** (How many days to keep backups).
*   **Timezone** (Default: Europe/Berlin).

### 3. Backup & Restore
*   Go to the Dashboard.
*   You will see a list of backup-ready containers.
*   Click **Backup** to start the process:
    1.  Container stops.
    2.  Volumes are compressed (`.tar.gz`).
    3.  Archive is encrypted (`.enc`).
    4.  Encrypted file is synced to Cloud (via Rclone).
    5.  Container restarts.

## 🌍 Multi-Language Support
The application automatically detects your language preference during setup. You can choose between:
*   🇬🇧 English
*   🇹🇷 Türkçe
*   🇩🇪 Deutsch

## 🔒 Security Note
*   **Never share your `BACKUP_PASSWORD`.** Without it, your encrypted backups are irretrievable.
*   Sensitive environment variables are stored in `.env` and are never exposed in the UI logs.

## 📜 License
This project is licensed under the MIT License.
