# docs_visualizer.py 분할 — 설계

날짜: 2026-06-06
브랜치: feat/vibelign-product-renew

## 배경
`vibelign/core/docs_visualizer.py` 는 1,300줄 / 앵커 61개로, 코드맵 비대(맵 줄수 1순위)·유지보수성 모두에서 최대 거대 파일이다. 마크다운→시각 아티팩트 변환의 여러 책임(모델/파싱/추출/다이어그램/오케스트레이션)이 한 파일에 섞여 있다.

## 목표
책임별 모듈로 분할하되 **공개 API·import 구조를 100% 보존**(소비처 무수정).

## 제약 (검증된 사실)
- 소비처 3곳:
  - `docs_html_visualizer.py`, `vib_docs_build_cmd.py`: `import ... docs_visualizer as _DOCS_VISUALIZER` (네임스페이스). 실제 사용 심볼: `current_generated_at`, `source_generated_at`, `visualize_markdown_file`.
  - `planning_cli/storage.py`: `from ...docs_visualizer import _slugify`.
- 테스트(`test_docs_visualizer.py`, `test_docs_build_cmd.py`, 58 케이스)는 `importlib.util.spec_from_file_location("vibelign.core.docs_visualizer", path)` 로 로드 → `__package__="vibelign.core"` → 배럴의 상대 import 정상 동작.

## 설계: 배럴 + 4 모듈 (순환 없는 DAG)

| 모듈 | 내용 | 의존 |
|---|---|---|
| `docs_visualizer_models.py` | dataclass 9개: VisualSection, GlossaryEntry, ActionItem, DiagramBlock, HeuristicEnhancedFields, AIEnhancedFields, DocsVisualArtifact, DiagramSignals, DiagramCandidate | 없음 |
| `docs_visualizer_text.py` | 저수준 텍스트/마크다운 유틸 + 날짜 헬퍼: current_generated_at, source_generated_at, _slugify, _strip_inline_markdown, _split_mermaid_aware_lines, _readme_override_hint, _overview_override_hint, _circled_number, _ordered_step_parts, _split_table_row, _iter_non_code_lines, _dedupe_keep_order, _extract_heading_ranges, _first_meaningful_paragraph | (stdlib only) |
| `docs_visualizer_extract.py` | 콘텐츠 추출: _section_summary, _section_body_preview, _extract_sections, _extract_glossary, _extract_action_items, _extract_bullet_section, _extract_components, _extract_warnings, _extract_ordered_steps, _extract_checklist_steps, _extract_decision_lines, _extract_table_rows, _extract_file_like_items | models, text |
| `docs_visualizer_diagram.py` | mermaid 다이어그램: _signal_score, _collect_diagram_signals, _safe_mermaid_label, _render_*(3), _build_*_candidate(4), _select_best_candidate, _generate_heuristic_diagrams, _extract_mermaid_blocks, _is_example_mermaid_context, _usable_authored_diagrams | models, text, extract |
| `docs_visualizer.py` (유지) | 오케스트레이션 + 배럴: build_artifact_shell, _derive_title, _derive_summary, _extract_tldr_one_liner, _truncate_with_warning, visualize_markdown_bytes, visualize_markdown_file, trust_failure_reason, is_trusted_visual_artifact + 하위 모듈 전체 re-export | 위 전부 |

배럴 re-export 는 명시적(`from .docs_visualizer_models import (...)` 형태)으로 하여 ruff F401 회피(또는 `__all__`).

## 원칙
- **코드는 이동만**(재작성 금지). 앵커 주석도 함께 이동해 보존.
- 모듈 간 import 는 명시적·비순환. 구현 중 호출 그래프 확인해 경계의 함수 위치를 미세 조정(예: diagram 이 쓰는 extract 헬퍼가 순환을 만들면 text 로 내림).

## 검증
1. `ruff check` (undefined/unused name 탐지).
2. `pytest tests/test_docs_visualizer.py tests/test_docs_build_cmd.py` (58케이스) + 관련 planning/storage 테스트.
3. import 스모크: `python -c "import vibelign.core.docs_visualizer as d; d.visualize_markdown_file; d._slugify; d.current_generated_at"`.
4. **윈도 안전**: GUI 번들 vib-runtime 재빌드 → `vib docs-build` 동작 확인(PyInstaller 가 배럴 import 따라 새 모듈 자동 번들). push 시 CI windows 빌드로 회귀 차단.
5. 코드맵 재생성 → docs_visualizer 앵커 61개가 5개 파일로 분산(맵 줄수 추가 감소) 확인.

## 비목표
- 동작/출력 변경 없음(순수 구조 분할).
- 다른 거대 파일은 이번 범위 밖.
