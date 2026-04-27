"""
DallaePC Agent UI — pywebview + FastAPI (port 8766)
"""
from __future__ import annotations
import base64, os, sys, threading
from pathlib import Path

_WV_ERROR = None
try:
    import webview
    _WV = True
except Exception as e:
    _WV = False
    _WV_ERROR = str(e)

try:
    from PIL import Image
    import pystray
    _TRAY = True
except ImportError:
    _TRAY = False

import baepo_server, settings_manager, updater

VERSION = updater.CURRENT_VERSION


def _icon_path():
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return Path(base) / "dallae_icon.png"

ICON_PATH = _icon_path()


def _icon_b64() -> str:
    try:
        with open(ICON_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


# ── JS Bridge ─────────────────────────────────────────────────────────────

class JsApi:
    def __init__(self):
        self._window = None
        self._tray   = None

    def hide(self):
        if self._window:
            self._window.hide()

    def show(self):
        if self._window:
            self._window.show()

    def quit(self):
        if self._tray:
            self._tray.stop()
        if self._window:
            self._window.destroy()


# ── HTML ──────────────────────────────────────────────────────────────────

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"/>
<title>Dallae PC Agent</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0f172a;--card:#111827;--card2:#1e2433;
  --accent:#4f46e5;--accent2:#6366f1;
  --text:#e5e7eb;--muted:#6b7280;--border:#1e2433;
  --green:#22c55e;--chat-ai:#1e2433;--chat-me:#312e81;
}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--text);
  font-family:'Malgun Gothic','Segoe UI',sans-serif;font-size:14px;}
/* ── LAYOUT ── */
#app{display:flex;flex-direction:column;height:100vh;}
/* ── HEADER ── */
#header{background:var(--card);border-bottom:1px solid var(--border);
  padding:0 14px;height:52px;display:flex;align-items:center;gap:8px;flex-shrink:0;}
#header img{width:26px;height:26px;border-radius:6px;}
#app-name{font-weight:700;font-size:0.95rem;margin-right:4px;}
#status-dot{font-size:10px;color:var(--muted);}
#status-text{font-size:0.8rem;color:var(--muted);}
#header-right{margin-left:auto;display:flex;align-items:center;gap:6px;}
.icon-btn{background:none;border:none;color:var(--muted);cursor:pointer;
  font-size:1.1rem;padding:6px;border-radius:6px;transition:color .15s,background .15s;}
.icon-btn:hover{color:var(--text);background:var(--card2);}
/* mode toggle */
#mode-toggle{display:flex;background:var(--card2);border-radius:8px;padding:2px;gap:2px;}
.mtbtn{background:none;border:none;color:var(--muted);font-family:inherit;
  font-size:0.75rem;font-weight:600;padding:4px 10px;border-radius:6px;cursor:pointer;
  transition:all .15s;white-space:nowrap;}
.mtbtn.active{background:var(--accent);color:#fff;}
/* ── UPDATE BANNER ── */
#update-banner{display:none;background:#4c1d95;padding:6px 14px;
  font-size:0.82rem;color:#c4b5fd;align-items:center;gap:10px;flex-shrink:0;}
#update-banner.show{display:flex;}
#update-btn{background:#7c3aed;border:none;color:#fff;font-size:0.78rem;
  font-weight:600;padding:3px 10px;border-radius:6px;cursor:pointer;margin-left:auto;}
/* ── CONNECTION STRIP ── */
#conn-strip{padding:5px 16px;border-bottom:1px solid var(--border);flex-shrink:0;
  display:flex;flex-direction:column;gap:2px;}
#conn-ip{font-size:0.8rem;color:var(--muted);}
#conn-mode-status{font-size:0.73rem;color:#374151;}
/* ── MESSAGES ── */
#messages{flex:1;overflow-y:auto;padding:14px 14px 8px;
  display:flex;flex-direction:column;gap:10px;}
.msg-row{display:flex;align-items:flex-end;gap:6px;}
.msg-row.ai{justify-content:flex-start;}
.msg-row.me{justify-content:flex-end;}
.msg-name{font-size:0.7rem;color:var(--muted);flex-shrink:0;padding-bottom:2px;}
.bubble{max-width:76%;padding:9px 13px;border-radius:14px;
  font-size:0.88rem;line-height:1.55;white-space:pre-wrap;word-break:break-word;
  user-select:text;cursor:text;}
.msg-row.ai .bubble{background:var(--chat-ai);border-bottom-left-radius:3px;}
.msg-row.me .bubble{background:var(--chat-me);border-bottom-right-radius:3px;}
.msg-time{font-size:0.65rem;color:#374151;align-self:flex-end;flex-shrink:0;padding-bottom:3px;}
.typing{color:var(--muted);font-size:0.8rem;font-style:italic;padding:4px 8px;}
/* ── QUICKBAR ── */
#quickbar{border-top:1px solid var(--border);background:var(--card);
  padding:8px 12px;display:flex;gap:6px;flex-shrink:0;}
.qbtn{background:var(--card2);border:none;color:var(--text);cursor:pointer;
  font-family:inherit;font-size:0.82rem;padding:7px 14px;border-radius:8px;
  transition:background .15s,color .15s;white-space:nowrap;}
.qbtn:hover{background:var(--accent);color:#fff;}
.qbtn.active{background:var(--accent);color:#fff;}
#tray-btn{margin-left:auto;color:var(--muted);}
#tray-btn:hover{color:var(--text);background:var(--card2);}
/* ── INPUT ── */
#input-area{background:var(--card);padding:10px 12px;
  display:flex;gap:8px;flex-shrink:0;border-top:1px solid var(--border);}
#msg-input{flex:1;background:var(--card2);border:none;border-radius:10px;
  color:var(--text);font-family:'Malgun Gothic','Segoe UI',sans-serif;
  font-size:0.88rem;padding:9px 13px;outline:none;resize:none;
  min-height:40px;max-height:120px;line-height:1.45;}
#msg-input::placeholder{color:#4b5563;}
#send-btn{background:var(--accent);border:none;border-radius:10px;color:#fff;
  font-family:inherit;font-size:0.85rem;font-weight:600;padding:0 18px;
  cursor:pointer;transition:opacity .15s;flex-shrink:0;}
#send-btn:hover{opacity:.85;}
#send-btn:disabled{opacity:.4;cursor:default;}
/* ── SETTINGS OVERLAY ── */
#settings-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);
  z-index:100;backdrop-filter:blur(4px);}
#settings-overlay.open{display:flex;align-items:flex-start;justify-content:flex-end;}
#settings-panel{background:var(--card);width:340px;height:100%;overflow-y:auto;
  border-left:1px solid var(--border);display:flex;flex-direction:column;}
#settings-header{padding:16px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
#settings-header h2{font-size:0.9rem;font-weight:700;}
#settings-close{background:none;border:none;color:var(--muted);font-size:1.1rem;
  cursor:pointer;padding:4px;}
#settings-close:hover{color:var(--text);}
/* TABS */
.tabs{display:flex;border-bottom:1px solid var(--border);flex-shrink:0;}
.tab{flex:1;padding:10px;background:none;border:none;color:var(--muted);
  font-family:inherit;font-size:0.78rem;cursor:pointer;transition:all .15s;
  border-bottom:2px solid transparent;}
.tab.active{color:var(--text);border-bottom-color:var(--accent);}
.tab-pane{display:none;padding:14px 16px;flex:1;}
.tab-pane.active{display:block;}
/* FORM */
.form-group{margin-bottom:14px;}
.form-label{font-size:0.75rem;color:var(--muted);margin-bottom:5px;display:block;}
.form-input{width:100%;background:var(--card2);border:none;border-radius:8px;
  color:var(--text);font-family:inherit;font-size:0.85rem;
  padding:8px 11px;outline:none;}
.form-input:focus{box-shadow:0 0 0 2px var(--accent);}
.radio-group{display:flex;flex-direction:column;gap:6px;margin:6px 0;}
.radio-row{display:flex;align-items:center;gap:8px;cursor:pointer;
  font-size:0.85rem;color:var(--text);}
.radio-row input{accent-color:var(--accent);}
.check-row{display:flex;align-items:center;gap:8px;cursor:pointer;
  font-size:0.85rem;color:var(--text);margin-bottom:6px;}
.check-row input{accent-color:var(--accent);}
.section-label{font-size:0.72rem;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;margin:14px 0 8px;}
.divider{border:none;border-top:1px solid var(--border);margin:12px 0;}
.save-btn{background:var(--accent);border:none;border-radius:8px;color:#fff;
  font-family:inherit;font-size:0.85rem;font-weight:600;padding:9px 20px;
  cursor:pointer;width:100%;margin-top:10px;transition:opacity .15s;}
.save-btn:hover{opacity:.85;}
.info-row{background:var(--card2);border-radius:8px;padding:10px 12px;
  display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}
.info-key{font-size:0.78rem;color:var(--muted);}
.info-val{font-size:0.85rem;font-weight:600;}
.hint{font-size:0.72rem;color:#374151;margin-top:4px;}
/* ── SCROLLBAR ── */
#messages::-webkit-scrollbar{width:4px;}
#messages::-webkit-scrollbar-track{background:transparent;}
#messages::-webkit-scrollbar-thumb{background:var(--card2);border-radius:4px;}
#settings-panel::-webkit-scrollbar{width:4px;}
#settings-panel::-webkit-scrollbar-thumb{background:var(--card2);border-radius:4px;}
</style>
</head>
<body>
<div id="app">

  <!-- Header -->
  <div id="header">
    <img id="logo" src="data:image/png;base64,[[ICON_B64]]" alt=""
         onerror="this.style.display='none'"/>
    <span id="app-name">Dallae PC Agent</span>
    <span style="font-size:0.7rem;color:#374151;margin-right:2px;">v[[VERSION]]</span>
    <span id="status-dot">●</span>
    <span id="status-text">연결 중...</span>
    <div id="header-right">
      <div id="mode-toggle">
        <button class="mtbtn active" id="mtbtn-chatbot" onclick="setMode('chatbot')">챗봇</button>
        <button class="mtbtn"        id="mtbtn-report"  onclick="setMode('report')">신고</button>
      </div>
      <button class="icon-btn" title="설정" onclick="openSettings()">⚙</button>
    </div>
  </div>

  <!-- Update banner -->
  <div id="update-banner">
    <span id="update-text"></span>
    <button id="update-btn" onclick="doUpdate()">업데이트</button>
  </div>

  <!-- Connection strip -->
  <div id="conn-strip">
    <span id="conn-ip"></span>
    <span id="conn-mode-status">알림 : 현재 챗봇모드입니다.</span>
  </div>

  <!-- Messages -->
  <div id="messages"></div>

  <!-- Quick bar -->
  <div id="quickbar">
    <button class="qbtn" id="btn-sleep" onclick="doSleep()">🌙 취침</button>
    <button class="qbtn" id="btn-wake"  onclick="doWake()">☀️ 기상</button>
    <button class="qbtn" id="btn-mute"  onclick="toggleMute()">🔊 음소거</button>
    <button class="qbtn" id="tray-btn"  onclick="pywebview.api.hide()">트레이</button>
  </div>

  <!-- Input -->
  <div id="input-area">
    <textarea id="msg-input" placeholder="메시지를 입력하세요..." rows="1"></textarea>
    <button id="send-btn" onclick="sendChat()">전송</button>
  </div>

</div><!-- #app -->

<!-- Settings -->
<div id="settings-overlay" onclick="overlayClick(event)">
  <div id="settings-panel">
    <div id="settings-header">
      <h2>설정</h2>
      <button id="settings-close" onclick="closeSettings()">✕</button>
    </div>
    <div class="tabs">
      <button class="tab active" onclick="switchTab(0)">기상·취침</button>
      <button class="tab"        onclick="switchTab(1)">API 키</button>
      <button class="tab"        onclick="switchTab(2)">연동 정보</button>
    </div>

    <!-- Tab 0: 기상·취침 -->
    <div class="tab-pane active" id="tab-0">
      <div class="section-label">기상 모드</div>
      <div class="radio-group">
        <label class="radio-row">
          <input type="radio" name="wake_mode" value="normal" checked> 일반 기상
        </label>
        <label class="radio-row">
          <input type="radio" name="wake_mode" value="game"> 게임 세팅
        </label>
      </div>
      <hr class="divider"/>
      <div class="section-label">취침 옵션</div>
      <div class="radio-group">
        <label class="radio-row">
          <input type="radio" name="sleep_mode" value="keep_windows" checked> 창 유지 (기본)
        </label>
        <label class="radio-row">
          <input type="radio" name="sleep_mode" value="close_all"> 모든 창 닫기
        </label>
      </div>
      <hr class="divider"/>
      <div class="section-label">기상 시 실행</div>
      <label class="check-row">
        <input type="checkbox" id="use-chrome"> Chrome 기상 실행
      </label>
      <div id="chrome-fields" style="display:none">
        <div class="form-group">
          <label class="form-label">사이트 URL</label>
          <input class="form-input" id="wake-chrome-url" type="text" placeholder="https://..."/>
        </div>
        <div class="form-group">
          <label class="form-label">바탕화면 바로가기 이름 (선택)</label>
          <input class="form-input" id="wake-shortcut" type="text"/>
        </div>
      </div>
      <label class="check-row">
        <input type="checkbox" id="use-game"> 게임 세팅 사용
      </label>
      <div id="game-fields" style="display:none">
        <div class="form-group">
          <label class="form-label">전적검색 URL</label>
          <input class="form-input" id="game-url" type="text" placeholder="https://www.op.gg"/>
        </div>
        <div class="form-group">
          <label class="form-label">게임 바로가기 이름</label>
          <input class="form-input" id="game-shortcut" type="text"/>
        </div>
        <span class="hint">순서: 전적검색 → 게임 실행 (고정)</span>
      </div>
      <button class="save-btn" onclick="saveWakeSettings()">저장</button>
    </div>

    <!-- Tab 1: API 키 -->
    <div class="tab-pane" id="tab-1">
      <div class="form-group">
        <label class="form-label">Claude (Anthropic)</label>
        <input class="form-input" id="api-claude" type="password" placeholder="sk-ant-..."/>
      </div>
      <div class="form-group">
        <label class="form-label">Gemini (Google) — 폴백</label>
        <input class="form-input" id="api-gemini" type="password" placeholder="AIza..."/>
      </div>
      <span class="hint">저장 후 즉시 적용. 재실행 불필요.</span>
      <button class="save-btn" style="margin-top:16px" onclick="saveApiKeys()">저장</button>
    </div>

    <!-- Tab 2: 연동 정보 -->
    <div class="tab-pane" id="tab-2">
      <div class="section-label">사용자 이름</div>
      <div class="form-group">
        <input class="form-input" id="user-name" type="text" placeholder="이름 입력 시 채팅 인사에 표시됩니다"/>
        <span class="hint">저장 후 다음 실행부터 반영됩니다.</span>
      </div>
      <button class="save-btn" onclick="saveName()">이름 저장</button>
      <hr class="divider"/>
      <div class="section-label">채팅 응답 언어</div>
      <div class="form-group">
        <select class="form-input" id="chat-language" onchange="setLanguage(this.value)">
          <option value="한국어">한국어</option>
          <option value="English">English</option>
          <option value="日本語">日本語</option>
          <option value="中文">中文</option>
          <option value="Français">Français</option>
          <option value="Tiếng Việt">Tiếng Việt</option>
        </select>
      </div>
      <hr class="divider"/>
      <div class="section-label">모바일 앱 연결 정보</div>
      <div class="info-row"><span class="info-key">PC IP</span><span class="info-val" id="info-ip">-</span></div>
      <div class="info-row"><span class="info-key">포트</span><span class="info-val">8766</span></div>
      <div class="info-row"><span class="info-key">UUID</span><span class="info-val" id="info-uuid">-</span></div>
    </div>

  </div><!-- settings-panel -->
</div><!-- settings-overlay -->

<script>
const API = 'http://localhost:8766';
let SID          = 'wv_' + Date.now();
let loading      = false;
let isMuted      = false;
let updateUrl    = null;
let settings     = {};
let chatMode     = 'chatbot';
let chatLanguage = '한국어';

// ── Fetch helpers ──────────────────────────────────────────────────────────
async function get(path) {
  const r = await fetch(API + path);
  return r.ok ? r.json() : null;
}
async function post(path, body) {
  const r = await fetch(API + path, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  return r.ok ? r.json() : null;
}

// ── State polling ──────────────────────────────────────────────────────────
async function pollState() {
  const s = await get('/api/state');
  if (!s) return;
  isMuted = s.muted;
  updateStatusUI(s.sleeping, s.muted);
}
function updateStatusUI(sleeping, muted) {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  if (sleeping) {
    dot.style.color = '#60a5fa'; text.style.color = '#60a5fa';
    text.textContent = '취침 중';
  } else {
    dot.style.color = '#22c55e'; text.style.color = '#22c55e';
    text.textContent = '활성';
  }
  const muteBtn = document.getElementById('btn-mute');
  muteBtn.textContent = muted ? '🔇 음소거 중' : '🔊 음소거';
  muteBtn.classList.toggle('active', muted);
}

// ── Mode / Language ────────────────────────────────────────────────────────
function setMode(m) {
  chatMode = m;
  document.getElementById('mtbtn-chatbot').classList.toggle('active', m === 'chatbot');
  document.getElementById('mtbtn-report').classList.toggle('active',  m === 'report');
  const statusEl = document.getElementById('conn-mode-status');
  if (m === 'report') {
    statusEl.textContent = '알림 : 현재 신고모드입니다. 요청사항이나 버그를 전달해주세요.';
    statusEl.style.color = '#f59e0b';
  } else {
    statusEl.textContent = '알림 : 현재 챗봇모드입니다.';
    statusEl.style.color = '#374151';
  }
}
function setLanguage(lang) {
  chatLanguage = lang;
}

// ── Quick actions ──────────────────────────────────────────────────────────
async function doSleep() {
  await post('/api/sleep', {});
  setTimeout(pollState, 500);
}
async function doWake() {
  const mode = settings.default_wake_mode || 'normal';
  await post('/api/wake', {mode});
  setTimeout(pollState, 2500);
}
async function toggleMute() {
  await post(isMuted ? '/api/unmute' : '/api/mute', {});
  await pollState();
}

// ── Chat ───────────────────────────────────────────────────────────────────
function _nowTime() {
  const d = new Date();
  return d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
}
function addMsg(text, role) {
  const msgs = document.getElementById('messages');
  const row  = document.createElement('div');
  row.className = 'msg-row ' + role;

  const name   = document.createElement('span');
  name.className = 'msg-name';
  name.textContent = role === 'ai' ? '달래' : '나';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  const ts = document.createElement('span');
  ts.className = 'msg-time';
  ts.textContent = _nowTime();

  if (role === 'ai') {
    row.appendChild(name);
    row.appendChild(bubble);
    row.appendChild(ts);
  } else {
    row.appendChild(ts);
    row.appendChild(bubble);
    row.appendChild(name);
  }

  msgs.appendChild(row);
  msgs.scrollTop = msgs.scrollHeight;
}

function addTyping() {
  const msgs = document.getElementById('messages');
  const el   = document.createElement('div');
  el.className = 'typing'; el.id = 'typing-indicator';
  el.textContent = '달래가 입력 중...';
  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
  return el;
}

async function sendChat() {
  const input = document.getElementById('msg-input');
  const text  = input.value.trim();
  if (!text || loading) return;
  input.value = ''; autoResize(input);
  addMsg(text, 'me');
  loading = true;
  document.getElementById('send-btn').disabled = true;
  const typing = addTyping();
  try {
    const res = await fetch(API + '/api/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({message: text, session_id: SID, mode: chatMode, language: chatLanguage})
    });
    typing.remove();
    if (res.ok) {
      const data = await res.json();
      if (data.reply) addMsg(data.reply, 'ai');
    } else {
      const err = await res.json().catch(() => ({}));
      addMsg(err.error || 'AI 응답 오류가 발생했습니다.', 'ai');
    }
  } catch(e) {
    typing.remove();
    addMsg('서버 연결 오류. 잠시 후 다시 시도하세요.', 'ai');
  }
  loading = false;
  document.getElementById('send-btn').disabled = false;
  input.focus();
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

// ── Settings ───────────────────────────────────────────────────────────────
function openSettings() {
  document.getElementById('settings-overlay').classList.add('open');
  loadSettingsIntoForm();
}
function closeSettings() {
  document.getElementById('settings-overlay').classList.remove('open');
}
function overlayClick(e) {
  if (e.target === document.getElementById('settings-overlay')) closeSettings();
}
function switchTab(idx) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', i===idx));
  document.querySelectorAll('.tab-pane').forEach((p,i) => p.classList.toggle('active', i===idx));
}
function loadSettingsIntoForm() {
  const s = settings;
  // wake mode
  document.querySelectorAll('input[name="wake_mode"]').forEach(r => {
    r.checked = (r.value === (s.default_wake_mode || 'normal'));
  });
  // sleep mode
  document.querySelectorAll('input[name="sleep_mode"]').forEach(r => {
    r.checked = (r.value === (s.sleep_mode || 'keep_windows'));
  });
  // chrome
  const useChrome = !!s.wake_chrome_url;
  document.getElementById('use-chrome').checked = useChrome;
  document.getElementById('chrome-fields').style.display = useChrome ? 'block' : 'none';
  document.getElementById('wake-chrome-url').value = s.wake_chrome_url || '';
  document.getElementById('wake-shortcut').value   = s.wake_shortcut_name || '';
  // game
  const useGame = !!s.game_setting_enabled;
  document.getElementById('use-game').checked = useGame;
  document.getElementById('game-fields').style.display = useGame ? 'block' : 'none';
  document.getElementById('game-url').value      = s.game_chrome_url || 'https://www.op.gg';
  document.getElementById('game-shortcut').value = s.game_shortcut_name || '';
  // api keys (show if set)
  document.getElementById('api-claude').value = s.anthropic_key ? '••••••••' : '';
  document.getElementById('api-gemini').value = s.gemini_key    ? '••••••••' : '';
  // user name
  document.getElementById('user-name').value = s.user_name || '';
  // language
  document.getElementById('chat-language').value = chatLanguage;
  // info
  document.getElementById('info-ip').textContent   = s._ip || '-';
  document.getElementById('info-uuid').textContent = s.uuid ? s.uuid.substring(0,16)+'...' : '-';
}

async function saveWakeSettings() {
  const wakeModeEl = document.querySelector('input[name="wake_mode"]:checked');
  const sleepModeEl = document.querySelector('input[name="sleep_mode"]:checked');
  const useChrome = document.getElementById('use-chrome').checked;
  const useGame   = document.getElementById('use-game').checked;
  await post('/api/settings', {
    default_wake_mode:   wakeModeEl  ? wakeModeEl.value  : 'normal',
    sleep_mode:          sleepModeEl ? sleepModeEl.value : 'keep_windows',
    wake_chrome_url:     useChrome ? document.getElementById('wake-chrome-url').value.trim() : '',
    wake_shortcut_name:  document.getElementById('wake-shortcut').value.trim(),
    game_setting_enabled: useGame,
    game_chrome_url:     document.getElementById('game-url').value.trim(),
    game_shortcut_name:  document.getElementById('game-shortcut').value.trim(),
  });
  await reloadSettings();
  alert('저장되었습니다.');
}

async function saveApiKeys() {
  const c = document.getElementById('api-claude').value.trim();
  const g = document.getElementById('api-gemini').value.trim();
  const body = {};
  if (c && c !== '••••••••') body.anthropic_key = c;
  if (g && g !== '••••••••') body.gemini_key = g;
  if (Object.keys(body).length) {
    await post('/api/settings', body);
    await reloadSettings();
  }
  alert('API 키가 저장되었습니다.');
}

async function saveName() {
  const name = document.getElementById('user-name').value.trim();
  await post('/api/settings', {user_name: name});
  await reloadSettings();
  alert('저장되었습니다. 다음 실행부터 반영됩니다.');
}

// ── Update ─────────────────────────────────────────────────────────────────
async function doUpdate() {
  if (!updateUrl) return;
  const btn = document.getElementById('update-btn');
  btn.disabled = true;
  btn.textContent = '다운로드 중...';
  const res = await post('/api/update/install', {url: updateUrl});
  if (res && res.ok) {
    btn.textContent = '설치 중... 잠시 후 재시작됩니다';
  } else {
    btn.textContent = '실패 — 재시도';
    btn.disabled = false;
  }
}

// ── Init ───────────────────────────────────────────────────────────────────
async function reloadSettings() {
  const s = await get('/api/settings');
  if (s) settings = s;
}

function showGreeting() {
  const s    = settings;
  const name = s.user_name ? s.user_name + '님' : '';
  const isFirst = !s.first_chat_done;
  if (isFirst) {
    const greeting = name
      ? name + ', 안녕하세요!\\n달래 PC Agent입니다.'
      : '안녕하세요! 달래 PC Agent입니다.';
    addMsg(greeting, 'ai');
    addMsg(
      '달래 PC Agent를 이용해주셔서 감사합니다.\\n' +
      '본 챗봇은 Claude Sonnet 기반으로 작동하며,\\n' +
      '이 안내는 최초 1회만 표시됩니다.\\n\\n' +
      '문의사항은 프로그램 우상단 신고버튼을 사용하시면 개발자에 자동으로 전달됩니다.',
      'ai'
    );
    post('/api/settings', {first_chat_done: true});
  } else {
    addMsg('DallaePC Agent 정상 가동중입니다.', 'ai');
  }
}

async function init() {
  // load settings
  await reloadSettings();

  // connection strip
  const localIp = settings._ip || '...';
  document.getElementById('conn-ip').textContent = localIp + ' : 8766';

  // greeting
  showGreeting();

  // chrome/game toggle wiring
  document.getElementById('use-chrome').addEventListener('change', e => {
    document.getElementById('chrome-fields').style.display = e.target.checked ? 'block' : 'none';
  });
  document.getElementById('use-game').addEventListener('change', e => {
    document.getElementById('game-fields').style.display = e.target.checked ? 'block' : 'none';
  });

  // input events
  const input = document.getElementById('msg-input');
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });
  input.addEventListener('input', () => autoResize(input));

  // poll state
  await pollState();
  setInterval(pollState, 5000);

  input.focus();
}

window.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>
"""

# ── App ────────────────────────────────────────────────────────────────────

class BaepoApp:
    def __init__(self):
        self._settings = settings_manager.load()
        self._load_api_keys()
        baepo_server.start_server(self._settings)
        self._window    = None
        self._tray_icon = None
        self._api       = JsApi()
        updater.check_update_async(self._on_update)

    def _load_api_keys(self):
        s = self._settings
        if s.get("anthropic_key") and not os.environ.get("ANTHROPIC_API_KEY_BAEPO"):
            os.environ["ANTHROPIC_API_KEY_BAEPO"] = s["anthropic_key"]
        if s.get("gemini_key") and not os.environ.get("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = s["gemini_key"]

    def _on_update(self, info):
        if info and self._window:
            ver = info.get("version", "")
            url = info.get("url", "")
            js = (
                "document.getElementById('update-banner').classList.add('show');"
                f"document.getElementById('update-text').textContent='새 버전 {ver} 사용 가능';"
                f"updateUrl='{url}';"
            )
            self._window.evaluate_js(js)

    def _start_tray(self):
        if not _TRAY:
            return
        try:
            img = Image.open(ICON_PATH).resize((64, 64))
        except Exception:
            return
        menu = pystray.Menu(
            pystray.MenuItem("열기", lambda: self._window.show() if self._window else None),
            pystray.MenuItem("종료", self._tray_quit),
        )
        self._tray_icon = pystray.Icon("DallaePC", img, "Dallae PC Agent", menu)
        self._api._tray = self._tray_icon
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _tray_quit(self, *_):
        if self._tray_icon:
            self._tray_icon.stop()
        if self._window:
            self._window.destroy()

    def _build_html(self) -> str:
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"

        html = _HTML_TEMPLATE
        html = html.replace("[[ICON_B64]]", _icon_b64())
        html = html.replace("[[VERSION]]", VERSION)
        # IP를 설정에 임시 저장해서 JS에서 /api/settings로 조회 가능하게
        self._settings["_ip"] = ip
        baepo_server.set_settings_ref(self._settings)
        return html

    def run(self):
        if not _WV:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk(); root.withdraw()
            messagebox.showerror(
                "DallaePC — 오류",
                f"UI 모듈(webview) 로드 실패:\n{_WV_ERROR}\n\n"
                "Microsoft WebView2 Runtime을 설치하세요:\n"
                "https://developer.microsoft.com/en-us/microsoft-edge/webview2/"
            )
            root.destroy()
            return

        self._start_tray()
        html = self._build_html()

        win = webview.create_window(
            "Dallae PC Agent",
            html=html,
            js_api=self._api,
            width=500,
            height=740,
            min_size=(420, 580),
            resizable=True,
            background_color="#0f172a",
        )
        self._window     = win
        self._api._window = win

        def on_closing():
            win.hide()
            return False

        win.events.closing += on_closing
        webview.start(debug=False)
