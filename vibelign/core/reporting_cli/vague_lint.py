# === ANCHOR: VAGUE_LINT_START ===
from __future__ import annotations

from vibelign.core.reporting_cli.models import ReportModel

# 정량 표현으로 대체돼야 할 주관·과장어. 단어장 확장이 아니라 고정 규칙 셋.
_VAGUE_TERMS: tuple[str, ...] = (
    "대폭", "대거", "많이", "크게", "상당히", "매우", "엄청", "획기적",
    "혁신적", "압도적", "급격히", "현저히", "월등히",
)
_LINT_KINDS = {"paragraph", "summary"}


def lint_model(model: ReportModel) -> list[dict]:
    """paragraph/summary 블록에서 모호·과장어 출현을 (section, block, term, offset) 으로 모은다.
    비차단 경고용 — 렌더를 막지 않는다."""
    out: list[dict] = []
    for si, section in enumerate(model.sections):
        for bi, block in enumerate(section.blocks):
            if block.kind not in _LINT_KINDS or not block.text:
                continue
            for term in _VAGUE_TERMS:
                start = block.text.find(term)
                while start != -1:
                    out.append({"section": si, "block": bi, "term": term, "offset": start})
                    start = block.text.find(term, start + 1)
    return out
# === ANCHOR: VAGUE_LINT_END ===
