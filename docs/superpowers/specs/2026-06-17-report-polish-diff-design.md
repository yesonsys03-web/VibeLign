# 보고서 다듬기: 블록 diff·부분 수락 + 환각·과장 방어 — 설계 스펙

- 날짜: 2026-06-17
- 대상: VibeLign 보고서 기능 (`vib report --polish`, `reporting_cli`, GUI `ReportView`/`ExportReportModal`)
- 산출물: 이 설계 1개 → 구현 계획서 2개 (기능 1, 기능 3)
- 근거: 딥리서치(한국 보고 문화·AI 신뢰성·인간 편집 워크플로우, `tasks/whrtz2v7q.output`) + 파이프라인 코드 매핑

---

## 1. 배경과 목표

현재 `vib report --polish`는 기획안 마크다운을 파싱→`ReportModel` 빌드→AI 어조 다듬기→렌더→파일 저장을 **한 번에** 수행하고 경로만 돌려준다(`vib_report_cmd.py:42-119`). 다듬기는 전체를 통째로 덮어쓰며 사용자가 개입할 지점이 없다.

현장 리서치의 핵심 신호 두 가지를 해결한다.

- **신뢰·통제 (기능 1)**: 성숙한 AI 도구는 변경을 자동 적용하지 않고 diff로 미리보기한 뒤 사용자가 단위별로 수락/거부한다(Tiptap, VS Code Copilot — 3-0). 사람이 게이트키퍼다.
- **환각·과장 방어 (기능 3)**: AI는 진실이 아니라 다음 토큰을 최적화해 자신 있게 숫자를 바꾸거나 과장을 끼워넣을 수 있다(KPMG "vibe citing" 45개 인용 중 5개만 정확 — 3-0). 정확성·검증 가능성이 도입의 1차 장벽이다.

### 목표
1. 다듬기를 **블록 단위 diff + 부분 수락**으로 전환하고, 전용 검토 화면(보고서 서브탭)에서 수행한다.
2. 다듬기가 **숫자·사실을 바꾸거나 과장을 신규 생성하지 못하게** 결정론적으로 막고, 모호어를 경고한다.

### 비목표 (YAGNI — 이번 범위 아님)
- 보고서 종류·주기별 템플릿 분기, 임원용 1페이지 요약 (별도 기능 2).
- 문장 단위 diff(블록 단위로 확정), 출처 자동 인용 생성, 2차 AI 검증 패스.
- 새 LLM provider 추가, 다듬기 외 섹션(bullets) 자동 수정.

---

## 2. 공통 백본 — `vib report` 2단계 분리

블록 수락/거부를 끼우려면 생성 파이프라인의 중간을 열어야 한다. **생성 로직은 그대로 두고 진입/출력 계약만 분리**한다.

### 2.1 모델 직렬화 모듈 (신규, 단일 책임)
- 신규 파일: `vibelign/core/reporting_cli/model_json.py`
- `polish_cache.py:13-58`이 이미 `ReportModel`↔JSON 직렬화를 한다. 그 로직을 이 모듈로 **추출**해 `model_to_dict(ReportModel) -> dict` / `model_from_dict(dict) -> ReportModel`로 공개하고, `polish_cache.py`는 이를 호출하도록 변경(중복 제거).
- `model_from_dict`는 **스키마 검증**을 수행한다(필수 필드·타입·허용 block.kind). render 모드가 외부에서 받은 JSON을 신뢰하기 전 관문.

### 2.2 emit 모드 — 구조화 모델 반환 (파일 미저장)
- 명령: `vib report <plan> --type T --polish --emit-model --json`
- 동작: `build_report_model`로 base, `polish_report_model`로 polished 계산 후 **렌더·저장 없이** JSON 반환.
- 출력 스키마:
```json
{
  "ok": true,
  "report_type": "work",
  "slug": "예약-앱",
  "base":     { "title": "...", "report_type": "work", "date": "...", "sections": [ ... ] },
  "polished": { "title": "...", "report_type": "work", "date": "...", "sections": [ ... ] },
  "guards":   [ { "section": 0, "block": 1, "reason": "number_dropped", "missing": ["50%"] } ],
  "vague_warnings": [ { "section": 0, "block": 0, "term": "대폭", "offset": 12 } ]
}
```
- `guards`/`vague_warnings`는 기능 3이 채운다(기능 1만 구현 시 빈 배열).

### 2.3 render 모드 — 병합 모델을 렌더·저장
- 명령: `vib report --render-model <path>|- --type T --format X --json` (`-`는 stdin)
- 동작: 호출자가 준 병합 모델 JSON을 `model_from_dict`로 검증·복원 → `render_html/docx/pptx` → `write_report(_bytes)` → `{ok, path}` 반환.
- 저장 경로·보안은 기존 `storage.py:54-125` 그대로(상대경로 가드, slug, 중복 회피).

### 2.4 GUI→CLI 모델 전달 통로
- **stdin 우선**(`--render-model -`): 임시파일 없이 깔끔. 계획 첫 작업으로 `runVib` 브리지의 stdin 주입 지원 여부 확인(`commands/vib_bridge.rs`, `lib/vib/core.ts`).
- 미지원 시 폴백: GUI가 병합 모델을 `.vibelign/reports/.tmp-model-*.json`(프로젝트 내, storage 가드 통과)로 쓰고 경로 전달 후 삭제.

---

## 3. 기능 1 — 블록 diff + 부분 수락 (보고서 서브탭)

### 3.1 데이터 흐름
```
ReportView(보고서 서브탭)
  → emitReportModel(cwd, plan, type)            # vib report --emit-model --json
  → { base, polished, guards, vague_warnings }
  → 섹션별 블록 diff 렌더 (paragraph/summary 만 diff, bullets 읽기전용)
  → 사용자 블록별 [수락]/[거부] (기본=수락; guard 걸린 블록은 기본=원본)
  → TS에서 병합 모델 구성: 수락→polished.text, 거부→base.text, bullets→base
  → renderReportModel(merged, format)            # vib report --render-model - --format X
  → { path } → 기존 내보내기/복사 흐름(copyReportTo 등, 이미 구현)으로 저장
```

### 3.2 컴포넌트 (구조화 — 작고 단일책임)
**Python**
- `vib_report_cmd.py`: `--emit-model`/`--render-model` 분기 추가. 각 분기는 **얇은 디스패치**만; 실제 로직은 아래 헬퍼로 위임(엔트리 파일 비대화 금지).
- `reporting_cli/emit.py` (신규): `emit_report_payload(plan, type, polish, provider) -> dict`. base/polished/guards/vague를 조립.
- `reporting_cli/model_json.py` (신규, §2.1).
- `cli_command_groups.py`: `--emit-model`, `--render-model` 인자 등록.

**TS (`lib/vib/report.ts`)**
- `emitReportModel(...)`, `renderReportModel(model, format, ...)` 래퍼.
- 모델 타입 미러: `lib/vib/reportModel.ts` (신규) — `ReportModel/Section/Block` TS 타입 + `mergeModel(base, polished, decisions)` 순수 함수(테스트 용이).

**TS (검토 UI — `ReportView` 하위)**
- `components/report-review/ReportDiffReview.tsx`: 섹션 목록 + 선택 섹션 블록 diff.
- `components/report-review/BlockDiff.tsx`: 단일 블록 `원본 | 다듬 + [수락][거부]` (+ guard 배지, vague 하이라이트 — 기능 3).
- `components/report-review/useReviewState.ts`: 블록별 결정 상태 훅(순수 로직 분리).
- 큰 단일 파일 금지: UI/상태/머지 로직을 위처럼 분리한다.

### 3.3 에러 처리
- polish provider 전부 실패 → polished=base(diff 0건), "다듬을 항목 없음" 안내(기존 graceful fallback 유지, `polish.py:53-81`).
- render-model 입력 손상 → `model_from_dict`가 거부 → `{ok:false, error}`.
- docx/pptx 미설치 → 기존 `ReportRendererUnavailable` 경로 재사용.

### 3.4 테스트
- Python: `model_json` 라운드트립; `emit_report_payload` JSON 스키마; render-model 정상/손상 입력; 혼합 수락/거부 병합 모델 렌더 정확성.
- TS: `mergeModel` 순수 함수 단위 테스트(수락/거부/bullets 조합); `BlockDiff` accept/reject 토글이 머지 결과를 바꾼다; "저장"이 올바른 병합 모델로 `renderReportModel` 호출.

---

## 4. 기능 3 — 환각·과장 방어 (수치 가드 + 모호어 린트)

기능 1의 emit 계약에 올라타되, **백엔드(①②③)는 독립적으로 먼저 동작 가능**(가드는 UI 없이도 조용히 원문 폴백).

### 4.1 ① 프롬프트 강화
- `polish.py:34-37`의 다듬기 프롬프트에 명시: "숫자·비율·금액·날짜·고유명사는 절대 변경하지 말고, 원문에 없는 사실이나 과장 표현을 새로 만들지 마. 군더더기만 덜어내고 의미는 그대로."

### 4.2 ② 결정론적 수치 가드 (신규, 단일 책임)
- 신규 파일: `vibelign/core/reporting_cli/polish_guard.py`
- `extract_numbers(text) -> set[str]`: 숫자·`%`·금액(만/억/원)·날짜를 정규식으로 추출.
- `guard_polished(original, polished) -> (ok: bool, reason, missing)`: 원본의 모든 수치가 polished에 보존되고 **새 수치가 없으면** ok. 아니면 실패 사유 반환.
- `polish_report_model`(`polish.py:53-81`)에 통합: 블록 다듬기 성공 후 `guard_polished` 통과 시에만 교체, 실패 시 **원문 유지 + guard 기록**. 가드 기록은 emit payload의 `guards[]`로 전달.
- 불변식: 가드는 **절대 렌더를 깨지 않는다** — 항상 안전한 원문으로 폴백.

### 4.3 ③ 모호어 린트 (신규, 단일 책임)
- 신규 파일: `vibelign/core/reporting_cli/vague_lint.py`
- 규칙 리스트(`대폭·대거·많이·크게·상당히·매우·획기적·혁신적·압도적` 등) → 최종 모델의 paragraph/summary 블록 스캔 → `[{section, block, term, offset}]`.
- **비차단**: 경고만. emit payload의 `vague_warnings[]`로 전달, 서브탭에서 하이라이트.
- 단어장 확장이 아니라 규칙 기반 표면화임에 유의(번역 단어장 금지 정책과 무관, 한국어 모호어 린트는 별개).

### 4.4 GUI 표시 (기능 1 화면에 슬롯)
- `BlockDiff`: guard 걸린 블록에 "숫자 보존됨" 배지 + 기본 결정=원본.
- vague 경고: 해당 블록 텍스트에 밑줄/하이라이트 + 툴팁.

### 4.5 테스트
- guard: `%` 누락→복원, 보존→통과, 새 숫자 주입→복원, 날짜 변경→복원.
- lint: 모호어 탐지·offset 정확, clean 텍스트→빈 배열.
- 프롬프트: 핵심 제약 문구 포함(contains) 가벼운 검증.

---

## 5. 의존성·순서

1. **기능 3 백엔드** (①②③: 프롬프트+`polish_guard.py`+`vague_lint.py`) — 기능 1과 독립. 가드는 UI 없이도 동작(조용한 원문 폴백). 먼저 머지 가능.
2. **공통 백본 + 기능 1** (`model_json.py`, emit/render 모드, 서브탭 diff UI) — emit payload에 `guards`/`vague_warnings` 슬롯 포함.
3. **기능 3 UI 표시** (배지·하이라이트) — 기능 1 화면 위에 얹음.

→ 구현 계획서는 2개:
- **Plan A (기능 1)**: 공통 백본 + 블록 diff 검토 화면.
- **Plan B (기능 3)**: 수치 가드 + 모호어 린트(백엔드) + 기능 1 화면 위 표시.

---

## 6. 구조화 규율 (구현 내내 준수 — 사용자 명시 요구 + CLAUDE.md)

- **가능한 가장 작은 패치.** 요청 파일만 수정, 무관 파일 금지, 파일 전체 재작성 금지.
- **앵커 경계 준수**: `ANCHOR: NAME_START`~`END` 사이만 수정. 작업 전 `.vibelign/project_map.json` 먼저 읽기.
- **진입 파일을 얇게**: `vib_report_cmd.py` 분기는 디스패치만, 로직은 `emit.py`/`polish_guard.py`/`vague_lint.py`로 위임.
- **단일 책임 모듈**: 직렬화/emit/가드/린트/머지를 각각 별도 파일로. 한 파일이 커지면 책임이 섞였다는 신호.
- **명확한 인터페이스**: 각 유닛은 "무엇을 하는가 / 어떻게 쓰는가 / 무엇에 의존하는가"가 한눈에. 내부를 안 읽어도 역할이 보이게.
- **새 파일은 설계에 명시된 것만** 생성(임의 생성 금지). 본 스펙이 명시한 신규 파일: `model_json.py`, `emit.py`, `polish_guard.py`, `vague_lint.py`(Python); `reportModel.ts`, `report-review/*`(TS).
- **임포트 구조 변경 금지**(명시 허락 없이).
- **순수 로직과 I/O 분리**: 머지·가드·린트는 순수 함수로 두어 단위 테스트 가능하게.
- **작업 흐름**: `vib anchor` → `vib checkpoint` → 작업 → `vib guard --strict` → `vib checkpoint`. 진짜 의사결정만 `transfer_set_decision`.

---

## 7. 계획에서 해소할 통합점 (열린 항목)

- **생성 진입 위치**: 현재 생성은 `ExportReportModal`, 보고서는 `ReportView` 서브탭으로도 승격됨. 리뷰가 `ReportView`로 가면서 **생성 진입을 모달→서브탭으로 옮길지** 기존 배선 확인 후 결정(설계는 "서브탭에 리뷰가 산다"까지 확정).
- **`runVib` stdin 지원**: §2.4 — 미지원 시 임시파일 폴백 채택.
- **포맷별 미리보기**: HTML은 자기완결 iframe 미리보기 가능, docx/pptx는 경로만(기존 모달 동작 유지).

---

## 8. 영향 받는 기존 파일 (참조)

| 레이어 | 파일:라인 | 역할 |
|---|---|---|
| 엔트리 | `vibelign/commands/vib_report_cmd.py:42-119` | emit/render 분기 추가 |
| CLI 등록 | `vibelign/cli/cli_command_groups.py` | `--emit-model`/`--render-model` 인자 |
| 모델 | `vibelign/core/reporting_cli/models.py` | `ReportModel/Section/Block`(변경 없음, 직렬화 대상) |
| polish | `vibelign/core/reporting_cli/polish.py:28-81` | 프롬프트 강화 + 가드 통합 |
| 캐시 | `vibelign/core/reporting_cli/polish_cache.py:13-58` | 직렬화 로직을 `model_json.py`로 추출·재사용 |
| 렌더 | `html_renderer.py`/`docx_renderer.py`/`pptx_renderer.py` | render 모드에서 재사용(변경 최소) |
| 저장 | `vibelign/core/reporting_cli/storage.py:54-125` | render 모드에서 재사용(변경 없음) |
| GUI 래퍼 | `vibelign-gui/src/lib/vib/report.ts` | emit/render 래퍼 추가 |
| GUI 화면 | `vibelign-gui/src/pages/ReportView.tsx` (+ `ExportReportModal.tsx`) | diff 검토 UI |
| 브리지 | `vibelign-gui/src-tauri/src/commands/vib_bridge.rs` | stdin 주입 확인(필요 시) |

신규 파일: `reporting_cli/model_json.py`, `reporting_cli/emit.py`, `reporting_cli/polish_guard.py`, `reporting_cli/vague_lint.py`, `lib/vib/reportModel.ts`, `components/report-review/{ReportDiffReview,BlockDiff}.tsx`, `components/report-review/useReviewState.ts`.
