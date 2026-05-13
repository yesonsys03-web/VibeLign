# MCP Host-LLM Pivot — 수동 평가 Runbook

## 평가 목표

host LLM(Claude Code)이 신규 MCP 도구 `project_map_get` + `anchor_read_content` 만으로 사용자 자연어 요청을 정확한 file:anchor로 매핑하는가.

Baseline = `patch_suggester.suggest_patch(request, use_ai=False)` (Task 4 `tests/benchmark/test_patch_suggester_baseline.py` 에서 락된 수치).

- `BASELINE_FILE_PASSING = 14/20` (sample_project 인공 시나리오)
- `BASELINE_ANCHOR_PASSING = 0/19` — **단, 이 값은 sample_project에 앵커가 0개이기 때문에 측정 불가 영역**. 실제 사용자 프로젝트(앵커 다수)에서 별도 측정 필요.

## 한계 (먼저 알아둘 것)

sample_project는 anchor marker가 0개이므로 `correct_anchor` 매핑 평가는 사실상 불가능하다. 이 한계는 의도적 — host LLM이 신규 도구로 file 매핑을 어떻게 하는지가 1차 측정, anchor 매핑은 사용자 실 프로젝트가 필요.

## 데이터셋

1. `tests/benchmark/scenarios.json` — 인공 시나리오 20개 (sample_project, file 매핑만 의미 있음)
2. `tests/benchmark/user_requests.json` — 사용자 실제 자연어 요청 N개 (Task 0 산출물, 비어 있을 수 있음). **anchor가 있는 실 프로젝트로 평가하려면 이 데이터셋이 필수**.

## 사전 준비

1. Claude Code (또는 Cursor) 에 VibeLign MCP 서버 등록
2. 평가용 worktree 만들기: `git worktree add ../eval-worktree`
3. sample_project 평가: 평가 worktree에 `tests/benchmark/sample_project` 복사
4. 사용자 프로젝트 평가: 본인의 실제 프로젝트 사본 (vib doctor 통과한 anchor가 있는 상태)

## 평가 절차

각 시나리오마다 **새 대화로**:

1. `request` 텍스트를 그대로 Claude에게 입력
2. Claude에게 명시적 지시:
   > "정답 파일과 앵커 이름만 알려줘. 코드 수정은 하지 마. VibeLign MCP 도구(`project_map_get`, `anchor_read_content`) 를 활용해도 좋아."
3. Claude의 답을 기록 (file:anchor)
4. 정답(`correct_files`, `correct_anchor`)과 대조

## 메트릭

| 메트릭 | 정의 |
|---|---|
| File-level pass | Claude가 답한 파일이 `correct_files` 중 하나에 포함 (Task 4 의 `_file_matches` 와 동일 로직) |
| Anchor-level pass | file이 맞고 + anchor도 `correct_anchor` 와 정확히 일치 (`correct_anchor=null`인 시나리오는 anchor 평가 제외) |
| Tool 호출 분포 | 평균 호출 수, 가장 많이 쓰인 도구 |
| 응답 시간 | Claude의 처음 도구 호출~최종 답변까지 |

## 성공 기준

- **sample_project (file-level)**: ≥ 14/20 (baseline 동등) 그리고 가능하면 ≥ 17/20 (개선 증거)
- **사용자 프로젝트 (file-level)**: 5+ 자연어 요청에서 ≥ 60% pass
- **사용자 프로젝트 (anchor-level)**: 5+ 자연어 요청에서 ≥ 50% pass (sample_project에선 측정 불가, 이 기준이 anchor의 실제 평가)
- **도구 호출 수**: 평균 5번 이하로 수렴

## 결과 기록

`.vibelign/eval/2026-05-13-mcp-pivot/results.md` 에 표 형태:

| id | dataset | request | correct | got (host LLM) | baseline | tools used | tool_count |
|---|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... | ... |

## 의사결정

- **성공** (모든 성공 기준 충족) → full migration plan 작성:
  - `vibelign/core/ai_codespeak.py` deprecation 계획
  - `ACTION_MAP` 단순화 또는 폐기
  - `vib patch --ai` 플래그 deprecation
  - marketing 메시지 갱신 ("LLM IDE의 안전한 편집 손")
- **부분 성공** (file-level ok, anchor-level 미달) → 추가 MCP 도구 도입 검토:
  - `anchor_search(query)` — anchor 이름/의도 fuzzy 검색
  - `anchor_list_by_file(file)` — 특정 파일의 anchor 목록 + 의도
  - plan v3 작성
- **실패** (file-level baseline 이하) → 가설 재검토. host LLM이 도구를 잘 못 쓰는 건지, 도구가 부족한 건지 차이 진단 필요.

## 참고

- 본 PoC plan: `docs/superpowers/plans/2026-05-13-mcp-host-llm-pivot-plan.md`
- Baseline 락: `tests/benchmark/test_patch_suggester_baseline.py`
- 관련 메모: `vibelign-mcp-pivot` (auto-memory)
