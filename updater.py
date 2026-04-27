"""
OTA 업데이터 — GitHub Releases의 update.json 폴링 기반.
업데이트 시 설정 백업 → EXE 다운로드 → 재실행.
"""
import json
import os
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Callable, Optional

CURRENT_VERSION = "0.1.3"

UPDATE_JSON_URL = "https://raw.githubusercontent.com/Utobit/dallae-baepo-releases/main/update.json"

DOWNLOAD_DIR = Path(os.environ.get("TEMP", ".")) / "DallaeBaepo"


def _fetch_update_info() -> Optional[dict]:
    try:
        with urllib.request.urlopen(UPDATE_JSON_URL, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _version_tuple(v: str):
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0,)


def check_update() -> Optional[dict]:
    """
    새 버전이 있으면 {'version':..., 'url':..., 'notes':...} 반환.
    없거나 실패하면 None.
    """
    info = _fetch_update_info()
    if not info:
        return None
    remote_ver = info.get("version", "0.0.0")
    if _version_tuple(remote_ver) > _version_tuple(CURRENT_VERSION):
        return info
    return None


def download_and_install(url: str, on_progress: Optional[Callable[[int], None]] = None):
    """
    1. settings 백업
    2. EXE 다운로드
    3. 현재 프로세스 종료 + 새 EXE 실행
    """
    from settings_manager import backup

    backup()

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOAD_DIR / "DallaeBaepo_new.exe"

    def _reporthook(block, block_size, total):
        if on_progress and total > 0:
            pct = min(100, int(block * block_size * 100 / total))
            on_progress(pct)

    urllib.request.urlretrieve(url, dest, reporthook=_reporthook)

    # 새 EXE를 실행하고 현재 프로세스 종료
    os.startfile(str(dest))
    sys.exit(0)


def check_update_async(on_result: Callable[[Optional[dict]], None]):
    threading.Thread(target=lambda: on_result(check_update()), daemon=True).start()
