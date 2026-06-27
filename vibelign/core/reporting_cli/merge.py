# === ANCHOR: MERGE_START ===
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
# === ANCHOR: MERGE_END ===
