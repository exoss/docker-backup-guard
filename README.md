# Docker Backup Guard

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Rclone](https://img.shields.io/badge/Rclone-333333?style=for-the-badge&logo=rclone&logoColor=white)
![7-Zip](https://img.shields.io/badge/7--Zip-0096D6?style=for-the-badge&logo=7-zip&logoColor=white)

**Docker Backup Guard** is a lightweight, secure, and user-friendly backup solution designed for Docker environments. Optimized for **Raspberry Pi (ARM64)** and generic Linux servers (AMD64), it uses a powerful **7-Zip** based engine to provide high-ratio compression and AES-256 encryption.

It implements a **"Single File Strategy"** to keep your cloud storage organized and uses **"Atomic Snapshots"** to minimize container downtime.

![Dashboard Screenshot](https://via.placeholder.com/800x400?text=Dashboard+Screenshot+Placeholder)

## 🚀 Features

*   **Atomic Snapshots:** Minimizes downtime by stopping the container only for the duration of a fast filesystem copy (`cp -rp`), then immediately restarting it before compression begins.
*   **7-Zip Powered Engine:** Uses **LZMA2** algorithm for superior compression and **AES-256** for military-grade encryption (including filename encryption).
*   **Single File Strategy:** Instead of cluttering your cloud with hundreds of files, it creates one consolidated **Master Archive** (`Backup_YYYYMMDD.7z`) per session.
*   **Smart Volume Detection:** Automatically identifies and backs up volumes and bind mounts of containers labeled with `backup.enable=true`.
*   **Cloud Sync:** Integrated **Rclone** support to sync encrypted backups to Google Drive, Dropbox, S3, or any other cloud provider.
*   **Upload & Delete:** Automatically deletes the local master archive after a successful cloud upload to save SD card space on Raspberry Pi.
*   **Multi-Language Support:** Fully localized UI in **English**, **Türkçe**, and **Deutsch**.
*   **Notifications:** Real-time status updates via **Gotify**.

## 🛠️ Installation

### Prerequisites

*   Docker & Docker Compose installed on your host.
*   An Rclone configuration file (`rclone.conf`) ready.

### ☁️ Creating rclone.conf (Recommended for Windows Users)

If you are running this on a headless server or Raspberry Pi, the easiest way to generate a valid `rclone.conf` is to use your local Windows machine:

1.  **Download Rclone for Windows:**
    Visit [rclone.org/downloads](https://rclone.org/downloads/) and download the Windows zip file. Extract it to a folder (e.g., `C:\rclone`).

2.  **Generate Config:**
    Open a command prompt (cmd) or PowerShell in that folder and run:
    ```powershell
    ./rclone.exe config
    ```
    Follow the interactive steps to set up your cloud provider (Google Drive, S3, Dropbox, etc.).

3.  **Locate the File:**
    Once finished, your config file is typically saved at:
    `C:\Users\YOUR_USERNAME\AppData\Roaming\rclone\rclone.conf`

4.  **Import to Docker Backup Guard:**
    *   Open the file with Notepad.
    *   Copy the entire content.
    *   Paste it into the **"Rclone Configuration Content"** box in the Docker Backup Guard Setup Wizard.
    *   Save your settings!

### Quick Start (Docker Compose)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/exoss/docker-backup-guard.git
    cd docker-backup-guard
    ```

2.  **Run with Docker Compose:**
    ```bash
    docker-compose up -d --build
    ```

3.  **Access the UI:**
    Open your browser and navigate to `http://localhost:8501`.

### Installation via Portainer Stacks

1.  Log in to Portainer and go to **Stacks**.
2.  Click **Add stack**.
3.  Name it `docker-backup-guard`.
4.  Paste the contents of `docker-compose.yml` into the Web Editor.
5.  **Important:** Since Portainer might not have access to local relative paths easily, use absolute paths for volumes.

    Example volume mapping:
    ```yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /path/to/your/backups:/backups
      - /path/to/your/rclone_config_dir:/app/rclone.conf # Maps a directory to store the config file
      - /var/lib/docker/volumes:/var/lib/docker/volumes:ro # Required for Smart Volume Detection
    ```
    > 🔧 **Technical Note:** The read-only bind mount `/var/lib/docker/volumes:/var/lib/docker/volumes:ro` is critical. It allows the backup engine to directly access and archive named Docker volumes from the host filesystem.

6.  Click **Deploy the stack**.

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
*   **Backup Password** (Crucial for 7-Zip encryption!).
*   **Retention Policy** (How many days to keep backups).
*   **Rclone Remote Name** (Must match your `rclone.conf`).
*   **Cloud Destination Path** (Folder on the cloud where backups will be stored).
*   **Timezone** (Default: Europe/Berlin).

### 3. Backup Process
*   **Full Backup:** Triggers the backup process for ALL enabled containers.
    1.  **Snapshot Phase:** For each container: Stop -> Fast Copy (`cp -rp`) -> Start.
    2.  **Compression Phase:** The snapshot folder is compressed into a single `Backup_XXX.7z` file using gentle settings (`-mx=3 -mmt=2`) to prevent system freeze.
    3.  **Upload Phase:** The master archive is synced to your defined Cloud Destination.
    4.  **Cleanup Phase:** The local master archive is deleted immediately after upload to save space.

*   **Single Container Backup:** Triggers the same process but only for the selected container.

## 🌍 Multi-Language Support
The application automatically detects your language preference during setup. You can choose between:
*   🇬🇧 English
*   🇹🇷 Türkçe
*   🇩🇪 Deutsch

## 🔒 Security Note
*   **Never share your `BACKUP_PASSWORD`.** It is used to encrypt the 7-Zip archive. Without it, your data is irretrievable.
*   Sensitive environment variables are stored in `.env` and are never exposed in the UI logs.

## 📜 License
This project is licensed under the MIT License.
