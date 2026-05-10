"""Pin save_memory_state 의 unique tmp 정책.

Why: 두 프로세스/스레드가 동시 save_memory_state 를 호출할 때 같은 `.tmp`
이름을 쓰면 한쪽이 rename 한 직후 다른 쪽이 rename 하다가 FileNotFoundError
발생. pid + uuid 로 unique 화한 후로는 두 호출이 서로의 tmp 를 침범하지
않아야 한다.
"""
from __future__ import annotations

import threading
from pathlib import Path

from vibelign.core.memory.store import save_memory_state, load_memory_state


def test_concurrent_save_memory_state_no_filenotfound(tmp_path: Path) -> None:
    target = tmp_path / "work_memory.json"
    state = load_memory_state(target)  # 빈 파일에서 default state
    errors: list[BaseException] = []

    def writer() -> None:
        try:
            for _ in range(20):
                save_memory_state(target, state)
        except BaseException as exc:  # noqa: BLE001 — 어떤 예외든 캡처
            errors.append(exc)

    threads = [threading.Thread(target=writer) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, f"동시 save_memory_state 가 실패: {[type(e).__name__ for e in errors]}"
    assert target.exists()
    # 모든 worker 의 tmp 가 정리되었는지 (dangling tmp 없음)
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == [], f"dangling tmp 가 남았어요: {leftovers}"
