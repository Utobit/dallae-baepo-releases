# DallaePC Agent — 배포 로드맵

## 현재 배포 상태 (v1.0.4 APK / v0.1.3 EXE)

### 구성
- **DallaePC.exe** — Windows PC 에이전트 (포트 8766, pywebview UI)
- **DallaePC.apk** — Android 모바일 컨트롤러 (Flutter)
- **utobit.org** — Netlify 배포 랜딩페이지 (이 레포 자동 연동)

### 현재 기능
- 취침 / 기상 모드 (크롬 URL, 바탕화면 바로가기, 게임 세팅)
- 볼륨 조절 / 음소거
- AI 챗봇 (Claude 기반, 채팅/신고 모드)
- 채팅 기억 (일별 요약, 서버 로컬 저장)
- AI 판단 전달 — <<전달확인>> 마커 + 재확인 후 AWS 릴레이
- 수면 기록 (달력 + 로그)
- OTA 자동업데이트 (EXE/APK 모두)
- Android 홈 위젯 (취침/기상)
- QR 스캔 연결
- 달래 아이콘 (앱/EXE)

### 배포 구조
```
dallae-baepo-releases (GitHub)
├── DallaePC.exe       — PC 에이전트 (Windows)
├── DallaePC.apk       — 모바일 앱 (Android)
├── update.json        — OTA 버전 정보
├── index.html         — 랜딩페이지 (Netlify → utobit.org)
└── ROADMAP.md         — 이 파일
```

### 다운로드 URL
- EXE: `https://github.com/Utobit/dallae-baepo-releases/raw/main/DallaePC.exe`
- APK: `https://github.com/Utobit/dallae-baepo-releases/raw/main/DallaePC.apk`

### 빌드 환경
- PC EXE: `D:\Dev\LinaAI\subprojects\dallae_baepo\app`
  - **반드시 `.venv\Scripts\pyinstaller.exe baepo.spec` 사용** (global Python 사용 시 webview 누락)
  - 빌드 후 `--distpath dist_tempX` → releases 폴더로 복사
- APK: `D:\Dev\LinaAI\subprojects\dallae_baepo\mobile\baepo_mobile`
  - `flutter build apk --release`
  - 버전 변경 시 `pubspec.yaml`, `lib/services/api_service.dart` (_currentApkVersion), `update.json` 동시 수정

---

## 향후 업데이트 계획

### P0 — 다음 배포 묶음
- [ ] **Android 홈 위젯** — 취침/기상 버튼 (현재 진행 중)

### P1 — 기능 확장
1. **외국어 지원** — 홈페이지(index.html), PC UI(baepo_ui.py), 앱 다국어
2. **채팅 봇 상대 추가** — 달래 외 다른 캐릭터/페르소나
3. **달래 성우 고용** — TTS 음성 교체
4. **PC 환경 테스트 기능** — 연결 상태, 네트워크, 사양 확인
5. **카카오톡 챗봇** — PC 설정 안내, 원격 관리 도우미
6. **앱 자체 기능 강화**
   - 알림 (푸시 / 로컬)
   - 홈 위젯 확장 (볼륨, 상태 표시)
   - 채팅 내보내기 / 공유

### P2 — 인프라
- GitHub Releases로 바이너리 이관 (50MB 경고 해소)
- 코드 서명 (Windows SmartScreen 경고 제거)
- iOS 버전 검토
