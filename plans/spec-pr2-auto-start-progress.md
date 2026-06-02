# PR 2 Spec: 자동 start + 5단계 진행 + Claude Code 체크박스 동작

작성일: 2026-06-02
브랜치: `feat/vibelign-product-renew`
상위 문서: `VibeLign-코알못UX-통합기획안.md` §12 PR 2, §5(vib start 의미 변경)

## 목적

PR 1에서 만든 입력 바 화면에서 **폴더를 고르면, 사용자가 터미널을 열지 않아도 프로젝트가 VibeLign 준비 상태가 되도록** 한다. 비대화형 `vib start`를 자동 실행하고, 진행 상황을 입력 바 아래에 5단계로 보여주며, Claude Code 자동 준비 체크박스를 실제로 동작시킨다.

이 PR은 **준비(start) 자동화**만 담당한다. 입력 텍스트를 기획방으로 넘기거나 LLM을 호출하지 않는다(PR 3/4).

## 상위 결정

- `vib start = 이 프로젝트의 자동 안전장치를 켠다`로 의미를 고정한다(통합기획안 §5).
- GUI는 **비대화형 start**를 호출해야 한다. 현재 `run_vib_start`는 첫 체크포인트 저장을 `input("[Y/n]")`(대화형)로 묻는다 — GUI 경로에서는 막힌다.
- 5단계 진행 메시지는 기존 vib progress 스트리밍 경로(`run_vib_with_progress`)를 사용하고, GUI에서는 그 이벤트를 온보딩 진행 UI에 연결한다. `run_vib`는 `cmd.output()` 기반이라 실시간 표시 경로로 쓰지 않는다.
- watch는 start 완료 **후** GUI가 이어서 켠다(긴 수명 데몬을 Python start에 끼워넣지 않는다).
- Claude Code 준비는 start 성공/부분 성공 상태와 분리된 subtask로 처리한다. start와 설치를 하나의 성공/실패 상태로 묶지 않는다.

## 범위

### 포함

1. **비대화형 start 플래그**: `vib start --non-interactive`(또는 `--auto`) 추가
   - `input("[Y/n]")`(현 `vib_start_cmd.py:1124`) 분기를 건너뛰고 **첫 체크포인트를 자동 생성**(기존 `run_vib_checkpoint(SimpleNamespace(message=["시작"]))` 재사용, 현 `:1129-1132`).
   - 그 외 동작(rules/`.vibelign`/project_map/anchor/hook/git secret hook/doctor)은 그대로.
2. **5단계 progress 이벤트 emit**: `vib_start_cmd.py`가 진행 단계를 JSON line 마커로 stdout에 출력 → Rust `run_vib_with_progress` 브리지가 파싱해 per-call progress 이벤트로 중계 → GUI가 listen.
3. **5단계 진행 UI**: 입력 바 **아래 동일 위치**에 한 줄씩 표시(통합기획안 §4-1):
   - `프로젝트 확인 중...` → `안전 규칙 준비 중...` → `되돌리기 지점 저장 중...` → `파일 변경 감시 준비 중...` → `준비 완료`
4. **watch 자동 시작**: 비대화형 start 성공 후 GUI가 `startWatch(cwd)` 호출(기존 `start_watch` Tauri command 재사용). Python `vib start` 안에서 장수 watch 프로세스를 직접 시작하지 않는다.
5. **Claude Code 체크박스 실제 동작**: 첫 화면 체크박스 ON 시, start 완료 후 기존 설치 backend(`start_native_install`/`start_wsl_install`)를 별도 subtask로 트리거.
6. **부분 실패 처리**: Claude Code 준비 실패 ≠ 전체 실패. "Claude Code 준비만 실패했어요. 프로젝트 안전장치는 켜져 있어요." 분리 표시(통합기획안 §4-1-1).

### 제외

- 입력 바 텍스트를 기획방으로 전달 (PR 3)
- 기획방 UI / `vib plan` 엔진 (PR 3)
- LLM CLI 호출 (PR 4)
- anchor 자동 정리·guard 자동 실행 정밀화 (PR 8)
- Home 재구성 (PR 6)

## 현재 코드 기준 (구현 근거)

| 사실 | 위치 |
|---|---|
| `run_vib_start(args: Namespace) -> None` | `vibelign/commands/vib_start_cmd.py:960` |
| `--quickstart` 플래그 존재(비대화형 플래그는 **없음**) | `:100-102` |
| 대화형 차단 지점: 첫 체크포인트 `input("[Y/n]")` | `:1124` |
| 첫 체크포인트 자동 생성 코드(재사용) | `:1129-1132` |
| start 실행 순서: `_setup_project`→tools→hooks→git secret→doctor→checkpoint→(quickstart)anchor | `:970-1164` |
| GUI start 호출: `vibStart(cwd, tools)` → `invoke("run_vib")` | `vibelign-gui/src/lib/vib/core.ts:76-82`, `src-tauri/.../lib.rs:110` |
| 폴더 선택 / start 트리거 / 완료 콜백 | `Onboarding.tsx:302-305` / `:290-299` / `onComplete(dir, null):299` |
| vib progress 스트리밍 경로 | `run_vib_with_progress` / `runVibWithProgress(...)` |
| 프론트 listen / 1초 폴링 | `Onboarding.tsx:178-189` / `:222-231` |
| watch 시작 command | `watch.ts:5` → `start_watch`(`lib.rs:123`) |
| Claude 설치 command 등록 | `lib.rs:103-107`(`start_native_install`/`start_wsl_install`/`add_claude_to_user_path`/`uninstall_claude_code`) |
| 부분 실패: `needs_manual_step`/`needs_wsl_fallback`(soft-fail) | `macos.rs:250`, `windows.rs:362-403` |

## 5단계 진행 계약

`vib_start_cmd.py`는 비대화형 모드에서 각 단계 시작 시 stdout에 한 줄 JSON 마커를 출력한다. 형식(예시):

```text
{"type":"vib_start_progress","step":1,"total":5,"label":"프로젝트 확인 중..."}
{"type":"vib_start_progress","step":2,"total":5,"label":"안전 규칙 준비 중..."}
{"type":"vib_start_progress","step":3,"total":5,"label":"되돌리기 지점 저장 중..."}
{"type":"vib_start_progress","step":4,"total":5,"label":"파일 변경 감시 준비 중..."}
{"type":"vib_start_progress","step":5,"total":5,"label":"준비 완료"}
```

- Rust `run_vib_with_progress` 브리지가 stdout 라인에서 `type == "vib_start_progress"` JSON을 감지하면 호출별 progress 이벤트로 emit한다. GUI는 이 이벤트를 받아 온보딩 진행 UI에 표시한다.
- 마커는 GUI 표시용 보조 신호다. 누락돼도 start 자체는 정상 동작해야 한다(마커 파싱 실패가 start 실패로 이어지면 안 됨).
- 단계 라벨은 사용자 문구이므로 금지어 계약(통합기획안 §8)을 따른다. `watch`/`anchor`/`guard` 같은 내부 용어를 라벨에 노출하지 않는다("파일 변경 감시 준비 중"은 OK, "watch 시작"은 금지).
- JSON 파싱 실패 라인은 일반 stdout으로 취급한다. progress parser가 stderr/stdout 전체를 실패시키면 안 된다.

## 동작 / 시나리오

| 상황 | PR 2 동작 |
|---|---|
| 폴더 선택 후 전송, Claude 체크박스 OFF | `run_vib_with_progress(["start", "--non-interactive"])` 실행 → 5단계 진행 표시 → 성공 후 GUI가 watch 자동 시작 → "준비 완료" |
| 폴더 선택 후 전송, Claude 체크박스 ON, 미설치 | start 완료/부분 성공 상태 표시 후 Claude 설치 흐름을 별도 subtask로 실행, 설치 로그는 접힌 고급 영역 |
| Claude 체크박스 ON, 이미 설치됨 | "Claude Code 준비됨" 표시, 설치 재실행 안 함 |
| Claude 설치 실패 | start 안전장치는 성공 유지. "Claude Code 준비만 실패했어요" 분리 표시. 전체 실패 처리 금지 |
| start 부분 실패(일부 단계 실패) | "자동 안전장치 일부가 꺼져 있어요. [다시 켜기] [자세히 보기]"(통합기획안 §5) |
| watch 시작 실패 | "파일 변경 감시를 켜지 못했어요. [다시 켜기]". start 전체는 성공 유지 |
| 폴더 미선택 전송 | start 실행 안 함(PR 1의 안내 유지) |

## 상태와 에러

- **비대화형 보장**: `--non-interactive`에서는 어떤 `input()`도 호출되지 않아야 한다(EOF로 멈추지 않음). 회귀 테스트로 고정.
- **부분 성공 표면화**: start 단계별 성공/실패를 GUI가 구분 표시. "조용한 실패" 금지(통합기획안 §14-4).
- **로그 분리**: start/설치 raw 로그는 기본 숨김, "자세히 보기"에서만.
- **Windows**: 기존 콘솔 깜빡임 회귀(v2.2.24에서 수정)를 비대화형 start 경로에서도 재발시키지 않는지 확인.

## 구현 메모

- 비대화형 플래그는 `vib_start_cmd.py`의 argparse에 추가하고, `:1121-1135` 블록을 `if args.non_interactive: <자동 체크포인트> else: <기존 input 분기>`로 분기.
- progress 마커 출력은 각 주요 단계(`_setup_project` 전/후, checkpoint 전, watch 준비 안내 전, 완료) 경계에 삽입.
- Rust 측: 기존 `run_vib_with_progress` 경로(`commands::vib_bridge::run_vib_with_progress`)에 `vib_start_progress` JSON line 파싱을 추가한다. `run_vib`는 완료 후 stdout 반환용으로 유지한다.
- GUI 측: `Onboarding.tsx`의 `handleStart`(`:290-299`)를 `runVibWithProgress(["start", "--non-interactive"], dir, ..., onProgress)` → 성공 시 `startWatch(dir)` → `onComplete` 순으로 확장. 진행 UI는 호출별 progress 이벤트를 입력 바 아래에 연결한다.
- Claude 체크박스: 기존 `start_native_install`/`start_wsl_install`을 체크박스 ON일 때 start 완료 후 별도 subtask로 트리거. 부분 실패 상태(`needs_manual_step`/`needs_wsl_fallback`)를 그대로 활용한다. 설치 중이어도 start 결과와 watch 상태는 유지한다.
- **전체 파일 재작성 금지**(CLAUDE.md 규칙). `vib_start_cmd.py`는 분기 추가 + 마커 출력만. `Onboarding.tsx`는 핸들러 확장만.

## 자동 테스트

Python:

```text
tests/cli/test_vib_start_non_interactive.py
```

1. `--non-interactive`에서 `input()`이 호출되지 않는다(monkeypatch로 input 차단해도 통과).
2. `--non-interactive`에서 첫 체크포인트가 자동 생성된다.
3. progress JSON line 5개가 순서대로 stdout에 출력된다.
4. 마커 파싱 불가 상황을 가정해도 start 종료 코드는 성공이다.

GUI(vitest):

```text
vibelign-gui/src/pages/__tests__/Onboarding.pr2-start.test.tsx
```

5. 폴더 선택 후 전송 → `vibStart`가 non-interactive로 호출된다.
6. 진행 이벤트 수신 시 5단계 라벨이 입력 바 아래에 순서대로 렌더된다.
7. start 성공 후 `startWatch`가 호출된다.
8. Claude 설치 실패 이벤트가 와도 전체 실패 UI가 아니라 분리 메시지가 뜬다.
9. 진행 라벨에 금지어(`watch`/`anchor`/`guard`/`vib start`)가 보이지 않는다.
10. malformed progress JSON line은 일반 stdout으로 남고 start 실패로 처리되지 않는다.

## 수동 QA

### 시나리오 1: 폴더만 선택하고 전송 (Claude OFF)

```text
입력 바 → + 폴더 선택 → ● 전송
```

통과 기준: 터미널을 열지 않고 5단계 진행 → "준비 완료". 첫 체크포인트 생성됨. watch 켜짐. 입력 바는 사라지지 않고 자리 유지.

### 시나리오 2: Claude 체크박스 ON, 미설치

통과 기준: 안전장치 준비가 먼저 완료/부분 완료 상태를 표시한 뒤 Claude 설치 subtask가 진행. 설치 raw 로그는 접힘. 설치 성공/실패가 안전장치 상태와 분리 표시.

### 시나리오 3: Claude 설치 실패

통과 기준: "Claude Code 준비만 실패했어요. 프로젝트 안전장치는 켜져 있어요." 안전장치는 정상.

### 시나리오 4: 비대화형 검증(터미널)

```text
cd <tmp git repo>
python -m vibelign.cli.vib_cli start --non-interactive
```

통과 기준: 입력 프롬프트 없이 끝까지 진행, 첫 체크포인트 생성, progress JSON line 5개 출력.

## 완료 정의

1. `vib start --non-interactive`가 입력 프롬프트 없이 완료되고 첫 체크포인트를 자동 생성한다.
2. GUI에서 폴더 선택 후 전송하면 비대화형 start가 실행되고, 입력 바 아래에 5단계 진행이 한 줄씩 표시된다.
3. start 성공 후 watch가 자동으로 켜진다.
4. Claude Code 체크박스가 실제 설치를 트리거하고, 실패해도 전체 온보딩을 실패시키지 않는다.
5. start/watch 부분 실패가 "다시 켜기" 가능한 상태로 표면화된다.
6. 진행 라벨에 내부 용어 금지어가 노출되지 않는다.
7. 입력 텍스트 전달·기획방·LLM 호출은 들어가지 않았다(PR 3/4 분리 유지).
