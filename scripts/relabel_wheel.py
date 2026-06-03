# === ANCHOR: RELABEL_WHEEL_START ===
"""Replace a wheel's platform tag and move it to a destination directory.

Used as CIBW_REPAIR_WHEEL_COMMAND_LINUX. auditwheel refuses to handle wheels
that contain only an executable (no .so), but our binary is built inside the
manylinux container so manylinux compatibility holds by construction. We
only need to relabel the wheel from linux_<arch> to manylinux_<arch>.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


# === ANCHOR: RELABEL_WHEEL_MAIN_START ===
def main() -> int:
    if len(sys.argv) != 4:
        sys.stderr.write("usage: relabel_wheel.py <wheel> <dest_dir> <plat_tag>\n")
        return 1
    wheel = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    plat = sys.argv[3]
    subprocess.run(
        [sys.executable, "-m", "wheel", "tags", "--remove", "--platform-tag", plat, str(wheel)],
        check=True,
    )
    retagged = next(wheel.parent.glob(f"*{plat}*.whl"))
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(retagged, dest / retagged.name)
    print(f"relabeled -> {dest / retagged.name}")
    return 0
# === ANCHOR: RELABEL_WHEEL_MAIN_END ===


if __name__ == "__main__":
    raise SystemExit(main())
# === ANCHOR: RELABEL_WHEEL_END ===
