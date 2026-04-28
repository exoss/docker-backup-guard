# This module contains the backup and restore logic.
import json
import logging
import docker
import os
import time
import concurrent.futures
import shutil
import subprocess
import requests
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
import urllib3
import warnings
from app.api_handlers import APIHandler
from app.languages import get_text
from app.security import decrypt_value

# Module-level constants for performance optimizations (O(1) lookups and memory efficiency)
EXCLUDED_PATHS = frozenset([
    "/", "/proc", "/sys", "/dev", "/run", "/tmp",
    "/var/run", "/var/lib/docker", "/etc/localtime", "/etc/timezone",
    "/var/run/docker.sock"
])
TRANSITION_STATES = frozenset(['restarting', 'paused', 'dead'])

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
        if os.path.isdir(self.rclone_config):
            self.rclone_config = os.path.join(self.rclone_config, "rclone.conf")
        self.rclone_remote_name = os.getenv("RCLONE_REMOTE_NAME", "remote")
        self.rclone_destination = os.getenv("RCLONE_DESTINATION", "backups")
        
        # Decrypt sensitive fields
        self.backup_password = decrypt_value(os.getenv("BACKUP_PASSWORD"))
        self.healthcheck_url = os.getenv("HEALTHCHECK_URL")
        self.portainer_api_configured = bool(os.getenv("PORTAINER_URL") and os.getenv("PORTAINER_TOKEN"))

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

    def _get_rclone_target_path(self):
        destination = (self.rclone_destination or "").strip()
        destination = destination.lstrip("/")
        if destination:
            return f"{self.rclone_remote_name}:{destination}"
        return f"{self.rclone_remote_name}:"

    def _run_rclone(self, args, timeout=600):
        if not os.path.exists(self.rclone_config):
            self._log(f"Rclone configuration file not found: {self.rclone_config}", "WARNING")
            return None

        cmd = ["rclone", *args, "--config", self.rclone_config]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                err_msg = stderr if stderr else stdout
                self._log(f"Rclone Error: {err_msg}", "ERROR")
            return result
        except subprocess.TimeoutExpired:
            self._log(f"Rclone command timed out: {' '.join(cmd)}", "ERROR")
            return None
        except Exception as e:
            self._log(f"Exception during Rclone operation: {e}", "ERROR")
            return None

    def _log(self, message, level="INFO"):
        """Simple logging function wrapper around logging module"""
        lvl = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(lvl, message)
        # Also print to stdout if not handled by root logger (redundancy check, though root usually has StreamHandler)
        # print(f"[{level}] {message}") 

    def _send_healthcheck(self, status="success", message=""):
        """
        Sends a ping to the configured Healthcheck URL.
        Supports Healthchecks.io and Uptime Kuma (Push).
        """
        if not self.healthcheck_url:
            return

        url = self.healthcheck_url.strip().rstrip("/")
        final_url = url
        
        # --- Service Detection & URL Construction ---
        
        # 1. Healthchecks.io (hc-ping.com)
        if "hc-ping.com" in url:
            if status == "start":
                final_url = f"{url}/start"
            elif status == "failure":
                final_url = f"{url}/fail"
            # "success" uses base URL
            
            # Healthchecks.io allows POST body for logs
            if message:
                try:
                    self._log(f"Sending Healthcheck (POST) to {final_url}...")
                    requests.post(final_url, data=str(message).encode('utf-8'), timeout=10)
                    self._log("Healthcheck ping successful.")
                    return
                except Exception as e:
                    self._log(f"Healthcheck ping failed: {e}", "WARNING")
                    return

        # 2. Uptime Kuma (Push Monitor)
        elif "/api/push/" in url:
            # Uptime Kuma Push URL format: .../api/push/TOKEN?status=up&msg=OK&ping=
            try:
                parsed = urllib.parse.urlparse(url)
                query = urllib.parse.parse_qs(parsed.query)
                
                if status == "success":
                    query['status'] = ['up']
                    query['msg'] = ['Backup Successful']
                elif status == "failure":
                    query['status'] = ['down']
                    query['msg'] = [f'Backup Failed: {message}']
                elif status == "start":
                    # Optional: Uptime Kuma doesn't natively have "start" state like HC.io
                    # We can send a message but keep status=up, or just skip to avoid "flapping"
                    # Let's send a ping with "Backup Started" message
                    query['status'] = ['up']
                    query['msg'] = ['Backup Process Started']
                
                # Update query string
                new_query = urllib.parse.urlencode(query, doseq=True)
                final_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
                
            except Exception as e:
                self._log(f"Error parsing Uptime Kuma URL: {e}", "WARNING")
                # Fallback to original URL
                final_url = url

        # --- Generic Request (GET) ---
        try:
            self._log(f"Sending Healthcheck (GET) to {final_url}...")
            # Verify=False is often needed for self-hosted Uptime Kuma with self-signed certs
            # We enable it by default but could catch SSLError
            response = requests.get(final_url, timeout=10)
            
            if response.status_code == 200:
                self._log("Healthcheck ping successful.")
            else:
                self._log(f"Healthcheck ping returned status code: {response.status_code}", "WARNING")
        except requests.exceptions.SSLError:
             self._log("SSL Error on Healthcheck. Retrying with verify=False...", "WARNING")
             try:
                 with warnings.catch_warnings():
                     warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                     requests.get(final_url, timeout=10, verify=False)
                 self._log("Healthcheck ping successful (verify=False).")
             except Exception as e:
                 self._log(f"Healthcheck ping failed (verify=False): {e}", "WARNING")
        except Exception as e:
            self._log(f"Healthcheck ping failed: {e}", "WARNING")

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
        """Finds container volume and bind mount paths (on Host), excluding system paths."""
        mounts = []
        
        for mount in container.attrs['Mounts']:
            # Bind mounts and Volumes
            if mount['Type'] in ['bind', 'volume']:
                source = mount['Source']
                
                # --- EXCLUSION LOGIC ---
                # 1. Exact match exclusion
                if source in EXCLUDED_PATHS:
                    self._log(f"Skipping system path: {source} (Container: {container.name})", "WARNING")
                    continue
                    
                # 2. Subdirectory match for critical system paths (e.g. /proc/cpuinfo, /dev/mem)
                # Performance optimization: str.startswith accepts a tuple of strings natively,
                # which is evaluated in C and is significantly faster than any() with a generator.
                if source.startswith(("/proc/", "/sys/", "/dev/", "/run/")):
                    self._log(f"Skipping system sub-path: {source} (Container: {container.name})", "WARNING")
                    continue
                
                # 3. Special case: Root mount (/)
                # Dashdot/Glances often mount / as /hostfs. If source is /, we skip.
                if source == "/":
                    self._log(f"Skipping Root FS mount: {source} (Container: {container.name})", "WARNING")
                    continue
                # -----------------------

                resolved_path = self._resolve_host_path(source)
                mounts.append(resolved_path)
        return mounts

    def _is_portainer(self, container):
        """Checks if a container is Portainer based on image name."""
        try:
            # Prevent N+1 API calls by accessing image info from pre-loaded attributes
            # instead of using container.image, which triggers a lazy-loading API call.
            image_name = container.attrs.get('Config', {}).get('Image') or container.attrs.get('Image') or ""
            if "portainer/portainer" in image_name:
                return True
        except:
            pass
        # Fallback: check name
        if "portainer" in container.name.lower():
            return True
        return False

    def get_backup_candidates(self):
        """Finds containers to backup (backup.enable=true)"""
        if not self.client:
            return []
        
        candidates = []
        # Check if Portainer API is configured
        api_configured = self.portainer_api_configured

        # Performance optimization: use Docker API server-side filtering
        # instead of fetching all containers and filtering client-side.
        for container in self.client.containers.list(filters={"label": "backup.enable=true"}):
            # Check if it is Portainer
            if self._is_portainer(container):
                if api_configured:
                    self._log(f"Detected Portainer container: {container.name}. Skipping file-level backup in favor of API backup.", "INFO")
                    continue
                else:
                    self._log(f"Detected Portainer container: {container.name}, but API credentials missing. Falling back to Stop/Copy backup.", "WARNING")

            candidates.append(container)
        return candidates

    def _rclone_sync(self, source_file):
        """Syncs encrypted file to cloud via Rclone (using subprocess)."""
        target_path = self._get_rclone_target_path()
        self._log(f"Starting Rclone sync: {source_file} -> {target_path}")
        result = self._run_rclone(["copy", source_file, target_path], timeout=1800)
        if not result or result.returncode != 0:
            return False
        self._log("Rclone sync successful.")
        return True

    def _cleanup_remote_backups(self, retention_days):
        """Deletes remote backups older than retention_days using rclone."""
        try:
            retention_days = int(retention_days)
        except Exception:
            retention_days = 7

        if retention_days <= 0:
            self._log("Remote cleanup skipped (Retention is 0).")
            return True

        target_path = self._get_rclone_target_path()
        self._log(f"Running remote cleanup (Retention: {retention_days} days) on {target_path}...")

        delete_result = self._run_rclone(
            ["delete", target_path, "--min-age", f"{retention_days}d", "--include", "*.7z"],
            timeout=1800,
        )
        if not delete_result or delete_result.returncode != 0:
            return False

        self._run_rclone(["rmdirs", target_path, "--leave-root"], timeout=600)
        return True

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
            
            # 1. Download Backup into temp directory without modification
            backup_path = api.download_portainer_backup(temp_dir)
            if not backup_path:
                self._log("Failed to download Portainer backup.", "ERROR")
                return False
            # 2. No validation or renaming; push raw file into 7z
                
            # 3. Compress & Encrypt (7z)
            master_archive_name = f"Portainer_Backup_{timestamp}.7z"
            master_archive_path = os.path.join(self.backup_root, master_archive_name)
            
            self._log(f"Compressing and Encrypting to {master_archive_name}...")
            
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
            
            # 4. Upload via Rclone
            success = self._rclone_sync(master_archive_path)
            
            if success:
                self._log(f"Portainer Backup successful and uploaded: {master_archive_name}")
                retention_days = os.getenv("RETENTION_DAYS", "7")
                self._cleanup_remote_backups(retention_days)
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

    def _retry_operation(self, func, retries=3, delay=5, *args, **kwargs):
        """Retries a function call with delay."""
        last_exception = None
        for i in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self._log(f"Operation failed (Attempt {i+1}/{retries}): {e}. Retrying in {delay}s...", "WARNING")
                time.sleep(delay)
        raise last_exception

    def _process_group_backup(self, group_name, containers, backup_tree_root, progress_callback=None, lang="en"):
        """
        Stops all containers in the group, copies their volumes preserving structure, 
        and restarts them immediately. Includes retry logic for robustness.
        """
        msg = get_text(lang, "progress_processing_group").format(group=group_name, count=len(containers))
        self._log(msg)
        if progress_callback:
            progress_callback(msg)
        
        # 1. Collect Unique Volume Paths
        unique_paths = set()

        # Bulk fetch container states to avoid N+1 API calls during reload
        container_ids = [c.id for c in containers]
        fresh_containers = {}
        if container_ids:
            try:
                # We use client.containers.list to efficiently fetch all fresh container states at once
                # Performance optimization: Chunk container IDs to avoid Docker API URI length limits
                chunk_size = 30
                temp_containers = {}
                for i in range(0, len(container_ids), chunk_size):
                    chunk = container_ids[i:i + chunk_size]
                    chunk_containers = self.client.containers.list(all=True, filters={"id": chunk})
                    for c in chunk_containers:
                        temp_containers[c.id] = c
                fresh_containers = temp_containers
            except Exception as e:
                self._log(f"Error bulk fetching containers: {e}", "WARNING")

        for container in containers:
            try:
                # Use fresh state if available, otherwise fallback to original object
                fresh_c = fresh_containers.get(container.id, container)

                # If we couldn't get a fresh state from bulk list, fallback to individual reload
                if container.id not in fresh_containers:
                    fresh_c.reload()

                # Check if container is in a transition state (restarting, paused)
                if fresh_c.status in TRANSITION_STATES:
                     self._log(f"Container {fresh_c.name} is in '{fresh_c.status}' state. Waiting 10s...", "WARNING")
                     time.sleep(10)
                     fresh_c.reload()
                
                paths = self.get_container_volumes(fresh_c)
                unique_paths.update(paths)
            except Exception as e:
                 self._log(f"Error inspecting container {container.name}: {e}", "ERROR")
                 continue
            
        if not unique_paths:
            self._log(f"No volumes found for group {group_name}.", "WARNING")
            return

        # 2. Stop Phase
        stopped_containers = []
        try:
            self._log(f"Stopping group {group_name}...")
            if progress_callback:
                progress_callback(get_text(lang, "progress_stopping").format(group=group_name))
                
            if containers:
                def _stop_container(container):
                    try:
                        # Use retry logic for stopping
                        self._retry_operation(container.stop, retries=3, delay=5)
                        return container
                    except Exception as e:
                        self._log(f"Failed to stop {container.name} after retries: {e}", "WARNING")
                        # If we can't stop it, should we proceed?
                        # For data safety, maybe yes (snapshot might be fuzzy), but better to warn.
                        return None

                # Performance Optimization: Parallelize container stopping to reduce I/O wait time
                # as each stop operation can take up to 10s for graceful exits.
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(containers), 10)) as executor:
                    results = list(executor.map(_stop_container, containers))
                    stopped_containers = [c for c in results if c is not None]

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
                    if progress_callback:
                        progress_callback(get_text(lang, "progress_snapshot").format(path=relative_path))
                    
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
            if progress_callback:
                progress_callback(get_text(lang, "progress_error_group").format(group=group_name, error=e))
            
        finally:
            # 4. Start Phase
            self._log(f"Restarting group {group_name}...")
            if progress_callback:
                progress_callback(get_text(lang, "progress_restarting").format(group=group_name))
                
            if stopped_containers:
                def _start_container(container):
                    try:
                        # Use retry logic for starting
                        self._retry_operation(container.start, retries=3, delay=5)
                    except Exception as e:
                        self._log(f"Failed to start {container.name} after retries: {e}", "ERROR")

                # Performance Optimization: Parallelize container starting to reduce service downtime
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(stopped_containers), 10)) as executor:
                    list(executor.map(_start_container, stopped_containers))

    def perform_backup(self, container_id=None, progress_callback=None, lang="en"):
        """
        Executes the 'Stack-Aware' backup process.
        1. Groups containers by Docker Compose Project.
        2. Stops the entire stack -> Copies volumes (preserving structure) -> Starts stack.
        3. Compresses the entire file tree.
        4. Uploads to Cloud.
        """
        # 0. Send "Start" Signal to Healthcheck
        self._send_healthcheck("start")

        if not self.backup_password:
            self._log("ERROR: BACKUP_PASSWORD is not set!", "ERROR")
            if progress_callback:
                progress_callback(get_text(lang, "progress_password_error"))
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
                if progress_callback:
                    progress_callback(get_text(lang, "progress_no_containers"))
                return False

            self._log(f"Starting Backup for {len(candidates)} containers...")

        # Step 1.5: Portainer API Backup (Standalone)
        # Only run if full backup (no container_id) or if specifically requested?
        # Let's run it always as it's quick and useful context.
        if progress_callback:
            progress_callback(get_text(lang, "progress_backup_portainer"))
        
        if not self.perform_portainer_backup():
            msg = "Portainer Backup Failed! Check logs for details."
            self._log(msg, "ERROR")
            if progress_callback:
                progress_callback(f"⚠️ {msg}")
            # We don't abort the whole backup, but we notify.
            # return False # Uncomment if Portainer backup is critical for success


        # Step 2: Grouping & Snapshot
        groups = self._group_containers(candidates)
        self._log(f"Found {len(groups)} backup groups (Stacks/Standalone).")
        
        for group_name, containers in groups.items():
            self._process_group_backup(group_name, containers, backup_tree_root, progress_callback=progress_callback, lang=lang)

        # Step 3: Compression Phase (Heavy Lifting)
        try:
            master_archive_name = f"Backup_{timestamp}.7z"
            master_archive_path = os.path.join(self.backup_root, master_archive_name)
            
            # Check if temp dir has content
            if not os.listdir(backup_tree_root):
                self._log("No data found in staging directory. Aborting backup.", "ERROR")
                shutil.rmtree(temp_dir)
                if progress_callback:
                    progress_callback(get_text(lang, "progress_no_data"))
                return False

            self._log("Compressing Backup Archive (Gentle Mode: -mx=3)...")
            if progress_callback:
                progress_callback(get_text(lang, "progress_compressing"))
            
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
                
                # Send Gotify Notification (Failure)
                APIHandler().send_gotify_notification(
                    get_text(lang, "notif_full_error_title"), 
                    get_text(lang, "notif_full_error_msg"), 
                    priority=8
                )
                
                if progress_callback:
                    progress_callback(get_text(lang, "progress_compression_failed").format(error=result_master.stderr))
                return False
            
            self._log(f"Backup Archive created: {master_archive_path}")
            
            # Update State File (Success)
            archive_size = os.path.getsize(master_archive_path)
            self._update_state_file("success", archive_size, len(candidates))

            # Step 4: Cloud Sync
            if progress_callback:
                progress_callback(get_text(lang, "progress_uploading"))
            success = self._rclone_sync(master_archive_path)
            
            if success:
                # Immediate cleanup for successful upload
                self._log(f"Cloud sync successful. Deleting local archive: {master_archive_name}")
                if progress_callback:
                    progress_callback(get_text(lang, "progress_upload_success"))
                
                # Send Healthcheck Ping
                self._send_healthcheck("success")
                
                # Send Gotify Notification
                APIHandler().send_gotify_notification(
                    get_text(lang, "notif_full_success_title"), 
                    get_text(lang, "notif_full_success_msg")
                )
                
                try:
                    os.remove(master_archive_path)
                except OSError as e:
                    self._log(f"Error deleting local archive: {e}", "WARNING")
            else:
                if progress_callback:
                    progress_callback(get_text(lang, "progress_upload_failed"))
            
            return success
            
        finally:
            # Step 5: Cleanup Staging
            if os.path.exists(temp_dir):
                self._log("Cleaning up staging directory...")
                shutil.rmtree(temp_dir)
            
            retention_days = int(os.getenv("RETENTION_DAYS", "7"))
            self._cleanup_local_backups(retention_days)
            self._cleanup_remote_backups(retention_days)

    def _cleanup_local_backups(self, retention_days):
        """Deletes local backups older than retention_days"""
        self._log(f"Running cleanup (Retention: {retention_days} days)...")
        now = time.time()
        cutoff = now - (retention_days * 86400)
        
        # Performance optimization: use os.scandir() instead of os.listdir() to avoid extra stat() calls
        with os.scandir(self.backup_root) as it:
            for entry in it:
                if entry.is_file() and entry.name.endswith(".7z"):
                    if entry.stat().st_mtime < cutoff:
                        self._log(f"Deleting old backup: {entry.name}")
                        os.remove(entry.path)

if __name__ == "__main__":
    engine = BackupEngine()
    engine.perform_backup()
