# This module contains the backup and restore logic.
import docker
import os
import time
import shutil
import subprocess
from datetime import datetime
from dotenv import load_dotenv

class BackupEngine:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Docker connection error: {e}")
            self.client = None
        
        self.backup_root = "/backups"
        os.makedirs(self.backup_root, exist_ok=True)
        
        # Load env
        env_path = ".env/config.env" if os.path.isdir(".env") else ".env"
        load_dotenv(dotenv_path=env_path)
        
        self.rclone_config = os.getenv("RCLONE_CONFIG_PATH", "/app/rclone.conf")
        self.rclone_remote_name = os.getenv("RCLONE_REMOTE_NAME", "remote")
        self.rclone_destination = os.getenv("RCLONE_DESTINATION", "backups")
        self.backup_password = os.getenv("BACKUP_PASSWORD")

    def _log(self, message, level="INFO"):
        """Simple logging function"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        # Gotify integration can be added here in the future

    def _resolve_host_path(self, host_path):
        """
        Resolves a host path to the container's mount point.
        If the path starts with /var/lib/docker/volumes, it assumes it's a named volume 
        and is already mounted at the same path.
        Otherwise, it prepends /hostfs to access the host filesystem.
        """
        if host_path.startswith("/var/lib/docker/volumes"):
            return host_path
        
        # Remove leading slash to join correctly
        clean_path = host_path.lstrip("/")
        return os.path.join("/hostfs", clean_path)

    def get_container_volumes(self, container):
        """Finds container volume and bind mount paths (on Host)"""
        mounts = []
        for mount in container.attrs['Mounts']:
            # Bind mounts and Volumes
            if mount['Type'] in ['bind', 'volume']:
                source = mount['Source']
                # Exclude docker socket or system directories if necessary
                if source == "/var/run/docker.sock":
                    continue
                    
                resolved_path = self._resolve_host_path(source)
                mounts.append(resolved_path)
        return mounts

    def get_backup_candidates(self):
        """Finds containers to backup (backup.enable=true)"""
        if not self.client:
            return []
        
        candidates = []
        for container in self.client.containers.list():
            labels = container.labels
            if labels.get("backup.enable") == "true":
                candidates.append(container)
        return candidates

    def _rclone_sync(self, source_file):
        """Syncs encrypted file to cloud via Rclone (using subprocess)."""
        if not os.path.exists(self.rclone_config):
            self._log(f"Rclone configuration file not found: {self.rclone_config}", "WARNING")
            return False

        try:
            # Use the configured remote name and destination
            target_path = f"{self.rclone_remote_name}:{self.rclone_destination}"
            
            self._log(f"Starting Rclone sync: {source_file} -> {target_path}")
            
            # Using direct subprocess command instead of rclone-python wrapper
            # to avoid 'flags' keyword argument errors and improve stability.
            cmd = [
                "rclone", "copy",
                source_file,
                target_path,
                "--config", self.rclone_config
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self._log(f"Rclone Error: {result.stderr}", "ERROR")
                return False
            
            self._log("Rclone sync successful.")
            return True
            
        except Exception as e:
            self._log(f"Exception during Rclone operation: {e}", "ERROR")
            return False

    def perform_backup(self, container_id=None):
        """
        Executes the 'Single File Strategy' backup process using Snapshot logic.
        Refactored to match 'ornek.sh' performance:
        1. Snapshot Phase: Stop -> Copy (cp -rp) -> Start for each container (Fast, Minimal Downtime).
        2. Compression Phase: Compress the entire snapshot folder with gentle settings (-mx=3 -mmt=2) to prevent freezing.
        3. Upload & Cleanup.
        """
        if not self.backup_password:
            self._log("ERROR: BACKUP_PASSWORD is not set!", "ERROR")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join(self.backup_root, f"temp_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)
        
        candidates = self.get_backup_candidates()
        
        # Filter if specific container requested
        if container_id:
            candidates = [c for c in candidates if c.id == container_id or c.short_id == container_id]
            
        if not candidates:
            self._log("No containers found for backup.", "WARNING")
            shutil.rmtree(temp_dir)
            return False

        self._log(f"Starting Backup for {len(candidates)} containers...")

        # Step 2: Snapshot Phase (Stop -> Copy -> Start)
        for container in candidates:
            try:
                container_name = container.name
                self._log(f"Processing container: {container_name}")
                
                source_paths = self.get_container_volumes(container)
                if not source_paths:
                    self._log(f"No volumes found for {container_name}, skipping.", "WARNING")
                    continue

                # Prepare container-specific staging dir
                container_stage_dir = os.path.join(temp_dir, container_name)
                os.makedirs(container_stage_dir, exist_ok=True)

                # Stop Container
                self._log(f"Stopping {container_name}...")
                container.stop()
                
                try:
                    # Copy Volumes (Fast I/O copy)
                    for i, src in enumerate(source_paths):
                        # Destination: temp_dir/container_name/vol_X_basename
                        # We use index to avoid name collisions if multiple volumes have same basename
                        basename = os.path.basename(src.rstrip("/"))
                        dest = os.path.join(container_stage_dir, f"{i}_{basename}")
                        
                        # Use subprocess cp -rp for preservation and speed
                        # cp -rp /hostfs/path /backups/temp_.../container/0_data
                        cmd_cp = ["cp", "-rp", src, dest]
                        self._log(f"Snapshotting {src} -> {dest}")
                        subprocess.run(cmd_cp, check=True)
                        
                except subprocess.CalledProcessError as e:
                    self._log(f"Snapshot Error for {container_name}: {e}", "ERROR")
                except Exception as e:
                    self._log(f"Error creating snapshot for {container_name}: {e}", "ERROR")
                        
                finally:
                    # Start Container immediately
                    self._log(f"Starting {container_name}...")
                    container.start()
            
            except Exception as e:
                self._log(f"Error processing container {container.name}: {e}", "ERROR")

        # Step 3: Compression Phase (Heavy Lifting)
        # Services are UP, now we compress the staging folder
        try:
            master_archive_name = f"Backup_{timestamp}.7z"
            master_archive_path = os.path.join(self.backup_root, master_archive_name)
            
            # Check if temp dir has content
            if not os.listdir(temp_dir):
                self._log("No data found in staging directory. Aborting backup.", "ERROR")
                shutil.rmtree(temp_dir)
                return False

            self._log("Compressing Backup Archive (Gentle Mode: -mx=3)...")
            
            # 7-Zip Command aligned with ornek.sh for Raspberry Pi stability
            # -mx=3: Fast compression (low CPU/RAM)
            # -mmt=2: Limit to 2 threads to prevent freeze
            # -mhe=on: Encrypt filenames
            cmd_master = [
                "7z", "a", "-t7z",
                "-mx=3", "-mmt=2",
                "-mhe=on",
                f"-p{self.backup_password}",
                master_archive_path,
                "."
            ]
            
            result_master = subprocess.run(cmd_master, cwd=temp_dir, capture_output=True, text=True)
            
            if result_master.returncode != 0:
                self._log(f"Compression Error: {result_master.stderr}", "ERROR")
                return False
            
            self._log(f"Backup Archive created: {master_archive_path}")
            
            # Step 4: Cloud Sync
            success = self._rclone_sync(master_archive_path)
            
            if success:
                # Immediate cleanup for successful upload (Upload & Delete)
                self._log(f"Cloud sync successful. Deleting local archive: {master_archive_name}")
                try:
                    os.remove(master_archive_path)
                except OSError as e:
                    self._log(f"Error deleting local archive: {e}", "WARNING")
            
            return success

        finally:
            # Step 5: Cleanup Staging
            if os.path.exists(temp_dir):
                self._log("Cleaning up staging directory...")
                shutil.rmtree(temp_dir)
            
            retention_days = int(os.getenv("RETENTION_DAYS", "7"))
            self._cleanup_local_backups(retention_days)

    def _cleanup_local_backups(self, retention_days):
        """Deletes local backups older than retention_days"""
        self._log(f"Running cleanup (Retention: {retention_days} days)...")
        now = time.time()
        cutoff = now - (retention_days * 86400)
        
        for filename in os.listdir(self.backup_root):
            file_path = os.path.join(self.backup_root, filename)
            if os.path.isfile(file_path) and filename.endswith(".7z"):
                if os.path.getmtime(file_path) < cutoff:
                    self._log(f"Deleting old backup: {filename}")
                    os.remove(file_path)

if __name__ == "__main__":
    engine = BackupEngine()
    engine.perform_backup()
