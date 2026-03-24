# === ANCHOR: ACTION_ENGINE_ACTION_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Action:
    action_type: str          # "add_anchor", "split_file", "fix_mcp", 등
    description: str          # 사람이 읽을 수 있는 설명
    target_path: Optional[str] = None   # 대상 파일 경로 (없을 수 있음)
    command: Optional[str] = None       # 실행 가능한 CLI 명령어 (있을 경우)
    depends_on: List[str] = field(default_factory=list)  # 먼저 실행되어야 할 action_type 목록

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "description": self.description,
            "target_path": self.target_path,
            "command": self.command,
            "depends_on": self.depends_on,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Action":
        return cls(
            action_type=data["action_type"],
            description=data["description"],
            target_path=data.get("target_path"),
            command=data.get("command"),
            depends_on=data.get("depends_on", []),
        )
# === ANCHOR: ACTION_ENGINE_ACTION_END ===
