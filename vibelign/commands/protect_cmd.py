# === ANCHOR: PROTECT_CMD_START ===
from argparse import Namespace
from pathlib import Path
from collections.abc import Callable
from typing import cast

from vibelign.core import protected_files as protected_files_mod
from vibelign.core.protected_files import set_readonly, unset_readonly


from vibelign.terminal_render import cli_print

print = cli_print
get_protected = cast(Callable[[Path], set[str]], protected_files_mod.get_protected)
normalize_relpath = cast(Callable[[str], str], protected_files_mod.normalize_relpath)
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
        print(f"경고: '{target_input}' 파일 또는 폴더가 존재하지 않습니다.")
        print("경로를 다시 확인하세요.")
        return

    try:
        rel = normalize_relpath(str(target_path.relative_to(root)))
    except ValueError:
        print(f"오류: 프로젝트 루트 밖의 경로는 보호할 수 없습니다.")
        return

    is_dir = target_path.is_dir()

    def _iter_files(p: Path):
        return list(p.rglob("*")) if p.is_dir() else [p]

    # --remove: 보호 해제
    if remove_mode:
        if rel in protected:
            protected.discard(rel)
            save_protected(root, protected)
            failed = 0
            for f in _iter_files(target_path):
                if f.is_file():
                    try:
                        unset_readonly(f)
                    except PermissionError:
                        failed += 1
            if failed:
                print(f"경고: {failed}개 파일의 읽기 전용 해제 실패 — 권한을 확인하세요.")
            label = "폴더" if is_dir else "파일"
            print(f"보호 해제: {rel} ({label})")
            print("이제 일반 파일로 취급됩니다.")
        else:
            print(f"'{rel}'은 보호 목록에 없습니다.")
        return

    # 보호 추가
    if rel in protected:
        print(f"'{rel}'은 이미 보호 중입니다.")
    else:
        protected.add(rel)
        save_protected(root, protected)
        files = [f for f in _iter_files(target_path) if f.is_file()]
        failed = 0
        for f in files:
            try:
                set_readonly(f)
            except PermissionError:
                failed += 1
        if is_dir:
            ok_count = len(files) - failed
            print(f"[잠금] 보호 설정 완료: {rel}/ ({ok_count}개 파일 읽기 전용)")
            if failed:
                print(f"경고: {failed}개 파일 읽기 전용 설정 실패 — 권한을 확인하세요.")
        else:
            if failed:
                print(f"[잠금] 보호 목록에 추가됨: {rel}")
                print(f"경고: 읽기 전용 설정 실패 — 권한이 부족합니다.")
            else:
                print(f"[잠금] 보호 설정 완료: {rel} (읽기 전용)")
        print()
        print("보호 목록 확인: vib protect --list")
        print("보호 해제:      vib protect --remove " + rel)


# === ANCHOR: PROTECT_CMD_RUN_PROTECT_END ===
# === ANCHOR: PROTECT_CMD_END ===
