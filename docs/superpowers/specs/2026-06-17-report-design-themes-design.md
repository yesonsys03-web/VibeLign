# 보고서 디자인 테마 — 설계 스펙

- 날짜: 2026-06-17
- 대상: VibeLign 보고서 렌더링 (`reporting_cli` 렌더러, `vib report`, GUI `ExportReportModal`/`ReportView`)
- 산출물: 이 설계 1개 → 구현 계획서 1개

## 1. 배경과 목표

보고서 **종류**는 업무/제안/결과 3가지로, 이는 "어떤 섹션이 들어가나"(내용 구조, `REPORT_TEMPLATES`)를 정한다. 시각 **디자인**은 `html_renderer.py:8-34` 의 단일 인라인 CSS(`_HEAD`) 하나뿐이다. 디자인을 종류와 **직교(orthogonal) 축**으로 분리해, 같은 내용에 다양한 룩을 입힌다 → 종류(3) × 테마(N) 조합.

핵심 통찰: `ReportModel`(포맷 독립 IR) → 시맨틱 HTML → `_HEAD` CSS 로 이미 디자인이 내용과 분리돼 있다. HTML/PDF 는 CSS 교체만으로 디자인이 완전히 바뀌고, PDF 는 그 HTML 을 인쇄하므로 **자동 적용**된다.

### 목표
- 테마 레지스트리 + `--theme` CLI/GUI 선택. 초기 5종: `classic`(기본=현재), `minimal`, `executive`, `compact`, `pastel`.
- HTML/PDF 는 테마별 손 작성 CSS(레이아웃·타이포 자유). Word/PPT 는 테마 팔레트(색·폰트)만 적용.

### 비목표 (YAGNI)
- 사용자 정의 CSS 업로드, 테마 에디터, 썸네일 갤러리.
- Word/PPT 의 테마별 레이아웃 차별(팔레트 색·폰트까지만).
- 내용 구조 다양성(주간/월간 등 — 별도 "기능 2", 이 스펙 범위 아님).

## 2. 핵심 추상화 — `themes.py`

신규 파일 `vibelign/core/reporting_cli/themes.py`:

```python
@dataclass(frozen=True)
class Theme:
    id: str
    label: str
    html_css: str          # <style> 안에 들어갈 CSS (HTML/PDF) — 테마별 손 작성
    accent: str            # 팔레트 (Word/PPT) — 제목/머리글 색
    ink: str               # 본문 색
    paper: str             # 배경(HTML/PDF 용; Word/PPT 는 흰 배경 유지)
    heading_font: str      # 제목/머리글 폰트
    body_font: str         # 본문 폰트

THEMES: dict[str, Theme] = { "classic": …, "minimal": …, "executive": …, "compact": …, "pastel": … }
THEME_IDS: tuple[str, ...] = ("classic", "minimal", "executive", "compact", "pastel")

def get_theme(theme_id: str) -> Theme:   # 모르는/빈 id → classic 폴백
```

`classic` 의 `html_css` 는 현재 `_HEAD` 의 `<style>` 내용 그대로(동작 불변). `accent="#9B1B1B"`, 세리프 폰트 등 현재 값 반영.

### 5개 테마 디자인 의도
| id | 룩 | 팔레트·폰트 방향 |
|---|---|---|
| classic | 세리프·격식(현재) | accent 레드(#9B1B1B), Noto Serif KR |
| minimal | 산세리프·넓은 여백·무채+포인트 | accent 무채 그레이/단색, Pretendard/Apple SD Gothic |
| executive | 네이비·표지형 헤더·굵은 타이포 | accent 네이비(#1B3A6B), 굵은 산세리프 |
| compact | 작은 폰트·좁은 여백·정보 밀집 | accent 초록, 작은 사이즈, 좁은 max-width |
| pastel | 따뜻한 베이지·파스텔·둥근 모서리 | accent 파스텔(#C97B5A 류), 부드러운 라운드 |

## 3. 렌더러가 테마를 소비

- **html_renderer**: `render_html(model, theme="classic")`. `_HEAD` 를 CSS 주입형(`_head(title, css)`)으로 바꿔 `get_theme(theme).html_css` 를 끼운다. 시맨틱 HTML(h1/h2/section/ul/p.summary)은 불변 — 테마는 CSS 만 다름.
- **docx_renderer**: `render_docx(model, theme="classic")`. 팔레트 적용 — 제목/머리글 `run.font.color.rgb = accent`, `run.font.name = heading_font`; 본문 `body_font`. 레이아웃·구조 불변.
- **pptx_renderer**: `render_pptx(model, theme="classic")`. 제목 색=accent, 폰트=heading/body. 슬라이드 구조 불변.

모든 렌더 함수에 `theme` 인자는 **기본값 `"classic"`** → 기존 호출 호환.

## 4. 계약 전달 (테마 축을 흐름에 끼움)

- **`render_job.render_and_write(root, model, fmt, *, slug_source, output, force, theme="classic")`** → 각 렌더러로 `theme` 전달.
- **CLI**: `vib report … --theme <id>` (기본 classic, choices=THEME_IDS). `vib_report_cmd` 가 일반 경로·render-decisions 경로 양쪽에서 `render_and_write(…, theme=raw.theme)` 호출. `ReportArgs` 에 `theme: str` 추가. `cli_command_groups` 인자 등록.
- **emit 무관**(렌더 안 함). **render-decisions 는 `--theme` 받음**.
- **GUI 래퍼** (`report.ts`): `generatePlanningReport/Pdf/Office`·`renderReportWithDecisions` 에 `theme` 파라미터 추가 → `--theme` 인자.
- **GUI 모달**: `ExportReportModal` 에 테마 드롭다운(종류·포맷·다듬기 옆). 선택 테마를 `generate*` 와 `onReviewRequest(type, format, theme)` 로 전달. 마지막 선택은 `localStorage`("vibelign_report_theme") 기억.
- **ReportView**: 리뷰 흐름에서 `theme` 를 보관해 `renderReportWithDecisions(…, theme)` 로 전달.

## 5. 미리보기 UX
모달의 기존 HTML iframe 미리보기는 `generatePlanningReport(cwd, plan, type, polish, theme)` 결과라, 테마 선택 시 그 테마로 다시 렌더돼 그대로 반영된다. docx/pptx/pdf 는 기존대로 경로만(미리보기 없음). 별도 썸네일 불필요.

## 6. 에러 처리
- `get_theme` 가 모르는/빈 id 를 받으면 `classic` 폴백(렌더 안 깨짐).
- CLI `--theme` 는 argparse `choices` 로 1차 검증; 그 외 경로는 `get_theme` 폴백이 2차 안전망.
- 폰트 미설치: CSS 는 font stack 으로 OS 기본 대체; docx/pptx 는 지정 폰트명만 기록(뷰어가 대체).

## 7. 테스트
- `themes.py`: `THEME_IDS` 5개 모두 `get_theme` 로 조회 가능·필드 비어있지 않음; 모르는 id→classic.
- `html_renderer`: `render_html(model, "minimal")` 출력이 minimal 시그니처(예: 특정 폰트/색 토큰) 포함; `render_html(model, "nope")` == classic 출력.
- `docx_renderer`/`pptx_renderer`: 테마 accent 색·폰트가 실제 run 에 적용됐는지 확인.
- `render_job`: `theme` 가 렌더러로 전달돼 출력에 반영.
- `vib_report_cmd`: `--theme minimal` → 출력 HTML 에 minimal CSS 반영; 기본(미지정)=classic.
- GUI: `report.ts` 래퍼가 `--theme` 인자 포함; 모달 드롭다운이 선택값을 전달.

## 8. 구조화 규율
- 최소 패치·앵커 준수·단일책임. 신규 파일은 `themes.py` 하나.
- 렌더러는 `theme` 인자만 추가(시그니처 확장), 내부 구조 불변.
- 5개 테마 CSS 는 `themes.py` 안에 상수로 모음(작업의 대부분).
- 신규 production 소스(themes.py)는 앵커 스텁→Edit 로 precheck 통과.

## 9. 영향 파일
| 파일 | 변경 |
|---|---|
| `reporting_cli/themes.py` | 신규 — Theme/THEMES/get_theme + 5 CSS |
| `reporting_cli/html_renderer.py` | `_HEAD`→CSS 주입형, `render_html(model, theme)` |
| `reporting_cli/docx_renderer.py` | `render_docx(model, theme)` 팔레트 적용 |
| `reporting_cli/pptx_renderer.py` | `render_pptx(model, theme)` 팔레트 적용 |
| `reporting_cli/render_job.py` | `render_and_write(…, theme)` 전달 |
| `commands/vib_report_cmd.py` | `--theme` → 두 렌더 경로 전달, ReportArgs |
| `cli/cli_command_groups.py` | `--theme` 인자(choices=THEME_IDS) |
| `gui/src/lib/vib/report.ts` | 래퍼에 theme 파라미터 |
| `gui/.../ExportReportModal.tsx` | 테마 드롭다운 + localStorage + onReviewRequest 확장 |
| `gui/src/pages/ReportView.tsx` | 리뷰 흐름에 theme 전달 |
