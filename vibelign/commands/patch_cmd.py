# === ANCHOR: PATCH_CMD_START ===
import json
from pathlib import Path
from vibelign.core.patch_suggester import suggest_patch


from vibelign.terminal_render import cli_print
print = cli_print

PATCH_TEMPLATE = '''AI_DEV_SYSTEM_SINGLE_FILE.md 규칙을 따르세요.

작업 내용:
{request}

제안 대상 파일:
{target_file}

제안 대상 앵커:
{target_anchor}

신뢰도:
{confidence}

이 대상을 선택한 이유:
{rationale}

제약 조건:
- 패치만 할 것
- 관련 없는 모듈은 수정하지 말 것
- 진입 파일은 작게 유지할 것

목표:
[예상 결과]
'''

# === ANCHOR: PATCH_CMD_RUN_PATCH_START ===
def run_patch(args):
    request = " ".join(args.request).strip()
    suggestion = suggest_patch(Path.cwd(), request)
    if args.json:
        print(json.dumps(suggestion.to_dict(), indent=2))
        return
    rationale_text = "\n".join(f"- {item}" for item in suggestion.rationale)
    out = Path.cwd() / "VIBELIGN_PATCH_REQUEST.md"
    if out.exists():
        print(f"경고: 기존 {out.name} 파일을 덮어씁니다")
    out.write_text(PATCH_TEMPLATE.format(request=request, target_file=suggestion.target_file, target_anchor=suggestion.target_anchor, confidence=suggestion.confidence, rationale=rationale_text), encoding="utf-8")
    print(f"{out.name} 파일을 생성했습니다")
    print(f"제안 파일: {suggestion.target_file}")
    print(f"제안 앵커: {suggestion.target_anchor}")
    print(f"신뢰도: {suggestion.confidence}")
# === ANCHOR: PATCH_CMD_RUN_PATCH_END ===
# === ANCHOR: PATCH_CMD_END ===
