# === ANCHOR: PATCH_FANOUT_START ===
from typing import cast


# === ANCHOR: PATCH_FANOUT_APPLY_LAZY_FANOUT_START ===
def apply_lazy_fanout(
    request: str,
    sub_first: dict[str, object],
    sub_intents: list[str],
# === ANCHOR: PATCH_FANOUT_APPLY_LAZY_FANOUT_END ===
) -> dict[str, object]:
    plan = dict(cast(dict[str, object], sub_first["patch_plan"]))
    plan["request"] = request
    pending = list(sub_intents[1:])
    plan["pending_sub_intents"] = pending
    plan["sub_intents"] = list(sub_intents)
    qs = [str(x) for x in cast(list[object], plan.get("clarifying_questions") or [])]
    qs.append(
        f"lazy fan-out: 첫 의도만 상세 계획했습니다. 나머지 {len(pending)}건은 순차적으로 patch_get 하세요."
    )
    plan["clarifying_questions"] = qs
    sub_first["patch_plan"] = plan
    return sub_first
# === ANCHOR: PATCH_FANOUT_END ===
