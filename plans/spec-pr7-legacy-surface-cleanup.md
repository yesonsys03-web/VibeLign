# PR 7 Spec: Legacy Surface Cleanup

작성일: 2026-06-02
브랜치: `feat/vibelign-product-renew`
상위 문서: `VibeLign-코알못UX-통합기획안.md` §2, §12 PR 7

## 목적

`patch`, `CodeSpeak`, `plan-structure`를 초보 제품 표면에서 제거하고 legacy/deprecated 경로로 격하한다.

PR 7은 실제 내부 엔진 삭제가 아니다. 초보자가 처음 보는 화면, 주요 도움말, README 첫 흐름, CLI help 추천 경로에서 제거하는 것이 목표다.

## 원칙

1. 초보 표면에서는 보이지 않는다.
2. 고급 사용자는 찾을 수 있다.
3. 내부 MCP/엔진 의존성은 깨지지 않는다.
4. 삭제는 의존성 맵과 deprecation 기간 이후에 결정한다.

## 현재 노출 표면

| 표면 | 현재 상태 |
|---|---|
| CLI main epilog | `patch`, `plan-structure`가 AI 수정 요청으로 노출 |
| CLI subcommand | `vib patch`, `vib plan-structure` 정상 등록 |
| GUI Home | `PatchCard`, `AnchorCard`, `GuardCard` 등 기능 카드 접근 |
| GUI command data | `COMMANDS`, `PATCH_COMMAND`, `plan-structure` entry |
| README / README.ko | quickstart와 release notes에 `vib patch` 다수 노출 |
| docs/MANUAL.md | `vib patch`, `vib plan-structure` 상세 섹션 |
| MCP | `patch_get`, `patch_apply` handlers 유지 필요 |
| core | `codespeak`, `patch_suggester`, `patch_contract` 유지 필요 |

## 범위

### 포함

- CLI help에서 `patch`, `plan-structure`를 초보 추천 그룹에서 제거
- `vib patch` 실행 시 deprecation/legacy 안내 출력
- `vib plan-structure` 실행 시 legacy 안내 출력
- GUI command data에서 `patch`/`plan-structure`를 advanced/legacy category로 이동
- README/README.ko의 첫 사용 흐름에서 `vib patch` 제거
- docs/MANUAL.md에서 초보 추천 흐름을 `vib plan`/기획방/host LLM MCP 방식으로 갱신
- 초보 표면 금지어 regression test 추가
- 내부 의존성 목록 작성

### 제외

- `vibelign/core/codespeak.py` 삭제
- `vibelign/core/patch_suggester.py` 삭제
- `vibelign/patch/` 삭제
- MCP `patch_get`/`patch_apply` 삭제
- benchmark/test fixture 삭제
- `vib bench --patch` 삭제

## 사용자 문구

### `vib patch` 실행 시

```text
vib patch는 legacy 기능이에요.
초보 흐름에서는 더 이상 추천하지 않아요.
자연어 수정은 Claude Code/Codex/Cursor 같은 host AI가 VibeLign MCP 도구를 직접 읽는 방식으로 진행하세요.
```

PR 7에서 실제 실행 차단까지 할지 여부:

- PR 7 결정: 경고만 출력하고 계속 실행한다. `--legacy-confirm`은 아직 요구하지 않는다.
- 다음 릴리즈: `--legacy-confirm` 요구
- 최종: hidden command 또는 삭제

### `vib plan-structure` 실행 시

```text
vib plan-structure는 내부 구조 계획용 legacy 기능이에요.
새 기획방/초보 흐름에서는 vib plan과 plans/*.md를 사용해요.
```

## CLI help 계약

`vib --help`의 초보 섹션에서 다음은 제거한다.

- `patch`
- `plan-structure`

대신 고급/legacy 그룹이 있다면 아래처럼 둔다.

```text
고급 / legacy:
  patch           legacy: 구조화된 수정 계획 생성
  plan-structure  legacy: 내부 구조 계획 JSON 생성
```

## GUI 계약

- 초보 Home 기본 화면에는 `PatchCard`가 없다(PR 6에서 이미 제거).
- 고급 기능 보기 내부에서 legacy badge와 함께 접근 가능하다.
- `COMMANDS`는 category 또는 visibility 필드를 갖도록 확장할 수 있다.

후보 필드:

```ts
visibility: "beginner" | "advanced" | "legacy"
```

PR 7에서 `PATCH_COMMAND = COMMANDS.find(...)!`는 non-null assertion 때문에 legacy 숨김 후 깨질 수 있다. 사용처를 먼저 검색하고, 필요하면 `getPatchCommand()`처럼 안전 함수로 바꾼다.

## README / docs 계약

### README 첫 흐름

제거:

- `vib patch "add button"` 같은 초보 quickstart
- “Tell AI exactly how to edit” 문구
- CodeSpeak/patch rules를 초보 소개처럼 보이게 하는 섹션

유지 가능:

- release notes의 과거 측정 기록
- docs/superpowers의 연구 문서
- legacy 섹션의 deprecation notice

### docs/MANUAL.md

- `vib patch` 섹션은 legacy로 이동
- `vib plan-structure` 섹션은 internal/legacy로 이동
- 새 초보 흐름은 `vib plan` 또는 GUI 기획방 기준으로 작성

## 의존성 맵

PR 7 구현 전 반드시 검색한다.

```bash
rg -n "PATCH_COMMAND|PatchCard|vib patch|CodeSpeak|plan-structure|patch_get|patch_apply|codespeak|patch_suggester" \
  vibelign vibelign-gui README.md README.ko.md docs tests
```

분류:

| 분류 | 처리 |
|---|---|
| 초보 UI/첫 문서 | 제거 또는 쉬운 말로 대체 |
| 고급 UI/manual | legacy badge 추가 |
| 내부 core/MCP/tests | 유지 |
| 과거 연구/릴리즈 노트 | 유지 가능 |
| command help 추천 | legacy 그룹으로 이동 |

## 자동 테스트

Python:

```text
tests/cli/test_legacy_surface.py
```

1. `vib --help` 초보 그룹에 `patch`, `plan-structure`가 없다.
2. `vib patch ...` 실행 시 legacy/deprecated 안내가 출력된다.
3. `vib plan-structure ...` 실행 시 legacy 안내가 출력된다.
4. MCP patch handler snapshot은 유지된다.

GUI:

```text
vibelign-gui/src/pages/__tests__/LegacySurface.test.tsx
```

5. 초보 Home에 `PatchCard`가 없다.
6. 고급 기능 보기 후 legacy 기능이 badge와 함께 보인다.
7. `COMMANDS`에서 legacy visibility를 가진 항목은 beginner list에 나오지 않는다.

Docs:

```text
tests/test_beginner_surface_docs.py
```

8. README 첫 흐름에 `vib patch`가 없다.
9. README 첫 흐름에 `CodeSpeak`가 없다.
10. manual의 `vib patch` 섹션은 `legacy` 문구를 포함한다.

## 수동 QA

### 시나리오 1: 초보 첫 흐름

```text
README 첫 200줄 확인
GUI Onboarding → Home 확인
```

통과 기준:

- `vib patch`, `CodeSpeak`, `plan-structure`가 추천 경로로 보이지 않는다.

### 시나리오 2: 고급 사용자가 legacy 기능 찾기

```text
Home → 고급 기능 보기
vib --help
docs/MANUAL.md legacy 섹션
```

통과 기준:

- 기능이 사라진 것처럼 보이지 않는다.
- legacy/deprecated 상태가 명확하다.

### 시나리오 3: 내부 MCP 회귀

```text
pytest tests/test_mcp_patch_get.py tests/test_mcp_patch_apply.py
```

통과 기준:

- MCP patch tools는 그대로 동작한다.

## 완료 정의

1. 초보 UI와 주요 문서 첫 흐름에서 `patch`, `CodeSpeak`, `plan-structure`가 제거되었다.
2. CLI/help/manual에서는 legacy/deprecated 상태가 명확하다.
3. 내부 core/MCP/test 의존성은 깨지지 않았다.
4. 실제 삭제 후보와 유지 후보가 의존성 맵으로 분류되었다.
5. 자동 테스트와 수동 QA가 통과한다.
