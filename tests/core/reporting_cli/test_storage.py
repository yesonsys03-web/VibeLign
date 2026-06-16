from pathlib import Path

import pytest

from vibelign.core.reporting_cli.models import ReportModel
from vibelign.core.reporting_cli.storage import write_report


def _model() -> ReportModel:
    return ReportModel(title="예약 앱", report_type="work", date="2026-06-15")


def test_write_default_path_under_reports_dir(tmp_path: Path):
    dest = write_report(tmp_path, _model(), "<html></html>", slug_source="예약 앱")
    assert dest.parent == tmp_path / ".vibelign" / "reports"
    assert dest.suffix == ".html"
    assert "work" in dest.name
    assert dest.read_text(encoding="utf-8") == "<html></html>"


def test_write_explicit_relative_output(tmp_path: Path):
    dest = write_report(
        tmp_path, _model(), "<x>", slug_source="x", output="out/report.html"
    )
    assert dest == tmp_path / "out" / "report.html"
    assert dest.read_text(encoding="utf-8") == "<x>"


def test_write_explicit_output_rejects_existing_without_force(tmp_path: Path):
    existing = tmp_path / "out" / "report.html"
    existing.parent.mkdir()
    existing.write_text("<old>", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_report(
            tmp_path, _model(), "<new>", slug_source="x", output="out/report.html"
        )
    assert existing.read_text(encoding="utf-8") == "<old>"


def test_write_explicit_output_force_overwrites(tmp_path: Path):
    existing = tmp_path / "out" / "report.html"
    existing.parent.mkdir()
    existing.write_text("<old>", encoding="utf-8")

    dest = write_report(
        tmp_path,
        _model(),
        "<new>",
        slug_source="x",
        output="out/report.html",
        force=True,
    )
    assert dest == existing
    assert existing.read_text(encoding="utf-8") == "<new>"


def test_write_creates_parent_dirs(tmp_path: Path):
    dest = write_report(tmp_path, _model(), "<x>", slug_source="예약 앱")
    assert dest.exists()


def test_write_default_path_does_not_overwrite_existing(tmp_path: Path):
    first = write_report(tmp_path, _model(), "<first>", slug_source="예약 앱")
    second = write_report(tmp_path, _model(), "<second>", slug_source="예약 앱")
    assert first != second
    assert first.read_text(encoding="utf-8") == "<first>"
    assert second.read_text(encoding="utf-8") == "<second>"


def test_write_default_path_limits_long_filename(tmp_path: Path):
    long_title = "가" * 180
    dest = write_report(tmp_path, _model(), "<x>", slug_source=long_title)
    assert len(dest.name) < 120
    assert dest.suffix == ".html"


@pytest.mark.parametrize(
    "output",
    [
        "/tmp/report.html",            # POSIX 절대경로
        "../report.html",              # 상위 디렉터리 탈출
        "out/../report.html",          # 중간 탈출
        "C:/report.html",              # Windows 드라이브 절대경로
        "\\\\server\\share\\r.html",   # UNC 경로
        "\\report.html",               # 드라이브 루트 상대(Windows)
    ],
)
def test_write_rejects_unsafe_output_paths(tmp_path: Path, output: str):
    # is_absolute() 는 플랫폼 의존 — Windows 에서 "/tmp/x" 는 절대경로가 아니라
    # 드라이브 루트로 새므로, 가드가 OS 무관하게 거부해야 한다(아래 6종 전부).
    with pytest.raises(ValueError, match="project-relative"):
        write_report(tmp_path, _model(), "<x>", slug_source="x", output=output)


def test_write_rejects_symlink_escape(tmp_path: Path, tmp_path_factory: pytest.TempPathFactory):
    # 심볼릭 링크 경유 탈출: "link/escaped.html" 은 어휘적으론 안전하지만
    # link 가 프로젝트 외부를 가리키면 실제 쓰기 위치가 root 밖이 된다.
    outside = tmp_path_factory.mktemp("outside")
    link = tmp_path / "link"
    link.symlink_to(outside)

    with pytest.raises(ValueError, match="project-relative"):
        write_report(tmp_path, _model(), "<x>", slug_source="x", output="link/escaped.html")

    # 외부 디렉터리에 파일이 생성되지 않아야 한다
    assert not (outside / "escaped.html").exists()
