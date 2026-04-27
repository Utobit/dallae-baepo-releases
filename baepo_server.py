"""
FastAPI server — mobile communication, port 8766.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import socket
import threading
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pc_control
import settings_manager
import updater

app = FastAPI(title="DallaeBaepo", version=updater.CURRENT_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_state: dict = {
    "sleeping": False,
    "muted": False,
    "volume": -1,
    "sleep_since": "",
    "last_wake": "",
}
_settings_ref: list[dict] = [{}]


def set_settings_ref(s: dict):
    _settings_ref[0] = s


def _save_state_after_sleep(result: dict):
    s = _settings_ref[0]
    if "volume_before_sleep" in result:
        s["volume_before_sleep"] = result["volume_before_sleep"]
        settings_manager.save(s)
    _state["sleeping"] = True
    _state["muted"] = True
    _state["sleep_since"] = datetime.now().isoformat(timespec="seconds")
    settings_manager.append_sleep_log("sleep")


def _after_wake(_):
    _state["sleeping"] = False
    _state["muted"] = False
    _state["last_wake"] = datetime.now().isoformat(timespec="seconds")
    settings_manager.append_sleep_log("wake")


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/state")
async def api_state():
    _state["volume"] = pc_control.get_volume()
    _state["muted"]  = pc_control.is_muted()
    return _state


@app.post("/api/sleep")
async def api_sleep():
    s = _settings_ref[0]
    pc_control.do_sleep_async(s, on_done=_save_state_after_sleep)
    return {"ok": True, "mode": s.get("sleep_mode", "keep_windows")}


class WakeRequest(BaseModel):
    mode: str = "normal"


@app.post("/api/wake")
async def api_wake(payload: WakeRequest):
    s = _settings_ref[0]
    pc_control.do_wake_async(s, mode=payload.mode, on_done=_after_wake)
    return {"ok": True, "mode": payload.mode}


@app.post("/api/mute")
async def api_mute():
    pc_control.mute()
    _state["muted"] = True
    return {"ok": True}


@app.post("/api/unmute")
async def api_unmute():
    pc_control.unmute()
    _state["muted"] = False
    return {"ok": True}


class VolumeRequest(BaseModel):
    level: int


@app.post("/api/volume")
async def api_volume(payload: VolumeRequest):
    pc_control.set_volume(payload.level)
    _state["volume"] = payload.level
    return {"ok": True, "level": payload.level}


@app.get("/api/update/check")
async def api_update_check():
    info = updater.check_update()
    if info:
        return {"available": True, **info}
    return {"available": False, "current": updater.CURRENT_VERSION}


class _InstallPayload(BaseModel):
    url: str

@app.post("/api/update/install")
async def api_update_install(payload: _InstallPayload):
    import threading
    def _do():
        try:
            updater.download_and_install(payload.url)
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()
    return {"ok": True}


@app.get("/api/qr")
async def api_qr():
    s = _settings_ref[0]
    uid = s.get("uuid", "")
    ip = _local_ip()
    return {"ip": ip, "uuid": uid, "port": 8766}


@app.get("/api/sleep_log")
async def api_sleep_log():
    return settings_manager.load_sleep_log()


@app.get("/api/apk/download")
async def api_apk_download():
    base = os.path.dirname(os.path.abspath(__file__))
    apk_path = os.path.join(base, "..", "dallae-baepo-releases", "DallaePC.apk")
    apk_path = os.path.normpath(apk_path)
    if not os.path.exists(apk_path):
        return JSONResponse({"error": "APK not found"}, status_code=404)
    return StreamingResponse(
        open(apk_path, "rb"),
        media_type="application/vnd.android.package-archive",
        headers={"Content-Disposition": "attachment; filename=DallaeBaepo.apk"},
    )


# ── AI Chat ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    mode: str = "chatbot"       # "chatbot" | "report"
    language: str = "한국어"    # 응답 언어
    category: str = ""          # report 전용: 버그 | 기능요청 | 칭찬 | 기타


CHAT_SYSTEM = (
    "당신은 '달래'입니다. 사용자의 PC에 상주하는 전담 AI 비서입니다.\n"
    "규칙:\n"
    "1. 응답 언어: {language}. 한자 사용 금지.\n"
    "2. 어조는 친근하고 따뜻하되 절제됩니다. 'ㅋ','ㅎ', 이모티콘 남발 금지.\n"
    "3. PC 관련(취침·기상·음소거·볼륨)은 실질적으로 안내합니다.\n"
    "4. 일상 대화에도 자연스럽게 응합니다.\n"
    "5. 불편사항·버그·건의·기능 요청 등 개발자에게 전달할 내용이면 응답 마지막 줄에 정확히 "
    "'<<전달확인>>' 만 추가하세요. 그 외에는 절대 추가하지 마세요.\n"
    "6. 현재 세션 내 대화만 기억합니다. '다음에 기억할게요', '앞으로는' 같은 "
    "   세션을 넘는 약속은 절대 하지 마세요. 모르는 것은 솔직히 모른다고 하세요.\n"
    "7. [기억 사용 금지 표현] 유저 기억 정보가 주어져도 '기억해요', '이전에 말씀하셨잖아요', "
    "   '저는 당신의 ~를 알고 있어요' 같은 표현은 절대 하지 마세요. "
    "   기억은 자연스러운 맥락으로만 활용하고, 기억 사용 사실을 드러내지 마세요.\n"
    "현재 PC 상태: {dev_status}\n"
    "{memory_block}"
)

FORWARD_MARKER = "<<전달확인>>"

_chat_histories: dict[str, list] = {}
_forwarded_log: list = []
_pending_forward: dict[str, dict] = {}

_YES_WORDS = {"네", "예", "응", "ㅇㅇ", "yes", "맞아", "보내줘", "전달해", "전달해줘", "보내", "전달"}
_NO_WORDS  = {"아니", "아니요", "노", "no", "괜찮아", "됐어", "ㄴㄴ", "아니오"}

# ── 메모리 시스템 ──────────────────────────────────────────────────────────

def _memory_dir() -> Path:
    base = Path(os.path.dirname(os.path.abspath(__file__)))
    d = base / "memory"
    d.mkdir(exist_ok=True)
    return d


def _user_memory_path() -> Path:
    return _memory_dir() / "user_memory.json"


def _daily_log_path(day: str | None = None) -> Path:
    if day is None:
        day = date.today().isoformat()
    return _memory_dir() / f"daily_{day}.jsonl"


def _load_user_memory() -> dict:
    p = _user_memory_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_updated": "", "summary": "", "raw_count": 0}


def _save_user_memory(mem: dict) -> None:
    try:
        _user_memory_path().write_text(
            json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _append_daily_log(entry: dict) -> int:
    """일별 로그에 추가하고 현재 줄 수 반환."""
    p = _daily_log_path()
    try:
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return sum(1 for _ in open(p, encoding="utf-8"))
    except Exception:
        return 0


def _build_memory_block() -> str:
    mem = _load_user_memory()
    summary = mem.get("summary", "").strip()
    if not summary:
        return ""
    return f"[유저 기억 요약]\n{summary}\n"


SUMMARIZE_THRESHOLD = 10   # 일별 로그 N줄 이상이면 요약 트리거
SUMMARIZE_KEEP_RECENT = 5  # 요약 후 최근 N개 대화는 원본 유지


def _maybe_summarize_async(system_fn, history_snapshot: list) -> None:
    """일별 로그가 임계값 초과 시 백그라운드에서 요약 실행."""
    p = _daily_log_path()
    try:
        count = sum(1 for _ in open(p, encoding="utf-8"))
    except Exception:
        return
    if count < SUMMARIZE_THRESHOLD:
        return

    def _run():
        try:
            lines = p.read_text(encoding="utf-8").strip().split("\n")
            entries = [json.loads(l) for l in lines if l.strip()]
            # 요약 대상: 오래된 항목 (recent N개 제외)
            to_summarize = entries[:-SUMMARIZE_KEEP_RECENT] if len(entries) > SUMMARIZE_KEEP_RECENT else entries
            if not to_summarize:
                return
            text_block = "\n".join(
                f"[{e.get('role','?')}] {e.get('message','')}" for e in to_summarize
            )
            mem = _load_user_memory()
            existing = mem.get("summary", "")
            prompt = (
                "아래는 달래PC 앱 사용자와 AI 달래 간의 대화 로그입니다.\n"
                "이전 요약이 있으면 통합하고, 중복을 제거하여 핵심 정보만 간결하게 정리하세요.\n"
                "유저의 이름, 선호, 불편사항, 요청사항, 생활 패턴 등 기억할 만한 내용 중심으로.\n"
                f"이전 요약:\n{existing}\n\n새 대화:\n{text_block}"
            )
            new_summary = system_fn(
                "당신은 대화 요약 전문가입니다. 핵심만 간결하게 요약하세요.",
                [{"role": "user", "content": prompt}]
            )
            mem["summary"] = new_summary
            mem["last_updated"] = date.today().isoformat()
            mem["raw_count"] = mem.get("raw_count", 0) + len(to_summarize)
            _save_user_memory(mem)
            # 요약된 항목을 로그에서 제거하고 최근 항목만 유지
            recent = entries[-SUMMARIZE_KEEP_RECENT:]
            with open(p, "w", encoding="utf-8") as f:
                for e in recent:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def _chat_log_path() -> str:
    return str(_memory_dir() / "chat_log.jsonl")


def _append_chat_log(entry: dict) -> None:
    try:
        with open(_chat_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


_DEFAULT_RELAY_URL   = "https://zu10cm90hd.execute-api.ap-northeast-2.amazonaws.com"
_DEFAULT_RELAY_TOKEN = "ntHRYDD3IVBgayzcqeF2MYO504RI2u43XsaEq87tTiY"


def _forward_to_lina_async(entry: dict) -> None:
    """유저 메시지를 AWS 릴레이 서버로 비동기 전달 (실패해도 조용히 무시)."""
    import urllib.request, urllib.error, json as _json
    lina_url = (
        os.environ.get("BAEPO_RELAY_URL", "").strip()
        or _DEFAULT_RELAY_URL
    ).rstrip("/")
    lina_token = os.environ.get("BAEPO_FORWARD_TOKEN", "").strip() or _DEFAULT_RELAY_TOKEN
    if not lina_url or not lina_token:
        return
    s = _settings_ref[0]
    payload = {
        **entry,
        "uuid":      s.get("uuid", ""),
        "user_name": s.get("user_name", ""),
        "app_ver":   "0.1.2",
    }

    def _send():
        try:
            data = _json.dumps(payload, ensure_ascii=False).encode()
            req = urllib.request.Request(
                f"{lina_url}/feedback",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "X-Baepo-Token": lina_token,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8):
                pass
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


def _dev_status_str() -> str:
    if _state.get("sleeping"):
        since = _state.get("sleep_since", "")
        return f"취침 중 (취침 시작: {since}). 취침 중 깨울 수 있습니다."
    return "활동 중"


def _chat_with_claude(system_prompt: str, messages: list) -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY_BAEPO") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("no_key")
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=messages[-20:],
    )
    return resp.content[0].text


def _chat_with_gemini(system_prompt: str, messages: list) -> str:
    import google.generativeai as genai
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("no_key")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction=system_prompt,
    )
    gemini_history = []
    for m in messages[:-1]:
        gemini_history.append({
            "role": "user" if m["role"] == "user" else "model",
            "parts": [m["content"]],
        })
    chat = model.start_chat(history=gemini_history)
    last_msg = messages[-1]["content"] if messages else ""
    resp = chat.send_message(last_msg)
    return resp.text


DEV_CHAT_LIMIT = 5  # free chats funded by developer per installation


@app.post("/api/chat")
async def api_chat(payload: ChatRequest):
    sid = payload.session_id or "default"
    ts_now = datetime.now().isoformat(timespec="seconds")

    # ── 신고모드: AI 미사용, 직접 전송 ───────────────────────────────────
    if payload.mode == "report":
        entry = {"ts": ts_now, "session": sid, "message": payload.message,
                 "mode": "report", "category": payload.category}
        _forwarded_log.append(entry)
        _forward_to_lina_async(entry)
        _append_chat_log({"ts": ts_now, "session": sid, "role": "user", "message": payload.message, "mode": "report"})
        return {"reply": "접수되었습니다. 개발자에게 전달합니다.",
                "forwarded": True, "engine": "direct", "dev_remaining": -1}

    # ── 재확인 대기 중인 세션 처리 ───────────────────────────────────────
    pending = _pending_forward.get(sid)
    if pending:
        user_text = payload.message.strip()
        is_yes = any(w in user_text for w in _YES_WORDS)
        is_no  = any(w in user_text for w in _NO_WORDS)
        if is_yes:
            _pending_forward.pop(sid, None)
            fwd_entry = {**pending, "mode": "chatbot_confirmed"}
            _forwarded_log.append(fwd_entry)
            _forward_to_lina_async(fwd_entry)
            _append_chat_log({"ts": ts_now, "session": sid, "role": "user", "message": user_text})
            reply_text = "전달했습니다. 개발자가 확인할 예정입니다."
            _append_chat_log({"ts": ts_now, "session": sid, "role": "assistant", "message": reply_text, "forwarded": True})
            history = _chat_histories.setdefault(sid, [])
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": reply_text})
            s = _settings_ref[0]
            return {"reply": reply_text, "forwarded": True, "engine": "direct",
                    "dev_remaining": s.get("dev_chats_remaining", 0)}
        elif is_no:
            _pending_forward.pop(sid, None)
            _append_chat_log({"ts": ts_now, "session": sid, "role": "user", "message": user_text})
            reply_text = "알겠습니다. 전달하지 않겠습니다."
            _append_chat_log({"ts": ts_now, "session": sid, "role": "assistant", "message": reply_text})
            history = _chat_histories.setdefault(sid, [])
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": reply_text})
            s = _settings_ref[0]
            return {"reply": reply_text, "forwarded": False, "engine": "direct",
                    "dev_remaining": s.get("dev_chats_remaining", 0)}
        # 명확한 답 아니면 pending 유지 후 AI 처리로 계속

    # ── 일반 채팅 처리 ───────────────────────────────────────────────────
    history = _chat_histories.setdefault(sid, [])
    history.append({"role": "user", "content": payload.message})
    _append_daily_log({"ts": ts_now, "session": sid, "role": "user", "message": payload.message})
    _append_chat_log({"ts": ts_now, "session": sid, "role": "user", "message": payload.message})

    system_prompt = CHAT_SYSTEM.format(
        language=payload.language,
        dev_status=_dev_status_str(),
        memory_block=_build_memory_block(),
    )

    s = _settings_ref[0]
    dev_remaining = s.get("dev_chats_remaining", DEV_CHAT_LIMIT)
    using_dev = dev_remaining > 0

    reply = None
    used_engine = ""

    if using_dev:
        for engine, fn in [("claude", _chat_with_claude), ("gemini", _chat_with_gemini)]:
            try:
                reply = fn(system_prompt, list(history))
                used_engine = engine
                break
            except RuntimeError as e:
                if "no_key" in str(e):
                    continue
            except Exception:
                continue
        if reply is not None:
            s["dev_chats_remaining"] = max(0, dev_remaining - 1)
            settings_manager.save(s)
    else:
        user_claude = s.get("anthropic_key", "").strip()
        user_gemini = s.get("gemini_key", "").strip()
        if user_claude:
            os.environ["ANTHROPIC_API_KEY_BAEPO"] = user_claude
        if user_gemini:
            os.environ["GEMINI_API_KEY"] = user_gemini
        for engine, fn in [("claude", _chat_with_claude), ("gemini", _chat_with_gemini)]:
            try:
                reply = fn(system_prompt, list(history))
                used_engine = engine
                break
            except RuntimeError as e:
                if "no_key" in str(e):
                    continue
            except Exception:
                continue

    if reply is None:
        history.pop()
        if not using_dev and not s.get("anthropic_key") and not s.get("gemini_key"):
            return JSONResponse(
                {"error": "무료 체험이 종료되었습니다. 설정 → API 키에 본인의 API 키를 입력하면 계속 사용하실 수 있습니다."},
                status_code=503,
            )
        return JSONResponse(
            {"error": "AI 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요."},
            status_code=503,
        )

    # ── AI 마커 파싱: <<전달확인>> ─────────────────────────────────────
    needs_confirm = FORWARD_MARKER in reply
    reply_clean = reply.replace(FORWARD_MARKER, "").strip()

    if needs_confirm:
        _pending_forward[sid] = {
            "ts": ts_now,
            "session": sid,
            "message": payload.message,
        }
        reply_clean += "\n\n이 내용을 개발자에게 전달할까요? (네 / 아니오)"

    history.append({"role": "assistant", "content": reply_clean})
    log_entry = {"ts": ts_now, "session": sid, "role": "assistant",
                 "message": reply_clean, "engine": used_engine}
    _append_daily_log(log_entry)
    _append_chat_log(log_entry)

    # 일별 로그가 임계값 초과 시 백그라운드 요약
    def _ai_summarize(sys_p, msgs):
        for _, fn in [("claude", _chat_with_claude), ("gemini", _chat_with_gemini)]:
            try:
                return fn(sys_p, msgs)
            except Exception:
                continue
        return ""
    _maybe_summarize_async(_ai_summarize, list(history))

    # 키워드 직접 트리거 (기존 호환)
    keyword_forward = any(kw in payload.message for kw in ["전달해줘", "개발자에게", "전달해", "건의"])
    forward_triggered = keyword_forward and not needs_confirm
    if forward_triggered:
        fwd_entry = {"ts": ts_now, "session": sid, "message": payload.message, "mode": "chatbot"}
        _forwarded_log.append(fwd_entry)
        _forward_to_lina_async(fwd_entry)

    return {
        "reply": reply_clean,
        "forwarded": forward_triggered,
        "engine": used_engine,
        "dev_remaining": s.get("dev_chats_remaining", 0),
    }


@app.get("/api/chat/forwarded")
async def api_chat_forwarded():
    return _forwarded_log


@app.get("/api/chat/memory")
async def api_chat_memory():
    return _load_user_memory()


@app.delete("/api/chat/memory")
async def api_chat_memory_reset():
    _save_user_memory({"last_updated": "", "summary": "", "raw_count": 0})
    return {"ok": True}


# ── Settings ───────────────────────────────────────────────────────────────

@app.get("/api/settings")
async def api_settings_get():
    s = dict(_settings_ref[0])
    s.pop("extension_key", None)
    return s


class SettingsPatch(BaseModel):
    sleep_mode: Optional[str] = None
    wake_chrome_url: Optional[str] = None
    wake_shortcut_name: Optional[str] = None
    game_setting_enabled: Optional[bool] = None
    game_chrome_url: Optional[str] = None
    game_shortcut_name: Optional[str] = None
    default_wake_mode: Optional[str] = None
    user_name: Optional[str] = None
    anthropic_key: Optional[str] = None
    gemini_key: Optional[str] = None
    first_chat_done: Optional[bool] = None


@app.post("/api/settings")
async def api_settings_patch(payload: SettingsPatch):
    s = _settings_ref[0]
    data = payload.model_dump(exclude_none=True)
    s.update(data)
    # API 키 변경 시 즉시 env 반영
    if "anthropic_key" in data:
        os.environ["ANTHROPIC_API_KEY_BAEPO"] = data["anthropic_key"]
    if "gemini_key" in data:
        os.environ["GEMINI_API_KEY"] = data["gemini_key"]
    settings_manager.save(s)
    return {"ok": True}


# ── Utils ──────────────────────────────────────────────────────────────────

def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def get_local_ip() -> str:
    return _local_ip()


def start_server(settings: dict, host: str = "0.0.0.0", port: int = 8766):
    set_settings_ref(settings)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    return server
