# VibeLign CLI vs GUI 커맨드 비교 분석

## 명령어별 플래그/옵션 현황

### 1. **START** (프로젝트 초기 설정)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 기본 실행 | - | ✓ | 완전 |
| 도구 선택 | `--all-tools` | ✗ | **누락** |
| 특정 도구 지정 | `--tools <list>` | ✗ | **누락** |
| 강제 재생성 | `--force` | ✗ | **누락** |
| 빠른 시작 | `--quickstart` | ✗ | **누락** |

---

### 2. **CHECKPOINT** (게임 세이브)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 메시지 저장 | `message` | ✓ | 완전 |
| JSON 출력 | `--json` | ✗ | **누락** |
| 목록 조회 | `"list"` | ✗ | **누락** |

---

### 3. **UNDO** (되돌리기)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 최근 저장으로 복원 | - | ✓ | 완전 |
| 목록 선택 후 복원 | `--list` | ✓ | 완전 |
| ID로 직접 복원 | `--checkpoint-id <ID>` | ✗ | **누락** |
| 확인 생략 | `--force` | ✗ | **누락** |
| JSON 출력 | `--json` | ✗ | **누락** |

---

### 4. **DOCTOR** (건강 검진)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 기본 점검 | - | ✓ | 완전 |
| 꼼꼼한 검사 | `--strict` | ✗ | **누락** |
| 자세한 설명 | `--detailed` | ✗ | **누락** |
| 고치는 방법 | `--fix-hints` | ✗ | **누락** |
| 자동 앵커 추가 | `--fix` | ✗ | **누락** |
| 리포트 저장 | `--write-report` | ✗ | **누락** |
| 실행 계획 | `--plan` / `--patch` / `--apply` | ✗ | **누락** |
| JSON 출력 | `--json` | ✗ | **누락** |

---

### 5. **GUARD** (AI 작업 검증)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 기본 검사 | - | ✓ | 완전 |
| 꼼꼼한 검사 | `--strict` | ✗ | **누락** |
| 시간 범위 지정 | `--since-minutes <N>` | ✗ | **누락** |
| 리포트 저장 | `--write-report` | ✗ | **누락** |
| JSON 출력 | `--json` | ✗ | **누락** |

---

### 6. **ANCHOR** (안전 구역 표시)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 자동 삽입 | `--auto` | ✓ (기본) | 완전 |
| 추천 받기 | `--suggest` | ✗ | **누락** |
| 검증하기 | `--validate` | ✗ | **누락** |
| 미리 보기 | `--dry-run` | ✗ | **누락** |
| 확장자 필터 | `--only-ext <EXT>` | ✗ | **누락** |
| 의도 등록 | `--set-intent` | ✗ | **누락** |
| 의도 자동 생성 | `--auto-intent` | ✗ | **누락** |
| JSON 출력 | `--json` | ✗ | **누락** |

---

### 7. **SCAN** (코드맵 갱신)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 기본 스캔 | - | ✓ | 완전 |
| 자동 수정 | `--auto` | ✗ | **누락** |

---

### 8. **WATCH** (실시간 감시)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 시작/종료 | - | ✓ | 완전 |
| 꼼꼼 모드 | `--strict` | ✗ | **누락** |
| 로그 저장 | `--write-log` | ✗ | **누락** |
| 감시 간격 설정 | `--debounce-ms <N>` | ✗ | **누락** |

---

### 9. **TRANSFER** (AI 도구 전환)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 기본 생성 | - | ✓ | 완전 |
| 경량 버전 | `--compact` | ✓ | 완전 |
| 전체 포함 | `--full` | ✗ | **누락** |
| Handoff 블록 | `--handoff` | ✓ | 완전 |
| Handoff 자동 생성 | `--no-prompt` | ✓ | `--handoff` 실행 시 자동 적용 |
| Handoff 콘솔 출력 | `--print` | ✗ | **누락** |
| Handoff 요약 직접 지정 | `--session-summary <TEXT>` | ✗ | **누락** |
| 다음 작업 직접 지정 | `--first-next-action <TEXT>` | 부분 | GUI 기본 문구 자동 전달, 사용자 입력 UI 없음 |
| 미리 보기 | `--dry-run` | ✗ | **누락** |
| 파일명 지정 | `--out <FILE>` | ✗ | **누락** |

---

### 10. **PATCH** (안전한 수정 계획)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 수정 계획 생성 | `request` | ✗ | **전체 미구현** |
| AI 분석 | `--ai` | ✗ | **미구현** |
| 미리 보기 | `--preview` | ✗ | **미구현** |
| 리포트 저장 | `--write-report` | ✗ | **미구현** |
| 클립보드 복사 | `--copy` | ✗ | **미구현** |

---

### 11. **PROTECT** (중요 파일 잠금)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 파일 보호 | `file` | ✗ | **전체 미구현** |
| 보호 해제 | `--remove` | ✗ | **미구현** |
| 목록 보기 | `--list` | ✗ | **미구현** |

---

### 12. **SECRETS** (비밀정보 검사)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 검사 | `--staged` | ✗ | **전체 미구현** |
| Hook 설치 | `--install-hook` | ✗ | **미구현** |
| Hook 제거 | `--uninstall-hook` | ✗ | **미구현** |

---

### 13. **EXPLAIN** (변경 내용 설명)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 변경 설명 | - | ✗ | **전체 미구현** |
| AI 분석 | `--ai` | ✗ | **미구현** |
| 시간 범위 | `--since-minutes <N>` | ✗ | **미구현** |
| 리포트 저장 | `--write-report` | ✗ | **미구현** |

---

### 14. **ASK** (파일 설명)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 파일 설명 | `file` | ✗ | **전체 미구현** |
| 특정 질문 | `question` | ✗ | **미구현** |
| 파일로 저장 | `--write` | ✗ | **미구현** |

---

### 15. **CONFIG** (API 키 설정)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| API 키 설정 | - | ✓ | 부분 |
| Gemini 모델 선택 | (상호작용) | ✗ | **누락** |

---

### 16. **EXPORT** (도구별 설정)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| Claude 설정 | `claude` | ✗ | **전체 미구현** |
| OpenCode 설정 | `opencode` | ✗ | **미구현** |
| Cursor 설정 | `cursor` | ✗ | **미구현** |
| Antigravity 설정 | `antigravity` | ✗ | **미구현** |

---

### 17. **HISTORY** (저장 기록)

| 기능 | CLI 플래그 | GUI 구현 | 상태 |
|------|----------|--------|------|
| 목록 보기 | - | ✓ | 완전 |

---

### 18. **INSTALL / INIT / MANUAL / BENCH / RULES / COMPLETION**

모두 **미구현** ✗

---

## 통계

| 카테고리 | 개수 | 비율 |
|---------|------|------|
| 완전 구현 | 10 | 43% |
| 부분 구현 | 1 | 4% |
| 미구현 | 9 | 53% |
| **총 커맨드** | **20** | **100%** |

---

## 누락된 플래그/옵션 순위

### 🔴 HIGH (자주 쓰임 + 누락 많음)

| 우선순위 | 커맨드 | 누락 옵션 | 개수 |
|---------|-------|---------|------|
| 1️⃣ | **DOCTOR** | `--strict`, `--fix`, `--write-report`, `--plan`, `--patch`, `--apply`, `--json` | 7 |
| 2️⃣ | **EXPLAIN** | 전체 미구현 (5개 옵션) | 5 |
| 3️⃣ | **GUARD** | `--strict`, `--since-minutes`, `--write-report`, `--json` | 4 |
| 4️⃣ | **ANCHOR** | `--validate`, `--dry-run`, `--auto-intent`, `--set-intent`, `--only-ext` | 5 |

### 🟡 MEDIUM (워크플로우 필수)

| 우선순위 | 커맨드 | 누락 옵션 | 개수 |
|---------|-------|---------|------|
| 5️⃣ | **PATCH** | 전체 미구현 (5개 옵션) | 5 |
| 6️⃣ | **ASK** | 전체 미구현 (3개 옵션) | 3 |
| 7️⃣ | **TRANSFER** | `--full`, `--print`, `--session-summary`, `--first-next-action`, `--dry-run`, `--out` | 6 |
| 8️⃣ | **START** | `--all-tools`, `--tools`, `--force`, `--quickstart` | 4 |

### 🟢 LOW (선택 기능)

| 우선순위 | 커맨드 | 누락 옵션 | 개수 |
|---------|-------|---------|------|
| 9️⃣ | **PROTECT** | 전체 미구현 (3개 옵션) | 3 |
| 🔟 | **SECRETS** | 전체 미구현 (3개 옵션) | 3 |
| 1️⃣1️⃣ | **EXPORT** | 전체 미구현 | - |
| 1️⃣2️⃣ | **CONFIG** | GEMINI_MODEL 선택 | 1 |

---

## 구현 권장 체크리스트

### Phase 1: 핵심 기능 강화 (필수) ⭐⭐⭐
```
☐ DOCTOR   → --strict, --fix, --write-report 추가 (7시간)
☐ EXPLAIN  → 전체 구현 (8시간)
☐ GUARD    → --strict, --write-report 추가 (3시간)
☐ ANCHOR   → --validate, --dry-run 추가 (4시간)
```
**소계**: ~22시간

### Phase 2: 중요 워크플로우 (높음) ⭐⭐
```
☐ PATCH    → 전체 구현 (8시간)
☐ ASK      → 전체 구현 (6시간)
☐ TRANSFER → --full, --print, --session-summary, --first-next-action, --dry-run, --out 보강 (4시간)
```
**소계**: ~18시간

### Phase 3: 보조 기능 (중간) ⭐
```
☐ PROTECT  → 전체 구현 (4시간)
☐ SECRETS  → 전체 구현 (5시간)
☐ START    → --all-tools, --quickstart (3시간)
☐ CONFIG   → GEMINI_MODEL 선택 (2시간)
```
**소계**: ~14시간

### Phase 4: 관리 기능 (낮음)
```
☐ EXPORT   → 전체 구현 (3시간)
☐ INSTALL  → 구현 (2시간)
```
**소계**: ~5시간

---

## 기술 구현 패턴

### 1. Boolean 플래그 (토글/체크박스)
```
--strict, --force, --json, --write-report, --dry-run, --auto, --detailed
```

### 2. 텍스트 입력 (입력 필드)
```
--checkpoint-id, --since-minutes, --out, --tools, --only-ext, --session-summary, --first-next-action
```

### 3. 드롭다운 선택 (라디오/셀렉트)
```
--compact vs --full, export tools (claude/opencode/cursor...)
```

### 4. 상호 배제 옵션 (mutually exclusive)
```
DOCTOR:   --plan vs --patch vs --apply
TRANSFER: --compact vs --full
```

---

## 파일 경로

- **CLI 정의**: `/Users/usabatch/coding/VibeLign/vibelign/vib_cli.py` (1450+ 줄)
- **GUI 카드 정의**: `/Users/usabatch/coding/VibeLign/vibelign-gui/src/pages/Home.tsx` (1287 줄)
- **각 커맨드 구현**:
  - `/Users/usabatch/coding/VibeLign/vibelign/commands/doctor_cmd.py`
  - `/Users/usabatch/coding/VibeLign/vibelign/commands/guard_cmd.py`
  - `/Users/usabatch/coding/VibeLign/vibelign/commands/anchor_cmd.py`
  - 등등...

---

## 요약

### 현황
- **총 20개 커맨드** 중 **10개만 GUI에 완전 구현** (50%)
- **누락된 플래그**: 총 **56개** 이상
- **완전 미구현 커맨드**: 9개 (PATCH, PROTECT, SECRETS, EXPLAIN, ASK, EXPORT, INSTALL, BENCH, INIT)

### 가장 시급한 3가지
1. **DOCTOR 강화** (가장 자주 쓰이는 커맨드, 7개 옵션 누락)
2. **EXPLAIN 구현** (AI 작업 후 필수 확인 기능)
3. **PATCH 구현** (AI 수정 계획 생성, 중요 기능)

### 예상 소요 시간
- **Phase 1 (필수)**: 22시간
- **Phase 2 (높음)**: 18시간
- **Phase 3 (중간)**: 14시간
- **Phase 4 (낮음)**: 5시간
- **총합**: ~59시간 (스프린트로 2주)
