# 🔄 Restore Wizard — Teknik Tasarım Dokümanı

> **Versiyon:** 1.0 | **Hedef sürüm:** v2.0.0 | **Durum:** Tasarım aşaması
>
> Bu doküman Restore Wizard özelliğinin çalışma prensibini, mimarisini ve kullanıcı akışını tanımlar.

---

## 1. Problem Tanımı

### Mevcut durum (manuel restore)

Şu an bir backup'tan geri yüklemek için gereken adımlar:

```bash
# 1. Backup'ı bul
ls /backups/
# Backup_20250625_030000.7z

# 2. Elle aç
mkdir /tmp/restore && cd /tmp/restore
7z x /backups/Backup_20250625_030000.7z -pŞİFRE

# 3. İçeriği anlamaya çalış
tree hostfs/
# hostfs/var/lib/docker/volumes/db_data/_data/...
# hostfs/opt/npm/nginx/...
# Bu hangi container'a aitti?

# 4. Container'ları durdur
docker stop wordpress_db wordpress_app

# 5. Dosyaları elle kopyala
cp -rp hostfs/opt/npm/nginx/* /hostfs/opt/npm/nginx/
cp -rp hostfs/var/lib/docker/volumes/db_data/_data/* /var/lib/docker/volumes/db_data/_data/

# 6. Container'ları başlat
docker start wordpress_db wordpress_app

# 7. Dua et 🤞
```

**Sorunlar:**
- Hangi dosyanın hangi container'a ait olduğunu bilmek zor
- Yanlış yere kopyalama riski
- Container'ları hangi sırayla durdurup başlatacağını bilmek gerek
- Hiçbir önizleme, doğrulama veya geri alma mekanizması yok
- Felaket anında panikle hata yapma olasılığı çok yüksek

### Hedef

Restore işlemini **3 tık**ta, **güvenli** ve **öngörülebilir** hale getirmek.

---

## 2. Temel Prensip

Backup sırasında oluşan **path mapping**'i tersten çalıştırmak:

```
┌─────────────────────────────────────────────────────────────┐
│                       BACKUP AKIŞI                          │
│                                                             │
│  Docker mount Source        _resolve_host_path()            │
│  ──────────────────  ────▶  ──────────────────             │
│  /var/lib/docker/           /var/lib/docker/                │
│    volumes/db_data/_data  →   volumes/db_data/_data         │
│  (named volume - direkt)                                    │
│                                                             │
│  /opt/npm/nginx           → /hostfs/opt/npm/nginx           │
│  (bind mount - /hostfs ile)                                 │
│                         │                                   │
│                         ▼                                   │
│                   Archive içi:                              │
│                   hostfs/var/lib/docker/volumes/...         │
│                   hostfs/opt/npm/nginx/...                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      RESTORE AKIŞI                          │
│                                                             │
│  Archive içi path          _map_archive_to_host()           │
│  ──────────────────  ────▶  ──────────────────             │
│  hostfs/var/lib/docker/    /var/lib/docker/                 │
│    volumes/db_data/_data →   volumes/db_data/_data          │
│  (named volume - direkt)                                    │
│                                                             │
│  hostfs/opt/npm/nginx/    → /hostfs/opt/npm/nginx/          │
│  (bind mount - /hostfs ile)                                 │
│                         │                                   │
│                         ▼                                   │
│                   Gerçek host path'leri:                    │
│                   /var/lib/docker/volumes/...               │
│                   /hostfs/opt/npm/nginx/...                 │
└─────────────────────────────────────────────────────────────┘
```

### Kritik içgörü

Backup **alırken** bir `restore_map.json` oluşturursak, restore **ederken** container'lar silinmiş/taşınmış olsa bile nereye kopyalanacağını biliriz.

---

## 3. Veri Yapısı: `restore_map.json`

Her backup archive'inin içine gömülen bu dosya restore işleminin belkemiğidir.

```json
{
  "version": 1,
  "created_at": "2025-06-25T03:00:00+02:00",
  "hostname": "my-homeserver",
  "backup_type": "full",
  "containers": {
    "wordpress_db": {
      "compose_project": "wordpress",
      "image": "mariadb:10",
      "volumes": {
        "hostfs/var/lib/docker/volumes/db_data/_data": {
          "type": "volume",
          "source": "/var/lib/docker/volumes/db_data/_data",
          "target": "/var/lib/mysql",
          "size_bytes": 1288490188,
          "file_count": 15432
        }
      }
    },
    "wordpress_app": {
      "compose_project": "wordpress",
      "image": "wordpress:latest",
      "volumes": {
        "hostfs/var/lib/docker/volumes/wp_content/_data": {
          "type": "volume",
          "source": "/var/lib/docker/volumes/wp_content/_data",
          "target": "/var/www/html/wp-content",
          "size_bytes": 933232640,
          "file_count": 8201
        },
        "hostfs/opt/npm/nginx": {
          "type": "bind",
          "source": "/opt/npm/nginx",
          "target": "/etc/nginx/conf.d",
          "size_bytes": 12288,
          "file_count": 1
        }
      }
    }
  },
  "stacks": {
    "wordpress": {
      "containers": ["wordpress_db", "wordpress_app"],
      "stop_order": ["wordpress_app", "wordpress_db"],
      "start_order": ["wordpress_db", "wordpress_app"]
    }
  }
}
```

### Nasıl oluşturulur

```python
# engine.py — perform_backup() içinde, backup başarılı olduktan sonra:

def generate_restore_map(self, groups, backup_tree_root):
    """
    Backup sırasında çağrılır.
    Her container-volume-target eşleşmesini kaydeder.
    """
    restore_map = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "hostname": socket.gethostname(),
        "backup_type": "full",
        "containers": {},
        "stacks": {}
    }

    for group_name, containers in groups.items():
        # Stack bilgisi
        container_names = [c.name for c in containers]
        restore_map["stacks"][group_name] = {
            "containers": container_names,
            "stop_order": list(reversed(container_names)),
            "start_order": container_names
        }

        for container in containers:
            volumes_info = {}
            for mount in container.attrs.get("Mounts", []):
                if mount["Type"] not in ("bind", "volume"):
                    continue

                source = mount["Source"]
                resolved = self._resolve_host_path(source)

                # Archive içindeki path'i hesapla
                if resolved.startswith("/hostfs"):
                    archive_path = "hostfs" + resolved[7:]
                else:
                    archive_path = "hostfs" + resolved

                volumes_info[archive_path] = {
                    "type": mount["Type"],
                    "source": source,
                    "target": mount.get("Destination", ""),
                    "resolved_host_path": resolved
                }

            restore_map["containers"][container.name] = {
                "compose_project": container.labels.get("com.docker.compose.project"),
                "image": container.attrs.get("Config", {}).get("Image", ""),
                "volumes": volumes_info
            }

    return restore_map

# Archive içine ekle:
# 7z a backup.7z restore_map.json
```

---

## 4. RestoreEngine Sınıfı

```python
# app/restore_engine.py (yeni dosya)

import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
import docker
from app.languages import get_text


class RestoreEngine:
    """Backup archive'lerinden container volume'lerini geri yükler."""

    def __init__(self):
        self.client = docker.from_env()
        self.backup_root = "/backups"
        self.temp_root = os.path.join(self.backup_root, "restore_temp")

    # ──────────────────────────────────────────────────────
    # 1. KEŞİF — Hangi backup'lar var?
    # ──────────────────────────────────────────────────────

    def list_local_backups(self):
        """Local /backups dizinindeki .7z dosyalarını listeler."""
        backups = []
        if not os.path.isdir(self.backup_root):
            return backups

        with os.scandir(self.backup_root) as it:
            for entry in it:
                if entry.is_file() and entry.name.endswith(".7z"):
                    stat = entry.stat()
                    backups.append({
                        "name": entry.name,
                        "path": entry.path,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "location": "local"
                    })
        return sorted(backups, key=lambda b: b["modified"], reverse=True)

    def list_cloud_backups(self, rclone_config, remote_name, destination):
        """Rclone remote üzerindeki .7z backup'larını listeler."""
        target = f"{remote_name}:{destination}"
        cmd = [
            "rclone", "lsjson",
            "--config", rclone_config,
            "--files-only",
            "--include", "*.7z",
            target
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return []

        backups = []
        for item in json.loads(result.stdout):
            backups.append({
                "name": item["Name"],
                "path": f"{target}/{item['Name']}",
                "size_bytes": item["Size"],
                "modified": item["ModTime"],
                "location": "cloud"
            })
        return sorted(backups, key=lambda b: b["modified"], reverse=True)

    # ──────────────────────────────────────────────────────
    # 2. METADATA — Backup'ın içinde ne var?
    # ──────────────────────────────────────────────────────

    def read_restore_map(self, archive_path, password):
        """
        Archive içindeki restore_map.json'ı okur.
        Eğer restore_map yoksa (eski backup), archive içeriğini manuel analiz eder.
        """
        cmd = [
            "7z", "l", "-slt",
            f"-p{password}",
            archive_path,
            "restore_map.json"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if "restore_map.json" in result.stdout:
            # restore_map var → extract et ve parse et
            extract_cmd = [
                "7z", "x", "-y",
                f"-p{password}",
                archive_path,
                "restore_map.json",
                f"-o{self.temp_root}"
            ]
            subprocess.run(extract_cmd, capture_output=True, check=True)

            map_path = os.path.join(self.temp_root, "restore_map.json")
            with open(map_path) as f:
                restore_map = json.load(f)
            os.remove(map_path)
            return restore_map
        else:
            # Eski backup → manuel analiz
            return self._analyze_archive_structure(archive_path, password)

    def _analyze_archive_structure(self, archive_path, password):
        """
        Eski tip backup'lar için: archive içindeki hostfs/ dizin yapısından
        container-volume eşleşmesini çıkarmaya çalışır.
        """
        cmd = ["7z", "l", "-slt", f"-p{password}", archive_path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        # hostfs/ altındaki her benzersiz üst dizini bir volume olarak kabul et
        paths = set()
        for line in result.stdout.split("\n"):
            if line.startswith("Path = hostfs/"):
                p = line[7:]  # "hostfs/" prefix'ini kaldır
                # 3. seviyeye kadar grupla
                parts = p.split("/")
                if len(parts) >= 3:
                    paths.add("/".join(parts[:3]))

        return {
            "version": 0,
            "legacy": True,
            "volumes": sorted(paths),
            "note": "Bu backup eski formatta. Manuel eşleştirme gerekebilir."
        }

    # ──────────────────────────────────────────────────────
    # 3. ÖNİZLEME — Ne olacak?
    # ──────────────────────────────────────────────────────

    def preview_restore(self, archive_path, password, selections=None):
        """
        Dry-run: Hangi dosyalar nereye kopyalanacak?
        Çakışma var mı? Ne kadar yer lazım?

        Dönüş:
        {
            "total_files": 23634,
            "total_size_bytes": 2317235708,
            "conflicts": [
                {
                    "path": "wp_content/_data/plugins/akismet/index.php",
                    "archive_mtime": "2025-06-25T02:58:00",
                    "destination_mtime": "2025-06-26T10:00:00",
                    "archive_size": 5120,
                    "destination_size": 5120,
                    "recommendation": "skip"  // "skip" | "overwrite" | "review"
                }
            ],
            "missing_destinations": [...],
            "estimated_duration_seconds": 180
        }
        """
        restore_map = self.read_restore_map(archive_path, password)
        preview = {
            "archive_name": os.path.basename(archive_path),
            "containers": {},
            "total_files": 0,
            "total_size_bytes": 0,
            "conflicts": [],
            "missing_destinations": [],
            "estimated_duration_seconds": 0
        }

        for container_name, info in restore_map.get("containers", {}).items():
            if selections and container_name not in selections.get("containers", []):
                continue

            container_preview = {"volumes": {}, "status": "ok"}
            for archive_rel_path, vol_info in info.get("volumes", {}).items():
                dest = self._map_archive_to_host(archive_rel_path)
                if not os.path.exists(dest):
                    container_preview["volumes"][archive_rel_path] = {
                        "destination": dest,
                        "status": "missing_destination",
                        "files": vol_info.get("file_count", "?"),
                        "size": vol_info.get("size_bytes", "?")
                    }
                    preview["missing_destinations"].append(dest)
                    container_preview["status"] = "warning"
                    continue

                # Çakışma analizi — archive'teki dosyalar hedefte var mı?
                # Bu kısım archive'i kısmen extract edip rsync --dry-run ile yapılır
                conflicts = self._detect_conflicts(archive_path, password, archive_rel_path, dest)
                preview["conflicts"].extend(conflicts)

                container_preview["volumes"][archive_rel_path] = {
                    "destination": dest,
                    "status": "conflict" if conflicts else "ok",
                    "conflict_count": len(conflicts),
                    "files": vol_info.get("file_count", "?"),
                    "size": vol_info.get("size_bytes", "?")
                }
                preview["total_files"] += vol_info.get("file_count", 0)
                preview["total_size_bytes"] += vol_info.get("size_bytes", 0)

            preview["containers"][container_name] = container_preview

        # Süre tahmini: ~1 GB/dk baz al
        preview["estimated_duration_seconds"] = max(
            30, int(preview["total_size_bytes"] / (1024**3) * 60)
        )

        return preview

    # ──────────────────────────────────────────────────────
    # 4. GERİ YÜKLEME — Asıl işlem
    # ──────────────────────────────────────────────────────

    def execute_restore(self, archive_path, password, selections=None,
                        conflict_policy="newer", dry_run=False,
                        progress_callback=None):
        """
        Ana restore akışı.

        Parametreler:
        - archive_path: .7z dosyasının yolu
        - password: 7z şifresi
        - selections: {
            "containers": ["wordpress_db", "wordpress_app"],  # None = hepsi
            "volumes": {"wordpress_db": ["db_data"]}         # None = hepsi
          }
        - conflict_policy: "skip" | "newer" | "overwrite"
        - dry_run: True ise sadece simüle et
        - progress_callback: callable(msg, step, total_steps)
        """
        restore_map = self.read_restore_map(archive_path, password)
        temp_dir = os.path.join(self.temp_root, f"restore_{int(time.time())}")
        os.makedirs(temp_dir, exist_ok=True)

        report = {
            "started_at": datetime.now().isoformat(),
            "archive": os.path.basename(archive_path),
            "status": "running",
            "steps": [],
            "errors": [],
            "restored_files": 0,
            "restored_bytes": 0,
            "skipped_files": 0,
            "containers_stopped": [],
            "containers_started": []
        }

        try:
            # ── Adım 1: Extract ──────────────────────────
            self._report(progress_callback, "Extracting archive...", 1, 5)
            extract_cmd = [
                "7z", "x", "-y",
                f"-p{password}",
                f"-o{temp_dir}",
                archive_path
            ]
            result = subprocess.run(extract_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Extract failed: {result.stderr}")

            # ── Adım 2: Container'ları eşle ve durdur ─────
            self._report(progress_callback, "Matching and stopping containers...", 2, 5)
            running = {c.name: c for c in self.client.containers.list()}
            matched = self._match_containers(restore_map, running, selections)

            if not dry_run:
                for container in matched["to_stop"]:
                    container.stop(timeout=30)
                    report["containers_stopped"].append(container.name)

            # ── Adım 3: Dosyaları kopyala ─────────────────
            self._report(progress_callback, "Restoring files...", 3, 5)
            for container_name, targets in matched["targets"].items():
                for archive_rel, dest_path in targets.items():
                    src = os.path.join(temp_dir, archive_rel)
                    if not os.path.exists(src):
                        report["errors"].append(f"Source not found in archive: {archive_rel}")
                        continue

                    if conflict_policy != "overwrite":
                        total, skipped = self._rsync_with_policy(
                            src, dest_path, conflict_policy, dry_run
                        )
                    else:
                        total, skipped = self._rsync_all(src, dest_path, dry_run)

                    report["restored_files"] += total
                    report["skipped_files"] += skipped

            # ── Adım 4: Container'ları başlat ─────────────
            self._report(progress_callback, "Starting containers...", 4, 5)
            if not dry_run:
                for container in matched["to_start"]:
                    container.start()
                    report["containers_started"].append(container.name)

            # ── Adım 5: Doğrula ───────────────────────────
            self._report(progress_callback, "Verifying...", 5, 5)
            verification = self._verify_restore(matched, report["errors"])

            report["status"] = "success" if not report["errors"] else "partial"
            report["completed_at"] = datetime.now().isoformat()
            report["verification"] = verification

        except Exception as e:
            report["status"] = "failed"
            report["errors"].append(str(e))
            # ROLLBACK: başlatılan container'ları eski haline döndürmeye çalış
            self._attempt_rollback(matched, report, dry_run)

        finally:
            # Temizlik
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        return report

    # ──────────────────────────────────────────────────────
    # 5. YARDIMCI METODLAR
    # ──────────────────────────────────────────────────────

    def _map_archive_to_host(self, archive_relative_path):
        """
        Archive içindeki path'i gerçek host path'ine çevirir.

        hostfs/var/lib/docker/volumes/db_data/_data/...
          → /var/lib/docker/volumes/db_data/_data/...   (named volume, direkt)

        hostfs/opt/npm/nginx/...
          → /hostfs/opt/npm/nginx/...                    (bind mount, /hostfs üzerinden)
        """
        if archive_relative_path.startswith("hostfs/"):
            real = archive_relative_path[7:]
            if real.startswith("var/lib/docker/volumes/"):
                return "/" + real
            else:
                return "/hostfs/" + real
        return archive_relative_path

    def _match_containers(self, restore_map, running_containers, selections):
        """
        Archive'teki container'ları şu an çalışan container'larla eşleştirir.

        Eşleştirme stratejisi (sırasıyla):
        1. Container name birebir eşleşme (wordpress_db → wordpress_db)
        2. compose.project label'ı ile eşleşme (stack bazlı restore)
        3. Volume path ile eşleşme (aynı volume'ü kullanan başka container)
        """
        matched = {"targets": {}, "to_stop": [], "to_start": [], "unmatched": []}

        for container_name, info in restore_map.get("containers", {}).items():
            if selections and container_name not in selections.get("containers", restore_map["containers"].keys()):
                continue

            # Strateji 1: İsim eşleşmesi
            if container_name in running_containers:
                container = running_containers[container_name]
                matched["targets"][container_name] = self._build_target_map(
                    info, selections
                )
                matched["to_stop"].append(container)
                matched["to_start"].append(container)
                continue

            # Strateji 2: Compose project eşleşmesi
            compose_project = info.get("compose_project")
            if compose_project:
                found = False
                for name, c in running_containers.items():
                    if c.labels.get("com.docker.compose.project") == compose_project:
                        matched["targets"][container_name] = self._build_target_map(
                            info, selections
                        )
                        matched["to_stop"].append(c)
                        matched["to_start"].append(c)
                        found = True
                        break
                if found:
                    continue

            # Strateji 3: Eşleşme yok — volume path'leri hala geçerliyse restore et
            matched["targets"][container_name] = self._build_target_map(
                info, selections
            )
            matched["unmatched"].append(container_name)

        return matched

    def _build_target_map(self, container_info, selections):
        """
        Archive path → destination path mapping'i oluşturur.
        selections'daki volume filtresini uygular.
        """
        targets = {}
        for archive_rel, vol_info in container_info.get("volumes", {}).items():
            dest = vol_info.get("resolved_host_path") or self._map_archive_to_host(archive_rel)
            targets[archive_rel] = dest
        return targets

    def _detect_conflicts(self, archive_path, password, archive_rel_path, dest):
        """
        Archive'teki dosyalarla hedeftekileri karşılaştırır.
        rsync --dry-run --itemize-changes kullanır.
        """
        # Önce sadece ilgili path'i extract et
        temp_extract = os.path.join(self.temp_root, "conflict_check")
        os.makedirs(temp_extract, exist_ok=True)

        extract_cmd = [
            "7z", "x", "-y", f"-p{password}",
            archive_path, archive_rel_path, f"-o{temp_extract}"
        ]
        subprocess.run(extract_cmd, capture_output=True, check=True)

        src = os.path.join(temp_extract, archive_rel_path)
        cmd = ["rsync", "-avun", "--itemize-changes", src + "/", dest + "/"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        conflicts = []
        for line in result.stdout.split("\n"):
            if line and not line.startswith("sending") and not line.startswith("sent"):
                conflicts.append({"path": line, "recommendation": "review"})

        shutil.rmtree(temp_extract)
        return conflicts

    def _rsync_with_policy(self, src, dest, policy, dry_run):
        """Politikaya göre rsync çalıştırır."""
        cmd = ["rsync", "-av"]
        if policy == "newer":
            cmd.append("-u")  # sadece daha yeniyse
        elif policy == "skip":
            cmd.append("--ignore-existing")
        if dry_run:
            cmd.append("--dry-run")

        cmd.extend([src.rstrip("/") + "/", dest.rstrip("/") + "/"])
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Kopyalanan dosya sayısını say
        lines = [l for l in result.stdout.split("\n") if l and not l.startswith("sending") and not l.startswith("sent")]
        return len(lines), 0

    def _rsync_all(self, src, dest, dry_run):
        """Tüm dosyaları koşulsuz kopyalar."""
        return self._rsync_with_policy(src, dest, "overwrite", dry_run)

    def _verify_restore(self, matched, errors):
        """Restore sonrası temel doğrulama."""
        verified = {"checked": 0, "passed": 0, "failed": 0}
        for container_name, targets in matched.get("targets", {}).items():
            for dest in targets.values():
                verified["checked"] += 1
                if os.path.exists(dest):
                    verified["passed"] += 1
                else:
                    verified["failed"] += 1
                    errors.append(f"Verification failed: {dest} does not exist after restore")
        return verified

    def _attempt_rollback(self, matched, report, dry_run):
        """Restore başarısız olursa container'ları eski haline döndürmeye çalışır."""
        if dry_run:
            return
        for container in report.get("containers_stopped", []):
            try:
                container.start()
            except Exception:
                pass

    def _report(self, callback, message, step, total):
        """İlerleme raporlaması."""
        if callback:
            callback(message, step, total)
```

---

## 5. UI Tasarımı

### Akış: 3 adımda restore

```
╔══════════════════════════════════════════════════════════════╗
║                    ADIM 1 — BACKUP SEÇİMİ                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  📋 Kaynak                                                  ║
║  ┌──────────────────────────────────────────────────────┐   ║
║  │ ● Local backups   ○ Cloud backups (rclone)           │   ║
║  └──────────────────────────────────────────────────────┘   ║
║                                                              ║
║  ┌────┬─────────────────────────┬────────┬────────┬─────┐   ║
║  │    │ İsim                    │ Boyut  │ Tarih  │ Det.│   ║
║  ├────┼─────────────────────────┼────────┼────────┼─────┤   ║
║  │ 🔍 │ Backup_20250625_030000  │ 2.4 GB │ Bugün  │  →  │   ║
║  │    │ ✅ Full · 8 container   │        │ 03:00  │     │   ║
║  ├────┼─────────────────────────┼────────┼────────┼─────┤   ║
║  │    │ Backup_20250624_030000  │ 2.3 GB │ 1 gün  │  →  │   ║
║  │    │ ✅ Full · 8 container   │        │ önce   │     │   ║
║  ├────┼─────────────────────────┼────────┼────────┼─────┤   ║
║  │    │ Portainer_Backup_0625   │ 45 MB  │ Bugün  │  →  │   ║
║  │    │ ✅ Portainer config     │        │ 02:58  │     │   ║
║  └────┴─────────────────────────┴────────┴────────┴─────┘   ║
║                                                              ║
║                           [İleri: Önizleme →]               ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║                  ADIM 2 — RESTORE ÖNİZLEME                   ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  📦 Backup_20250625_030000.7z                                ║
║                                                              ║
║  Stack: wordpress (2 container)                     ⬇ aç/kapa║
║  ┌──────────────────────────────────────────────────────┐   ║
║  │                                                      │   ║
║  │  ☑ wordpress_db (mariadb:10)                         │   ║
║  │  │  📂 db_data → /var/lib/docker/volumes/...          │   ║
║  │  │     ▸ 1.2 GB · 15,432 dosya                       │   ║
║  │  │     ⚠️ Hedefte 3 dosya daha yeni                   │   ║
║  │  │                                                   │   ║
║  │  ☑ wordpress_app (wordpress:latest)                  │   ║
║  │     📂 wp_content → /var/.../wp_content/_data         │   ║
║  │     │  ▸ 890 MB · 8,201 dosya                        │   ║
║  │     │  ✅ Çakışma yok                                │   ║
║  │     📂 /opt/npm/nginx → host bind mount              │   ║
║  │        ▸ 12 KB · 1 dosya                             │   ║
║  │        ✅ Çakışma yok                                │   ║
║  └──────────────────────────────────────────────────────┘   ║
║                                                              ║
║  ⚙️ Seçenekler                                               ║
║  ┌──────────────────────────────────────────────────────┐   ║
║  │ Çakışma durumunda:                                    │   ║
║  │ ○ Atla (hedeftekini koru)                             │   ║
║  │ ● Backup daha yeniyse üzerine yaz                     │   ║
║  │ ○ Hepsini üzerine yaz ⚠️                              │   ║
║  │                                                       │   ║
║  │ ☐ Sadece simüle et (dry-run)                          │   ║
║  └──────────────────────────────────────────────────────┘   ║
║                                                              ║
║  📊 ~2.1 GB alan gerekli · Tahmini süre: ~3 dk              ║
║                                                              ║
║             [← Geri]              [⚠️ Restore Başlat]       ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║                  ADIM 3 — RESTORE İŞLEMİ                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  ████████████████░░░░░░░░ 72%                                ║
║                                                              ║
║  ✅ Arşiv açıldı                                (2.4 GB)    ║
║  ✅ Container'lar durduruldu                                   ║
║     ✓ wordpress_app                                          ║
║     ✓ wordpress_db                                           ║
║  ⏳ Dosyalar kopyalanıyor...                                  ║
║     ✓ db_data (1.2 GB) — 15,432 dosya                       ║
║     █ wp_content (890 MB) — 5,201 / 8,201 dosya             ║
║     · /opt/npm/nginx — bekliyor                              ║
║  · Container'lar başlatılıyor...                             ║
║                                                              ║
║  ──── Tamamlandı ───────────────────────────────────────    ║
║                                                              ║
║  ┌──────────────────────────────────────────────────────┐   ║
║  │ ✅ Restore Başarılı!                                 │   ║
║  │                                                      │   ║
║  │ Süre:          2 dk 47 sn                            │   ║
║  │ Dosya:         23,634 geri yüklendi                  │   ║
║  │ Atlanan:       3 (hedef daha yeni)                   │   ║
║  │ Hata:          0                                     │   ║
║  │                                                      │   ║
║  │ Container'lar başlatıldı: ✓                          │   ║
║  │   wordpress_db    → running (healthy)                │   ║
║  │   wordpress_app   → running (healthy)                │   ║
║  └──────────────────────────────────────────────────────┘   ║
║                                                              ║
║          [← Dashboard]          [📋 Raporu İndir]           ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 6. Güvenlik Katmanları

```
┌─────────────────────────────────────────────────┐
│              1. PRE-FLIGHT CHECK                 │
│  ┌──────────────────────────────────────────┐   │
│  │ • Hedef diskte yeterli alan var mı?      │   │
│  │   (archive boyutu × 1.5 = gerekli)       │   │
│  │ • Hedef path'ler yazılabilir mi?         │   │
│  │ • Container'lar durdurulabilir mi?       │   │
│  │ • Docker bağlantısı aktif mi?            │   │
│  └──────────────────────────────────────────┘   │
│                      │                          │
│                      ▼                          │
│              2. DRY-RUN                          │
│  ┌──────────────────────────────────────────┐   │
│  │ • rsync --dry-run ile simülasyon         │   │
│  │ • Hangi dosyalar değişecek?             │   │
│  │ • Çakışma listesi                       │   │
│  │ • Kullanıcı onayı ALINMADAN devam ETME  │   │
│  └──────────────────────────────────────────┘   │
│                      │                          │
│                      ▼                          │
│              3. SAFETY NET                       │
│  ┌──────────────────────────────────────────┐   │
│  │ • Mevcut dosyalar .backup_<ts> olarak    │   │
│  │   yedeklenir (son 3 restore saklanır)    │   │
│  │ • Restore başarısızsa otomatik ROLLBACK  │   │
│  │ • Tüm işlemler loglanır                  │   │
│  └──────────────────────────────────────────┘   │
│                      │                          │
│                      ▼                          │
│              4. ATOMIC OPERATIONS                │
│  ┌──────────────────────────────────────────┐   │
│  │ • Önce tüm container'lar durdurulur      │   │
│  │ • Tüm kopyalamalar yapılır               │   │
│  │ • YA HEP YA HİÇ: biri başarısız olursa   │   │
│  │   tüm volume'ler geri alınır             │   │
│  │ • Container'lar başlatılır               │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## 7. Kısmi Restore Senaryoları

| Senaryo | Nasıl |
|---------|-------|
| "wp_content'i 3 gün önceki haline döndür" | Sadece wordpress_app → wp_content volume'ünü seç, diğerlerini pas geç |
| "Tüm wordpress stack'ini geri yükle" | Stack seviyesinde seçim: wordpress (db + app container'ları birlikte) |
| "Sadece tek bir config dosyasını geri al" | Volume seçildikten sonra dosya bazlı filtre |
| "Son 7 günün en küçük backup'ını bul" | Metadata bazlı filtreleme + sıralama |
| "Portainer config'ini geri yükle" | Portainer backup'ları da aynı listede, API ile import et |

---

## 8. Uygulama Planı

### Phase 1 — Temel Altyapı (1-2 hafta)
- [ ] `restore_map.json` oluşturma — `engine.py` içinde backup sırasında
- [ ] `RestoreEngine` sınıfı — `app/restore_engine.py`
- [ ] Local backup listeleme + metadata okuma
- [ ] Basit restore (tek container, çakışma kontrolü olmadan)

### Phase 2 — UI Entegrasyonu (1-2 hafta)
- [ ] Yeni "Restore" tab'ı — `ui.py` içinde
- [ ] 3 adımlı wizard akışı
- [ ] İlerleme çubuğu + canlı log
- [ ] Dry-run önizleme

### Phase 3 — Güvenlik + Cloud (1 hafta)
- [ ] Çakışma tespiti + policy seçenekleri
- [ ] Cloud'dan indirme + restore
- [ ] Rollback mekanizması
- [ ] Kısmi restore (volume/container/stacks seviyesi)
- [ ] Restore raporu (indirilebilir)

---

> **Sonraki adım:** `RESTORE_DESIGN.md` onaylandıktan sonra Phase 1 implementasyonuna başlanabilir.
