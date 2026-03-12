import subprocess
from pathlib import Path
from vibeguard.core.ai_dev_system import AI_DEV_SYSTEM_CONTENT
from vibeguard.commands.export_cmd import AGENTS_MD_CONTENT, TEMPLATES

GITIGNORE_CONTENT = """\
# macOS
.DS_Store
.AppleDouble
.LSOverride

# Python
__pycache__/
*.py[cod]
*.pyo
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
.venv/
venv/
env/

# VibeGuard 생성 파일
VIBEGUARD_PATCH_REQUEST.md
VIBEGUARD_EXPLAIN.md
VIBEGUARD_GUARD.md
vibeguard_exports/

# IDE
.vscode/
.idea/
"""


def _run_git(git_args, cwd):
    return subprocess.run(["git"] + git_args, cwd=cwd, capture_output=True, text=True)


def run_init(args):
    root = Path.cwd()
    tool = args.tool

    print("=" * 50)
    print("  VibeGuard 초기 설정을 시작합니다")
    print("=" * 50)
    print()

    # 1. AI_DEV_SYSTEM_SINGLE_FILE.md
    ai_dev_path = root / "AI_DEV_SYSTEM_SINGLE_FILE.md"
    if ai_dev_path.exists():
        print(f"[건너뜀] {ai_dev_path.name} 이미 존재합니다")
    else:
        ai_dev_path.write_text(AI_DEV_SYSTEM_CONTENT, encoding="utf-8")
        print(f"[생성]   {ai_dev_path.name}")

    # 2. AGENTS.md
    agents_path = root / "AGENTS.md"
    if agents_path.exists():
        print(f"[건너뜀] {agents_path.name} 이미 존재합니다")
    else:
        agents_path.write_text(AGENTS_MD_CONTENT, encoding="utf-8")
        print(f"[생성]   {agents_path.name}")

    # 3. 도구별 템플릿
    export_root = root / "vibeguard_exports" / tool
    if export_root.exists():
        print(f"[건너뜀] vibeguard_exports/{tool}/ 이미 존재합니다")
    else:
        export_root.mkdir(parents=True, exist_ok=True)
        for name, content in TEMPLATES[tool].items():
            (export_root / name).write_text(content, encoding="utf-8")
        (export_root / "README.md").write_text(
            f"# VibeGuard 내보내기: {tool}\n\n프로젝트 루트의 `AI_DEV_SYSTEM_SINGLE_FILE.md`를 주요 규칙 파일로 유지하세요.\n",
            encoding="utf-8",
        )
        print(f"[생성]   vibeguard_exports/{tool}/")

    # 4. .gitignore
    gitignore_path = root / ".gitignore"
    if gitignore_path.exists():
        print(f"[건너뜀] .gitignore 이미 존재합니다")
    else:
        gitignore_path.write_text(GITIGNORE_CONTENT, encoding="utf-8")
        print(f"[생성]   .gitignore")

    # 5. git init (없을 경우에만)
    if not (root / ".git").exists():
        result = _run_git(["init"], cwd=root)
        if result.returncode == 0:
            print(f"[완료]   Git 저장소 초기화")
        else:
            print(f"[오류]   Git 초기화 실패: {result.stderr.strip()}")
            return
    else:
        print(f"[건너뜀] Git 저장소 이미 존재합니다")

    # 6. 첫 번째 체크포인트
    _run_git(["add", "-A"], cwd=root)
    result = _run_git(
        ["commit", "-m", "vibeguard: 초기 체크포인트 (vibeguard init)"],
        cwd=root,
    )
    if result.returncode == 0:
        print(f"[저장]   첫 번째 체크포인트 생성 완료")
    else:
        if "nothing to commit" in result.stdout + result.stderr:
            print(f"[건너뜀] 변경사항이 없어 체크포인트를 생략합니다")
        else:
            print(f"[건너뜀] 체크포인트 생략: {result.stderr.strip()}")

    print()
    print("✓ 초기 설정이 완료되었습니다!")
    print()
    print("다음 단계:")
    print(f"  1. vibeguard doctor --strict   → 프로젝트 상태 확인")
    print(f"  2. vibeguard anchor            → 안전 편집 구역 설정")
    print(f"  3. AI 작업 전: vibeguard checkpoint '작업 설명'")
    print(f"  4. AI 작업 후: vibeguard guard --strict")
    print()
    print(f"  설정된 AI 도구: {tool}")
    print(f"  규칙 파일:      AI_DEV_SYSTEM_SINGLE_FILE.md")
    print(f"  AGENTS.md:      OpenCode/Claude Code 자동 참조")
