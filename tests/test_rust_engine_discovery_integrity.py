"""Pin Rust 엔진 integrity 검사의 dev-path manifest auto-regen 정책.

Why: cargo build 직후 .sha256 매니페스트가 누락된 환경 결함은 사용자 책임
영역 밖이고 tamper 탐지 목적도 약하다 (target/{debug,release} 는 쓰기 가능).
사용자에게 RUST_ENGINE_INTEGRITY_FAILED 로 가는 대신 자동 회복하되, 번들/
설치본 경로에서는 여전히 실패시키도록 경계를 핀한다.
"""
from __future__ import annotations

from pathlib import Path

from vibelign.core.checkpoint_engine.rust_engine.discovery import _verify_integrity


def test_dev_target_debug_path_auto_regenerates_missing_manifest(tmp_path: Path) -> None:
    binary_path = tmp_path / "vibelign-core" / "target" / "debug" / "vibelign-engine"
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    binary_path.write_bytes(b"fake engine bytes")

    assert _verify_integrity(binary_path) is None
    manifest = binary_path.with_suffix(binary_path.suffix + ".sha256")
    assert manifest.exists(), "dev path 에서는 missing manifest 가 자동 생성돼야 한다"
    digest = manifest.read_text(encoding="utf-8").split()[0]
    assert len(digest) == 64


def test_dev_target_release_path_auto_regenerates_missing_manifest(tmp_path: Path) -> None:
    binary_path = tmp_path / "vibelign-core" / "target" / "release" / "vibelign-engine"
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    binary_path.write_bytes(b"another fake engine")

    assert _verify_integrity(binary_path) is None
    manifest = binary_path.with_suffix(binary_path.suffix + ".sha256")
    assert manifest.exists()


def test_bundled_path_does_not_auto_regenerate(tmp_path: Path) -> None:
    """site-packages/vibelign/_bundled 같은 설치본 경로에서는 매니페스트 누락이
    빌드/배포 단계의 누락 신호이므로 명시적으로 실패해야 한다."""
    binary_path = tmp_path / "site-packages" / "vibelign" / "_bundled" / "vibelign-engine"
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    binary_path.write_bytes(b"bundled engine")

    assert _verify_integrity(binary_path) == "integrity manifest missing"
    manifest = binary_path.with_suffix(binary_path.suffix + ".sha256")
    assert not manifest.exists(), "번들 경로에서는 자동 생성 금지"


def test_existing_manifest_mismatch_still_fails(tmp_path: Path) -> None:
    """매니페스트가 있지만 binary 와 sha 불일치 (실제 tamper 또는 빌드 회귀)는
    auto-regen 대상이 아니라 명시적 실패로 보고한다."""
    binary_path = tmp_path / "vibelign-core" / "target" / "debug" / "vibelign-engine"
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    binary_path.write_bytes(b"current bytes")
    manifest = binary_path.with_suffix(binary_path.suffix + ".sha256")
    manifest.write_text("0" * 64 + "  vibelign-engine\n", encoding="utf-8")

    assert _verify_integrity(binary_path) == "integrity check failed"


def test_dev_path_case_insensitive_match(tmp_path: Path) -> None:
    """Windows NTFS 의 case-preserving 특성에 robust 하도록 케이스 다른 경로도
    dev 빌드로 인식되어 auto-regen 되어야 한다."""
    binary_path = tmp_path / "Vibelign-Core" / "Target" / "Release" / "vibelign-engine"
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    binary_path.write_bytes(b"mixed case path engine")

    assert _verify_integrity(binary_path) is None
    manifest = binary_path.with_suffix(binary_path.suffix + ".sha256")
    assert manifest.exists()
