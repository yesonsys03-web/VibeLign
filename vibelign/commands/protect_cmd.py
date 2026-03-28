# === ANCHOR: PROTECT_CMD_START ===
from argparse import Namespace
from pathlib import Path
from collections.abc import Callable
from typing import cast

from vibelign.core import protected_files as protected_files_mod


from vibelign.terminal_render import cli_print

print = cli_print
get_protected = cast(Callable[[Path], set[str]], protected_files_mod.get_protected)
save_protected = cast(
    Callable[[Path, set[str]], None], protected_files_mod.save_protected
)


# === ANCHOR: PROTECT_CMD_RUN_PROTECT_START ===
def run_protect(args: Namespace) -> None:
    root = Path.cwd()
    protected = get_protected(root)
    file_value = getattr(args, "file", None)
    target_input = file_value if isinstance(file_value, str) else ""
    list_mode = bool(getattr(args, "list", False))
    remove_mode = bool(getattr(args, "remove", False))

    # 파일 인자가 없거나 --list 플래그 → 목록 출력
    if not target_input or list_mode:
        if not protected:
            print("보호된 파일이 없습니다.")
            print()
            print("보호하려면: vib protect <파일명>")
            print("예시:       vib protect main.py")
        else:
            print(f"보호된 파일 목록 ({len(protected)}개):")
            print()
            for f in sorted(protected):
                exists = (root / f).exists()
                status = "" if exists else "  [파일 없음]"
                print(f"  [잠금] {f}{status}")
            print()
            print("보호 해제하려면: vib protect --remove <파일명>")
        return

    # 파일명 정규화 (프로젝트 루트 기준 상대 경로)
    target_path = Path(target_input)

    # 절대경로 또는 상대경로 처리
    if not target_path.is_absolute():
        target_path = root / target_path

    if not target_path.exists():
        print(f"경고: '{target_input}' 파일이 존재하지 않습니다.")
        print("파일명과 경로를 다시 확인하세요.")
        return

    try:
        rel = str(target_path.relative_to(root))
    except ValueError:
        print(f"오류: 프로젝트 루트 밖의 파일은 보호할 수 없습니다.")
        return

    # --remove: 보호 해제
    if remove_mode:
        if rel in protected:
            protected.discard(rel)
            save_protected(root, protected)
            print(f"보호 해제: {rel}")
            print(f"이제 이 파일은 일반 파일로 취급됩니다.")
        else:
            print(f"'{rel}'은 보호 목록에 없습니다.")
        return

    # 보호 추가
    if rel in protected:
        print(f"'{rel}'은 이미 보호 중입니다.")
    else:
        protected.add(rel)
        save_protected(root, protected)
        print(f"[잠금] 보호 설정 완료: {rel}")
        print()
        print("이 파일이 AI에 의해 수정되면 guard와 watch가 강하게 경고합니다.")
        print("보호 목록 확인: vib protect --list")
        print("보호 해제:      vib protect --remove " + rel)


# === ANCHOR: PROTECT_CMD_RUN_PROTECT_END ===
# === ANCHOR: PROTECT_CMD_END ===
