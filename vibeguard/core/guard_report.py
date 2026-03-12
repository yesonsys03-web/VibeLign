from dataclasses import dataclass, asdict

@dataclass
class GuardReport:
    overall_level: str
    doctor_level: str
    doctor_score: int
    change_risk_level: str
    blocked: bool
    summary: str
    recommendations: list[str]
    doctor: dict
    explain: dict
    def to_dict(self):
        return asdict(self)

def combine_guard(doctor, explain):
    total = doctor.score + {"LOW": 0, "MEDIUM": 3, "HIGH": 6}.get(explain.risk_level, 0)
    overall = "HIGH" if total >= 14 or explain.risk_level == "HIGH" else "WARNING" if total >= 6 else "GOOD"
    blocked = overall == "HIGH"
    recs = []
    if blocked:
        recs.append("변경된 파일을 확인할 때까지 AI 수정을 멈추세요.")
    if doctor.stats.get("oversized_entry_files", 0):
        recs.append("추가 변경 전에 진입 파일에서 로직을 밖으로 빼세요.")
    if doctor.stats.get("missing_anchor_files", 0):
        recs.append("다음 AI 패치 전에 `vibeguard anchor`를 실행하세요.")
    if explain.risk_level in {"MEDIUM", "HIGH"}:
        recs.append("계속하기 전에 Git으로 변경사항을 확인하거나 백업을 저장하세요.")
    if not recs:
        recs.append("프로젝트가 안정적으로 보입니다. 다음 소규모 AI 패치를 진행해도 됩니다.")
    return GuardReport(overall, doctor.level, doctor.score, explain.risk_level, blocked, f"구조 건강도는 {doctor.level}(점수={doctor.score})이고 최근 변경 위험도는 {explain.risk_level}입니다. 종합 가드 수준은 {overall}입니다.", recs, doctor.to_dict(), explain.to_dict())
