# This module contains the backup and restore logic.
import json
import logging
import docker
import os
import time
import shutil
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from app.api_handlers import APIHandler

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

        # Setup Logging
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure root logger if not already configured with a file handler
        root_logger = logging.getLogger()
        if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
            fh = logging.FileHandler(os.path.join(log_dir, "app.log"))
            fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            root_logger.addHandler(fh)
            # Ensure level is at least INFO
            root_logger.setLevel(logging.INFO)
            
        self.logger = logging.getLogger("BackupEngine")

    def _log(self, message, level="INFO"):
        """Simple logging function wrapper around logging module"""
        lvl = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(lvl, message)
        # Also print to stdout if not handled by root logger (redundancy check, though root usually has StreamHandler)
        # print(f"[{level}] {message}") 

    def _update_state_file(self, status, size_bytes=0, protected_count=0):
        """Updates the JSON state file with KPI data."""
        state_path = os.path.join(self.backup_root, "backup_state.json")
        data = {}
        
        # Read existing data to preserve history (e.g. last success)
        if os.path.exists(state_path):
            try:
                with open(state_path, "r") as f:
                    data = json.load(f)
            except Exception:
                pass # Start fresh if corrupt

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data["last_attempt"] = now
        data["last_status"] = status
        data["protected_containers"] = protected_count
        
        if status == "success":
            data["last_success"] = now
            data["last_size_bytes"] = size_bytes
            
        try:
            with open(state_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self._log(f"Failed to update state file: {e}", "WARNING")

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

    def perform_portainer_backup(self):
        """
        Executes a standalone backup for Portainer Configuration via API.
        Downloads tar.gz, encrypts to 7z, and uploads via Rclone.
        """
        if not self.backup_password:
            self._log("ERROR: BACKUP_PASSWORD is not set!", "ERROR")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join(self.backup_root, f"temp_portainer_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            api = APIHandler()
            if not (api.portainer_url and api.portainer_token):
                self._log("Portainer credentials missing or incomplete.", "ERROR")
                return False

            self._log("Starting Standalone Portainer Backup...")
            
            # 1. Download Backup
            backup_name = f"portainer_backup_{timestamp}.tar.gz"
            backup_path = os.path.join(temp_dir, backup_name)
            
            if not api.download_portainer_backup(backup_path, password=self.backup_password):
                self._log("Failed to download Portainer backup.", "ERROR")
                return False
                
            # 2. Compress & Encrypt (7z)
            master_archive_name = f"Portainer_Backup_{timestamp}.7z"
            master_archive_path = os.path.join(self.backup_root, master_archive_name)
            
            self._log(f"Compressing and Encrypting to {master_archive_name}...")
            
            # Using 7z to wrap the tar.gz into an encrypted 7z archive
            cmd = [
                "7z", "a", "-t7z",
                "-mx=3", "-mhe=on",
                f"-p{self.backup_password}",
                master_archive_path,
                backup_path 
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self._log(f"Compression Error: {result.stderr}", "ERROR")
                return False
            
            # 3. Upload via Rclone
            success = self._rclone_sync(master_archive_path)
            
            if success:
                self._log(f"Portainer Backup successful and uploaded: {master_archive_name}")
                # Cleanup local archive
                try:
                    os.remove(master_archive_path)
                except:
                    pass
                return True
            else:
                self._log("Portainer Backup upload failed.", "ERROR")
                return False

        except Exception as e:
            self._log(f"Exception during Portainer Backup: {e}", "ERROR")
            return False
            
        finally:
            # Cleanup temp dir
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def _group_containers(self, candidates):
        """Groups containers by Docker Compose Project."""
        groups = {}
        for container in candidates:
            # Check for com.docker.compose.project label
            project = container.labels.get("com.docker.compose.project")
            if project:
                if project not in groups:
                    groups[project] = []
                groups[project].append(container)
            else:
                # Standalone containers get their own group
                groups[container.name] = [container]
        return groups

    def _process_group_backup(self, group_name, containers, backup_tree_root):
        """
        Stops all containers in the group, copies their volumes preserving structure, 
        and restarts them immediately.
        """
        self._log(f"Processing Group: {group_name} ({len(containers)} containers)")
        
        # 1. Collect Unique Volume Paths
        unique_paths = set()
        for container in containers:
            paths = self.get_container_volumes(container)
            unique_paths.update(paths)
            
        if not unique_paths:
            self._log(f"No volumes found for group {group_name}.", "WARNING")
            return

        # 2. Stop Phase
        stopped_containers = []
        try:
            self._log(f"Stopping group {group_name}...")
            for container in containers:
                try:
                    container.stop()
                    stopped_containers.append(container)
                except Exception as e:
                    self._log(f"Failed to stop {container.name}: {e}", "WARNING")

            # 3. Copy Phase (Snapshot)
            for src in unique_paths:
                try:
                    # Remove /hostfs prefix to build destination path
                    # src: /hostfs/opt/npm/data -> relative: opt/npm/data
                    if src.startswith("/hostfs"):
                        relative_path = src[len("/hostfs"):].lstrip("/")
                    else:
                        # Handle named volumes or other paths
                        relative_path = src.lstrip("/")
                    
                    dest = os.path.join(backup_tree_root, relative_path)
                    dest_parent = os.path.dirname(dest)
                    
                    if not os.path.exists(dest_parent):
                        os.makedirs(dest_parent, exist_ok=True)
                    
                    self._log(f"Snapshotting: {src} -> {dest}")
                    
                    # Check if src is directory
                    if os.path.isdir(src):
                        # cp -rp src dest
                        # If dest does not exist, it creates dest as copy of src
                        cmd = ["cp", "-rp", src, dest]
                        subprocess.run(cmd, check=True, timeout=300) # 5 min timeout per volume
                    else:
                        # File bind mount
                        cmd = ["cp", "-p", src, dest]
                        subprocess.run(cmd, check=True, timeout=60)

                except subprocess.TimeoutExpired:
                     self._log(f"Timeout while copying {src}", "ERROR")
                except Exception as e:
                    self._log(f"Error copying {src}: {e}", "ERROR")

        except Exception as e:
            self._log(f"Error processing group {group_name}: {e}", "ERROR")
            
        finally:
            # 4. Start Phase
            self._log(f"Restarting group {group_name}...")
            for container in stopped_containers:
                try:
                    container.start()
                except Exception as e:
                    self._log(f"Failed to start {container.name}: {e}", "ERROR")

    def perform_backup(self, container_id=None):
        """
        Executes the 'Stack-Aware' backup process.
        1. Groups containers by Docker Compose Project.
        2. Stops the entire stack -> Copies volumes (preserving structure) -> Starts stack.
        3. Compresses the entire file tree.
        4. Uploads to Cloud.
        """
        if not self.backup_password:
            self._log("ERROR: BACKUP_PASSWORD is not set!", "ERROR")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join(self.backup_root, f"temp_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create a root for the file tree inside temp_dir
        # We use 'hostfs' to indicate these are files from the host
        backup_tree_root = os.path.join(temp_dir, "hostfs")
        os.makedirs(backup_tree_root, exist_ok=True)
        
        candidates = self.get_backup_candidates()
        
        # Filter if specific container requested
        if container_id:
            candidates = [c for c in candidates if c.id == container_id or c.short_id == container_id]
            
            if not candidates:
                self._log("No containers found for backup.", "WARNING")
                shutil.rmtree(temp_dir)
                self._update_state_file("skipped", 0, 0)
                return False

            self._log(f"Starting Backup for {len(candidates)} containers...")

        # Step 1.5: Portainer API Backup (Standalone)
        # Only run if full backup (no container_id) or if specifically requested?
        # Let's run it always as it's quick and useful context.
        self.perform_portainer_backup()

        # Step 2: Grouping & Snapshot
        groups = self._group_containers(candidates)
        self._log(f"Found {len(groups)} backup groups (Stacks/Standalone).")
        
        for group_name, containers in groups.items():
            self._process_group_backup(group_name, containers, backup_tree_root)

        # Step 3: Compression Phase (Heavy Lifting)
        try:
            master_archive_name = f"Backup_{timestamp}.7z"
            master_archive_path = os.path.join(self.backup_root, master_archive_name)
            
            # Check if temp dir has content
            if not os.listdir(backup_tree_root):
                self._log("No data found in staging directory. Aborting backup.", "ERROR")
                shutil.rmtree(temp_dir)
                return False

            self._log("Compressing Backup Archive (Gentle Mode: -mx=3)...")
            
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
                self._update_state_file("failed", 0, len(candidates))
                return False
            
            self._log(f"Backup Archive created: {master_archive_path}")
            
            # Update State File (Success)
            archive_size = os.path.getsize(master_archive_path)
            self._update_state_file("success", archive_size, len(candidates))

            # Step 4: Cloud Sync
            success = self._rclone_sync(master_archive_path)
            
            if success:
                # Immediate cleanup for successful upload
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
