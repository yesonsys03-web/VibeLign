# === ANCHOR: META_PATHS_START ===
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetaPaths:
    root: Path

    @property
    def vibelign_dir(self) -> Path:
        return self.root / ".vibelign"

    @property
    def config_path(self) -> Path:
        return self.vibelign_dir / "config.yaml"

    @property
    def project_map_path(self) -> Path:
        return self.vibelign_dir / "project_map.json"

    @property
    def state_path(self) -> Path:
        return self.vibelign_dir / "state.json"

    @property
    def anchor_index_path(self) -> Path:
        return self.vibelign_dir / "anchor_index.json"

    @property
    def anchor_meta_path(self) -> Path:
        return self.vibelign_dir / "anchor_meta.json"

    @property
    def checkpoints_dir(self) -> Path:
        return self.vibelign_dir / "checkpoints"

    @property
    def plans_dir(self) -> Path:
        return self.vibelign_dir / "plans"

    @property
    def reports_dir(self) -> Path:
        return self.vibelign_dir / "reports"

    @property
    def watch_state_path(self) -> Path:
        return self.vibelign_dir / "watch_state.json"

    @property
    def watch_log_path(self) -> Path:
        return self.vibelign_dir / "watch.log"

    @property
    def scan_cache_path(self) -> Path:
        return self.vibelign_dir / "scan_cache.json"

    @property
    def analysis_cache_path(self) -> Path:
        return self.vibelign_dir / "analysis_cache.json"

    @property
    def ui_label_index_path(self) -> Path:
        return self.vibelign_dir / "ui_label_index.json"

    @property
    def docs_visual_dir(self) -> Path:
        return self.vibelign_dir / "docs_visual"

    def docs_visual_path(self, source_relative_path: str) -> Path:
        rel = Path(source_relative_path.replace("\\", "/"))
        return self.docs_visual_dir / Path(f"{rel.as_posix()}.json")

    @property
    def docs_index_path(self) -> Path:
        return self.vibelign_dir / "docs_index.json"

    def ensure_vibelign_dirs(self) -> None:
        self.vibelign_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.docs_visual_dir.mkdir(parents=True, exist_ok=True)

    def ensure_vibelign_dir(self) -> None:
        self.vibelign_dir.mkdir(parents=True, exist_ok=True)

    def report_path(self, command: str, fmt: str) -> Path:
        suffix = ".json" if fmt == "json" else ".md"
        return self.reports_dir / f"{command}_latest{suffix}"


# === ANCHOR: META_PATHS_END ===
