# Draft: Multi AI Planning CLI

## Requirements (confirmed)
- 코알못은 바이브코딩 전에 기획이 필요하다는 사실과 Markdown 파일 개념을 모른다.
- VibeLign이 CLI에서 기획 시작을 돕고, 최종적으로 AI가 이해하기 쉬운 `.md` 기획안을 자동 생성해야 한다.
- 사용자가 효과를 본 방식은 Claude, ChatGPT, Gemini를 오가며 기획안을 서로 검토시키는 방식이다.
- 이 흐름을 VibeLign 안에 통합해 CLI로 여러 AI를 호출하고 기획안을 작성/검토/통합하게 한다.

## Technical Decisions
- 새 사용자-facing 명령은 `vib plan`으로 설계한다.
- `vib plan-structure`는 새 `vib plan` 범위의 제품 의존성/완성 목표에서 제외한다. 삭제 대상이 아니라 기존 guard/precheck 구조 계획 보조 기능으로만 취급한다.
- 결과물은 프로젝트 루트의 `plans/{slug}.md`로 저장한다. 초보자는 Markdown을 몰라도 되지만 AI 툴은 그 파일을 읽을 수 있다.
- API key 방식은 초보 기본 흐름에서 제외하고, 사용자가 로그인한 공식 CLI를 subprocess로 호출한다.
- Claude Code CLI는 설계자 클로이, Codex CLI는 검토자 지오, Antigravity CLI는 탐색자 미나로 부른다.
- 락인 효과는 모델 소유가 아니라 `plans/*.md`, 페르소나 검토 루프, 다음 작업 연결이 VibeLign에 쌓이는 워크플로우 락인으로 정의한다.

## Research Findings
- `vib plan-structure`는 이미 존재하지만 `.vibelign/plans/*.json`에 구조 계획을 저장하는 명령이다.
- 구현 확인: CLI 등록, `.vibelign/plans/*.json` 저장, planning state 저장, guard/precheck 소비 경로, 구조 planner 테스트가 존재한다.
- 검증 확인: `uv run pytest tests/test_structure_planner.py tests/test_guard_planning.py::GuardPlanningTest::test_active_plan_passes_for_allowed_existing_and_new_file tests/test_vib_precheck.py::VibPrecheckTest::test_valid_plan_with_anchors_allows` 통과.
- 실사용 확인: 임시 git 프로젝트에서 `vib plan-structure "로그인 기능" --json`은 JSON plan을 생성하지만 project_map이 없으면 `vibelign/core/new_feature.py` 같은 보수적 fallback을 낸다.
- Metis 검토: `vib plan-structure`는 미성숙한 rules-based live infrastructure로 보고, 완성/개선은 제외하되 CLI dispatch, `.vibelign/plans/*.json`, active planning state, guard/precheck 소비 계약은 깨지지 않게 좁은 회귀 검사를 남긴다.
- 기존 API key 지원은 참고만 하고 이번 초보 흐름에는 쓰지 않는다.
- 구현은 `claude`, `codex`, `antigravity` CLI 설치/로그인 상태를 확인하고 stdout/stderr만 수집하는 방향이다.

## Open Questions
- 없음. 다만 기존 계획 문서의 "`vib plan-structure`는 유지/그대로 동작" 문구는 "`vib plan` 프로젝트 범위에서는 완성/개선하지 않되, 기존 구조 계획 계약은 회귀시키지 않음"으로 낮춰야 한다.

## Scope Boundaries
- INCLUDE: CLI 기획 시작, 다중 AI 검토 루프, Markdown 기획안 생성, CLI fallback, 페르소나 채팅 UI, 테스트/QA 계획, 기존 `vib plan-structure`와 명칭/저장소/state 충돌 방지, 기존 command의 좁은 비회귀 smoke test.
- EXCLUDE: 코드 수정 자동 실행, CodeSpeak/patch 생성, `vib plan-structure` 완성/리빌드/삭제.
