# Dictionary containing translations for English, Turkish, and German
TRANSLATIONS = {
    "en": {
        # Titles
        "page_title_setup": "Restore Container - Setup",
        "header_setup": "🛠️ Initial Setup Wizard",
        "page_title_dashboard": "Restore Container",
        "header_dashboard": "📦 Restore Container Dashboard",
        
        # Setup Wizard
        "warning_env_missing": "⚠️ Configuration file (`.env`) not found. Please configure the settings below before using the system.",
        "subheader_portainer": "🚀 Portainer Integration",
        "info_portainer": "Portainer API access is required to manage containers.",
        "label_portainer_url": "Portainer URL",
        "label_portainer_token": "Portainer Access Token",
        "help_portainer_token": "API Token obtained from Portainer",
        
        "subheader_gotify": "🔔 Notifications (Gotify)",
        "info_gotify": "Used to report backup statuses.",
        "label_gotify_url": "Gotify URL",
        "label_gotify_token": "Gotify App Token",
        
        "subheader_security": "🔒 Security & Backup",
        "label_backup_pass": "Backup Encryption Password",
        "help_backup_pass": "Key used for AES-256 encryption.",
        "label_retention": "Retention Period (Days)",
        "help_retention": "Duration to keep old backups.",
        "label_timezone": "Timezone",
        "label_healthcheck": "Healthcheck URL (Optional)",
        
        "subheader_rclone": "☁️ Rclone Settings",
        "label_rclone_path": "Rclone Config Path",
        "help_rclone_path": "Path to rclone.conf mounted inside the container.",
        
        "btn_save": "💾 Save Settings & Start",
        "error_missing_fields": "⛔ Error: Portainer URL, Token, and Backup Password are required!",
        "success_setup": "✅ Setup completed successfully! Restarting application...",
        
        # Dashboard
        "menu_title": "Menu",
        "system_online": "System Online",
        "subheader_candidates": "📋 Containers to Backup",
        "warning_no_candidates": "⚠️ No containers found with `backup.enable=true` label.",
        "label_status": "Status",
        "label_image": "Image",
        "btn_backup": "🚀 Backup: {name}",
        "status_backing_up": "Backing up: {name}...",
        "status_scanning": "🔍 Scanning Volume and Mount points...",
        "error_no_pass": "ERROR: Backup password not found!",
        "status_failed": "Backup Failed ❌",
        "status_success_encrypt": "✅ Backup and Encryption completed.",
        "status_waiting_cloud": "☁️ Waiting for cloud sync... (Rclone)",
        "status_complete": "Backup Completed Successfully! 🎉",
        "status_error_process": "❌ Error occurred during backup.",
        "status_error_label": "Backup Error ⛔",
        
        # Notifications
        "notif_success_title": "Backup Successful",
        "notif_success_msg": "Container {name} successfully backed up.",
        "notif_error_title": "Backup Error",
        "notif_error_msg": "Error backing up {name}!",
        
        # Settings View
        "checkbox_show_settings": "Show Settings (Masked)",
        "lang_select_label": "Select Language / Dil Seçimi / Sprache wählen"
    },
    
    "tr": {
        # Titles
        "page_title_setup": "Restore Container - Kurulum",
        "header_setup": "🛠️ İlk Kurulum Sihirbazı",
        "page_title_dashboard": "Restore Container",
        "header_dashboard": "📦 Restore Container Paneli",
        
        # Setup Wizard
        "warning_env_missing": "⚠️ Konfigürasyon dosyası (`.env`) bulunamadı. Lütfen sistemi kullanmaya başlamadan önce aşağıdaki ayarları yapılandırın.",
        "subheader_portainer": "🚀 Portainer Entegrasyonu",
        "info_portainer": "Konteynerleri yönetmek için Portainer API erişimi gereklidir.",
        "label_portainer_url": "Portainer URL",
        "label_portainer_token": "Portainer Erişim Tokeni",
        "help_portainer_token": "Portainer'dan alacağınız API Token",
        
        "subheader_gotify": "🔔 Bildirimler (Gotify)",
        "info_gotify": "Yedekleme durumlarını bildirmek için kullanılır.",
        "label_gotify_url": "Gotify URL",
        "label_gotify_token": "Gotify Uygulama Tokeni",
        
        "subheader_security": "🔒 Güvenlik ve Yedekleme",
        "label_backup_pass": "Yedek Şifreleme Parolası",
        "help_backup_pass": "AES-256 şifreleme için kullanılacak anahtar.",
        "label_retention": "Saklama Süresi (Gün)",
        "help_retention": "Eski yedeklerin silinme süresi.",
        "label_timezone": "Zaman Dilimi",
        "label_healthcheck": "Healthcheck URL (Opsiyonel)",
        
        "subheader_rclone": "☁️ Rclone Ayarları",
        "label_rclone_path": "Rclone Konfigürasyon Yolu",
        "help_rclone_path": "Konteyner içine mount edilen rclone.conf dosyasının yolu.",
        
        "btn_save": "💾 Ayarları Kaydet ve Başlat",
        "error_missing_fields": "⛔ Hata: Portainer URL, Token ve Yedekleme Şifresi zorunludur!",
        "success_setup": "✅ Kurulum başarıyla tamamlandı! Uygulama yeniden başlatılıyor...",
        
        # Dashboard
        "menu_title": "Menü",
        "system_online": "Sistem Çevrimiçi",
        "subheader_candidates": "📋 Yedeklenecek Konteynerler",
        "warning_no_candidates": "⚠️ `backup.enable=true` etiketine sahip konteyner bulunamadı.",
        "label_status": "Durum",
        "label_image": "İmaj",
        "btn_backup": "🚀 Yedekle: {name}",
        "status_backing_up": "Yedekleniyor: {name}...",
        "status_scanning": "🔍 Volume ve Mount noktaları taranıyor...",
        "error_no_pass": "HATA: Yedekleme parolası bulunamadı!",
        "status_failed": "Yedekleme Başarısız ❌",
        "status_success_encrypt": "✅ Yedekleme ve Şifreleme tamamlandı.",
        "status_waiting_cloud": "☁️ Bulut senkronizasyonu bekleniyor... (Rclone)",
        "status_complete": "Yedekleme Başarıyla Tamamlandı! 🎉",
        "status_error_process": "❌ Yedekleme sırasında hata oluştu.",
        "status_error_label": "Yedekleme Hatası ⛔",
        
        # Notifications
        "notif_success_title": "Yedekleme Başarılı",
        "notif_success_msg": "{name} konteyneri başarıyla yedeklendi.",
        "notif_error_title": "Yedekleme Hatası",
        "notif_error_msg": "{name} yedeklenirken hata oluştu!",
        
        # Settings View
        "checkbox_show_settings": "Ayarları Göster (Maskelenmiş)",
        "lang_select_label": "Dil Seçimi / Select Language / Sprache wählen"
    },
    
    "de": {
        # Titles
        "page_title_setup": "Restore Container - Einrichtung",
        "header_setup": "🛠️ Ersteinrichtungs-Assistent",
        "page_title_dashboard": "Restore Container",
        "header_dashboard": "📦 Restore Container Dashboard",
        
        # Setup Wizard
        "warning_env_missing": "⚠️ Konfigurationsdatei (`.env`) nicht gefunden. Bitte konfigurieren Sie die Einstellungen unten, bevor Sie das System verwenden.",
        "subheader_portainer": "🚀 Portainer Integration",
        "info_portainer": "Für die Verwaltung der Container ist Zugriff auf die Portainer-API erforderlich.",
        "label_portainer_url": "Portainer URL",
        "label_portainer_token": "Portainer Zugriffs-Token",
        "help_portainer_token": "API-Token von Portainer",
        
        "subheader_gotify": "🔔 Benachrichtigungen (Gotify)",
        "info_gotify": "Wird verwendet, um den Sicherungsstatus zu melden.",
        "label_gotify_url": "Gotify URL",
        "label_gotify_token": "Gotify App Token",
        
        "subheader_security": "🔒 Sicherheit & Backup",
        "label_backup_pass": "Backup-Verschlüsselungspasswort",
        "help_backup_pass": "Schlüssel für AES-256-Verschlüsselung.",
        "label_retention": "Aufbewahrungsdauer (Tage)",
        "help_retention": "Dauer, für die alte Backups aufbewahrt werden.",
        "label_timezone": "Zeitzone",
        "label_healthcheck": "Healthcheck URL (Optional)",
        
        "subheader_rclone": "☁️ Rclone Einstellungen",
        "label_rclone_path": "Rclone Konfigurationspfad",
        "help_rclone_path": "Pfad zur rclone.conf, die im Container eingehängt ist.",
        
        "btn_save": "💾 Einstellungen speichern & starten",
        "error_missing_fields": "⛔ Fehler: Portainer URL, Token und Backup-Passwort sind erforderlich!",
        "success_setup": "✅ Einrichtung erfolgreich abgeschlossen! Anwendung wird neu gestartet...",
        
        # Dashboard
        "menu_title": "Menü",
        "system_online": "System Online",
        "subheader_candidates": "📋 Zu sichernde Container",
        "warning_no_candidates": "⚠️ Keine Container mit dem Label `backup.enable=true` gefunden.",
        "label_status": "Status",
        "label_image": "Image",
        "btn_backup": "🚀 Sichern: {name}",
        "status_backing_up": "Sicherung läuft: {name}...",
        "status_scanning": "🔍 Scanne Volume- und Mount-Punkte...",
        "error_no_pass": "FEHLER: Backup-Passwort nicht gefunden!",
        "status_failed": "Sicherung fehlgeschlagen ❌",
        "status_success_encrypt": "✅ Sicherung und Verschlüsselung abgeschlossen.",
        "status_waiting_cloud": "☁️ Warte auf Cloud-Sync... (Rclone)",
        "status_complete": "Sicherung erfolgreich abgeschlossen! 🎉",
        "status_error_process": "❌ Fehler während der Sicherung.",
        "status_error_label": "Sicherungsfehler ⛔",
        
        # Notifications
        "notif_success_title": "Sicherung erfolgreich",
        "notif_success_msg": "Container {name} erfolgreich gesichert.",
        "notif_error_title": "Sicherungsfehler",
        "notif_error_msg": "Fehler beim Sichern von {name}!",
        
        # Settings View
        "checkbox_show_settings": "Einstellungen anzeigen (Maskiert)",
        "lang_select_label": "Sprache wählen / Select Language / Dil Seçimi"
    }
}

def get_text(lang_code, key):
    """Retrieves translation for the given key and language code."""
    lang = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])
    return lang.get(key, f"[{key}]")
