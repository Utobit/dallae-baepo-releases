# DallaePC Agent — 배포 로드맵

## 현재 배포 상태 (v1.0.6 APK / v0.1.3 EXE)

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
1. **앱 UI 다국어 지원** *(지원예정 — 현재 한국어만)* — 홈페이지·PC UI·앱 텍스트 번역. AI 챗봇은 해당 언어로 질문하면 해당 언어로 답하므로 별도 설정 불필요. 구글 플레이 정식 배포 시 진행.
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
- **달래PC 창 단축키** — 전역 핫키로 언제든 창 앞으로 소환

---

## 장기 확장 플랜 (Dallae Specialist Modules)

> DallaePC를 기반으로 도메인별 전문 어시스턴트 모듈로 확장하는 장기 계획.
> 각 모듈은 별도 다운로드 (커스텀 패키지) 또는 EXE 내 옵션 활성화 방식으로 제공 예정.

---

### 🎮 Dallae Game Assistant
게임 실행 중 유저 플레이 데이터를 분석해 전문 피드백 제공.

- APM, FPS, 집중도·느슨도, 맵리딩 능력 등 게임별 능력치 데이터화
- 세션별 기록 → 장기 성장 곡선 추적
- 게임 특화 전문 육성 프로그램 자동 생성
- AI 피드백: "이 구간 반응속도가 평균보다 낮아요" 수준의 구체적 분석
- 구현 방향: 화면 캡처 + OCR / 게임 API 연동 / 키입력 타이밍 분석

---

### 🎨 Dallae Design Assistant
PC 내 디자인 파일(이미지·PSD 등)을 한곳에서 관리하는 폴더 컨트롤 패널.

**핵심 기능:**
- 유저가 직접 감시 폴더 등록 (C드라이브·D드라이브·바탕화면 등 분산 위치 통합)
- **최근 수정 이미지·PSD 파일을 날짜 역순으로 리스트업** (탐색기 없이 한눈에)
- 썸네일 미리보기 (jpg/png/psd)
- 더블클릭 → 파일 직접 열기 / 탐색기에서 위치 열기
- 파일·폴더 이동 지원 (리모컨처럼 상주하며 정리 보조)
- 구현 방향: Python pathlib + Pillow 썸네일, psd-tools PSD 미리보기, os.startfile()

**구현 가능 여부: ✅ 충분히 가능**
→ 별도 문서 참고 (아래 기술 검토 섹션)

---

### 🎵 Dallae Musician
음악 작업 환경 특화 어시스턴트. (기획 중)

- DAW 연동 (Ableton, FL Studio 등) 작업 흐름 지원
- 샘플·프로젝트 파일 관리 (Design Assistant와 동일 구조)
- 작업 시간 기록 및 집중도 분석

---

### 🏠 Dallae Home
스마트홈 + PC를 잇는 생활 밀착형 어시스턴트. (기획 중)

- 조명·가전 제어 연동 (IoT API)
- 루틴 자동화 (취침 시 조명 끄기 등 현재 기능 확장)
- 날씨·일정·할 일 통합 대시보드

---

### 🔧 Dallae Custom Mode
비개발자가 Cursor + Claude 워크플로우로 DallaePC를 직접 커스터마이징.

- 커스텀 다운로드 패키지: `CURSOR_RULES.md` + `HARNESS.md` + 소스 스켈레톤 포함
- 유저가 Cursor에서 폴더 열고 "이렇게 바꿔줘" → Cursor가 규칙 읽고 커스텀 파일만 수정
- EXE가 런타임에 `custom/` 폴더 탐지 → 동적 로드
- 서버 접근은 개발자 전용, 커스텀 레이어는 완전 개방

---

## 기술 검토: Dallae Design Assistant 구현 방안

```
[유저 등록 폴더]
  C:\Users\User\Desktop\Pinterest\
  D:\Design\Clover\
  D:\References\
  ...
        ↓ pathlib.rglob("*")
[파일 수집 + 필터]
  확장자: .jpg .jpeg .png .gif .webp .psd .ai .svg
  정렬: 수정일시(mtime) 역순
        ↓
[썸네일 생성]
  raster(jpg/png): Pillow → 200x200 thumb (캐시)
  PSD: psd-tools → 합성 이미지 추출 → Pillow thumb
  AI/SVG: 아이콘 placeholder
        ↓
[PC UI (pywebview)]
  그리드 뷰: 썸네일 + 파일명 + 수정일
  더블클릭: os.startfile(path)
  우클릭: 탐색기에서 열기 / 이동 / 이름 변경
  검색: 파일명 필터
```

추가 가능: 모바일 앱에서도 썸네일 목록 조회 (PC API 경유)
