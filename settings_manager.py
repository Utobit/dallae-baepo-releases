import json
import os
import uuid
from pathlib import Path

APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "DallaeBaepo"
SETTINGS_FILE = APPDATA_DIR / "settings.json"
BACKUP_FILE   = APPDATA_DIR / "settings_backup.json"
SLEEP_LOG     = APPDATA_DIR / "sleep_log.json"

DEFAULT_SETTINGS = {
    "uuid": "",
    "sleep_mode": "keep_windows",   # "keep_windows" | "close_all"
    "volume_before_sleep": -1,      # -1 = unknown
    "wake_chrome_url": "",          # URL to open on wake (empty = skip)
    "wake_shortcut_name": "",       # desktop shortcut name (empty = skip)
    "game_setting_enabled": False,
    "game_chrome_url": "https://www.op.gg",
    "game_shortcut_name": "",       # e.g. "리그 오브 레전드"
    "extension_key": "",
}


def _ensure_dir():
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    _ensure_dir()
    if not SETTINGS_FILE.exists():
        s = dict(DEFAULT_SETTINGS)
        s["uuid"] = str(uuid.uuid4())
        save(s)
        return s
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    # fill missing keys with defaults
    for k, v in DEFAULT_SETTINGS.items():
        if k not in data:
            data[k] = v
    if not data.get("uuid"):
        data["uuid"] = str(uuid.uuid4())
        save(data)
    return data


def save(s: dict):
    _ensure_dir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def backup():
    if SETTINGS_FILE.exists():
        import shutil
        shutil.copy2(SETTINGS_FILE, BACKUP_FILE)


def restore_from_backup():
    if BACKUP_FILE.exists():
        import shutil
        shutil.copy2(BACKUP_FILE, SETTINGS_FILE)
        return True
    return False


# ---------- sleep log ----------

def append_sleep_log(event: str):
    """event: 'sleep' | 'wake'"""
    from datetime import datetime
    _ensure_dir()
    log = []
    if SLEEP_LOG.exists():
        with open(SLEEP_LOG, encoding="utf-8") as f:
            try:
                log = json.load(f)
            except Exception:
                log = []
    log.append({"event": event, "ts": datetime.now().isoformat(timespec="seconds")})
    with open(SLEEP_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def load_sleep_log() -> list:
    if not SLEEP_LOG.exists():
        return []
    with open(SLEEP_LOG, encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []
