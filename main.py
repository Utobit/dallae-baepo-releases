"""
Dallae PC Agent — 배포판 진입점.
"""
import sys
import os
from pathlib import Path

# console=False 빌드에서 stdout/stderr이 None일 수 있음
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")


def _load_env_file():
    """EXE 옆 dallae_api_keys.env 에서 환경변수 로드."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)).parent
    env_path = base / "dallae_api_keys.env"
    if not env_path.exists():
        env_path = Path(__file__).parent / "dallae_api_keys.env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val:
            os.environ.setdefault(key, val)


_load_env_file()

# settings 복원 (업데이트 후 재실행 시)
import settings_manager
if "--restore-settings" in sys.argv:
    settings_manager.restore_from_backup()

import baepo_ui

if __name__ == "__main__":
    app = baepo_ui.BaepoApp()
    app.run()
