---
slug: report-writing-quality
status: approved
intent: unclear
pending-action: execute .omo/plans/report-writing-quality.md
approach: Add a report-writing quality layer on top of the existing vib report pipeline: preflight completeness scoring, user-confirmed AI completion help, report-matched visual card news generation, richer report intent metadata, a pre-generation review surface, and cross-format QA.
---

# Draft: report-writing-quality

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->
| C1 | Backend report-quality preflight returns deterministic completeness, audience, evidence, risk, action-item, and format-risk findings before render | active | vibelign/core/reporting_cli/models.py:7-55; vibelign/core/reporting_cli/templates.py:23-103; vibelign/core/reporting_cli/emit.py:18-61 |
| C2 | Emit payload gains a `quality` sidecar without changing `ReportModel`, renderers, cache keys, or model JSON consumers | active | vibelign/core/reporting_cli/model_json.py:9-60; vibelign/core/reporting_cli/render_job.py:36-69; tests/core/reporting_cli/test_emit.py:16-58 |
| C3 | GUI exposes a pre-generation quality review panel so users see missing inputs and risky choices before clicking final generate/export | active | vibelign-gui/src/components/plan-doc/ReportComposer.tsx:137-203; vibelign-gui/src/components/plan-doc/ReportComposer.tsx:370-429; vibelign-gui/src/pages/ReportView.tsx:139-188 |
| C4 | User-confirmed AI completion helps fill missing audience, purpose, evidence prompts, risks, next actions, and unresolved questions without inventing facts | active | vibelign/core/reporting_cli/polish.py:33-112; vibelign/core/reporting_cli/polish_guard.py:26-67; vibelign-gui/src/components/report-review/ReportDiffReview.tsx:15-73; vibelign-gui/src/lib/vib/report.ts:210-268 |
| C5 | HTML, GUI PDF conversion, DOCX, and PPTX parity QA proves essential content survives every export path | active | vibelign/core/reporting_cli/html_renderer.py:48-73; vibelign/core/reporting_cli/docx_renderer.py:47-126; vibelign/core/reporting_cli/pptx_renderer.py:32-105; vibelign-gui/src/lib/vib/report.ts:120-205; vibelign-gui/src-tauri/src/commands/report_pdf.rs:189-230 |
| C6 | Tests and manual QA cover the actual report-writing workflow, not only CLI argument plumbing | active | tests/core/reporting_cli/test_templates.py:19-54; tests/core/reporting_cli/test_reader.py:32-163; tests/cli/test_vib_report_cmd.py:36-320; vibelign-gui/src/pages/__tests__/ReportView.test.tsx:20-34; vibelign-gui/src/components/plan-doc/__tests__/ExportReportModal.test.tsx:56-224 |
| C7 | Optional card-news visual companion turns report messages into approved 2D comic-style cards with image assets plus editable text overlays | active | vibelign-gui/src/components/plan-doc/ReportComposer.tsx:321-429; vibelign-gui/src/lib/vib/report.ts:120-205; vibelign/core/reporting_cli/html_renderer.py:48-73 |

## Open assumptions (announced defaults)
<!-- Intent is UNCLEAR: research resolves ambiguity, defaults are adopted (not asked), and each is surfaced in the plan's human TL;DR for veto. -->
<!-- assumption | adopted default | rationale | reversible? -->
| The user means report writing quality, not only visual export polish | Cover both, but prioritize writing quality: completeness, audience fit, evidence, decision readiness, and actionability | Existing export polish already covers themes/fonts/rendering; backend and GUI still lack a writing-quality contract | yes |
| Target report style | Korean business report defaults: concise executive summary, purpose/audience, evidence or basis, decision/recommendation, risks, next actions | Existing templates are Korean and business-oriented but shallow; user has repeatedly pushed toward concrete report/specimen output | yes |
| LLM behavior | Do not make the quality diagnosis depend on nondeterministic LLM generation; after deterministic diagnosis, offer user-confirmed AI completion drafts/questions through existing official CLI-style provider flow | Users expect AI help because report writing is hard, but unsupported facts must be user-confirmed instead of silently invented | yes |
| Long md input | Support 2,000+ line planning/md files by deterministic chunking, section indexing, and relevant-source extraction before any AI prompt | Real planning files can exceed practical CLI/model prompt windows; truncating the file would miss evidence and break trust | yes |
| Visual output | Add optional 2D webtoon/card-news companion output with generated illustration backgrounds and UI-rendered text overlays | Reports are easier to share and understand with visuals, but text inside generated images is unreliable and must remain editable | yes |
| Export formats | Preserve existing CLI HTML/DOCX/PPTX paths and GUI HTML-to-PDF conversion; test parity instead of building a new report engine | Current pipeline is already broad and recently validated; replacing it would create unnecessary regression risk | yes |
| UI direction | Add preflight/review inside existing ReportComposer/ReportView surfaces, extracted into small components, not a new landing page or giant file | Current UI is generate-first and ReportComposer is already large; project rules prefer small scoped modules | yes |
| Scope size | Architecture tier | Work crosses backend model/CLI/GUI/tests/manual QA and requires a durable plan | yes |

## Findings (cited - path:lines)
- `PlanningData` and `ReportModel` do not have fields for audience, objective, evidence, KPI/impact, risk, recommendation strength, owner, timeline, or action items; they carry only basic plan fields and sections (`vibelign/core/reporting_cli/models.py:7-55`).
- Only three structured report templates exist: `work`, `proposal`, and `result`; their sections are generic and skip empty sources (`vibelign/core/reporting_cli/templates.py:23-103`, `tests/core/reporting_cli/test_templates.py:19-54`).
- The plan reader maps a fixed Korean heading list and strips bullets, but does not infer business-report semantics beyond that mapping (`vibelign/core/reporting_cli/reader.py:8-83`, `tests/core/reporting_cli/test_reader.py:32-109`).
- Generic `doc` mode preserves arbitrary Markdown sections but does not normalize them into a stronger report structure (`vibelign/core/reporting_cli/reader.py:89-178`, `tests/core/reporting_cli/test_reader.py:131-163`).
- AI polish is sentence/block-level tone cleanup for `paragraph` and `summary` blocks; it preserves facts and falls back, but does not restructure a report (`vibelign/core/reporting_cli/polish.py:33-112`).
- Existing guard/lint only protects numbers/non-answers and flags a fixed list of vague Korean terms; it does not score completeness, coherence, evidence, or decision readiness (`vibelign/core/reporting_cli/polish_guard.py:26-67`, `vibelign/core/reporting_cli/vague_lint.py:6-27`, `tests/core/reporting_cli/test_vague_lint.py:14-28`).
- `emit_report_payload` already exposes `base`, `polished`, `guards`, and `vague_warnings`, so a quality preflight payload can reuse this two-stage contract instead of inventing a parallel path (`vibelign/core/reporting_cli/emit.py:18-61`).
- CLI options are format/theme/font/polish/render plumbing; there is no audience, purpose, report frame, completeness, or preflight flag yet (`vibelign/commands/vib_report_cmd.py:31-54`, `vibelign/cli/cli_command_groups.py:685-724`).
- GUI generation probes only for empty sections, then either sends polish flow to review or generates immediately (`vibelign-gui/src/components/plan-doc/ReportComposer.tsx:137-203`).
- GUI preview appears only after generation; before generation the preview pane is an empty-state (`vibelign-gui/src/components/plan-doc/ReportComposer.tsx:370-429`).
- Block diff review exists only for AI polish; non-polish exports have no structured review step (`vibelign-gui/src/components/plan-doc/ReportComposer.tsx:158-178`, `vibelign-gui/src/pages/ReportView.tsx:139-151`, `vibelign-gui/src/components/report-review/ReportDiffReview.tsx:15-73`).
- Existing AI polish preserves facts and falls back, but it does not ask for missing facts or produce user-confirmed completion drafts for report gaps (`vibelign/core/reporting_cli/polish.py:33-112`, `vibelign/core/reporting_cli/polish_guard.py:26-67`).
- Long planning files can reach roughly 2,000 lines, so AI completion must not pass the entire md file in one prompt or rely on head/tail truncation.
- ReportView tests currently cover only list-to-open and empty state, not sourcePath entry, preflight, review handoff, or quality-warning flows (`vibelign-gui/src/pages/__tests__/ReportView.test.tsx:20-34`).
- GUI report lib tests cover CLI argument plumbing and file conversion, not user-facing writing-quality behavior (`vibelign-gui/src/lib/vib/__tests__/report.test.ts:32-283`).
- Memory confirms report export already has Satgat-style themes, GUI/backend theme/font controls, and known risks around backend/CLI/GUI sync; this plan should extend that pipeline, not replace it (`MEMORY.md:56-88`).

## Decisions (with rationale)
- Treat the task as UNCLEAR/open-ended and adopt defaults instead of asking an interview: the user asked to check missing parts and plan, not to choose a specific implementation fork.
- Plan a writing-quality layer, not another theme pack: existing work already expanded visual themes and font controls, while the remaining gap is quality semantics and pre-generation confidence.
- Use deterministic preflight as the base contract: tests can assert missing audience/evidence/risk/action-item findings without brittle LLM output snapshots.
- Reuse `emit_report_payload` shape and add a new quality payload rather than adding a separate reporting command family: it already returns pre-render model metadata and feeds GUI review.
- Keep deterministic diagnosis independent from AI, but add a separate opt-in AI completion step because users need help turning a plan/md file into a real report; AI output must be reviewed, edited, and approved by the user before it changes the report draft.
- Add long-source handling as a first-class requirement: chunk and index the md source, retrieve relevant chunks per missing finding, and include line ranges/source refs in suggestions.
- Add card-news visuals as an optional companion output: generate illustration assets from approved report/card prompts, keep Korean copy as HTML/CSS text overlays, and require per-card user approval.
- Preserve existing CLI and GUI compatibility: current `vib report` calls without new flags must keep working and existing HTML/PDF/DOCX/PPTX output paths must remain valid.

## Scope IN
- Backend quality rubric module for structured findings such as missing audience, missing objective, missing evidence/metrics, unresolved questions, weak next actions, missing risks, and format-specific risk.
- JSON-safe quality payload that can be returned during emit/preflight and mirrored in TypeScript.
- CLI or existing emit-model extension that lets GUI ask for quality diagnostics without rendering a final file.
- GUI preflight panel inside the report-writing flow, visible before final generation, with clear status/warning/action labels.
- User-confirmed AI completion path for missing report fields, with per-suggestion accept/edit/reject controls and safe “ask user for facts” prompts when evidence is missing.
- Optional report visual card set: 3-6 cards, 2D webtoon/business comic style, provider-adapter based image generation, editable text overlays, and per-card regenerate/delete/approve controls.
- Non-polish review path for quality diagnostics and AI completion suggestions, while preserving existing AI polish diff behavior.
- Focused tests across Python model/preflight, CLI JSON, TS wrappers, ReportComposer/ReportView behavior, and real surface generation/export QA.

## Scope OUT (Must NOT have)
- Do not build a second report renderer or replace the existing `vib report` pipeline.
- Do not require paid/API LLMs or silently call Claude/API for report quality. AI completion must be explicit, opt-in, and use the existing official CLI/provider subprocess style when available.
- Do not let AI invent unsupported evidence, numbers, decisions, or risk facts. When source material lacks facts, generate a user question or clearly marked draft suggestion that requires approval.
- Do not bake Korean report copy, numbers, or claims into generated images. Generated images are illustration layers only; all card text must remain selectable/editable UI text.
- Do not hard-code a single image model such as imagen2. Use an image-provider adapter so imagen2 or another model can be swapped.
- Do not rewrite existing Satgat theme/font catalog work.
- Do not make subjective "looks better" assertions without deterministic acceptance criteria.
- Do not add Word/PPT in-app preview as part of this plan; validate those formats by generated file/content checks.
- Do not expand `ReportComposer.tsx`, `vib_report_cmd.py`, or `cli_command_groups.py` into new catch-all files; extract small modules/components.

## Open questions
- None for the approval gate. This is an open-ended request, so the plan will surface adopted defaults for veto instead of asking a pre-plan interview.

## Approval gate
status: approved
pending action: execute .omo/plans/report-writing-quality.md with decision-complete todos, acceptance criteria, QA scenarios, dependency matrix, final verification wave, and human TL;DR.
approval request: approve the revised approach: deterministic Korean business-report quality preflight + user-confirmed AI completion help + existing report pipeline extension + GUI pre-generation review + cross-format parity QA.
scope-change record: user clarified that report writing should become easier through AI assistance; the plan now includes diagnosis plus user-confirmed AI completion instead of stopping at review.
scope-change record: user clarified that md source files can be very long, up to about 2,000 lines; the plan now requires chunked source indexing and relevant-chunk AI assistance instead of whole-file prompting.
scope-change record: user approved adding report-matched card-news visuals in a 2D webtoon/comic style; the plan now includes optional visual card generation with editable text overlays and image-provider abstraction.
approval record: user approved plan writing on 2026-06-20; final work plan filled at .omo/plans/report-writing-quality.md.
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
