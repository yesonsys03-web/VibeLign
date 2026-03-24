# === ANCHOR: ACTION_ENGINE_ISSUE_START ===
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Issue:
    found: str
    why_it_matters: str
    next_step: str
    path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "why_it_matters": self.why_it_matters,
            "next_step": self.next_step,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Issue":
        return cls(
            found=data["found"],
            why_it_matters=data["why_it_matters"],
            next_step=data["next_step"],
            path=data.get("path"),
        )
# === ANCHOR: ACTION_ENGINE_ISSUE_END ===
