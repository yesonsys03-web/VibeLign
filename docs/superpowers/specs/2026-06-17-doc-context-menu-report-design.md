# 우클릭 → 보고서 작성 (문서 / 코드탐색 탭) — 설계

- **작성일**: 2026-06-17
- **상태**: 설계 (구현 대기)
- **관련 스펙**: `2026-06-15-기획안-보고서-내보내기-design.md`, `2026-06-17-report-polish-diff-design.md`

## 1. 목표 (Goal)

DocsViewer("문서" 탭)와 CodeExplorer("코드탐색" 탭)에서 문서를 **우클릭하면 "보고서 작성"** 컨텍스트 메뉴가 나오고, 그 문서를 입력으로 기존 보고서 내보내기 흐름(`ExportReportModal`)이 열리도록 한다.

핵심 요구: **VibeLign 기획 양식이 아닌 임의의 기존 `.md` 문서도 보고서로 만들 수 있어야 한다.**

## 2. 배경 / 현재 상태 (Why this is non-trivial)

기존 보고서 엔진은 **기획 양식 헤딩만** 인식한다:

- `vibelign/core/reporting_cli/reader.py::parse_plan_markdown` 은 `## 한 줄 목표`, `## 핵심 기능` 등 고정 헤딩(`_FIELD_BY_HEADING`)에 매칭되는 본문만 `PlanningData` 필드로 추출하고, 그 외 줄은 버린다 (`reader.py:64` `if current is None: continue`).
- `templates.py::build_report_model` 은 `PlanningData` 필드를 보고서 타입별 템플릿(`work`/`proposal`/`result`) 섹션에 매핑한다.

결과: 임의의 `.md`(README, 노트, 일반 설계 문서)를 넣으면 인식 헤딩이 없어 **본문이 전부 사라지고 제목만 남은 빈 보고서**가 나온다. 따라서 "기존 md 문서도 가능" 요구는 기존 파이프라인 재사용만으로는 충족되지 않으며, **일반 마크다운 → 보고서** 변환 경로가 필요하다.

재사용 가능한 기존 자산(변경 없음):
- 프론트: `pages/ReportView.tsx`, `components/plan-doc/ExportReportModal.tsx`, `lib/vib/report.ts`
- 백엔드 렌더러: HTML/PDF/docx/pptx 렌더러, polish(어조 다듬기), page-number 스탬프 — 모두 `ReportModel` IR 위에서 동작
- 컨텍스트 메뉴 패턴: `components/code-explorer/CodeFileTree.tsx`(이미 `.md`/`.spec` 우클릭 → "기획방에서 검토")

## 3. 확정된 결정 (Decisions)

1. **변환 방식 = "둘 다 제공"**: 기본은 문서 구조 그대로 변환(LLM 불필요), 옵션으로 기존 "AI 다듬기"(per-block polish)를 켜면 어조 정리.
2. **AI = 기존 per-block polish 재사용** — 별도의 "기획 필드로 요약" 패스를 새로 만들지 않는다.
3. **트리거 흐름 = 기존 `ExportReportModal` 재사용** — 우클릭 → report 스테이지로 이동하며 그 문서를 source 로 채운 모달을 연다.
4. **`doc` = 새 보고서 타입** — `work` 를 오버로드하지 않는다.
5. **메뉴 노출 범위 = `.md` / `.markdown`** 문서만 (`.spec`/`.txt` 제외).

## 4. 아키텍처 (Architecture)

```
[DocsViewer / CodeExplorer 컨텍스트 메뉴]
        │  onGenerateReport(path)
        ▼
[App.tsx 상태: reportSourcePath] ──► navigate("report")
        ▼
[ReportView(sourcePath) → ExportReportModal(planPath=path, type="doc")]
        │  vib report <path> --type doc|work|proposal|result --format … [--polish]
        ▼
[Python CLI: --type doc 분기 → parse_generic_markdown → ReportModel]
        ▼
[기존 렌더러 (HTML/PDF/docx/pptx) + polish + page-number]  (변경 없음)
```

순 신규 로직은 **일반 마크다운 → ReportModel 변환** 하나뿐. 나머지는 배선(wiring)과 메뉴.

## 5. 컴포넌트 설계 (Components)

### 5.1 백엔드 — 일반 마크다운 보고서 (`--type doc`)

**신규 reader**: `reporting_cli/reader.py`(또는 신규 소모듈)에
`parse_generic_markdown(text: str) -> ReportModel` 추가.

- `# 제목` → `ReportModel.title`
- `##` / `###` → `Section.heading`
- 연속 단락 → `Block(kind="paragraph")`
- `-` / `*` / 번호 목록 → `Block(kind="bullets", items=[...])`
- 첫 헤딩 이전 본문(preamble)은 무제목 섹션 또는 도입 단락으로 보존 (빈 보고서 방지)
- 코드펜스(```), 표 등은 1차 범위에서 단순 텍스트 단락으로 보존(특수 렌더링은 비범위)

**CLI 분기**: `vibelign/commands/vib_report_cmd.py`
- `type == "doc"` 일 때 `parse_plan_markdown` + `build_report_model` 대신 `parse_generic_markdown` 으로 `ReportModel` 생성.
- ⚠️ **emit-model / polish / reject-blocks** 경로가 모델을 재빌드하는 지점이 2~3곳 존재 → 각 지점에 `type == "doc"` 분기를 동일하게 적용해야 함(메인 렌더 경로만 고치면 polish 시 빈 보고서 회귀).
- `report_type` 검증 화이트리스트에 `"doc"` 추가.

**polish 호환**: polish 는 `ReportModel` 블록 단위로 동작하므로 `doc` 모델에도 추가 코드 없이 적용됨.

### 5.2 프론트 — 컨텍스트 메뉴

- **CodeExplorer**: `components/code-explorer/CodeFileTree.tsx` 의 기존 메뉴(`.md`/`.spec`)에 **"보고서 작성" 버튼 추가** → 신규 prop `onGenerateReport?: (path: string) => void`. 단, 보고서 메뉴 항목은 `.md`/`.markdown` 에만 노출.
- **DocsViewer**: `DocsSidebar` 에 메뉴가 없음 → `CodeFileTree` 패턴을 그대로 복제(`onContextMenu` → `{x,y,path}` 상태, 전역 `mousedown`/`Escape` 해제)하여 "보고서 작성" 단일 항목 추가.

### 5.3 배선 / 내비게이션 (App.tsx)

- 신규 상태 `reportSourcePath: string | null`.
- 두 메뉴 콜백 모두 `reportSourcePath` 설정 + `navigate("report")` (기존 prop 전달 내비 패턴 유지, 라우터 변경 없음).
- `ReportView` 에 optional `sourcePath` prop 추가:
  - 있으면 저장된 plan 목록을 건너뛰고 `ExportReportModal` 을 `planPath = sourcePath`, 기본 `type = "doc"` 로 즉시 연다.
  - 없으면 기존 동작 그대로.
- 모달에서 사용자가 type 을 `work/proposal/result` 로 바꿀 수 있음(문서가 기획 양식일 때 유용).

## 6. 데이터 흐름 (Data flow)

1. 사용자가 `.md` 우클릭 → "보고서 작성"
2. `onGenerateReport(path)` → App `reportSourcePath=path` → `navigate("report")`
3. `ReportView` 가 `ExportReportModal` 을 `planPath=path, type="doc"` 로 오픈
4. 사용자가 포맷/테마/페이지번호/AI 다듬기 선택 → `lib/vib/report.ts` 가 `vib report <path> --type doc --format … [--polish]` 호출
5. CLI: `parse_generic_markdown(<path> 내용)` → `ReportModel` → 기존 렌더러 → `.vibelign/reports/` 출력
6. 기존 "내보내기" 로 사용자 폴더에 복사

## 7. 에러 처리 (Error handling)

- 빈/헤딩 없는 `.md`: preamble 보존 규칙으로 최소 1개 섹션 생성. 완전 빈 파일이면 명확한 에러 메시지("문서에 내보낼 내용이 없습니다").
- 문서 경로 접근: 기존 `docs_access.rs` 허용 확장자에 `.md`/`.markdown` 이미 포함(추가 작업 없음). 보고서 출력 prefix `.vibelign/reports/` 도 기존 허용.
- CLI 실패는 기존 `ReportResult` 에러 표면화 경로 재사용.

## 8. 테스트 (Testing)

- **Python 단위**: `parse_generic_markdown` — 헤딩→섹션, 중첩 헤딩, 불릿/번호 목록, preamble, 빈/엣지 케이스.
- **Python CLI**: `vib report --type doc` 를 실제 임의 `.md` 에 대해 — 일반/`--polish`/`--emit-model` 각 경로가 빈 보고서를 내지 않는지(회귀 가드).
- **기존 스위트 유지**: `tests/core/reporting_cli`, `tests/cli/test_vib_report_cmd.py` 그린.
- **프론트**: DocsSidebar 컨텍스트 메뉴 테스트(기존 `CodeFileTree` 커버리지 패턴 미러), CodeFileTree 의 신규 "보고서 작성" 항목.

## 9. 범위 밖 (Out of scope / YAGNI)

- 임의 md 를 LLM 으로 기획 필드(목표/기능/결정)로 요약·재구성하는 별도 패스.
- 코드펜스/표/이미지의 고급 렌더링.
- `.spec`/`.txt`/`.pdf`/`.docx` 등 비-마크다운 소스의 보고서화.
- 다중 문서 일괄 보고서.

## 10. 미해결/구현 시 확인 (Open items)

- `vib_report_cmd.py` 의 emit/polish/reject-blocks 분기 정확한 위치 식별(구현 시 코드 확인).
- `ExportReportModal` 이 `type="doc"` 일 때 work/proposal/result 전용 UI(예: 특정 섹션 토글)가 무의미하게 노출되지 않는지 점검.
