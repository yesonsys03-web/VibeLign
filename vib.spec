# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

hidden_imports = [
    "vibelign.commands.__init__","vibelign.commands.anchor_cmd","vibelign.commands.ask_cmd",
    "vibelign.commands.checkpoint_cmd","vibelign.commands.config_cmd","vibelign.commands.doctor_cmd",
    "vibelign.commands.explain_cmd","vibelign.commands.export_cmd","vibelign.commands.guard_cmd",
    "vibelign.commands.init_cmd","vibelign.commands.install_guide_cmd",
    "vibelign.commands.patch_cmd","vibelign.commands.protect_cmd",
    "vibelign.commands.vib_anchor_cmd","vibelign.commands.vib_backup_db_viewer_cmd",
    "vibelign.commands.vib_backup_db_maintenance_cmd","vibelign.commands.vib_bench_cmd","vibelign.commands.vib_checkpoint_cmd",
    "vibelign.commands.vib_docs_build_cmd","vibelign.commands.vib_doc_sources_cmd",
    "vibelign.commands.vib_doctor_cmd","vibelign.commands.vib_explain_cmd","vibelign.commands.vib_guard_cmd",
    "vibelign.commands.vib_history_cmd","vibelign.commands.vib_init_cmd","vibelign.commands.vib_manual_cmd",
    "vibelign.commands.vib_claude_hook_cmd","vibelign.commands.vib_patch_cmd",
    "vibelign.commands.vib_plan_structure_cmd","vibelign.commands.vib_precheck_cmd",
    "vibelign.commands.vib_scan_cmd","vibelign.commands.vib_secrets_cmd",
    "vibelign.commands.vib_start_cmd","vibelign.commands.vib_transfer_cmd","vibelign.commands.vib_undo_cmd",
    "vibelign.commands.watch_cmd",
    "vibelign.core.__init__","vibelign.core.ai_codespeak","vibelign.core.ai_dev_system",
    "vibelign.core.ai_explain","vibelign.core.analysis_cache","vibelign.core.anchor_tools",
    "vibelign.core.auto_install","vibelign.core.change_explainer","vibelign.core.codespeak",
    "vibelign.core.doctor_v2","vibelign.core.fast_tools","vibelign.core.feature_flags",
    "vibelign.core.git_hooks","vibelign.core.guard_report","vibelign.core.hook_setup",
    "vibelign.core.context_chunk","vibelign.core.http_retry","vibelign.core.import_resolver","vibelign.core.intent_ir",
    "vibelign.core.docs_cache","vibelign.core.docs_visualizer",
    "vibelign.core.keys_store","vibelign.core.local_checkpoints","vibelign.core.meta_paths","vibelign.core.patch_contract",
    "vibelign.core.patch_plan","vibelign.core.patch_suggester","vibelign.core.patch_validation",
    "vibelign.core.project_map","vibelign.core.project_root","vibelign.core.project_scan",
    "vibelign.core.protected_files",
    "vibelign.core.request_normalizer","vibelign.core.risk_analyzer","vibelign.core.scan_cache",
    "vibelign.core.secret_scan","vibelign.core.strict_patch","vibelign.core.structure_planner",
    "vibelign.core.structure_policy","vibelign.core.target_resolution",
    "vibelign.core.ui_label_index",
    "vibelign.core.watch_engine","vibelign.core.watch_reporter","vibelign.core.watch_rules","vibelign.core.watch_state",
    "vibelign.core.checkpoint_engine","vibelign.core.checkpoint_engine.contracts",
    "vibelign.core.checkpoint_engine.python_engine","vibelign.core.checkpoint_engine.router",
    "vibelign.core.checkpoint_engine.rust_checkpoint_engine","vibelign.core.checkpoint_engine.rust_engine",
    "vibelign.core.checkpoint_engine.shadow_runner",
    "vibelign.action_engine","vibelign.action_engine.action_planner",
    "vibelign.action_engine.executors.action_executor","vibelign.action_engine.executors.checkpoint_bridge",
    "vibelign.action_engine.generators.patch_generator","vibelign.action_engine.models.action",
    "vibelign.action_engine.models.issue","vibelign.action_engine.models.plan",
    "vibelign.terminal_render","vibelign.cli","vibelign.cli.vib_cli","vibelign.cli.cli_base",
    "vibelign.cli.cli_runtime","vibelign.cli.cli_command_groups","vibelign.cli.cli_core_commands",
    "vibelign.cli.cli_completion","vibelign.mcp","vibelign.mcp.mcp_server",
    "vibelign.mcp.mcp_runtime","vibelign.mcp.mcp_tool_loader","vibelign.mcp.mcp_tool_specs",
    "vibelign.mcp.mcp_dispatch","vibelign.mcp.mcp_handler_registry",
    "vibelign.mcp.mcp_patch_handlers","vibelign.mcp.mcp_checkpoint_handlers",
    "vibelign.mcp.mcp_protect_handlers","vibelign.mcp.mcp_misc_handlers",
    "vibelign.mcp.mcp_health_handlers","vibelign.mcp.mcp_transfer_handlers",
    "vibelign.mcp.mcp_anchor_handlers","vibelign.mcp.mcp_doctor_handlers",
    "vibelign.mcp.mcp_state_store","vibelign.patch","vibelign.patch.patch_builder",
    "vibelign.patch.patch_contract_helpers","vibelign.patch.patch_fanout",
    "vibelign.patch.patch_handoff","vibelign.patch.patch_output",
    "vibelign.patch.patch_preview","vibelign.patch.patch_render",
    "vibelign.patch.patch_steps","vibelign.patch.patch_targeting",
    "rich","rich.console","rich.markup","rich.table","rich.panel","rich.text","rich.style","rich.theme","rich.progress",
    "anthropic",
    "watchdog","watchdog.observers","watchdog.observers.fsevents","watchdog.observers.inotify",
    "watchdog.observers.read_directory_changes","watchdog.observers.winapi",
    "watchdog.observers.polling","watchdog.events","typing_extensions",
]

datas = []
if Path("vibelign/_bundled").exists():
    datas.append(("vibelign/_bundled", "vibelign/_bundled"))

a = Analysis(
    ["vibelign/_vib_entry.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

# onedir 빌드: 실행 파일은 슬림하게, 모든 바이너리/데이터는 `_internal/` 에 풀어둔다.
# Why: onefile 은 매 실행마다 `$TMPDIR/_MEI{pid}/` 로 재압축 해제해 1~3초 콜드스타트.
#      onedir 는 설치 시점에 한 번만 풀려 있어서 이후 호출은 dev 모드 수준으로 빠르다.
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="vib", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=True,
    disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[], name="vib",
)
