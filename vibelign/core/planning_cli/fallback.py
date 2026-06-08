# vibelign/core/planning_cli/fallback.py
# === ANCHOR: FALLBACK_START ===
from __future__ import annotations

# 폴백 시도 우선순위. 사용자 지정 provider 가 항상 맨 앞에 오고,
# 그 뒤를 이 순서로 보충한다. v1 에서는 UI 비노출 내부 상수.
INTERNAL_PROVIDER_PRIORITY: tuple[str, ...] = ("claude", "codex", "agy", "opencode")


def provider_try_order(preferred: str | None) -> list[str]:
    """preferred 를 맨 앞에 두고 내부 우선순위로 보충한 시도 목록(중복 제거)."""
    order: list[str] = []
    if preferred:
        order.append(preferred)
    for provider in INTERNAL_PROVIDER_PRIORITY:
        if provider not in order:
            order.append(provider)
    return order
# === ANCHOR: FALLBACK_END ===
