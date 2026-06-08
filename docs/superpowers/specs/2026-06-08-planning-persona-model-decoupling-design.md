# 기획방 페르소나↔모델 결합 분리 설계

- 날짜: 2026-06-08
- 상태: 설계 승인 대기 (스펙 리뷰 게이트)
- 관련 코드:
  - Rust 대화 경로: `vibelign-gui/src-tauri/src/commands/planning_persona.rs`, `planning_chat.rs`, `platform.rs`
  - Python 계획서 경로: `vibelign/core/planning_cli/` (`cli_adapters.py`, `personas.py`, `orchestrator.py`)
  - 전역 설정: `~/.vibelign/gui_config.json` (`vibelign-gui/src-tauri/src/commands/settings.rs` `config_path()`)
  - UI: `vibelign-gui/src/pages/Settings.tsx`, 기획방 페이지/컴포넌트

## 1. 문제

기획방의 각 페르소나가 특정 LLM CLI에 **하드코딩**되어 있다.

- 대화 경로(`planning_persona.rs`): `chloe→claude`, `gio→codex`, `mina→agy`, `deepseek→opencode` 고정.
- 계획서 경로(`planning_cli`): `chloe→claude`, `gio→codex`, `mina→agy` 고정 (deepseek/opencode 없음).

이로 인한 문제:

1. 페르소나 4종이 각각 다른 CLI에 묶여, 풀 기획방을 쓰려면 서로 다른 CLI를 모두 설치·로그인해야 한다.
2. 역할(role)과 공급자(provider)가 결합되어, 원하는 모델이 없으면 그 역할을 아예 못 쓴다.
3. 할당된 CLI가 없으면 폴백 없이 실패하거나(대화) 그 페르소나를 건너뛴다(계획서).
4. 두 경로가 이미 분기되어 있다 — deepseek/opencode는 대화에만, 로그인 인지 상태 분류는 계획서에만 존재.

## 2. 목표

- 페르소나(역할/프롬프트)와 공급자(CLI/모델)를 **분리**한다.
- 사용자가 **페르소나별로 어떤 모델이 그 역할을 맡을지 재배정**할 수 있다.
- 사용자가 **페르소나를 ON/OFF** 할 수 있다.
- 할당된 모델이 없거나 실패하면 **자동으로 다른 가용 모델로 폴백**한다.
- 설정을 **단일 소스**에 두어 대화·계획서 두 경로가 같은 규칙을 따른다.

## 3. 비목표 (YAGNI)

- 폴백 **순서**를 사용자가 직접 편집하는 UI. (v1은 내부 고정 순서, UI 비노출.)
- 페르소나의 **역할 텍스트/프롬프트** 편집 또는 새 페르소나 추가 UI.
- deepseek를 **계획서 생성 경로**에 추가 (deepseek 정책 변동 가능성 → 대화 전용 유지).
- API 키 직접 입력 기반 LLM 호출 (기존 CLI 패스스루 구조 유지).

## 4. 핵심 결정 (확정)

| 항목 | 결정 |
|---|---|
| 커스터마이즈 범위 | 공급자 재배정 + 페르소나 ON/OFF (역할 텍스트는 불변) |
| 폴백 발동 | 설치 안 됨 **및** 런타임 응답 실패(로그인 안 됨 등) 둘 다 |
| 폴백 모델 선택 | 자동 (내부 고정 우선순위), UI 비노출 |
| 설정 표면 | Settings 화면(주 설정) + 기획방(빠른 변경) |
| 설정 저장 위치 | 전역 `~/.vibelign/gui_config.json` |
| 아키텍처 | 공유 설정 파일을 Rust·Python이 둘 다 읽고, 폴백 알고리즘을 양쪽에 동일 구현(미러) |
| persona 집합 | 대화 = chloe·gio·mina·deepseek / 계획서 = chloe·gio·mina |
| provider 집합 | 양쪽 통일: claude·codex·agy·opencode |

## 5. 설정 스키마

`~/.vibelign/gui_config.json` 에 `planning_personas` 섹션 추가:

```jsonc
"planning_personas": {
  "version": 1,
  "personas": {
    "chloe":    { "enabled": true, "provider": "claude" },
    "gio":      { "enabled": true, "provider": "codex" },
    "mina":     { "enabled": true, "provider": "agy" },
    "deepseek": { "enabled": true, "provider": "opencode" }
  }
}
```

- `provider`: 그 페르소나의 1순위 공급자. 생략/미지값이면 빌트인 기본값.
- `enabled`: ON/OFF. 생략이면 기본 true.
- 섹션/파일 부재 → 전부 빌트인 기본값 (zero-config).
- `deepseek` 키는 대화 경로만 소비. 계획서 경로는 무시.
- 폴백 우선순위는 스키마에 두지 않음 — 코드 내부 상수 (3.비목표 참조).

원자적 쓰기는 기존 `gui_config.json` 패턴(임시 파일 + rename) 재사용.

## 6. 레지스트리

### 6.1 Provider 레지스트리 (양쪽 통일)

| provider | 실행 인자 | 비고 |
|---|---|---|
| `claude` | `-p <prompt>` | |
| `codex` | `exec <prompt>` | |
| `agy` | `-p <prompt>` | |
| `opencode` | `run -m opencode/deepseek-v4-flash-free <prompt>` | 무료, 최후 폴백 후보 |

- Rust: 기존 `PersonaSpec`에서 `executable`/`args_before_prompt`를 분리해 provider 레지스트리로 이동.
- Python: `cli_adapters.py`의 `resolve_cli_executable` / `build_cli_command` / `probe_cli_candidates` / `select_adapter` 에 `opencode` 추가.

### 6.2 Persona 레지스트리

각 페르소나 = `id` + `name` + `role/prompt` + `기본 provider` + `section_title`. 역할/프롬프트는 **현행 유지**.

- 대화(Rust): chloe, gio, mina, deepseek
- 계획서(Python `personas.py`): chloe, gio, mina (변경 없음 — deepseek 추가 안 함)

## 7. 해석 + 폴백 알고리즘 (양쪽 동일 의미)

입력: 활성(enabled) 페르소나 목록, 전역 설정, 내부 우선순위 상수.

각 페르소나에 대해:

1. `candidate = config.personas[id].provider` (없으면 persona 기본 provider).
2. 시도 목록 = `[candidate] + INTERNAL_PRIORITY` 에서 중복 제거 (candidate 우선, 순서 보존).
   - `INTERNAL_PRIORITY`(잠정): `["claude", "codex", "agy", "opencode"]`.
3. 시도 목록 순회:
   - 실행파일 해석 불가(`not_installed`) → 다음 provider.
   - 실행 후 상태가 `ok` 아님(`not_logged_in`, `timeout`, `process_error`, `bad_output` 등) → 다음 provider.
   - `ok` → 채택하고 종료.
4. 목록 소진(가용 provider 없음) → 그 페르소나 실패:
   - 대화: 안내 메시지 + status `failed`.
   - 계획서: 해당 페르소나 스킵(현행), 전원 실패 시 `cli_unavailable_template_only`.
5. `enabled=false` 페르소나는 호출하지 않음 (출력 없음).
6. **실제 응답한 provider를 기록**하여, 1순위와 다르면 UI가 "대체됨"을 표시할 수 있게 한다.

상태 분류:
- Python: 기존 `classify_cli_output`(로그인/레이트리밋/타임아웃 인지) 재사용.
- Rust: 현 `run_persona_response`의 "성공·비어있지 않음 → ok, 그 외 → 실패" 판정을 "ok 아니면 다음 provider"로 확장. (Python 수준의 세분 분류까지는 불필요 — 폴백 의미만 일치하면 됨.)

## 8. 코드 변경 지점

### 8.1 Rust (대화 경로)

- `planning_persona.rs`
  - `PersonaSpec`에서 실행 정보 분리 → `provider_spec(provider_id) -> (executable, args)` 레지스트리.
  - `persona_spec`은 역할/기본 provider/이름만 보유.
  - 설정 리더: `~/.vibelign/gui_config.json`의 `planning_personas` 파싱 (기존 `config_path()` 재사용).
  - `run_persona_response`: 시도 목록 순회 + 폴백 + 사용 provider 반환.
  - 반환 구조에 `provider_used`(또는 유사) 추가 → 챗 메시지 메타로 노출.
- `planning_chat.rs`
  - enabled 페르소나만 호출하도록 분기 (요청 페르소나 ∩ 활성).
  - 폴백 발생 정보(1순위≠실제)를 메시지에 전달.

### 8.2 Python (계획서 경로)

- `cli_adapters.py`: `opencode` 추가(`resolve_cli_executable`, `build_cli_command`, `probe_cli_candidates`, `select_adapter`).
- `orchestrator.py` `_resolve_adapters` + 실행 루프: 페르소나별 1순위 → 폴백 순회. 전역 설정을 읽어 기본 매핑/활성 반영. 기존 `--cli`/`--agents` 인자는 **명시적 오버라이드**로 유지(설정보다 우선).
- 설정 리더: `~/.vibelign/gui_config.json`의 `planning_personas` 파싱하는 작은 모듈 신규.
- `personas.py`: 변경 없음(deepseek 미추가). 단, 기본 provider가 설정으로 덮일 수 있음을 반영.

### 8.3 공유 설정 I/O

- 단일 JSON 파일, 두 런타임이 각자 읽음. 스키마(키 이름·기본값)를 스펙으로 고정하고 양쪽 테스트로 검증.
- 쓰기는 GUI(Rust/Settings 커맨드)만 담당. Python은 읽기 전용.

## 9. UI

### 9.1 Settings — "기획방 페르소나" 섹션

- 페르소나별 행: 이름·역할 + ON/OFF 토글 + provider 드롭다운.
- 드롭다운 옵션 = provider 레지스트리. 설치 감지 결과로 "설치됨/미설치" 주석 (`detectInstalledTools` / `probe_cli_candidates` 재사용).
- 저장 → `planning_personas` 섹션을 `gui_config.json`에 기록(tauri 커맨드).

### 9.2 기획방 — 빠른 변경

- 페르소나 칩/카드에 빠른 메뉴: ON/OFF, provider 교체. 같은 설정에 기록.
- 폴백이 일어난 페르소나에 "OO로 대체됨" 배지 (§7 단계 6의 `provider_used` 사용).

## 10. 엣지 케이스

| 상황 | 처리 |
|---|---|
| 전원 OFF | 기획방에서 안내(활성 페르소나 없음) |
| 가용 provider 0개 | 폴백 소진 → 기존 "활성 AI를 찾지 못해…" graceful 경로 |
| 설정의 미지 provider | 무시하고 기본/우선순위로 진행 |
| 설정 파일 손상/파싱 실패 | 빌트인 기본값으로 안전 폴백 (로그만) |
| `--cli` 명시 오버라이드(계획서) | 설정보다 우선 |

## 11. 테스트

- Python
  - `opencode` 어댑터 빌드/해석.
  - 폴백: 1순위 미설치 → 다음 채택, 런타임 실패 → 다음, 전원 실패 → 템플릿.
  - 전역 설정 읽기(기본 매핑/활성/미지값/파일 부재).
  - `--cli` 오버라이드가 설정보다 우선.
- Rust
  - provider 레지스트리 분리 후 명령 구성.
  - 폴백 resolver(가용성 주입)로 시도 순서/대체 provider 검증.
  - 설정 파싱(부재/부분/손상).
  - enabled 필터링.
- Conformance
  - 동일 시나리오(예: "chloe=claude 미설치, codex 가용")에서 양쪽이 같은 provider를 고르는지 명세 케이스로 고정.

## 12. 마이그레이션 / 호환성

- `planning_personas` 섹션 부재 = 현행 기본 동작과 동일 (무중단).
- 기존 `gui_config.json`의 다른 키(API 키·recent_projects)와 공존, 원자적 쓰기 유지.
- 계획서 경로의 기존 `--cli`/`--agents` 계약 불변.
