"""
PC 제어 모듈 — 배포판 전용.
Windows 전용. pycaw(볼륨), ctypes(화면), win32gui(창 닫기) 사용.
"""
import ctypes
import glob
import os
import subprocess
import sys
import time
import threading
from typing import Optional

# pycaw — 볼륨 제어
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    import pythoncom
    _PYCAW_OK = True
except ImportError:
    _PYCAW_OK = False

# win32gui — 창 열거/닫기
try:
    import win32gui
    import win32con
    _WIN32_OK = True
except ImportError:
    _WIN32_OK = False


# ──────────────────────────────────────────────────────────
# 화면 (모니터)
# ──────────────────────────────────────────────────────────

SC_MONITORPOWER = 0xF170
HWND_BROADCAST  = 0xFFFF
WM_SYSCOMMAND   = 0x0112


def monitor_off():
    ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)


def monitor_on():
    # 마우스 미세 이동으로 화면 깨우기
    ctypes.windll.user32.mouse_event(0x0001, 0, 0, 0, 0)  # MOUSEEVENTF_MOVE
    ctypes.windll.user32.mouse_event(0x0001, 1, 1, 0, 0)


# ──────────────────────────────────────────────────────────
# 볼륨
# ──────────────────────────────────────────────────────────

def _get_volume_interface() -> Optional[object]:
    if not _PYCAW_OK:
        return None
    try:
        pythoncom.CoInitialize()
        speakers = AudioUtilities.GetSpeakers()
        # pycaw >= 0.6: EndpointVolume property
        if hasattr(speakers, "EndpointVolume"):
            return speakers.EndpointVolume
        # legacy pycaw: Activate method
        interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def get_volume() -> int:
    vol = _get_volume_interface()
    if vol is None:
        return -1
    return int(vol.GetMasterVolumeLevelScalar() * 100)


def set_volume(level: int):
    vol = _get_volume_interface()
    if vol is None:
        return
    vol.SetMasterVolumeLevelScalar(max(0, min(100, level)) / 100, None)


def mute():
    vol = _get_volume_interface()
    if vol:
        vol.SetMute(1, None)


def unmute():
    vol = _get_volume_interface()
    if vol:
        vol.SetMute(0, None)


def is_muted() -> bool:
    vol = _get_volume_interface()
    if vol is None:
        return False
    return bool(vol.GetMute())


# ──────────────────────────────────────────────────────────
# 창 닫기 (전체)
# ──────────────────────────────────────────────────────────

def close_all_windows():
    if not _WIN32_OK:
        return

    def _enum(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass

    win32gui.EnumWindows(_enum, None)


# ──────────────────────────────────────────────────────────
# 바탕화면 바로가기 실행
# ──────────────────────────────────────────────────────────

def _desktop_paths() -> list[str]:
    paths = []
    user_desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    pub_desktop  = os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop")
    if os.path.isdir(user_desktop):
        paths.append(user_desktop)
    if os.path.isdir(pub_desktop):
        paths.append(pub_desktop)
    return paths


def run_desktop_shortcut(name: str) -> bool:
    """바탕화면에서 이름이 포함된 .lnk를 찾아 실행. 성공 시 True."""
    if not name.strip():
        return False
    for desktop in _desktop_paths():
        matches = glob.glob(os.path.join(desktop, f"*{name}*.lnk"))
        if matches:
            os.startfile(matches[0])
            return True
    return False


def open_chrome_url(url: str):
    if not url.strip():
        return
    # Chrome 경로 후보
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    chrome = next((p for p in chrome_candidates if os.path.exists(p)), None)
    if chrome:
        subprocess.Popen([chrome, url])
    else:
        os.startfile(url)  # 기본 브라우저로 fallback


# ──────────────────────────────────────────────────────────
# 취침 / 기상 시나리오
# ──────────────────────────────────────────────────────────

def do_sleep(settings: dict) -> dict:
    """
    취침 실행. 실행 전 볼륨·설정 상태를 반환해서 settings에 저장하도록 함.
    """
    saved_volume = get_volume()
    mute()
    if settings.get("sleep_mode") == "close_all":
        close_all_windows()
    monitor_off()
    return {"volume_before_sleep": saved_volume}


def do_wake(settings: dict, mode: str = "normal"):
    """
    mode: 'normal' | 'game'
    """
    monitor_on()
    time.sleep(2)
    unmute()
    saved_vol = settings.get("volume_before_sleep", -1)
    if isinstance(saved_vol, int) and saved_vol >= 0:
        set_volume(saved_vol)

    if mode == "game":
        game_url  = settings.get("game_chrome_url", "").strip()
        game_name = settings.get("game_shortcut_name", "").strip()
        if game_url:
            open_chrome_url(game_url)
            time.sleep(1)
        if game_name:
            run_desktop_shortcut(game_name)
    else:
        chrome_url    = settings.get("wake_chrome_url", "").strip()
        shortcut_name = settings.get("wake_shortcut_name", "").strip()
        if chrome_url:
            open_chrome_url(chrome_url)
        if shortcut_name:
            time.sleep(0.5)
            run_desktop_shortcut(shortcut_name)


def do_sleep_async(settings: dict, on_done=None):
    def _run():
        result = do_sleep(settings)
        if on_done:
            on_done(result)
    threading.Thread(target=_run, daemon=True).start()


def do_wake_async(settings: dict, mode: str = "normal", on_done=None):
    def _run():
        do_wake(settings, mode)
        if on_done:
            on_done({})
    threading.Thread(target=_run, daemon=True).start()
