# Plan A — 보고서 다듬기 블록 diff + 부분 수락 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `vib report --polish` 의 전체 덮어쓰기를 블록 단위 diff + 부분 수락으로 바꿔, 보고서 서브탭에서 원본/다듬을 비교하고 블록별로 수락·거부한 뒤 내보낸다.

**Architecture:** `vib report` 를 두 모드로 연다 — **emit**(`--emit-model`: base/polished 구조화 모델을 JSON 으로 반환, 파일 미저장), **render**(`--reject-blocks`: 원본 유지할 블록 인덱스만 받아 base+캐시된 polished 를 병합해 렌더·저장). 모델 직렬화는 `model_json.py` 로 단일화하고 `polish_cache.py` 가 재사용한다. GUI 는 emit 으로 받은 두 모델을 블록 diff 로 보여주고, 거부 인덱스만 render 로 돌려준다.

**Tech Stack:** Python 3 / pytest / ruff (백엔드), React 19 + TypeScript + Vitest + Tauri `runVib` 브리지 (GUI).

**스펙 대비 정제(중요):** 스펙 §2.3/2.4 는 "병합 모델 전체를 stdin/임시파일로 전달"을 제시했으나, `runVib`(`core.ts:29-43`)는 stdin 미지원이고 args 를 **배열**로 넘긴다(쉘 쿼팅 없음). 따라서 전체 모델 대신 **거부 블록 인덱스 JSON**(`[[section,block],...]`)만 인자로 넘기고 CLI 가 base+캐시 polished 를 병합한다. 전송 페이로드가 작아 Windows 에서 인코딩·쿼팅 문제가 원천 소거된다.

---

## File Structure

**신규 (단일 책임)**
- `vibelign/core/reporting_cli/model_json.py` — `ReportModel`↔dict 직렬화 + 스키마 검증
- `vibelign/core/reporting_cli/merge.py` — base/polished 블록 병합(순수 함수)
- `vibelign/core/reporting_cli/emit.py` — emit payload 조립
- `vibelign/core/reporting_cli/render_job.py` — 모델→파일 렌더·저장(기존 fmt 분기 추출, DRY)
- `vibelign-gui/src/lib/vib/reportModel.ts` — base/polished payload TS 타입 + 거부 인덱스 헬퍼
- `vibelign-gui/src/components/report-review/ReportDiffReview.tsx` — 섹션 목록 + 블록 diff 컨테이너
- `vibelign-gui/src/components/report-review/BlockDiff.tsx` — 단일 블록 원본/다듬 + 수락/거부
- `vibelign-gui/src/components/report-review/useReviewState.ts` — 블록 결정 상태 훅

**수정**
- `vibelign/core/reporting_cli/polish_cache.py` — 직렬화를 `model_json` 으로 위임(DRY)
- `vibelign/commands/vib_report_cmd.py` — emit/render 분기 추가(얇은 디스패치)
- `vibelign/cli/cli_command_groups.py` — `--emit-model`, `--reject-blocks` 인자 등록
- `vibelign-gui/src/lib/vib/report.ts` — `emitReportModel`, `renderReportWithDecisions` 래퍼
- `vibelign-gui/src/pages/ReportView.tsx` — 다듬기 선택 시 리뷰 화면 진입

**테스트**
- `tests/core/reporting_cli/test_model_json.py`, `test_merge.py`, `test_emit.py`, `test_render_job.py`
- `tests/commands/test_vib_report_cmd.py` (기존에 emit/render 케이스 추가)
- `vibelign-gui/src/lib/vib/__tests__/reportModel.test.ts`
- `vibelign-gui/src/components/report-review/__tests__/ReportDiffReview.test.tsx`

> **구조화 규율(CLAUDE.md):** 작업 전 `.vibelign/project_map.json` 읽기. 최소 패치·앵커 경계 준수·진입 파일 얇게·순수/IO 분리. 신규 파일은 위 목록만 생성.

---

## Task 1: 모델 직렬화 모듈 `model_json.py`

**Files:**
- Create: `vibelign/core/reporting_cli/model_json.py`
- Test: `tests/core/reporting_cli/test_model_json.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/core/reporting_cli/test_model_json.py
from __future__ import annotations

import pytest

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.model_json import model_from_dict, model_to_dict


def _sample() -> ReportModel:
    return ReportModel(
        title="예약 앱",
        report_type="work",
        date="2026-06-17",
        source_plan_path="plans/p.md",
        sections=[
            Section(heading="개요", blocks=[Block(kind="summary", text="요약")]),
            Section(heading="핵심", blocks=[Block(kind="bullets", items=["a", "b"])]),
        ],
    )


def test_roundtrip_preserves_model():
    model = _sample()
    restored = model_from_dict(model_to_dict(model))
    assert restored == model


def test_from_dict_rejects_invalid_block_kind():
    bad = model_to_dict(_sample())
    bad["sections"][0]["blocks"][0]["kind"] = "evil"
    with pytest.raises(ValueError):
        model_from_dict(bad)


def test_from_dict_rejects_missing_field():
    with pytest.raises(ValueError):
        model_from_dict({"title": "x", "sections": []})  # report_type/date 누락
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/core/reporting_cli/test_model_json.py -v`
Expected: FAIL — `ModuleNotFoundError: vibelign.core.reporting_cli.model_json`

- [ ] **Step 3: 구현**

```python
# vibelign/core/reporting_cli/model_json.py
from __future__ import annotations

from vibelign.core.reporting_cli.models import Block, ReportModel, Section

_ALLOWED_KINDS = {"paragraph", "bullets", "summary"}


def model_to_dict(model: ReportModel) -> dict:
    """ReportModel 을 JSON 직렬화 가능한 dict 로. (dataclasses.asdict 와 동일 구조)"""
    return {
        "title": model.title,
        "report_type": model.report_type,
        "date": model.date,
        "source_plan_path": model.source_plan_path,
        "sections": [
            {
                "heading": s.heading,
                "blocks": [
                    {"kind": b.kind, "text": b.text, "items": list(b.items)}
                    for b in s.blocks
                ],
            }
            for s in model.sections
        ],
    }


def model_from_dict(data: object) -> ReportModel:
    """dict 를 ReportModel 로 복원하며 스키마를 검증한다. 신뢰 못 할 입력의 관문."""
    if not isinstance(data, dict):
        raise ValueError("model 은 객체여야 합니다")
    for required in ("title", "report_type", "date"):
        if required not in data:
            raise ValueError(f"model 필수 필드 누락: {required}")
    sections_raw = data.get("sections", [])
    if not isinstance(sections_raw, list):
        raise ValueError("sections 는 리스트여야 합니다")
    sections: list[Section] = []
    for s in sections_raw:
        if not isinstance(s, dict) or "heading" not in s:
            raise ValueError("section 에 heading 이 필요합니다")
        blocks: list[Block] = []
        for b in s.get("blocks", []):
            kind = b.get("kind") if isinstance(b, dict) else None
            if kind not in _ALLOWED_KINDS:
                raise ValueError(f"잘못된 block kind: {kind!r}")
            blocks.append(
                Block(kind=kind, text=b.get("text", ""), items=list(b.get("items", [])))
            )
        sections.append(Section(heading=s["heading"], blocks=blocks))
    return ReportModel(
        title=data["title"],
        report_type=data["report_type"],
        date=data["date"],
        source_plan_path=data.get("source_plan_path", ""),
        sections=sections,
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/core/reporting_cli/test_model_json.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/model_json.py tests/core/reporting_cli/test_model_json.py
git commit -m "feat(report): ReportModel JSON 직렬화·검증 모듈 추가"
```

---

## Task 2: `polish_cache.py` 가 `model_json` 재사용 (DRY)

**Files:**
- Modify: `vibelign/core/reporting_cli/polish_cache.py:32-58`
- Test: `tests/core/reporting_cli/test_polish_cache.py` (기존, 회귀 확인)

- [ ] **Step 1: 기존 테스트가 통과하는지 먼저 확인(베이스라인)**

Run: `pytest tests/core/reporting_cli/test_polish_cache.py -v`
Expected: PASS (기존 그대로)

- [ ] **Step 2: 직렬화/역직렬화를 model_json 으로 교체**

`save_polish_cache` 의 `asdict(model)` 를 `model_to_dict(model)` 로, `load_polish_cache` 의 수동 재구성을 `model_from_dict(m)` 로 바꾼다. import 추가, `asdict`·`Block`·`Section` import 제거.

```python
# vibelign/core/reporting_cli/polish_cache.py (수정부)
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from vibelign.core.reporting_cli.model_json import model_from_dict, model_to_dict
from vibelign.core.reporting_cli.models import ReportModel

_SCHEMA = 1
# polish_cache_key(...) 는 변경 없음 (그대로 둔다)


def save_polish_cache(root: Path, slug: str, *, key: str, model: ReportModel) -> Path:
    dest = _cache_path(root, slug)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": _SCHEMA, "key": key, "model": model_to_dict(model)}
    dest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return dest


def load_polish_cache(root: Path, slug: str, *, key: str) -> ReportModel | None:
    path = _cache_path(root, slug)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if data.get("schema_version") != _SCHEMA or data.get("key") != key:
        return None
    try:
        return model_from_dict(data["model"])
    except (KeyError, ValueError):
        return None
```

> `polish_cache_key`, `_cache_path` 는 그대로 유지. `from dataclasses import asdict` 와 `Block, Section` import 는 삭제.

- [ ] **Step 3: 테스트 통과 확인**

Run: `pytest tests/core/reporting_cli/test_polish_cache.py -v`
Expected: PASS (기존 케이스 그대로 통과 — 직렬화 결과 동일 구조)

- [ ] **Step 4: 커밋**

```bash
git add vibelign/core/reporting_cli/polish_cache.py
git commit -m "refactor(report): polish 캐시 직렬화를 model_json 으로 단일화"
```

---

## Task 3: 블록 병합 순수 함수 `merge.py`

**Files:**
- Create: `vibelign/core/reporting_cli/merge.py`
- Test: `tests/core/reporting_cli/test_merge.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/core/reporting_cli/test_merge.py
from __future__ import annotations

from vibelign.core.reporting_cli.merge import merge_models
from vibelign.core.reporting_cli.models import Block, ReportModel, Section


def _pair():
    base = ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="S", blocks=[Block(kind="summary", text="원본")])],
    )
    polished = ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="S", blocks=[Block(kind="summary", text="다듬")])],
    )
    return base, polished


def test_no_reject_keeps_all_polished():
    base, polished = _pair()
    merged = merge_models(base, polished, reject=[])
    assert merged.sections[0].blocks[0].text == "다듬"


def test_reject_keeps_base_for_that_block():
    base, polished = _pair()
    merged = merge_models(base, polished, reject=[(0, 0)])
    assert merged.sections[0].blocks[0].text == "원본"


def test_reject_out_of_range_is_ignored():
    base, polished = _pair()
    merged = merge_models(base, polished, reject=[(9, 9)])
    assert merged.sections[0].blocks[0].text == "다듬"
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_merge.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# vibelign/core/reporting_cli/merge.py
from __future__ import annotations

from dataclasses import replace

from vibelign.core.reporting_cli.models import ReportModel, Section


def merge_models(
    base: ReportModel, polished: ReportModel, reject: list[tuple[int, int]]
) -> ReportModel:
    """polished 를 기본으로, reject 에 든 (section, block) 좌표만 base 블록으로 되돌린다.
    base/polished 는 동일 구조(같은 섹션·블록 수)라고 가정한다(emit 이 한 base 에서 파생)."""
    reject_set = {(int(s), int(b)) for s, b in reject}
    new_sections: list[Section] = []
    for si, (bsec, psec) in enumerate(zip(base.sections, polished.sections)):
        new_blocks = [
            (bblk if (si, bi) in reject_set else pblk)
            for bi, (bblk, pblk) in enumerate(zip(bsec.blocks, psec.blocks))
        ]
        new_sections.append(replace(psec, blocks=new_blocks))
    return replace(polished, sections=new_sections)
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_merge.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/merge.py tests/core/reporting_cli/test_merge.py
git commit -m "feat(report): base/polished 블록 병합 순수 함수 추가"
```

---

## Task 4: 모델→파일 렌더 헬퍼 `render_job.py` (기존 분기 추출, DRY)

**Files:**
- Create: `vibelign/core/reporting_cli/render_job.py`
- Test: `tests/core/reporting_cli/test_render_job.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/core/reporting_cli/test_render_job.py
from __future__ import annotations

from pathlib import Path

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.render_job import render_and_write


def _model():
    return ReportModel(
        title="리포트", report_type="work", date="2026-06-17",
        sections=[Section(heading="개요", blocks=[Block(kind="summary", text="요약")])],
    )


def test_render_and_write_html(tmp_path: Path):
    dest = render_and_write(tmp_path, _model(), "html", slug_source="리포트", output=None, force=False)
    assert dest.exists()
    assert dest.suffix == ".html"
    assert "요약" in dest.read_text(encoding="utf-8")
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_render_job.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현 — `vib_report_cmd.py:84-94` 의 fmt 분기를 그대로 옮긴다**

```python
# vibelign/core/reporting_cli/render_job.py
from __future__ import annotations

from pathlib import Path

from vibelign.core.reporting_cli import (
    render_docx,
    render_html,
    render_pptx,
    write_report,
    write_report_bytes,
)
from vibelign.core.reporting_cli.models import ReportModel


def render_and_write(
    root: Path,
    model: ReportModel,
    fmt: str,
    *,
    slug_source: str,
    output: str | None,
    force: bool,
) -> Path:
    """모델을 fmt 로 렌더해 저장하고 경로를 반환한다.
    예외는 호출자가 처리: ReportRendererUnavailable / FileExistsError / ValueError."""
    if fmt == "docx":
        data_bytes = render_docx(model)
        return write_report_bytes(
            root, model, data_bytes, slug_source=slug_source, ext=".docx", output=output, force=force
        )
    if fmt == "pptx":
        data_bytes = render_pptx(model)
        return write_report_bytes(
            root, model, data_bytes, slug_source=slug_source, ext=".pptx", output=output, force=force
        )
    html = render_html(model)
    return write_report(root, model, html, slug_source=slug_source, output=output, force=force)
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_render_job.py -v`
Expected: PASS

- [ ] **Step 5: `vib_report_cmd.py` 가 이 헬퍼를 쓰도록 교체**

`vib_report_cmd.py:84-100` 의 try 블록을 다음으로 교체(동작 동일, DRY):

```python
    fmt = getattr(raw, "format", "html") or "html"
    try:
        dest = render_and_write(
            root, model, fmt, slug_source=slug_source, output=raw.output, force=raw.force
        )
    except ReportRendererUnavailable as exc:
        _fail(want_json, str(exc))
        return
    except (FileExistsError, ValueError) as exc:
        _fail(want_json, str(exc))
        return
```

import 정리: `vib_report_cmd.py:10-20` 의 `render_docx/render_html/render_pptx/write_report/write_report_bytes` import 를 제거하고 `from vibelign.core.reporting_cli.render_job import render_and_write` 추가. `ReportRendererUnavailable`, `build_report_model`, `parse_plan_markdown`, `polish_report_model` 는 유지.

- [ ] **Step 6: 기존 보고서 커맨드 테스트 회귀 확인**

Run: `pytest tests/commands/test_vib_report_cmd.py -v`
Expected: PASS (기존 케이스 전부)

- [ ] **Step 7: 커밋**

```bash
git add vibelign/core/reporting_cli/render_job.py tests/core/reporting_cli/test_render_job.py vibelign/commands/vib_report_cmd.py
git commit -m "refactor(report): 렌더·저장 분기를 render_job 으로 추출"
```

---

## Task 5: emit payload 조립 `emit.py`

**Files:**
- Create: `vibelign/core/reporting_cli/emit.py`
- Test: `tests/core/reporting_cli/test_emit.py`

- [ ] **Step 1: 실패 테스트 작성 (polish 없이 base==polished, guards/vague 빈 배열)**

```python
# tests/core/reporting_cli/test_emit.py
from __future__ import annotations

from pathlib import Path

from vibelign.core.reporting_cli.emit import emit_report_payload

PLAN = """# 제목\n\n## 한 줄 목표\n예약을 빠르게\n\n## 핵심 기능\n- 예약\n- 알림\n"""


def _write_plan(tmp_path: Path) -> Path:
    p = tmp_path / "plan.md"
    p.write_text(PLAN, encoding="utf-8")
    return p


def test_emit_without_polish_base_equals_polished(tmp_path: Path):
    plan = _write_plan(tmp_path)
    payload = emit_report_payload(
        str(plan), "work", date="2026-06-17", polish=False, provider="auto", root=tmp_path
    )
    assert payload["ok"] is True
    assert payload["report_type"] == "work"
    assert payload["base"] == payload["polished"]
    assert payload["guards"] == []
    assert payload["vague_warnings"] == []
    assert payload["base"]["sections"][0]["heading"]  # 비어있지 않음


def test_emit_with_polish_uses_runner(tmp_path: Path, monkeypatch):
    plan = _write_plan(tmp_path)

    def fake_polish(model, **kwargs):
        from dataclasses import replace
        secs = []
        for s in model.sections:
            blocks = [replace(b, text=(b.text + "!" if b.kind == "summary" and b.text else b.text)) for b in s.blocks]
            secs.append(replace(s, blocks=blocks))
        return replace(model, sections=secs)

    monkeypatch.setattr("vibelign.core.reporting_cli.emit.polish_report_model", fake_polish)
    payload = emit_report_payload(
        str(plan), "work", date="2026-06-17", polish=True, provider="auto", root=tmp_path
    )
    base_summary = payload["base"]["sections"][0]["blocks"][0]["text"]
    pol_summary = payload["polished"]["sections"][0]["blocks"][0]["text"]
    assert pol_summary == base_summary + "!"
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_emit.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# vibelign/core/reporting_cli/emit.py
from __future__ import annotations

from pathlib import Path

from vibelign.core.reporting_cli import build_report_model, parse_plan_markdown
from vibelign.core.reporting_cli.model_json import model_to_dict
from vibelign.core.reporting_cli.polish import polish_report_model
from vibelign.core.reporting_cli.polish_cache import polish_cache_key, save_polish_cache
from vibelign.core.reporting_cli.storage import _report_slug


def emit_report_payload(
    plan_path: str,
    report_type: str,
    *,
    date: str,
    polish: bool,
    provider: str,
    root: Path,
) -> dict:
    """base/polished 구조화 모델 + (Plan B 에서 채울) guards/vague_warnings 를 조립한다.
    polish 시 결과를 polish 캐시에 저장해 render 단계가 재사용하게 한다."""
    plan = Path(plan_path).expanduser()
    data = parse_plan_markdown(plan.read_text(encoding="utf-8"))
    base = build_report_model(data, report_type, date=date, source_plan_path=str(plan))
    slug = _report_slug(data.title or data.idea or plan.stem)

    guards: list[dict] = []
    vague_warnings: list[dict] = []
    if polish:
        polished = polish_report_model(base, provider=provider, root=root)
        key = polish_cache_key(base, provider=provider)
        save_polish_cache(root, slug, key=key, model=polished)
    else:
        polished = base

    return {
        "ok": True,
        "report_type": report_type,
        "slug": slug,
        "base": model_to_dict(base),
        "polished": model_to_dict(polished),
        "guards": guards,
        "vague_warnings": vague_warnings,
    }
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_emit.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/emit.py tests/core/reporting_cli/test_emit.py
git commit -m "feat(report): emit payload(base/polished) 조립 모듈 추가"
```

---

## Task 6: CLI 분기 + 인자 등록 (emit / render-decisions)

**Files:**
- Modify: `vibelign/commands/vib_report_cmd.py` (ReportArgs Protocol + run_vib_report 분기)
- Modify: `vibelign/cli/cli_command_groups.py` (report 서브파서 인자)
- Test: `tests/commands/test_vib_report_cmd.py` (추가)

- [ ] **Step 1: 실패 테스트 작성 (emit / render-decisions JSON 계약)**

```python
# tests/commands/test_vib_report_cmd.py 에 추가
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from vibelign.commands.vib_report_cmd import run_vib_report

PLAN = "# 제목\n\n## 한 줄 목표\n예약을 빠르게\n\n## 핵심 기능\n- 예약\n"


def _args(**over):
    base = dict(
        plan="", type="work", format="html", output=None, force=False,
        date="2026-06-17", json=True, polish=False, cli="auto",
        emit_model=False, reject_blocks=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_emit_model_prints_base_and_polished(tmp_path, monkeypatch, capsys):
    plan = tmp_path / "p.md"; plan.write_text(PLAN, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    run_vib_report(_args(plan=str(plan), emit_model=True))
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True
    assert "base" in out and "polished" in out
    assert out["base"]["report_type"] == "work"


def test_render_decisions_writes_file(tmp_path, monkeypatch, capsys):
    plan = tmp_path / "p.md"; plan.write_text(PLAN, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    run_vib_report(_args(plan=str(plan), reject_blocks="[[0,0]]"))
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True
    assert Path(out["path"]).exists()
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/commands/test_vib_report_cmd.py -k "emit_model or render_decisions" -v`
Expected: FAIL — `emit_model` 분기 없음 → AttributeError 또는 일반 렌더 경로로 빠짐

- [ ] **Step 3: `ReportArgs` Protocol 에 필드 추가 (`vib_report_cmd.py:30-39`)**

```python
class ReportArgs(Protocol):
    plan: str
    type: str
    format: str
    output: str | None
    force: bool
    date: str | None
    json: bool
    polish: bool
    cli: str
    emit_model: bool
    reject_blocks: str | None
```

- [ ] **Step 4: `run_vib_report` 에 emit/render 분기 추가 (모델 빌드 직후, polish 블록 앞)**

`vib_report_cmd.py:70` (`slug_source = ...`) 다음에 삽입:

```python
    provider = getattr(raw, "cli", "auto") or "auto"

    # --emit-model: 렌더·저장 없이 base/polished 구조화 모델을 JSON 으로 반환한다.
    if getattr(raw, "emit_model", False):
        from vibelign.core.reporting_cli.emit import emit_report_payload
        payload = emit_report_payload(
            str(plan_path), raw.type, date=report_date,
            polish=getattr(raw, "polish", False), provider=provider, root=root,
        )
        print(json.dumps(payload, ensure_ascii=False))
        return

    # --reject-blocks: 거부 인덱스만 받아 base+캐시 polished 를 병합해 렌더·저장한다.
    reject_raw = getattr(raw, "reject_blocks", None)
    if reject_raw is not None:
        from vibelign.core.reporting_cli.merge import merge_models
        from vibelign.core.reporting_cli.polish_cache import (
            load_polish_cache,
            polish_cache_key,
            save_polish_cache,
        )
        try:
            reject = [(int(s), int(b)) for s, b in json.loads(reject_raw)]
        except (ValueError, TypeError):
            _fail(want_json, "reject-blocks JSON 형식이 잘못됐어요: [[section,block],...]")
            return
        slug = _report_slug(slug_source)
        key = polish_cache_key(model, provider=provider)
        polished = load_polish_cache(root, slug, key=key)
        if polished is None:
            polished = polish_report_model(model, provider=provider, root=root)
            save_polish_cache(root, slug, key=key, model=polished)
        model = merge_models(model, polished, reject)
        fmt = getattr(raw, "format", "html") or "html"
        try:
            dest = render_and_write(
                root, model, fmt, slug_source=slug_source, output=raw.output, force=raw.force
            )
        except ReportRendererUnavailable as exc:
            _fail(want_json, str(exc)); return
        except (FileExistsError, ValueError) as exc:
            _fail(want_json, str(exc)); return
        if want_json:
            print(json.dumps({"ok": True, "path": str(dest), "report_type": model.report_type}, ensure_ascii=False))
        else:
            clack_intro("VibeLign 보고서"); clack_success(f"보고서 저장: {dest}")
        return
```

> 기존 `if getattr(raw, "polish", False):` 캐시 블록과 그 뒤 일반 렌더 경로는 그대로 둔다(다듬기 없이 바로 내보내는 기존 모달 경로 유지).

- [ ] **Step 5: `cli_command_groups.py` report 서브파서에 인자 추가**

report 서브파서(`r = ...add_parser("report")`) 의 기존 `--polish` 인자 근처에 추가:

```python
    r.add_argument("--emit-model", action="store_true",
                   help="다듬기 전/후 구조화 모델을 JSON으로 출력(파일 미저장)")
    r.add_argument("--reject-blocks", default=None,
                   help='원본 유지할 블록 인덱스 JSON: [[section,block],...]')
```

> argparse 가 `--emit-model` → `args.emit_model`, `--reject-blocks` → `args.reject_blocks` 로 매핑한다.

- [ ] **Step 6: 통과 확인 + 전체 회귀**

Run: `pytest tests/commands/test_vib_report_cmd.py -v`
Expected: PASS (신규 2건 + 기존 전부)

- [ ] **Step 7: 커밋**

```bash
git add vibelign/commands/vib_report_cmd.py vibelign/cli/cli_command_groups.py tests/commands/test_vib_report_cmd.py
git commit -m "feat(report): vib report --emit-model / --reject-blocks 모드 추가"
```

---

## Task 7: TS 타입 + 거부 인덱스 헬퍼 `reportModel.ts`

**Files:**
- Create: `vibelign-gui/src/lib/vib/reportModel.ts`
- Test: `vibelign-gui/src/lib/vib/__tests__/reportModel.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

```ts
// vibelign-gui/src/lib/vib/__tests__/reportModel.test.ts
import { test, expect } from "vitest";
import { rejectPairs, type ReviewDecisions } from "../reportModel";

test("rejectPairs collects only rejected coordinates", () => {
  const decisions: ReviewDecisions = { "0:0": "accept", "0:1": "reject", "1:0": "reject" };
  expect(rejectPairs(decisions).sort()).toEqual([[0, 1], [1, 0]]);
});

test("rejectPairs empty when all accepted", () => {
  expect(rejectPairs({ "0:0": "accept" })).toEqual([]);
});
```

- [ ] **Step 2: 실패 확인**

Run: `npx vitest run src/lib/vib/__tests__/reportModel.test.ts`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

```ts
// vibelign-gui/src/lib/vib/reportModel.ts
export interface RModelBlock { kind: "paragraph" | "bullets" | "summary"; text: string; items: string[]; }
export interface RModelSection { heading: string; blocks: RModelBlock[]; }
export interface RModel {
  title: string; report_type: string; date: string; source_plan_path: string; sections: RModelSection[];
}
export interface GuardRecord { section: number; block: number; reason: string; missing: string[]; }
export interface VagueWarning { section: number; block: number; term: string; offset: number; }
export interface EmitPayload {
  ok: true; report_type: string; slug: string;
  base: RModel; polished: RModel; guards: GuardRecord[]; vague_warnings: VagueWarning[];
}

/** 블록 좌표 "section:block" → 결정. */
export type Decision = "accept" | "reject";
export type ReviewDecisions = Record<string, Decision>;

export function blockKey(section: number, block: number): string { return `${section}:${block}`; }

/** 거부된 블록 좌표만 [[section,block],...] 로 추린다(CLI --reject-blocks 페이로드). */
export function rejectPairs(decisions: ReviewDecisions): [number, number][] {
  const out: [number, number][] = [];
  for (const [key, d] of Object.entries(decisions)) {
    if (d !== "reject") continue;
    const [s, b] = key.split(":").map(Number);
    out.push([s, b]);
  }
  return out;
}

/** paragraph/summary 만 diff 대상(bullets 는 읽기전용). */
export function isPolishable(block: RModelBlock): boolean {
  return block.kind === "paragraph" || block.kind === "summary";
}
```

- [ ] **Step 4: 통과 확인**

Run: `npx vitest run src/lib/vib/__tests__/reportModel.test.ts`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/lib/vib/reportModel.ts vibelign-gui/src/lib/vib/__tests__/reportModel.test.ts
git commit -m "feat(gui-report): 보고서 모델 TS 타입 + 거부 인덱스 헬퍼"
```

---

## Task 8: GUI 래퍼 `emitReportModel` / `renderReportWithDecisions`

**Files:**
- Modify: `vibelign-gui/src/lib/vib/report.ts`
- Test: `vibelign-gui/src/lib/vib/__tests__/report.test.ts` (추가)

- [ ] **Step 1: 실패 테스트 작성 (runVib 모킹)**

```ts
// report.test.ts 에 추가
import { vi, test, expect } from "vitest";
vi.mock("../core", () => ({ runVib: vi.fn() }));
import { runVib } from "../core";
import { emitReportModel, renderReportWithDecisions } from "../report";

test("emitReportModel parses emit JSON", async () => {
  vi.mocked(runVib).mockResolvedValue({
    ok: true, stdout: JSON.stringify({ ok: true, report_type: "work", slug: "s", base: {}, polished: {}, guards: [], vague_warnings: [] }), stderr: "", code: 0,
  } as never);
  const r = await emitReportModel("/proj", "plans/p.md", "work", false);
  expect(r.ok).toBe(true);
  expect(vi.mocked(runVib).mock.calls[0][0]).toContain("--emit-model");
});

test("renderReportWithDecisions passes reject-blocks", async () => {
  vi.mocked(runVib).mockResolvedValue({ ok: true, stdout: JSON.stringify({ ok: true, path: "/p/r.html" }), stderr: "", code: 0 } as never);
  const r = await renderReportWithDecisions("/proj", "plans/p.md", "work", "html", [[0, 1]]);
  expect(r.ok).toBe(true);
  const args = vi.mocked(runVib).mock.calls[0][0];
  expect(args).toContain("--reject-blocks");
  expect(args).toContain("[[0,1]]");
});
```

- [ ] **Step 2: 실패 확인**

Run: `npx vitest run src/lib/vib/__tests__/report.test.ts`
Expected: FAIL — export 없음

- [ ] **Step 3: 구현 (report.ts 에 추가)**

```ts
// vibelign-gui/src/lib/vib/report.ts 에 추가
// 파일 상단 import 에 한 줄 추가(runVib·ReportType 은 이미 report.ts 에 존재):
import type { EmitPayload } from "./reportModel";

export type EmitResult = { ok: true; payload: EmitPayload } | { ok: false; error: string };

export async function emitReportModel(
  cwd: string, planPath: string, reportType: ReportType, polish: boolean,
): Promise<EmitResult> {
  const args = ["report", planPath, "--type", reportType, "--emit-model", "--json",
    ...(polish ? ["--polish"] : [])];
  const res = await runVib(args, cwd);
  try {
    const payload = JSON.parse(res.stdout.trim());
    if (!payload.ok) return { ok: false, error: String(payload.error ?? "모델 생성 실패") };
    return { ok: true, payload };
  } catch {
    return { ok: false, error: res.stderr.trim() || "모델 생성 실패" };
  }
}

export async function renderReportWithDecisions(
  cwd: string, planPath: string, reportType: ReportType, format: "html" | "pdf" | "docx" | "pptx",
  reject: [number, number][],
): Promise<PdfResult> {
  // PDF 는 HTML 생성 후 export_report_pdf 로 변환하므로 여기서는 html 로 렌더 후 호출자가 PDF 변환.
  const fmt = format === "pdf" ? "html" : format;
  const args = ["report", planPath, "--type", reportType, "--format", fmt,
    "--reject-blocks", JSON.stringify(reject), "--json"];
  const res = await runVib(args, cwd);
  try {
    const parsed = JSON.parse(res.stdout.trim());
    if (!parsed.ok || !parsed.path) return { ok: false, error: String(parsed.error ?? "렌더 실패") };
    return { ok: true, path: parsed.path };
  } catch {
    return { ok: false, error: res.stderr.trim() || "렌더 실패" };
  }
}
```

> `JSON.stringify(reject)` 는 `[[0,1]]` 처럼 공백 없는 JSON 을 만든다. runVib 가 args 를 배열로 넘기므로 Windows 에서도 쉘 쿼팅·인코딩 문제 없음. PDF 는 기존 `generateReportPdf` 패턴(HTML→`export_report_pdf`)을 재사용한다(Task 10 에서 배선).

- [ ] **Step 4: 통과 확인**

Run: `npx vitest run src/lib/vib/__tests__/report.test.ts`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/lib/vib/report.ts vibelign-gui/src/lib/vib/__tests__/report.test.ts
git commit -m "feat(gui-report): emit/render-decisions vib 래퍼 추가"
```

---

## Task 9: 리뷰 상태 훅 + 컴포넌트 (`useReviewState`, `BlockDiff`, `ReportDiffReview`)

**Files:**
- Create: `vibelign-gui/src/components/report-review/useReviewState.ts`
- Create: `vibelign-gui/src/components/report-review/BlockDiff.tsx`
- Create: `vibelign-gui/src/components/report-review/ReportDiffReview.tsx`
- Test: `vibelign-gui/src/components/report-review/__tests__/ReportDiffReview.test.tsx`

- [ ] **Step 1: 실패 테스트 작성**

```tsx
// __tests__/ReportDiffReview.test.tsx
import { test, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ReportDiffReview } from "../ReportDiffReview";
import type { EmitPayload } from "../../../lib/vib/reportModel";

afterEach(cleanup);

const payload: EmitPayload = {
  ok: true, report_type: "work", slug: "s", guards: [], vague_warnings: [],
  base: { title: "t", report_type: "work", date: "d", source_plan_path: "", sections: [
    { heading: "개요", blocks: [{ kind: "summary", text: "원본요약", items: [] }] }] },
  polished: { title: "t", report_type: "work", date: "d", source_plan_path: "", sections: [
    { heading: "개요", blocks: [{ kind: "summary", text: "다듬요약", items: [] }] }] },
};

test("거부 시 onConfirm 이 해당 좌표를 reject 로 전달", () => {
  const onConfirm = vi.fn();
  render(<ReportDiffReview payload={payload} onConfirm={onConfirm} onCancel={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "거부" }));
  fireEvent.click(screen.getByRole("button", { name: /저장|내보내기/ }));
  expect(onConfirm).toHaveBeenCalledWith([[0, 0]]);
});

test("기본은 모두 수락 → reject 빈 배열", () => {
  const onConfirm = vi.fn();
  render(<ReportDiffReview payload={payload} onConfirm={onConfirm} onCancel={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: /저장|내보내기/ }));
  expect(onConfirm).toHaveBeenCalledWith([]);
});
```

- [ ] **Step 2: 실패 확인**

Run: `npx vitest run src/components/report-review/__tests__/ReportDiffReview.test.tsx`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: `useReviewState.ts` 구현**

```ts
// vibelign-gui/src/components/report-review/useReviewState.ts
import { useState } from "react";
import {
  blockKey, isPolishable, rejectPairs,
  type Decision, type EmitPayload, type ReviewDecisions,
} from "../../lib/vib/reportModel";

/** guard 걸린 블록은 기본 reject(원본 유지), 그 외 polishable 블록은 기본 accept. */
export function initialDecisions(payload: EmitPayload): ReviewDecisions {
  const guarded = new Set(payload.guards.map((g) => blockKey(g.section, g.block)));
  const out: ReviewDecisions = {};
  payload.base.sections.forEach((sec, si) =>
    sec.blocks.forEach((blk, bi) => {
      if (!isPolishable(blk)) return;
      const key = blockKey(si, bi);
      out[key] = guarded.has(key) ? "reject" : "accept";
    }),
  );
  return out;
}

export function useReviewState(payload: EmitPayload) {
  const [decisions, setDecisions] = useState<ReviewDecisions>(() => initialDecisions(payload));
  const set = (si: number, bi: number, d: Decision) =>
    setDecisions((prev) => ({ ...prev, [blockKey(si, bi)]: d }));
  const setAll = (d: Decision) =>
    setDecisions((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, d])));
  return { decisions, set, setAll, reject: () => rejectPairs(decisions) };
}
```

- [ ] **Step 4: `BlockDiff.tsx` 구현**

```tsx
// vibelign-gui/src/components/report-review/BlockDiff.tsx
import type { CSSProperties } from "react";
import type { Decision, GuardRecord, RModelBlock } from "../../lib/vib/reportModel";

interface Props {
  heading: string;
  base: RModelBlock;
  polished: RModelBlock;
  decision: Decision;
  guard?: GuardRecord;
  onAccept: () => void;
  onReject: () => void;
}

export function BlockDiff({ heading, base, polished, decision, guard, onAccept, onReject }: Props) {
  const changed = base.text !== polished.text;
  return (
    <div style={box}>
      <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 6 }}>
        {heading}
        {guard && <span style={badge} title={`보존된 수치: ${guard.missing.join(", ")}`}>숫자 보존됨</span>}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <div style={col}><div style={label}>원본</div><div>{base.text}</div></div>
        <div style={col}><div style={label}>다듬</div><div style={{ color: changed ? "#1A1A1A" : "#999" }}>{polished.text}</div></div>
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        <button type="button" onClick={onAccept} style={decision === "accept" ? onBtn : offBtn}>수락</button>
        <button type="button" onClick={onReject} style={decision === "reject" ? onBtn : offBtn}>거부</button>
      </div>
    </div>
  );
}

const box: CSSProperties = { border: "1px solid #e5e0d0", borderRadius: 6, padding: 10, marginBottom: 8 };
const col: CSSProperties = { flex: 1, fontSize: 13, lineHeight: 1.6 };
const label: CSSProperties = { fontSize: 11, color: "#888", marginBottom: 2 };
const badge: CSSProperties = { marginLeft: 8, fontSize: 10, background: "#eef", color: "#225", padding: "1px 6px", borderRadius: 8 };
const onBtn: CSSProperties = { background: "#1A1A1A", color: "#fff", border: "none", padding: "4px 12px", borderRadius: 5, cursor: "pointer" };
const offBtn: CSSProperties = { background: "#e5e0d0", color: "#1A1A1A", border: "none", padding: "4px 12px", borderRadius: 5, cursor: "pointer" };
```

- [ ] **Step 5: `ReportDiffReview.tsx` 구현**

```tsx
// vibelign-gui/src/components/report-review/ReportDiffReview.tsx
import { useReviewState } from "./useReviewState";
import { BlockDiff } from "./BlockDiff";
import { blockKey, isPolishable, type EmitPayload } from "../../lib/vib/reportModel";

interface Props {
  payload: EmitPayload;
  onConfirm: (reject: [number, number][]) => void;
  onCancel: () => void;
}

export function ReportDiffReview({ payload, onConfirm, onCancel }: Props) {
  const { decisions, set, setAll, reject } = useReviewState(payload);
  const guardByKey = new Map(payload.guards.map((g) => [blockKey(g.section, g.block), g]));
  const diffs = payload.base.sections.flatMap((sec, si) =>
    sec.blocks.map((blk, bi) => ({ si, bi, sec, blk })).filter((x) => isPolishable(x.blk)),
  );

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button type="button" onClick={() => setAll("accept")}>모두 수락</button>
        <button type="button" onClick={() => setAll("reject")}>모두 원본</button>
      </div>
      {diffs.length === 0 && <p style={{ color: "#888" }}>다듬을 항목이 없어요. 바로 내보낼 수 있어요.</p>}
      {diffs.map(({ si, bi, sec }) => (
        <BlockDiff
          key={`${si}:${bi}`}
          heading={sec.heading}
          base={payload.base.sections[si].blocks[bi]}
          polished={payload.polished.sections[si].blocks[bi]}
          decision={decisions[blockKey(si, bi)] ?? "accept"}
          guard={guardByKey.get(blockKey(si, bi))}
          onAccept={() => set(si, bi, "accept")}
          onReject={() => set(si, bi, "reject")}
        />
      ))}
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <button type="button" onClick={() => onConfirm(reject())} style={{ background: "#9B1B1B", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 6, cursor: "pointer", fontWeight: 700 }}>
          저장 / 내보내기
        </button>
        <button type="button" onClick={onCancel}>취소</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: 통과 확인**

Run: `npx vitest run src/components/report-review/__tests__/ReportDiffReview.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 7: 커밋**

```bash
git add vibelign-gui/src/components/report-review/
git commit -m "feat(gui-report): 블록 diff 검토 컴포넌트(useReviewState/BlockDiff/ReportDiffReview)"
```

---

## Task 10: ReportView 배선 (다듬기 선택 → 리뷰 → 내보내기)

**Files:**
- Modify: `vibelign-gui/src/pages/ReportView.tsx`
- (참고) 기존 `ExportReportModal.tsx`, `report.ts` 의 `copyReportTo`/`generateReportPdf`

- [ ] **Step 1: 흐름 설계 확인 (코드 없음, 결정 기록)**

리뷰 진입 흐름:
1. 보고서 카드 "보고서 만들기" → 종류·포맷·다듬기 선택(기존 `ExportReportModal` 의 입력부 재사용).
2. **다듬기 ON 이면** `emitReportModel(cwd, plan, type, true)` → `ReportDiffReview` 표시. **OFF 면** 기존 `ExportReportModal` 경로 그대로(변경 없음).
3. 리뷰에서 "저장/내보내기" → `renderReportWithDecisions(cwd, plan, type, format, reject)` → 경로 수신 → 기존 내보내기/복사 흐름(`copyReportTo` + 기본 폴더, 이미 구현)으로 저장 + "파일 열기".
4. PDF 포맷이면 `renderReportWithDecisions(...,"pdf",...)` 가 HTML 을 만들고, 기존 `export_report_pdf`(Tauri)로 변환(기존 `generateReportPdf` 의 변환부 재사용).

> 통합점(스펙 §7) 해소: 생성 진입은 모달에 유지하되, 다듬기 ON 분기만 리뷰 화면으로 보낸다(모달→서브탭 전면 이전은 하지 않음 — 최소 변경).

- [ ] **Step 2: ReportView 에 리뷰 상태 추가**

`ReportView` 의 `reportFor` 상태 옆에 리뷰 페이로드 상태를 추가하고, `ReportDiffReview` 를 조건부 렌더한다. 핵심 배선:

```tsx
// ReportView.tsx (발췌 — 기존 import 에 추가)
import { useState } from "react";
import { emitReportModel, renderReportWithDecisions } from "../lib/vib/report";
import { ReportDiffReview } from "../components/report-review/ReportDiffReview";
import type { EmitPayload } from "../lib/vib/reportModel";

// ... 컴포넌트 내부 상태:
const [review, setReview] = useState<{ payload: EmitPayload; plan: string; type: "work" | "proposal" | "result"; format: "html" | "pdf" | "docx" | "pptx" } | null>(null);
```

- [ ] **Step 3a: 공용 내보내기 훅 추출 (중복 금지)**

`ExportReportModal.tsx` 의 "생성 결과 경로 → 기본 폴더 복사 → 파일 열기" 로직(`exportTo`, `getReportExportDir`+`copyReportTo` 호출부)을 `vibelign-gui/src/components/report-review/useReportExport.ts` 훅으로 추출한다. 모달은 이 훅을 호출하도록 바꾸되 **동작 불변**(기존 모달 테스트가 그대로 통과해야 함).

```ts
// useReportExport.ts (추출된 공용 로직)
import { useState } from "react";
import { copyReportTo, getReportExportDir } from "../../lib/vib/report";

export function useReportExport() {
  const [exportedPath, setExportedPath] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportErr, setExportErr] = useState<string | null>(null);
  async function exportTo(src: string, dir?: string) {
    setExporting(true); setExportErr(null);
    try {
      const target = dir ?? (await getReportExportDir());
      setExportedPath(await copyReportTo(src, target));
    } catch (e) {
      setExportErr(`저장 위치로 복사하지 못했어요: ${String(e)}`);
    } finally { setExporting(false); }
  }
  return { exportedPath, exporting, exportErr, exportTo, reset: () => setExportedPath(null) };
}
```

- [ ] **Step 3b: 리뷰 confirm 핸들러 — render + 공용 내보내기 재사용**

```tsx
const { exportTo } = useReportExport();

async function handleReviewConfirm(reject: [number, number][]) {
  if (!review) return;
  const r = await renderReportWithDecisions(projectDir, review.plan, review.type, review.format, reject);
  setReview(null);
  if (r.ok) {
    await exportTo(r.path);          // 기본 폴더 복사(이미 구현된 흐름)
  } else {
    // r.error 를 ReportView 의 인라인 에러 영역에 표시
  }
}
```

> PDF 포맷이면 `renderReportWithDecisions(..., "pdf", ...)` 가 HTML 을 만들고, 기존 `generateReportPdf` 의 `export_report_pdf` 변환부를 거쳐 `.pdf` 경로를 얻은 뒤 `exportTo(pdfPath)` 한다(기존 모달 PDF 분기와 동일 로직 재사용).

- [ ] **Step 4: 빌드·타입체크·기존 모달 테스트 회귀**

Run:
```bash
cd vibelign-gui && npx tsc --noEmit && npx vitest run src/components/plan-doc/__tests__/ExportReportModal.test.tsx
```
Expected: tsc 0 errors; 모달 테스트 PASS (동작 불변)

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/pages/ReportView.tsx vibelign-gui/src/components/report-review/
git commit -m "feat(gui-report): 다듬기 ON 시 블록 diff 리뷰 → 부분수락 내보내기 배선"
```

---

## Task 11: Windows 호환 검증 (명시 요구)

**Files:** (검증 전용 — 코드 변경 없음, 발견 시 수정)

- [ ] **Step 1: 전송 경로 점검** — `--reject-blocks` 는 `JSON.stringify` 결과(`[[0,1]]`)를 runVib **배열 인자**로 넘긴다. 쉘 미경유 → Windows 쿼팅·이스케이프 불필요. stdin/임시파일 미사용 확인.
- [ ] **Step 2: 인코딩 점검** — runVib 가 `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` 를 강제(`core.ts:20-21`). 한글 섹션·다듬 텍스트가 emit JSON 으로 깨지지 않음을 확인(emit payload 한글 라운드트립 테스트로 커버됨: Task 5).
- [ ] **Step 3: 경로 구분자 점검** — `plan.outputPath` 의 `\\` 는 pathlib 가 처리. emit/render 가 돌려주는 `path` 는 절대경로이며 GUI `toProjectRelative`/`copyReportTo` 가 정규화. Windows 절대경로(`C:\\...`)도 `copy_report_to`(Rust `PathBuf`)가 처리.
- [ ] **Step 4: provider 부재 graceful** — Windows 에 codex/opencode/agy 미설치 시 `polish_report_model` 이 블록마다 None → 원문 유지. 리뷰 화면은 "다듬을 항목이 없어요" 표시(Task 9 의 `diffs.length === 0` 분기). 에러 아님.
- [ ] **Step 5: 수동 점검 체크리스트 기록** — Windows 물리 장비에서: 다듬기 ON 보고서 생성 → 리뷰 표시 → 일부 거부 → docx/pptx/html 저장 → 문서 폴더 복사 → 파일 열기. (CI 자동화 불가 항목은 체크리스트로 남김 — 침묵 금지)
- [ ] **Step 6: 커밋(문서/체크리스트만 변경 시)**

```bash
git add docs/superpowers/plans/2026-06-17-report-polish-block-diff.md
git commit -m "docs(report): Windows 호환 검증 체크리스트"
```

---

## 완료 기준 (Definition of Done)
- `pytest tests/core/reporting_cli tests/commands/test_vib_report_cmd.py` 전부 통과.
- `cd vibelign-gui && npx tsc --noEmit && npx vitest run && npx eslint .` 무오류.
- `cargo check`(src-tauri) 통과(이 Plan 은 Rust 변경 없음 — 기존 `copy_report_to` 재사용).
- 다듬기 ON → 블록 diff 리뷰 → 부분 수락 → 내보내기 동선이 mac/Windows 에서 동작.

## 의존성
- 독립 실행 가능(Plan B 없이도 동작 — guards/vague_warnings 는 빈 배열로 무해).
- Plan B 가 emit 의 guards/vague_warnings 를 채우면 Task 9 의 배지·기본거부가 자동 활성화(추가 배선 불필요).
