# report-writing-quality - Work Plan

## TL;DR (For humans)
**What you'll get:** 보고서 작성 전에 "이 보고서가 업무용으로 충분한가"를 점검하고, 부족한 독자/목적/근거/리스크/다음 액션을 AI가 보완 초안이나 질문으로 제안하는 단계가 생깁니다. 2,000줄급 긴 md 파일도 전체를 한 번에 AI에 던지지 않고 섹션별로 나눠 관련 근거만 찾아 보완합니다. 사용자가 승인한 보고서 메시지는 2D 웹툰/만화풍 카드 뉴스 이미지 세트로도 만들 수 있고, 카드의 글자는 이미지에 박지 않고 HTML/CSS 텍스트로 얹어 편집 가능하게 유지합니다. 기존 HTML/PDF 변환/Word/PPT 내보내기는 그대로 유지합니다.

**Why this approach:** 현재 보고서 기능은 내보내기와 디자인은 강하지만, 좋은 한국어 업무 보고서의 내용 조건을 구조화하지 못하고 부족한 내용을 채우도록 도와주지도 못합니다. 새 렌더러를 만들지 않고 기존 `vib report` 파이프라인 위에 결정론적 품질 프리플라이트와 사용자 확인 기반 AI 보완 흐름을 얹어 검증 가능하게 개선합니다.

**What it will NOT do:** 새 보고서 엔진이나 새 테마팩을 만들지 않습니다. AI가 근거/수치/결정을 몰래 지어내거나, 사용자 승인 없이 원문/보고서 초안을 바꾸지 않습니다. Word/PPT 인앱 미리보기는 이번 범위가 아닙니다.

**Effort:** Large
**Risk:** Medium - Python CLI, GUI, 타입 미러, 긴 md chunking, AI 보완, 이미지 provider adapter, 카드 뉴스 UI, 포맷별 QA가 함께 움직이므로 동기화 실수가 핵심 리스크입니다.
**Decisions I made for you:** 이 요청을 open-ended로 보고, 한국어 업무 보고서 기준의 deterministic quality preflight를 기본 방향으로 채택했습니다. 여기에 사용자 확인 기반 AI 보완을 추가하되, AI polish와 마찬가지로 명시적 opt-in으로 두고, CLI HTML/DOCX/PPTX 및 GUI HTML-to-PDF 기존 경로를 보존합니다.

Your next move: `$omo:start-work .omo/plans/report-writing-quality.md`로 실행을 시작하세요. Full execution detail follows below.

---

> TL;DR (machine): Large/Medium plan to add deterministic report-quality preflight, user-confirmed AI completion assistance, optional visual card-news generation, GUI pre-generation review, and cross-format parity QA without replacing existing renderers.

## Scope
### Must have
- Add a deterministic backend quality preflight for `vib report` that reports whether a generated report is business-report-ready before final render.
- Detect and serialize at least these finding categories: `missing_audience`, `missing_objective`, `missing_evidence`, `missing_decision_or_recommendation`, `missing_risk`, `missing_next_action`, `unresolved_questions`, `format_risk`.
- Define each quality finding with stable JSON fields: `code`, `severity`, `message`, `source`, optional `section`, optional `block`, optional `suggestion`, and `blocking`.
- Keep the preflight based on existing parsed `PlanningData` / `ReportModel` content, not on nondeterministic LLM output.
- Add a user-confirmed AI completion step after deterministic diagnosis: missing fields can generate draft text, source-based candidate snippets, or user questions, and each item must be accepted, edited, or rejected before report generation uses it.
- For unsupported evidence, numbers, decisions, risks, owners, or dates, AI must ask the user or mark the text as a draft suggestion; it must not silently invent factual content.
- Support long planning/md files of at least 2,000 lines by deterministic section chunking, source indexing, and relevant-chunk retrieval before any AI completion prompt.
- Add an optional report-matched visual card-news output: 3-6 cards derived from approved report messages, generated 2D webtoon/business-comic illustration assets, and editable HTML/CSS text overlays.
- Use an image-provider adapter so imagen2 or another generation backend can be swapped; automated tests must use a fake provider and never require network/model access.
- Expose the quality report through the existing `--emit-model --json` flow as a sidecar field named `quality`; do not add a separate report command family and do not put quality fields inside `ReportModel`.
- Mirror the quality and AI completion payloads in TypeScript with strict types and parser helpers.
- Add a GUI pre-generation review panel in the existing report-writing surface so users see warnings, request AI help, review suggested additions, and then generate/export.
- Preserve current behavior for direct `vib report ... --format html|docx|pptx`, GUI HTML/PDF/Word/PPT exports, theme/font/font-size/page-number options, and AI polish review.
- Treat PDF as the existing GUI/Tauri HTML-to-PDF conversion path, not as a backend `vib report --format pdf` renderer.
- Add tests and real-surface QA evidence for backend, CLI JSON, GUI wiring, and CLI HTML/DOCX/PPTX plus GUI PDF conversion parity.

### Quality JSON contract
- Top-level sidecar shape: `quality: { schema_version: "report-quality-v1", status, score, readiness, summary, findings }`.
- Allowed top-level `status` values: `"ok"`, `"warn"`, `"block"`.
- `score` is an integer from 0 to 100 computed only from deterministic rubric checks; no LLM confidence, timestamp, or rendered-output inspection is allowed.
- Allowed `readiness` values: `"ready"`, `"needs_review"`, `"blocked"`.
- Each finding shape: `{ code, severity, message, source, blocking, section?, block?, suggestion? }`.
- Allowed finding `severity` values: `"info"`, `"warn"`, `"block"`.
- Required finding `code` values at launch: `missing_audience`, `missing_objective`, `missing_evidence`, `missing_decision_or_recommendation`, `missing_risk`, `missing_next_action`, `unresolved_questions`, `format_risk`, `parser_confidence`, `empty_content`.
- Allowed finding `source` values: `"planning_data"`, `"report_model"`, `"reader"`, `"template"`, `"format"`.
- Unknown backend finding codes must be preserved in JSON and rendered in TypeScript with a generic label; unknown top-level status/severity must normalize to `"warn"` without throwing.

### AI completion contract
- AI completion runs after deterministic quality diagnosis and before final render.
- Top-level sidecar shape: `assistance: { schema_version: "report-assist-v1", status, suggestions, questions, applied_suggestion_ids }`.
- Allowed `assistance.status` values: `"not_requested"`, `"ready"`, `"needs_user_input"`, `"failed"`.
- Each suggestion shape: `{ id, finding_code, kind, title, proposed_text, rationale, source_refs, requires_user_confirmation }`.
- Allowed suggestion `kind` values: `"draft_text"`, `"source_candidate"`, `"user_question"`, `"risk_candidate"`, `"next_action_candidate"`.
- Suggestions are never applied automatically. GUI must show accept, edit, reject, and generate-without-this controls per suggestion.
- Questions must be preferred over fabricated content when a missing field requires facts outside the selected plan/md file.
- Applying suggestions creates an in-memory/report-session working draft; the original md file is unchanged unless a later explicit save-back feature is approved.

### Long-source handling contract
- Long source threshold: any selected plan/md file over 600 lines or 40,000 characters must use chunked assistance mode.
- Chunking must preserve Markdown heading hierarchy and line ranges: `{ chunk_id, heading_path, start_line, end_line, text, signals }`.
- Chunk size target: 120-220 lines with overlap of heading context only; never split inside fenced code blocks or tables when avoidable.
- Build a deterministic source index before AI calls: title, heading path, detected report signals, keywords, and line ranges.
- For each missing quality finding, retrieve at most 5 relevant chunks plus the document title/outline. AI prompts receive only those chunks, not the full md.
- Suggestions must include `source_refs` with chunk ids and line ranges; suggestions without enough source support must become `user_question` items.
- Add a regression fixture with at least 2,000 lines where evidence appears outside the first and last 200 lines.

### Visual card-news contract
- Visual cards are optional companion output, not required for plain report generation.
- Top-level sidecar shape: `visual_cards: { schema_version: "report-visual-cards-v1", status, cards, assets }`.
- Generate 3-6 cards from approved report summary, decisions, evidence, risk, and next-action sections.
- Each card shape: `{ id, title, body, visual_prompt, negative_prompt, source_refs, image_asset_path?, approved }`.
- `visual_prompt` must describe only the illustration layer in a generic 2D webtoon/business comic style and must include `no readable text in image`.
- `title`, `body`, metrics, and captions are rendered by the GUI with HTML/CSS overlays, never by the image model.
- User controls per card: regenerate image, edit text, delete card, approve card.
- Exported visual-card evidence must include the JSON card plan and at least one rendered card screenshot or PNG produced with a fake image asset in tests.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Do not replace `vibelign/core/reporting_cli/html_renderer.py`, `docx_renderer.py`, `pptx_renderer.py`, or `render_job.py` with a new rendering pipeline.
- Do not make quality diagnosis depend on calling Claude, Codex, OpenCode, Agy, or any API.
- Do not make AI completion automatic. It must be a visible user action and must use the existing official CLI/provider subprocess pattern when available, not API-key orchestration.
- Do not pass the full md source to an AI provider in one prompt for long files. Do not use head/tail truncation as the long-file strategy.
- Do not let AI modify the original plan/md source file unless a separate explicit save-back action is implemented and confirmed by the user. Default application target is the report working draft only.
- Do not let AI invent unsupported evidence, numbers, dates, owners, or decisions. If the source material is missing facts, create a question or clearly marked draft assumption for user approval.
- Do not bake Korean report copy, numbers, factual claims, or source citations into generated image pixels. Images are illustration layers only; all card text must remain selectable/editable UI text.
- Do not imitate living artists, copyrighted characters, private persons, or real brand styles. Use generic style labels such as `2d_webtoon_business` or `clean_comic_editorial`.
- Do not hard-code a single image model such as imagen2; keep visual generation behind an image-provider adapter with fake-provider tests.
- Do not add `vib report --format pdf`; PDF remains `generateReportPdf()` creating HTML and calling Tauri `export_report_pdf`.
- Do not add `quality` fields to `ReportModel` or `model_json.py` roundtrip data; keep it as an emit sidecar.
- Do not alter the Satgat-inspired theme catalog or report font catalog except where a test fixture must select an existing theme/font.
- Do not grow `vibelign-gui/src/components/plan-doc/ReportComposer.tsx`, `vibelign/commands/vib_report_cmd.py`, or `vibelign/cli/cli_command_groups.py` into catch-all files; extract new quality logic into focused modules/components.
- Do not block all report generation for warnings. Only `empty_content` / selected report type producing zero sections may be blocking; other quality issues are warnings with an explicit "generate anyway" path.
- Do not add Word/PPT in-app preview. Validate those formats through generated files and extracted content.
- Do not weaken existing AI polish guard behavior, cache-key behavior, or reject-block replay behavior.
- Do not add broad docs/release churn outside the report-quality feature.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD for new backend quality logic and TS parser/state helpers; tests-after for React integration around existing components after the UI shape is wired.
- Python unit/CLI commands:
  - `python3 -m pytest tests/core/reporting_cli/test_report_quality.py tests/core/reporting_cli/test_report_assist.py tests/core/reporting_cli/test_report_visual_cards.py tests/core/reporting_cli/test_emit.py tests/core/reporting_cli/test_model_json.py tests/cli/test_vib_report_cmd.py -v`
  - `python3 -m pytest tests/core/reporting_cli/test_html_renderer.py tests/core/reporting_cli/test_docx_renderer.py tests/core/reporting_cli/test_pptx_renderer.py -v`
  - `python3 -m compileall vibelign/core/reporting_cli vibelign/commands`
- GUI unit commands:
  - `cd vibelign-gui && npm run test -- src/lib/vib/__tests__/reportQuality.test.ts src/lib/vib/__tests__/reportAssist.test.ts src/lib/vib/__tests__/reportVisualCards.test.ts src/lib/vib/__tests__/report.test.ts src/components/plan-doc/__tests__/ReportQualityPanel.test.tsx src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx src/components/plan-doc/__tests__/ExportReportModal.test.tsx src/pages/__tests__/ReportView.test.tsx`
  - `cd vibelign-gui && npm run build`
- CLI real-surface evidence:
  - `mkdir -p .omo/evidence/report-writing-quality`
  - `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type work --emit-model --json > .omo/evidence/report-writing-quality/cli-sparse-preflight.json`
  - `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --emit-model --json > .omo/evidence/report-writing-quality/cli-complete-preflight.json`
  - `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type work --assist-missing --json > .omo/evidence/report-writing-quality/cli-sparse-assist.json`
  - `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format html --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/cli-html-render.json`
  - `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format docx --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/cli-docx-render.json`
  - `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format pptx --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/cli-pptx-render.json`
  - `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --visual-cards --json > .omo/evidence/report-writing-quality/cli-visual-cards.json`
- GUI/Tauri-path evidence with available repo tooling:
  - `cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ReportQualityPanel.test.tsx src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx src/components/plan-doc/__tests__/ExportReportModal.test.tsx src/pages/__tests__/ReportView.test.tsx`
  - `cd vibelign-gui && npm run test -- src/lib/vib/__tests__/report.test.ts src/lib/vib/__tests__/reportVisualCards.test.ts`
  - GUI tests must make `quality_sparse.md` and `quality_complete.md` reachable through `ReportView` by mocking `listPlanningChatSessions` and/or passing `sourcePath`; do not rely on a manually preexisting session list.
  - AI completion evidence must prove a missing-evidence case yields a user question or editable draft suggestion, and that rejecting it still allows generate-without-this while accepting it changes only the report working draft.
  - Visual-card evidence must prove card copy remains editable HTML/CSS text overlay, fake image assets are used in tests, per-card approve/delete/regenerate controls work, and image prompts include `no readable text in image`.
  - PDF evidence must exercise `generateReportPdf()` and assert it renders HTML first, calls Tauri `invoke("export_report_pdf", ...)`, and never calls CLI `--format pdf`.
- Evidence: each todo below names a specific `.omo/evidence/report-writing-quality/task-N-...` artifact.

## Execution strategy
### Parallel execution waves
- Wave 1: Backend contract and fixtures. Todos 1-3 are mostly Python and can run in sequence because the emit contract depends on the quality model.
- Wave 2: TypeScript contract and GUI review surface. Todos 4-6 depend on Wave 1 payload shape; Todo 4 can start once the payload schema is stable.
- Wave 3: Cross-format parity, optional visual cards, docs/manual copy, and final QA. Todos 7-9 depend on both backend and GUI wiring.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | None | 2, 3, 4, 7, 8 | None |
| 2 | 1 | 3, 4, 7, 8 | None |
| 3 | 2 | 4, 7, 8 | None |
| 4 | 2, 3 | 5, 6, 8 | None |
| 5 | 4 | 6, 8, 9 | None |
| 6 | 5 | 7, 8, 9 | None |
| 7 | 3, 6 | 9 | None |
| 8 | 3, 4, 6 | 9 | None |
| 9 | 7, 8 | Final verification wave | None |

## Todos
> Implementation + Test = ONE todo. Never separate.
- [x] 1. Add deterministic report quality model, rubric, and shared fixtures
  What to do / Must NOT do: Create `vibelign/core/reporting_cli/report_quality.py` with dataclasses or typed dict builders for `ReportQuality`, `ReportQualityFinding`, top-level status (`ok|warn|block`), finding severity (`info|warn|block`), score buckets, readiness labels, and `analyze_report_quality(data: PlanningData, model: ReportModel, report_type: str) -> ReportQuality`. Implement exactly the Quality JSON contract above. Add shared fixtures `tests/fixtures/reporting_cli/quality_sparse.md`, `tests/fixtures/reporting_cli/quality_complete.md`, and `tests/fixtures/reporting_cli/quality_long_2000.md`, then add `tests/core/reporting_cli/test_report_quality.py` using those fixtures plus direct model builders. The sparse fixture must omit evidence, audience, risks, and next actions. The complete fixture must contain Korean business-report-ready content: goal, audience, problem/background, evidence or metric, decision/recommendation, risk, next action, and exclusions. The long fixture must be at least 2,000 lines and place critical evidence/risk/next-action material in middle sections, not only the first or last 200 lines. Detect at minimum `missing_audience`, `missing_objective`, `missing_evidence`, `missing_decision_or_recommendation`, `missing_risk`, `missing_next_action`, `unresolved_questions`, `format_risk`, parser-confidence issues for dropped/unknown sections, and `empty_content`. Scan bullets as well as paragraph/summary text for evidence/action/risk cues. Must NOT call any LLM, mutate `ReportModel`, alter `model_json.py`, or inspect rendered HTML.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 2, 3, 4, 7, 8
  References (executor has NO interview context - be exhaustive): `vibelign/core/reporting_cli/models.py:7-55`, `vibelign/core/reporting_cli/templates.py:23-103`, `vibelign/core/reporting_cli/reader.py:8-83`, `vibelign/core/reporting_cli/vague_lint.py:14-27`, `tests/core/reporting_cli/test_templates.py:19-54`, `.omo/drafts/report-writing-quality.md:14-29`.
  Acceptance criteria (agent-executable): `python3 -m pytest tests/core/reporting_cli/test_report_quality.py -v` exits 0; `test_report_quality.py` reads all three shared fixture files; sparse fixture returns `status == "warn"` or `"block"` with `missing_audience`, `missing_evidence`, `missing_risk`, and `missing_next_action`; complete fixture returns no `missing_audience`, `missing_objective`, `missing_evidence`, `missing_decision_or_recommendation`, `missing_risk`, or `missing_next_action`; long fixture proves middle-of-file evidence is detected and is not missed by truncation; `empty_content` is the only default blocking category; every finding has `code`, `severity`, `message`, `source`, and `blocking`.
  QA scenarios (name the exact tool + invocation): Happy: run `mkdir -p .omo/evidence/report-writing-quality && python3 - <<'PY' > .omo/evidence/report-writing-quality/task-1-quality-complete.json
import json
from vibelign.core.reporting_cli.models import Block, PlanningData, ReportModel, Section
from vibelign.core.reporting_cli.report_quality import analyze_report_quality, quality_to_dict

data = PlanningData(
    title="예약 앱 개선 제안",
    idea="전화 예약 누락을 줄이기 위해 예약 캘린더와 알림을 도입한다.",
    target_users="동네 미용실 사장님과 예약 담당 직원",
    problem="전화 예약 누락률이 최근 4주 평균 12%까지 증가했다.",
    features=["예약 캘린더", "예약 전날 알림", "노쇼 위험 안내"],
    decisions=["MVP는 예약 캘린더와 알림부터 출시한다."],
    open_questions=[],
    context_notes="근거: 최근 4주 예약 메모 120건 중 누락 14건. 리스크: 직원 교육 지연 시 도입률이 낮아진다. 다음 액션: 6월 30일까지 직원 2명 파일럿.",
)
model = ReportModel(
    title=data.title,
    report_type="proposal",
    date="2026-06-20",
    sections=[
        Section("제안 요약", [Block("summary", text=data.idea)]),
        Section("대상", [Block("paragraph", text=data.target_users)]),
        Section("근거", [Block("paragraph", text=data.context_notes)]),
        Section("주요 결정", [Block("bullets", items=data.decisions)]),
    ],
)
payload = quality_to_dict(analyze_report_quality(data, model, "proposal"))
assert payload["status"] in {"ok", "warn"}
codes = {item["code"] for item in payload["findings"]}
assert "missing_evidence" not in codes
assert "missing_risk" not in codes
assert "missing_next_action" not in codes
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY`; PASS means JSON is written and assertions hold. Failure: run `mkdir -p .omo/evidence/report-writing-quality && python3 - <<'PY' > .omo/evidence/report-writing-quality/task-1-quality-sparse.json
import json
from vibelign.core.reporting_cli.models import PlanningData, ReportModel
from vibelign.core.reporting_cli.report_quality import analyze_report_quality, quality_to_dict

data = PlanningData(title="예약 앱", idea="예약 앱을 만든다.")
model = ReportModel(title="예약 앱", report_type="work", date="2026-06-20", sections=[])
payload = quality_to_dict(analyze_report_quality(data, model, "work"))
codes = {item["code"] for item in payload["findings"]}
assert "missing_evidence" in codes
assert "missing_risk" in codes
assert "missing_next_action" in codes
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY`; PASS means sparse JSON includes the required warning codes.
  Commit: Y | `feat(reporting): add deterministic report quality preflight`

- [x] 2. Thread quality and default assistance sidecars through emit-model JSON without breaking existing consumers
  What to do / Must NOT do: Update `vibelign/core/reporting_cli/emit.py` so every `emit_report_payload(...)` response includes a JSON-safe `quality` sidecar computed from the base model and parsed source data plus `assistance: { schema_version: "report-assist-v1", status: "not_requested", suggestions: [], questions: [], applied_suggestion_ids: [] }`. Keep existing `ok`, `report_type`, `slug`, `key`, `base`, `polished`, `guards`, and `vague_warnings` fields unchanged. Add or update tests in `tests/core/reporting_cli/test_emit.py`, `tests/core/reporting_cli/test_model_json.py`, and `tests/cli/test_vib_report_cmd.py`. Must NOT require a new CLI flag for GUI preflight; `vib report PLAN_PATH --type T --emit-model --json` is the contract. Must prove `model_to_dict()` / `model_from_dict()` still roundtrip only `ReportModel`, with no quality or assistance sidecar inside the model.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 3, 4, 7, 8
  References (executor has NO interview context - be exhaustive): `vibelign/core/reporting_cli/emit.py:18-61`, `vibelign/commands/vib_report_cmd.py:126-140`, `tests/core/reporting_cli/test_emit.py:16-58`, `tests/cli/test_vib_report_cmd.py:253-290`, `vibelign/core/reporting_cli/model_json.py:9-60`, `tests/core/reporting_cli/test_model_json.py:22-42`.
  Acceptance criteria (agent-executable): `python3 -m pytest tests/core/reporting_cli/test_emit.py tests/core/reporting_cli/test_model_json.py tests/cli/test_vib_report_cmd.py -v` exits 0; existing emit tests still pass; new assertions prove `payload["quality"]["findings"]` exists, `payload["assistance"]["status"] == "not_requested"`, and neither sidecar changes `payload["base"] == payload["polished"]` when polish is false; `test_model_json.py` proves `model_to_dict()` / `model_from_dict()` do not serialize `quality` or `assistance` inside `ReportModel`.
  QA scenarios (name the exact tool + invocation): Happy: `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --emit-model --json > .omo/evidence/report-writing-quality/task-2-emit-complete.json`; PASS means JSON has `ok:true`, `quality.status`, `assistance.status:"not_requested"`, and no missing required categories. Failure: `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type work --emit-model --json > .omo/evidence/report-writing-quality/task-2-emit-sparse.json`; PASS means JSON has `ok:true` plus quality warnings and empty assistance suggestions, proving preflight does not fail the CLI or silently call AI.
  Commit: Y | `feat(reporting): expose report quality and assistance sidecars`

- [x] 3. Expand backend parity checks and add guarded AI completion generation
  What to do / Must NOT do: Reuse the fixtures created in Todo 1 and add backend tests proving the analyzer works for `work`, `proposal`, `result`, and `doc` where applicable. Include a parser-confidence regression for unrecognized/dropped sections and a bullet-scanning regression for evidence/action/risk cues. Add `vibelign/core/reporting_cli/source_chunks.py` or equivalent focused module for the Long-source handling contract, then add `vibelign/core/reporting_cli/report_assist.py` and an explicit opt-in CLI path such as `vib report PLAN_PATH --type T --assist-missing --json` that takes deterministic quality findings plus parsed source index/chunks and returns the AI completion contract. It may use the existing official CLI/provider subprocess pattern already used by polish, but tests must inject a fake provider and must not call network/API. It must prefer `user_question` suggestions when the selected plan/md lacks source facts for evidence, numbers, decisions, owners, or dates. Must NOT make tests assert exact prose from AI polish, silently apply suggestions to `ReportModel`, or send a 2,000-line source file as one AI prompt.
  Parallelization: Wave 1 | Blocked by: 2 | Blocks: 4, 7, 8
  References (executor has NO interview context - be exhaustive): `tests/core/reporting_cli/test_reader.py:32-163`, `tests/core/reporting_cli/test_templates.py:19-54`, `vibelign/core/reporting_cli/reader.py:43-178`, `vibelign/core/reporting_cli/templates.py:23-103`, `vibelign/core/reporting_cli/polish.py:33-112`, `vibelign/core/reporting_cli/polish_guard.py:26-67`.
  Acceptance criteria (agent-executable): `python3 -m pytest tests/core/reporting_cli/test_report_quality.py tests/core/reporting_cli/test_report_assist.py tests/core/reporting_cli/test_reader.py tests/core/reporting_cli/test_templates.py -v` exits 0; report-type parity tests use the Todo 1 fixtures; assist tests prove sparse input yields at least one `user_question`, complete input yields no fabricated unsupported evidence, long input creates multiple chunks with stable line ranges, retrieved chunks include the middle-of-file evidence section, and fake-provider output is guarded before serialization.
  QA scenarios (name the exact tool + invocation): Happy: `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_long_2000.md --type work --assist-missing --json > .omo/evidence/report-writing-quality/task-3-assist-long.json`; PASS means assistance output includes `source_refs` pointing to middle-of-file line ranges and no prompt contains the full 2,000-line source. Failure: `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type proposal --assist-missing --json > .omo/evidence/report-writing-quality/task-3-assist-sparse.json`; PASS means output includes `assistance.status:"needs_user_input"` and a `user_question` for missing evidence or next action without process failure.
  Commit: Y | `feat(reporting): add guarded report assistance suggestions`

- [x] 4. Mirror quality and AI completion payloads in TypeScript report wrappers
  What to do / Must NOT do: Add `vibelign-gui/src/lib/vib/reportQuality.ts` for strict TS types, severity helpers, category labels, and a parser/normalizer for backend `quality`. Add `vibelign-gui/src/lib/vib/reportAssist.ts` for `ReportAssistPayload`, `ReportAssistSuggestion`, `ReportAssistSourceRef`, suggestion kind labels, safe parser/normalizer, and helper state for accepted/edited/rejected suggestions. Update `vibelign-gui/src/lib/vib/reportModel.ts` only as needed to include `quality` and `assistance` on `EmitPayload`, not on `RModel`. Update `vibelign-gui/src/lib/vib/report.ts` tests so `emitReportModel(...)` preserves both sidecars and a new explicit wrapper such as `requestReportAssistance(...)` calls the opt-in assist CLI path. Must NOT use `any`, suppress TS errors, or let unknown categories crash the UI; unknown categories should render with a generic label and raw category preserved, and unknown top-level `quality.status`, `assistance.status`, suggestion `kind`, finding `severity`, or malformed `source_refs` must normalize to safe warning UI data without throwing.
  Parallelization: Wave 2 | Blocked by: 2, 3 and stable payload shape | Blocks: 5, 6, 8
  References (executor has NO interview context - be exhaustive): `vibelign-gui/src/lib/vib/reportModel.ts:1-34`, `vibelign-gui/src/lib/vib/report.ts:208-231`, `vibelign-gui/src/lib/vib/__tests__/report.test.ts:194-205`, `vibelign-gui/src/lib/vib/reportFontSizes.ts:1-36` as an example of small typed helper module.
  Acceptance criteria (agent-executable): `cd vibelign-gui && npm run test -- src/lib/vib/__tests__/reportQuality.test.ts src/lib/vib/__tests__/reportAssist.test.ts src/lib/vib/__tests__/report.test.ts` exits 0; `npm run build` has no TypeScript errors related to report quality or assistance; parser tests prove unknown finding codes, unknown top-level `quality.status`, unknown `assistance.status`, unknown suggestion `kind`, unknown finding `severity`, and malformed long-source refs all normalize to safe warning UI data without throwing.
  QA scenarios (name the exact tool + invocation): Happy: `mkdir -p .omo/evidence/report-writing-quality && cd vibelign-gui && npm run test -- src/lib/vib/__tests__/reportQuality.test.ts src/lib/vib/__tests__/reportAssist.test.ts > ../.omo/evidence/report-writing-quality/task-4-ts-quality-assist-test.txt`; PASS means labels, severity sort, assist suggestion state, and parser behavior are covered. Failure: `mkdir -p .omo/evidence/report-writing-quality && cd vibelign-gui && npm run test -- src/lib/vib/__tests__/reportAssist.test.ts -t "keeps assistance suggestions user-confirmed" > ../.omo/evidence/report-writing-quality/task-4-ts-assist-confirmation.txt`; PASS means parser returns safe warning objects, rejected suggestions are not applied, and accepted/edited suggestions are tracked by id.
  Commit: Y | `feat(gui-report): add typed report quality and assistance payloads`

- [x] 5. Add reusable GUI quality and AI completion review panel
  What to do / Must NOT do: Create `vibelign-gui/src/components/plan-doc/ReportQualityPanel.tsx` and tests in `vibelign-gui/src/components/plan-doc/__tests__/ReportQualityPanel.test.tsx`. The panel must show quality status, score or readiness label, finding list grouped by severity, concrete next action text, and a clear generate-anyway affordance for warnings. Add an AI help area inside the same panel or a small sibling component that lets the user request completion suggestions, then accept, edit, reject, or answer generated questions per suggestion. It must clearly distinguish source-backed candidate text from user-input-needed questions and show source refs as compact line-range chips such as `기획안 842-870줄`. For long md files, show that only relevant sections are being analyzed instead of pretending the whole file is sent at once. It must not mention internal test names or implementation details. Use compact operational UI consistent with existing report controls, not a marketing/landing-page layout.
  Parallelization: Wave 2 | Blocked by: 4 | Blocks: 6, 8, 9
  References (executor has NO interview context - be exhaustive): `vibelign-gui/src/components/plan-doc/ReportComposer.tsx:205-310`, `vibelign-gui/src/components/plan-doc/ReportComposer.tsx:370-429`, `vibelign-gui/src/components/report-review/ReportDiffReview.tsx:15-73`, `vibelign-gui/src/components/plan-doc/ReportFontSizeControls.tsx:16-44`.
  Acceptance criteria (agent-executable): `cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ReportQualityPanel.test.tsx` exits 0; tests cover ok, warning, blocking, unknown category, keyboard-accessible generate-anyway/cancel actions, request-AI-help loading/error states, accept/edit/reject suggestion controls, user-question answer capture, and rendering long-source line refs without layout overflow.
  QA scenarios (name the exact tool + invocation): Happy: `mkdir -p .omo/evidence/report-writing-quality && cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ReportQualityPanel.test.tsx > ../.omo/evidence/report-writing-quality/task-5-panel-test.txt`; PASS means warning panel renders labels, AI help suggestions, and invokes `onProceed` only with accepted/edited suggestions. Failure: `mkdir -p .omo/evidence/report-writing-quality && cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ReportQualityPanel.test.tsx -t "requires confirmation before applying assistance" > ../.omo/evidence/report-writing-quality/task-5-panel-assist-confirmation.txt`; PASS means rejected suggestions are not applied, blocking `empty_content` still disables final generate, and recovery guidance is shown.
  Commit: Y | `feat(gui-report): add report quality and assistance review panel`

- [x] 6. Wire pre-generation quality review and user-confirmed AI completion into ReportComposer and ReportView
  What to do / Must NOT do: Update `ReportComposer` so `handleGenerate` uses `emitReportModel(cwd, planPath, reportType, false, author)` as a preflight before final render. If quality status is `block`, stop and show `ReportQualityPanel`. If status is `warn`, stop and show the panel with a "generate anyway" action that resumes the same generation settings without re-losing selected format/theme/font/page-number options. Add an explicit "AI로 보완 초안 만들기" style action that calls `requestReportAssistance(...)` only after the user clicks it. Accepted/edited suggestions should build a report-session working draft passed into final generation or render decisions; rejected suggestions and unanswered questions must not alter output. If status is `ok`, proceed directly unless the user requests AI help. For long md files, keep the UI responsive while chunk indexing/assist runs, show progress/loading copy, and verify the request uses the assist wrapper rather than sending full file content through React state. Preserve the existing empty-section confirm behavior or fold it into the `block` path without losing the "문서 그대로로 변경" recovery. Keep AI polish behavior: if polish is on and user proceeds, route to existing block diff review after accepted assistance is applied. Update `ReportView` tests for `sourcePath`, `onSourceHandled`, review handoff, quality panel flow, AI assistance request, long-source assistance request, and accept/edit/reject behavior. In tests, make `quality_complete.md`, `quality_sparse.md`, and `quality_long_2000.md` reachable by mocking `listPlanningChatSessions` with those exact `outputPath` values and by adding a `sourcePath` entry test; do not depend on a live user's report list.
  Parallelization: Wave 2 | Blocked by: 5 | Blocks: 7, 8, 9
  References (executor has NO interview context - be exhaustive): `vibelign-gui/src/components/plan-doc/ReportComposer.tsx:137-203`, `vibelign-gui/src/components/plan-doc/ReportComposer.tsx:321-429`, `vibelign-gui/src/pages/ReportView.tsx:47-89`, `vibelign-gui/src/pages/ReportView.tsx:91-182`, `vibelign-gui/src/components/plan-doc/__tests__/ExportReportModal.test.tsx:56-224`, `vibelign-gui/src/pages/__tests__/ReportView.test.tsx:20-34`.
  Acceptance criteria (agent-executable): `cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ExportReportModal.test.tsx src/pages/__tests__/ReportView.test.tsx` exits 0; tests prove warning preflight pauses generation, generate-anyway calls the same export function with original options, block preflight prevents render, AI help is never called before the user requests it, accepted/edited assistance changes only the report working draft, rejected assistance is ignored, `ReportView` tests use the current inline `ReportComposer` instead of stale `ExportReportModal` mocks, and polish still routes to `onReviewRequest` after user proceeds.
  QA scenarios (name the exact tool + invocation): Happy: run `mkdir -p .omo/evidence/report-writing-quality && cd vibelign-gui && npm run test -- src/pages/__tests__/ReportView.test.tsx -t "quality_complete sourcePath opens ReportComposer and generates preview" > ../.omo/evidence/report-writing-quality/task-6-complete-generate.txt`; PASS means the test renders `ReportView projectDir="/proj" sourcePath="tests/fixtures/reporting_cli/quality_complete.md"`, calls `onSourceHandled`, opens the real inline `ReportComposer`, clicks `보고서 생성`, and observes `보고서 미리보기`. Failure: run `mkdir -p .omo/evidence/report-writing-quality && cd vibelign-gui && npm run test -- src/pages/__tests__/ReportView.test.tsx src/components/plan-doc/__tests__/ExportReportModal.test.tsx -t "quality_sparse AI assistance requires user confirmation" > ../.omo/evidence/report-writing-quality/task-6-sparse-assist-confirmation.txt`; PASS means mocked `emitReportModel` returns quality warnings, `requestReportAssistance` is called only after explicit user action, missing evidence becomes a user question or editable suggestion, and no iframe/file path appears until generate-anyway or accepted assistance is applied.
  Commit: Y | `feat(gui-report): gate report generation with quality and assistance review`

- [x] 7. Prove cross-format parity and preserve existing render options
  What to do / Must NOT do: Add or update tests proving quality metadata does not alter final rendered content unless the user proceeds. Verify CLI HTML, GUI PDF-via-HTML path, DOCX, and PPTX can still render complete fixture content with existing theme, font, font-size, author, and page-number options. For DOCX/PPTX, inspect generated package text using existing test helpers or standard libraries; do not rely only on file extension. Must NOT require Word/PPT desktop apps or add backend `--format pdf`.
  Parallelization: Wave 3 | Blocked by: 3, 6 | Blocks: 9
  References (executor has NO interview context - be exhaustive): `vibelign/core/reporting_cli/html_renderer.py:48-73`, `vibelign/core/reporting_cli/docx_renderer.py:47-126`, `vibelign/core/reporting_cli/pptx_renderer.py:32-105`, `vibelign/core/reporting_cli/render_job.py:36-69`, `tests/core/reporting_cli/test_html_renderer.py`, `tests/core/reporting_cli/test_docx_renderer.py`, `tests/core/reporting_cli/test_pptx_renderer.py`, `vibelign-gui/src/lib/vib/report.ts:120-205`, `vibelign-gui/src-tauri/src/commands/report_pdf.rs:189-230`.
  Acceptance criteria (agent-executable): `python3 -m pytest tests/core/reporting_cli/test_html_renderer.py tests/core/reporting_cli/test_docx_renderer.py tests/core/reporting_cli/test_pptx_renderer.py tests/cli/test_vib_report_cmd.py -v` exits 0; direct CLI generation commands for html/docx/pptx complete fixture all return JSON `ok:true`; generated files contain the Korean title and at least one evidence/next-action phrase; `cd vibelign-gui && npm run test -- src/lib/vib/__tests__/report.test.ts -t "generateReportPdf uses html render then export_report_pdf"` exits 0.
  QA scenarios (name the exact tool + invocation): Happy: run `mkdir -p .omo/evidence/report-writing-quality && bash -lc 'set -euo pipefail
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format html --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/task-7-html.json
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format docx --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/task-7-docx.json
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format pptx --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/task-7-pptx.json
python3 - <<PY > .omo/evidence/report-writing-quality/task-7-content-check.txt
import json, zipfile
from pathlib import Path

expected = ["예약", "근거"]
for name in ("html", "docx", "pptx"):
    payload = json.loads(Path(f".omo/evidence/report-writing-quality/task-7-{name}.json").read_text(encoding="utf-8"))
    assert payload["ok"] is True, payload
    path = Path(payload["path"])
    assert path.exists(), path
    if name == "html":
        text = path.read_text(encoding="utf-8")
    else:
        with zipfile.ZipFile(path) as zf:
            text = "\n".join(
                zf.read(member).decode("utf-8", "ignore")
                for member in zf.namelist()
                if member.endswith(".xml")
            )
    assert any(token in text for token in expected), (name, path)
    print(f"PASS {name}: {path}")
PY
cd vibelign-gui && npm run test -- src/lib/vib/__tests__/report.test.ts -t "generateReportPdf uses html render then export_report_pdf" > ../.omo/evidence/report-writing-quality/task-7-pdf-conversion.txt
'`; PASS means each CLI path exists, content extraction confirms expected Korean strings, and the GUI PDF wrapper calls `export_report_pdf` after HTML generation. Failure: run `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type work --format html --json --force > .omo/evidence/report-writing-quality/task-7-sparse-render.json`; PASS means CLI still renders because quality warnings are non-blocking outside GUI preflight.
  Commit: Y | `test(reporting): verify report quality across export formats`

- [x] 8. Add optional visual card-news companion output
  What to do / Must NOT do: Add backend card planner module `vibelign/core/reporting_cli/report_visual_cards.py` or a focused equivalent that converts approved report model/assistance output into 3-6 visual card specs. Add explicit opt-in CLI path such as `vib report PLAN_PATH --visual-cards --json` returning the `visual_cards` sidecar. Add an image-provider adapter boundary with a fake provider in tests; do not call real image generation in tests. In GUI, add typed helpers `vibelign-gui/src/lib/vib/reportVisualCards.ts` and `ReportVisualCardsPanel.tsx` or a small sibling component that previews the card plan, uses generated/fake image assets as illustration layers, overlays editable Korean text with HTML/CSS, and supports regenerate, edit, delete, and approve per card. Must NOT put Korean text in generated image prompts; prompts must include `no readable text in image`; do not hard-code imagen2.
  Parallelization: Wave 3 | Blocked by: 3, 4, 6 | Blocks: 9
  References (executor has NO interview context - be exhaustive): `vibelign/core/reporting_cli/templates.py:23-103`, `vibelign/core/reporting_cli/html_renderer.py:48-73`, `vibelign/core/reporting_cli/polish_guard.py:26-67`, `vibelign-gui/src/components/plan-doc/ReportComposer.tsx:321-429`, `vibelign-gui/src/lib/vib/report.ts:120-205`, `vibelign-gui/src/components/plan-doc/ReportFontSizeControls.tsx:16-44`.
  Acceptance criteria (agent-executable): `python3 -m pytest tests/core/reporting_cli/test_report_visual_cards.py tests/cli/test_vib_report_cmd.py -v` exits 0; `cd vibelign-gui && npm run test -- src/lib/vib/__tests__/reportVisualCards.test.ts src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx` exits 0; tests prove 3-6 cards, `source_refs` present, every `visual_prompt` includes `no readable text in image`, text overlays remain editable, fake provider is used, and per-card approve/delete/regenerate controls work.
  QA scenarios (name the exact tool + invocation): Happy: `mkdir -p .omo/evidence/report-writing-quality && python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --visual-cards --json > .omo/evidence/report-writing-quality/task-8-visual-cards.json`; PASS means JSON has `visual_cards.cards` length 3-6 and no card `visual_prompt` contains Korean report copy. Failure: `mkdir -p .omo/evidence/report-writing-quality && cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx -t "keeps Korean copy as editable overlays" > ../.omo/evidence/report-writing-quality/task-8-visual-overlays.txt`; PASS means fake image layer renders with separate title/body overlay controls and rejected cards are not exported.
  Commit: Y | `feat(reporting): add visual card news companion output`

- [x] 9. Final integration QA, docs copy, and handoff cleanup
  What to do / Must NOT do: Update only narrowly relevant user/developer docs if needed: `vibelign/commands/vib_manual_cmd.py` report entry or report docs/specs if the feature introduces visible wording. Record evidence under `.omo/evidence/report-writing-quality/`. Run full focused verification commands listed above. Confirm `.vibelign/project_map.json` / anchors are respected for changed files. Do not stage unrelated files or commit `.omo/evidence` unless the project convention requires it.
  Parallelization: Wave 3 | Blocked by: 7, 8 | Blocks: Final verification wave
  References (executor has NO interview context - be exhaustive): `vibelign/commands/vib_manual_cmd.py:930-953`, `AI_DEV_SYSTEM_SINGLE_FILE.md:1-240`, `.vibelign/project_map.json`, `.omo/drafts/report-writing-quality.md:55-92`.
  Acceptance criteria (agent-executable): All commands in Verification strategy exit 0 or pre-existing failures are documented with exact output; evidence files exist for CLI sparse/complete and GUI sparse/complete scenarios; `git diff --check` exits 0; the final plan compliance audit confirms no unfilled template markers remain.
  QA scenarios (name the exact tool + invocation): Happy: `mkdir -p .omo/evidence/report-writing-quality && bash -lc 'set -euo pipefail
python3 -m pytest tests/core/reporting_cli/test_report_quality.py tests/core/reporting_cli/test_report_visual_cards.py tests/core/reporting_cli/test_emit.py tests/core/reporting_cli/test_model_json.py tests/cli/test_vib_report_cmd.py -v
(cd vibelign-gui && npm run build)
vib guard --strict --write-report > .omo/evidence/report-writing-quality/task-9-vib-guard.txt
' > .omo/evidence/report-writing-quality/task-9-final-focused.txt`; PASS means focused backend, GUI build, and VibeLign guard pass with evidence. Failure: `mkdir -p .omo/evidence/report-writing-quality && git diff --check > .omo/evidence/report-writing-quality/task-9-diff-check.txt && git diff --name-only > .omo/evidence/report-writing-quality/task-9-changed-files.txt && python3 - <<'PY'
from pathlib import Path
allowed_prefixes = (
    "vibelign/core/reporting_cli/",
    "vibelign/commands/vib_report_cmd.py",
    "vibelign/cli/cli_command_groups.py",
    "tests/core/reporting_cli/",
    "tests/cli/test_vib_report_cmd.py",
    "tests/fixtures/reporting_cli/",
    "vibelign-gui/src/lib/vib/",
    "vibelign-gui/src/components/plan-doc/",
    "vibelign-gui/src/pages/",
    "vibelign/commands/vib_manual_cmd.py",
    "docs/superpowers/",
)
paths = [line.strip() for line in Path(".omo/evidence/report-writing-quality/task-9-changed-files.txt").read_text().splitlines() if line.strip()]
unexpected = [p for p in paths if not p.startswith(allowed_prefixes)]
assert not unexpected, unexpected
print("PASS allowed changed files")
PY`; PASS means no whitespace errors and changed files stay inside the planned feature scope.
  Commit: Y | `docs(reporting): document report quality preflight`

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE before implementation is declared complete.
- [x] F1. Plan compliance audit: run `mkdir -p .omo/evidence/report-writing-quality && python3 - <<'PY' > .omo/evidence/report-writing-quality/f1-plan-compliance.txt
from pathlib import Path
plan = Path(".omo/plans/report-writing-quality.md").read_text(encoding="utf-8")
draft = Path(".omo/drafts/report-writing-quality.md").read_text(encoding="utf-8")
for cid in ("C1", "C2", "C3", "C4", "C5", "C6", "C7"):
    assert cid in draft, cid
for needle in ("quality sidecar", "assistance", "visual_cards", "report-visual-cards-v1", "--visual-cards", "ReportVisualCardsPanel", "ReportModel", "HTML-to-PDF", "missing_audience", "ReportQualityPanel", "Final verification wave"):
    assert needle in plan, needle
assert "<" + "fill" not in plan
import re
for marker in ("T" + "BD", "TO" + "DO", "F" + "IXME", "X" + "XX", "place" + "holder", "APPEND" + " TASK"):
    assert marker not in plan, marker
assert not re.search(r"\{\{.*?\}\}", plan)
assert not re.search(r"\[[Tt][Oo][Dd][Oo]\]", plan)
assert not re.search(r"<[A-Za-z][A-Za-z0-9_-]*>", plan)
lines = plan.splitlines()
assert sum(line.lstrip().startswith("QA scenarios (name the exact tool + invocation)") for line in lines) == 9
assert sum(line.lstrip().startswith("Commit: Y |") for line in lines) == 9
print("APPROVE plan compliance")
PY`; approve only if the command exits 0 and the file says APPROVE.
- [x] F2. Code quality review: run `mkdir -p .omo/evidence/report-writing-quality && python3 - <<'PY' > .omo/evidence/report-writing-quality/f2-code-quality-scope.txt
from pathlib import Path
import subprocess
changed = subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines()
blocked_patterns = (" as any", "@ts-ignore", "@ts-expect-error")
for path in changed:
    if not Path(path).is_file():
        continue
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    for pattern in blocked_patterns:
        assert pattern not in text, (path, pattern)
for path in ("vibelign-gui/src/components/plan-doc/ReportComposer.tsx", "vibelign/commands/vib_report_cmd.py", "vibelign/cli/cli_command_groups.py"):
    p = Path(path)
    if p.exists():
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        assert len(lines) < 650, (path, len(lines))
print("APPROVE code quality scope")
PY`; approve only if no type suppression and no oversized wiring-file growth is detected. Backend PDF support is checked separately in F4.
- [x] F3. Real manual QA: refresh and verify required artifacts with this exact command: `mkdir -p .omo/evidence/report-writing-quality && bash -lc 'set -euo pipefail
(cd vibelign-gui && npm run test -- src/pages/__tests__/ReportView.test.tsx -t "quality_complete sourcePath opens ReportComposer and generates preview" > ../.omo/evidence/report-writing-quality/task-6-complete-generate.txt)
(cd vibelign-gui && npm run test -- src/pages/__tests__/ReportView.test.tsx src/components/plan-doc/__tests__/ExportReportModal.test.tsx -t "quality_sparse AI assistance requires user confirmation" > ../.omo/evidence/report-writing-quality/task-6-sparse-assist-confirmation.txt)
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type work --emit-model --json > .omo/evidence/report-writing-quality/f3-cli-sparse-preflight.json
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --emit-model --json > .omo/evidence/report-writing-quality/f3-cli-complete-preflight.json
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type work --assist-missing --json > .omo/evidence/report-writing-quality/f3-cli-sparse-assist.json
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_long_2000.md --type work --assist-missing --json > .omo/evidence/report-writing-quality/f3-cli-long-assist.json
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --visual-cards --json > .omo/evidence/report-writing-quality/task-8-visual-cards.json
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format html --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/task-7-html.json
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format docx --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/task-7-docx.json
python3 -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format pptx --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/task-7-pptx.json
(cd vibelign-gui && npm run test -- src/lib/vib/__tests__/report.test.ts -t "generateReportPdf uses html render then export_report_pdf" > ../.omo/evidence/report-writing-quality/task-7-pdf-conversion.txt)
(cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx -t "keeps Korean copy as editable overlays" > ../.omo/evidence/report-writing-quality/task-8-visual-overlays.txt)
python3 - <<PY > .omo/evidence/report-writing-quality/f3-real-qa.txt
import json
from pathlib import Path
for name in ("task-7-html", "task-7-docx", "task-7-pptx"):
    payload = json.loads(Path(f".omo/evidence/report-writing-quality/{name}.json").read_text(encoding="utf-8"))
    assert payload["ok"] is True, payload
    assert Path(payload["path"]).exists(), payload["path"]
for name in ("f3-cli-sparse-preflight", "f3-cli-complete-preflight"):
    payload = json.loads(Path(f".omo/evidence/report-writing-quality/{name}.json").read_text(encoding="utf-8"))
    assert payload["ok"] is True and "quality" in payload, payload
assist = json.loads(Path(".omo/evidence/report-writing-quality/f3-cli-sparse-assist.json").read_text(encoding="utf-8"))
assert assist["ok"] is True and assist["assistance"]["status"] in {"ready", "needs_user_input"}, assist
assert any(item["kind"] in {"user_question", "draft_text", "source_candidate"} for item in assist["assistance"]["suggestions"] + assist["assistance"]["questions"]), assist
long_assist = json.loads(Path(".omo/evidence/report-writing-quality/f3-cli-long-assist.json").read_text(encoding="utf-8"))
assert long_assist["ok"] is True and "assistance" in long_assist, long_assist
source_refs = [
    ref
    for item in long_assist["assistance"]["suggestions"] + long_assist["assistance"]["questions"]
    for ref in item.get("source_refs", [])
]
assert any(ref.get("start_line", 0) > 200 and ref.get("end_line", 0) < 1800 for ref in source_refs), source_refs
visual = json.loads(Path(".omo/evidence/report-writing-quality/task-8-visual-cards.json").read_text(encoding="utf-8"))
assert visual["ok"] is True and "visual_cards" in visual, visual
cards = visual["visual_cards"]["cards"]
assert 3 <= len(cards) <= 6, cards
assert all("no readable text in image" in card["visual_prompt"] for card in cards), cards
for name in ("task-6-complete-generate.txt", "task-6-sparse-assist-confirmation.txt", "task-7-pdf-conversion.txt", "task-8-visual-overlays.txt"):
    path = Path(".omo/evidence/report-writing-quality") / name
    assert path.exists() and path.stat().st_size > 0, path
print("APPROVE real manual QA artifacts")
PY
'`; approve only if GUI test logs, generated file JSON evidence, and PDF conversion test evidence exist.
- [x] F4. Scope fidelity: run `mkdir -p .omo/evidence/report-writing-quality && python3 - <<'PY' > .omo/evidence/report-writing-quality/f4-scope-fidelity.txt
from pathlib import Path
import re
checks = {
    "pdf_gui_conversion_exists": "export_report_pdf" in Path("vibelign-gui/src/lib/vib/report.ts").read_text(encoding="utf-8"),
    "polish_free_auto_preserved": "FREE_PROVIDERS" in Path("vibelign/core/reporting_cli/polish.py").read_text(encoding="utf-8"),
    "theme_catalog_not_required": Path("vibelign/core/reporting_cli/theme_catalog.py").exists(),
}
failed = [name for name, ok in checks.items() if not ok]
assert not failed, failed
backend_paths = [
    "vibelign/cli/cli_command_groups.py",
    "vibelign/commands/vib_report_cmd.py",
    "vibelign/core/reporting_cli/render_job.py",
    "vibelign/core/reporting_cli/html_renderer.py",
    "vibelign/core/reporting_cli/docx_renderer.py",
    "vibelign/core/reporting_cli/pptx_renderer.py",
]
for path in backend_paths:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    assert "pdf_renderer" not in text, path
    assert not re.search(r"choices\\s*=\\s*\\[[^\\]]*['\\\"]pdf['\\\"]", text), path
    assert not re.search(r"format\\s*(==|in)\\s*['\\\"]pdf['\\\"]", text), path
import subprocess
pdf = subprocess.run(
    ["python3", "-m", "vibelign.cli.vib_cli", "report", "tests/fixtures/reporting_cli/quality_complete.md", "--type", "proposal", "--format", "pdf", "--json"],
    text=True,
    capture_output=True,
)
assert pdf.returncode != 0, pdf.stdout + pdf.stderr
assert "pdf" in (pdf.stdout + pdf.stderr).lower()
print("APPROVE scope fidelity")
PY`; approve only if no new backend PDF renderer is introduced, direct CLI `--format pdf` is rejected, and existing GUI PDF / polish boundaries remain.
- [x] F5. Full focused verification: run `mkdir -p .omo/evidence/report-writing-quality && bash -lc 'set -euo pipefail
python3 -m pytest tests/core/reporting_cli/test_report_quality.py tests/core/reporting_cli/test_report_assist.py tests/core/reporting_cli/test_report_visual_cards.py tests/core/reporting_cli/test_emit.py tests/core/reporting_cli/test_model_json.py tests/cli/test_vib_report_cmd.py -v
python3 -m pytest tests/core/reporting_cli/test_html_renderer.py tests/core/reporting_cli/test_docx_renderer.py tests/core/reporting_cli/test_pptx_renderer.py -v
python3 -m compileall vibelign/core/reporting_cli vibelign/commands
cd vibelign-gui
npm run test -- src/lib/vib/__tests__/reportQuality.test.ts src/lib/vib/__tests__/reportAssist.test.ts src/lib/vib/__tests__/reportVisualCards.test.ts src/lib/vib/__tests__/report.test.ts src/components/plan-doc/__tests__/ReportQualityPanel.test.tsx src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx src/components/plan-doc/__tests__/ExportReportModal.test.tsx src/pages/__tests__/ReportView.test.tsx
npm run build
' > .omo/evidence/report-writing-quality/f5-full-focused.txt`; approve only if the command exits 0.

## Commit strategy
- Commit 1: `feat(reporting): add deterministic report quality preflight` - backend quality model and tests.
- Commit 2: `feat(reporting): expose report quality in emit payload` - emit/CLI JSON contract.
- Commit 3: `feat(reporting): add guarded report assistance suggestions` - sparse/complete fixtures, backend fixture coverage, and opt-in assist generation.
- Commit 4: `feat(gui-report): add typed report quality and assistance payloads` - TypeScript types/helpers and wrapper tests.
- Commit 5: `feat(gui-report): add report quality and assistance review panel` - reusable UI component and tests.
- Commit 6: `feat(gui-report): gate report generation with quality and assistance review` - ReportComposer/ReportView integration and GUI tests.
- Commit 7: `test(reporting): verify report quality across export formats` - parity tests and real-surface evidence.
- Commit 8: `feat(reporting): add visual card news companion output` - visual card planner/provider adapter, GUI card panel, fake-provider tests.
- Commit 9: `docs(reporting): document report quality preflight` - narrow docs/manual copy if visible user behavior changed.
- Keep commits atomic and do not include unrelated dirty worktree files. If the user asks to avoid Actions/CI, include `[skip ci]` only then.

## Success criteria
- Backend emits deterministic quality findings for sparse and complete report fixtures without calling an LLM.
- `vib report PLAN_PATH --emit-model --json` returns existing fields plus `quality` and default `assistance` sidecars and remains backward-compatible for current consumers.
- `vib report PLAN_PATH --assist-missing --json` is explicit opt-in and returns user-confirmed assistance suggestions/questions without mutating `ReportModel`.
- Long md files of at least 2,000 lines are chunked/indexed; assist output includes `source_refs` to relevant middle-of-file line ranges and does not rely on full-file prompting or head/tail truncation.
- GUI report generation shows quality warnings before final export, lets users request AI completion help, requires accept/edit/reject before applying suggestions, and preserves user-selected type, format, theme, fonts, font sizes, author, page-number, and polish settings when proceeding.
- Optional visual card-news output creates 3-6 approved cards with generated illustration assets, editable text overlays, source refs, and fake-provider test coverage; no Korean copy or factual claim is embedded into image pixels.
- Non-polish report generation has a reviewable quality and assistance path; AI polish block diff still works as opt-in and guarded.
- CLI HTML/DOCX/PPTX and GUI PDF conversion still generate successfully from the complete fixture and include the expected Korean title/content.
- Focused Python tests, GUI tests, GUI build, compile checks, real CLI QA, and GUI/Tauri PDF conversion QA are captured in `.omo/evidence/report-writing-quality/`.
- No new renderer, no automatic AI/API dependency, no unsupported fact invention, no unrelated theme/font rewrite, and no unfilled template markers remain in this plan.
