import json
from pathlib import Path
from vibeguard.core.risk_analyzer import analyze_project

def run_doctor(args):
    report = analyze_project(Path.cwd(), strict=args.strict)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return
    print(f"프로젝트 상태: {report.level} (점수={report.score})")
    print()
    print(f"전체 파일 수: {report.stats.get('files_scanned', 0)}")
    print(f"소스 파일 수: {report.stats.get('source_files_scanned', 0)}")
    print(f"너무 큰 진입 파일 수: {report.stats.get('oversized_entry_files', 0)}")
    print(f"앵커 없는 파일 수: {report.stats.get('missing_anchor_files', 0)}")
    print()
    if not report.issues:
        print("주요 구조적 문제가 없습니다.")
        return
    print("문제 목록:")
    for i, issue in enumerate(report.issues, 1):
        print(f"{i}. {issue}")
    print()
    print("개선 제안:")
    for i, suggestion in enumerate(report.suggestions, 1):
        print(f"{i}. {suggestion}")
