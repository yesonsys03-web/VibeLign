# === ANCHOR: GUARD_REPORT_START ===
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
# === ANCHOR: GUARD_REPORT_GUARDREPORT_START ===
class GuardReport:
    overall_level: str
    doctor_level: str
    doctor_score: int
    change_risk_level: str
    blocked: bool
    summary: str
    recommendations: list[str]
    doctor: Dict[str, Any]
    explain: Dict[str, Any]

    # === ANCHOR: GUARD_REPORT_TO_DICT_START ===
    def to_dict(self):
# === ANCHOR: GUARD_REPORT_GUARDREPORT_END ===
        return asdict(self)
    # === ANCHOR: GUARD_REPORT_TO_DICT_END ===


# === ANCHOR: GUARD_REPORT__DOCTOR_LEVEL_LABEL_START ===
def _doctor_level_label(level: str) -> str:
    return {
        "GOOD": "좋음",
        "WARNING": "주의",
        "HIGH": "위험",
    }.get(level, level)
# === ANCHOR: GUARD_REPORT__DOCTOR_LEVEL_LABEL_END ===


# === ANCHOR: GUARD_REPORT__RISK_LABEL_START ===
def _risk_label(level: str) -> str:
    return {
        "LOW": "낮음",
        "MEDIUM": "보통",
        "HIGH": "높음",
    }.get(level, level)
# === ANCHOR: GUARD_REPORT__RISK_LABEL_END ===


# === ANCHOR: GUARD_REPORT__OVERALL_LABEL_START ===
def _overall_label(level: str) -> str:
    return {
        "GOOD": "안정적",
        "WARNING": "한 번 더 확인 필요",
        "HIGH": "지금은 멈추는 편이 안전함",
    }.get(level, level)
# === ANCHOR: GUARD_REPORT__OVERALL_LABEL_END ===


# === ANCHOR: GUARD_REPORT_COMBINE_GUARD_START ===
def combine_guard(doctor, explain):
    total = doctor.score + {"LOW": 0, "MEDIUM": 3, "HIGH": 6}.get(explain.risk_level, 0)
    overall = (
        "HIGH"
        if total >= 14 or explain.risk_level == "HIGH"
        else "WARNING"
        if total >= 6
        else "GOOD"
    )
    blocked = overall == "HIGH"
    recs = []
    if blocked:
        recs.append("변경된 파일을 확인할 때까지 AI 수정을 멈추세요.")
    if doctor.stats.get("oversized_entry_files", 0):
        recs.append("추가 변경 전에 진입 파일에서 로직을 밖으로 빼세요.")
    if doctor.stats.get("missing_anchor_files", 0):
        recs.append("다음 AI 패치 전에 `vib anchor`를 실행하세요.")
    if explain.risk_level in {"MEDIUM", "HIGH"}:
        recs.append("계속하기 전에 Git으로 변경사항을 확인하거나 백업을 저장하세요.")
    if not recs:
        recs.append(
            "프로젝트가 안정적으로 보입니다. 다음 소규모 AI 패치를 진행해도 됩니다."
        )
    return GuardReport(
        overall,
        doctor.level,
        doctor.score,
        explain.risk_level,
        blocked,
        f"프로젝트 기본 상태는 {_doctor_level_label(doctor.level)}이고 점수는 {doctor.score}점입니다. 최근 바뀐 내용의 위험도는 {_risk_label(explain.risk_level)}이고, 전체 판단은 '{_overall_label(overall)}' 입니다.",
        recs,
        doctor.to_dict(),
        explain.to_dict(),
    )
# === ANCHOR: GUARD_REPORT_COMBINE_GUARD_END ===
# === ANCHOR: GUARD_REPORT_END ===
