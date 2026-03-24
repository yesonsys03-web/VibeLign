# === ANCHOR: ACTION_ENGINE_PLAN_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from vibelign.action_engine.models.action import Action


@dataclass
class Plan:
    actions: List[Action]
    source_score: int           # 분석 당시 project_score
    generated_at: str           # ISO 8601 타임스탬프
    warnings: List[str] = field(default_factory=list)  # 순환 의존 등 경고

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": [a.to_dict() for a in self.actions],
            "source_score": self.source_score,
            "generated_at": self.generated_at,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        return cls(
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            source_score=data["source_score"],
            generated_at=data["generated_at"],
            warnings=data.get("warnings", []),
        )
# === ANCHOR: ACTION_ENGINE_PLAN_END ===
