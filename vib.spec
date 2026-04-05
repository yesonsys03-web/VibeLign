# -*- mode: python ; coding: utf-8 -*-

hidden_imports = [
    "vibelign.commands.__init__","vibelign.commands.anchor_cmd","vibelign.commands.ask_cmd",
    "vibelign.commands.checkpoint_cmd","vibelign.commands.config_cmd","vibelign.commands.doctor_cmd",
    "vibelign.commands.explain_cmd","vibelign.commands.export_cmd","vibelign.commands.guard_cmd",
    "vibelign.commands.history_cmd","vibelign.commands.init_cmd","vibelign.commands.install_guide_cmd",
    "vibelign.commands.patch_cmd","vibelign.commands.protect_cmd","vibelign.commands.undo_cmd",
    "vibelign.commands.vib_anchor_cmd","vibelign.commands.vib_bench_cmd","vibelign.commands.vib_checkpoint_cmd",
    "vibelign.commands.vib_doctor_cmd","vibelign.commands.vib_explain_cmd","vibelign.commands.vib_guard_cmd",
    "vibelign.commands.vib_history_cmd","vibelign.commands.vib_init_cmd","vibelign.commands.vib_manual_cmd",
    "vibelign.commands.vib_patch_cmd","vibelign.commands.vib_scan_cmd","vibelign.commands.vib_secrets_cmd",
    "vibelign.commands.vib_start_cmd","vibelign.commands.vib_transfer_cmd","vibelign.commands.vib_undo_cmd",
    "vibelign.commands.watch_cmd",
    "vibelign.core.__init__","vibelign.core.ai_codespeak","vibelign.core.ai_dev_system",
    "vibelign.core.ai_explain","vibelign.core.analysis_cache","vibelign.core.anchor_tools",
    "vibelign.core.auto_install","vibelign.core.change_explainer","vibelign.core.codespeak",
    "vibelign.core.doctor_v2","vibelign.core.fast_tools","vibelign.core.feature_flags",
    "vibelign.core.git_hooks","vibelign.core.guard_report","vibelign.core.hook_setup",
    "vibelign.core.context_chunk","vibelign.core.http_retry","vibelign.core.intent_ir",
    "vibelign.core.keys_store","vibelign.core.local_checkpoints","vibelign.core.meta_paths","vibelign.core.patch_contract",
    "vibelign.core.patch_plan","vibelign.core.patch_suggester","vibelign.core.patch_validation",
    "vibelign.core.project_map","vibelign.core.project_scan","vibelign.core.protected_files",
    "vibelign.core.request_normalizer","vibelign.core.risk_analyzer","vibelign.core.scan_cache",
    "vibelign.core.secret_scan","vibelign.core.strict_patch","vibelign.core.target_resolution",
    "vibelign.core.ui_label_index",
    "vibelign.core.watch_engine","vibelign.core.watch_reporter","vibelign.core.watch_rules","vibelign.core.watch_state",
    "vibelign.action_engine","vibelign.action_engine.action_planner",
    "vibelign.action_engine.executors.action_executor","vibelign.action_engine.executors.checkpoint_bridge",
    "vibelign.action_engine.generators.patch_generator","vibelign.action_engine.models.action",
    "vibelign.action_engine.models.issue","vibelign.action_engine.models.plan",
    "vibelign.terminal_render","vibelign.cli","vibelign.vib_cli","vibelign.mcp_server",
    "rich","rich.console","rich.markup","rich.table","rich.panel","rich.text","rich.style","rich.theme","rich.progress",
    "git","gitdb","anthropic",
    "watchdog","watchdog.observers","watchdog.observers.fsevents","watchdog.observers.inotify",
    "watchdog.observers.read_directory_changes","watchdog.observers.winapi",
    "watchdog.observers.polling","watchdog.events",
]

a = Analysis(
    ["vibelign/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="vib", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[], runtime_tmpdir=None,
    console=True, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
