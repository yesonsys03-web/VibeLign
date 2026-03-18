# VibeLign MCP 개발 기획

## 개요

VibeLign을 MCP(Model Context Protocol) 서버로 만들면, Claude 등 AI 툴이 CLI 명령어 없이
VibeLign 기능을 **도구(tool)** 로 직접 호출할 수 있다.

**가능한가?** — 완전히 가능. 핵심 로직(`vibelign/core/`)은 이미 순수 Python 함수로 분리되어 있어서
MCP 어댑터만 씌우면 된다. 기존 CLI는 그대로 유지.

---

## 아키텍처

```
Claude Code / Cursor / Codex
        ↓  MCP protocol (stdio)
vibelign/mcp_server.py   ← 신규
        ↓  직접 함수 호출
vibelign/core/*.py       ← 기존 코드 재사용
```

- 전송 방식: **stdio** (가장 단순, Claude Code 기본)
- 기존 `vibelign/core/` 코드 100% 재사용, 신규 코드는 얇은 어댑터만

---

## 기대 효과

**기존 방식 (PostToolUse 훅 — 제거됨):**
```
Claude 파일 수정 → 훅 → shell에서 vib checkpoint 실행 → stdin 오염 버그
```

**MCP 방식:**
```
Claude 파일 수정 → Claude가 checkpoint_create 도구 직접 호출 → 깔끔
```

---

## MCP 도구 전체 목록

### 체크포인트 (백업/복원)

| 도구 | 대응 커맨드 | 설명 |
|------|-------------|------|
| `checkpoint_create` | `vib checkpoint` | 현재 상태 저장 |
| `checkpoint_list` | `vib history` | 체크포인트 목록 조회 |
| `checkpoint_restore` | `vib undo` | 특정 시점으로 복원 (`checkpoint_id` 파라미터) |

### 프로젝트 분석

| 도구 | 대응 커맨드 | 설명 |
|------|-------------|------|
| `doctor_run` | `vib doctor` | 프로젝트 건강 진단 (파일 길이, 임포트 등) |
| `scan_run` | `vib scan` | 코드 스캔 |
| `bench_run` | `vib bench` | 벤치마크 실행 |

### 보호/가드

| 도구 | 대응 커맨드 | 설명 |
|------|-------------|------|
| `guard_check` | `vib guard` | 보호 파일 침범 감지 |
| `protect_add` | `vib protect` | 보호 파일 등록 (`file_paths` 파라미터) |

### AI 컨텍스트

| 도구 | 대응 커맨드 | 설명 |
|------|-------------|------|
| `project_context_get` | `vib transfer` | PROJECT_CONTEXT.md 내용 반환 |
| `explain_get` | `vib explain` | 코드 설명 파일 반환 |
| `anchor_list` | `vib anchor` | 앵커 목록 조회 |

### 패치/변경

| 도구 | 대응 커맨드 | 설명 |
|------|-------------|------|
| `patch_apply` | `vib patch` | 패치 적용 |

### 설정/초기화

| 도구 | 대응 커맨드 | 설명 | 비고 |
|------|-------------|------|------|
| `init_run` | `vib init` | 프로젝트 초기화 | MCP 등록 포함 |
| `config_get` | `vib config` | 현재 설정 조회 | |
| `manual_get` | `vib manual` | 매뉴얼 텍스트 반환 | |

### MCP 미노출 (인터랙티브 전용 또는 불필요)

| 커맨드 | 이유 |
|--------|------|
| `vib start` | 사람이 세션 시작 시 1회 실행하는 것 — AI가 호출할 필요 없음 |
| `vib watch` | 백그라운드 프로세스 — MCP 도구로 적합하지 않음 |
| `vib ask` | AI 자신이 질문을 만들어 호출하는 구조가 어색 |
| `install_guide` | 사람용 안내 출력 |

---

## 구현 체크리스트

### Phase 1 — 기반 세팅

- [x] `pyproject.toml`에 `mcp` 의존성 추가
- [x] `vibelign/mcp_server.py` 파일 생성 (MCP 서버 진입점)
- [x] `pyproject.toml`에 `vibelign-mcp` 스크립트 엔트리포인트 추가

### Phase 2 — 핵심 도구 구현

- [x] `checkpoint_create` 도구 구현
- [x] `checkpoint_list` 도구 구현
- [x] `checkpoint_restore` 도구 구현
- [x] `project_context_get` 도구 구현

### Phase 3 — 추가 도구 구현

- [x] `doctor_run` 도구 구현
- [x] `guard_check` 도구 구현
- [x] `protect_add` 도구 구현
- [x] `anchor_list` 도구 구현
- [x] `config_get` 도구 구현

### Phase 4 — Claude Code 연동

- [x] `vib start`가 자동으로 `.claude/settings.json`에 MCP 등록 (`_register_mcp_claude`)
- [ ] `vib doctor`에 MCP 서버 상태 체크 추가

### Phase 5 — 릴리즈

- [ ] README에 MCP 설정 섹션 추가
- [ ] `pyproject.toml` 버전 bump
- [ ] 배포 및 태그

---

## MCP 설계 핵심 원칙

### 1. 모든 입출력은 JSON

MCP 프로토콜은 stdio로 JSON을 주고받는다. 도구의 입력 스키마도 JSON Schema로 선언해야
Claude가 올바르게 호출할 수 있다.

```
Claude → {"tool": "checkpoint_create", "arguments": {"message": "로그인 완성"}}
서버   → {"content": [{"type": "text", "text": "✓ 체크포인트 저장 완료"}]}
```

### 2. 논인터랙티브 설계 필수

MCP 서버는 stdin/stdout을 프로토콜 통신으로 사용하기 때문에 `input()` 호출은 절대 금지.
호출하면 프로세스가 멈추거나 프로토콜이 깨진다.
(PostToolUse 훅에서 stdin JSON이 오염됐던 버그와 동일한 맥락)

**원칙: 모든 결정은 파라미터로 받는다.**

```python
# 잘못된 방식 (CLI 스타일)
def checkpoint_restore():
    idx = input("번호: ")
    confirm = input("정말 되돌릴까요? [Y/n]: ")

# 올바른 방식 (MCP 스타일)
def checkpoint_restore(checkpoint_id: str) -> str:
    # 파라미터로 받음, 대화 없음
```

### 3. VibeLign에서 재설계가 필요한 기능

현재 `input()`을 사용하는 기능은 MCP 도구로 노출할 때 파라미터 방식으로 변경해야 한다.

| 기능 | 현재 방식 | MCP 변경 방향 |
|------|-----------|---------------|
| `vib undo` | 체크포인트 선택 + 확인 프롬프트 | `checkpoint_id` 파라미터로 직접 지정 |
| `vib ask` | 질문 입력 | `question` 파라미터 |
| `vib protect` | 파일 선택 | `file_paths` 파라미터 |

---

## 기술 스택

- Python `mcp` SDK (Anthropic 공식)
- 전송 방식: stdio
- Python 3.12+
