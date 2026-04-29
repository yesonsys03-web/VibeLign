# === ANCHOR: CLI_COMPLETION_START ===
import argparse


# === ANCHOR: CLI_COMPLETION_REGISTER_COMPLETION_COMMAND_START ===
def register_completion_command(sub, parser) -> None:
    from vibelign.terminal_render import cli_print

    p = sub.add_parser(
        "completion",
        help="탭 자동완성 설정 (zsh/bash/PowerShell)",
        description=(
            "vib 명령어의 탭 자동완성을 설정해요.\n"
            "한 번만 설정하면 vib + 탭키로 명령어가 자동 완성돼요.\n"
            "macOS/Linux: zsh, bash 지원\n"
            "Windows: PowerShell 지원"
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib completion            설정 방법 안내\n"
            "  vib completion --install  자동으로 설정 (zsh/bash/PowerShell 자동 감지)"
        ),
    )
    p.add_argument("--install", action="store_true", help="자동으로 쉘 프로파일에 설정")
    p.set_defaults(func=lambda args: run_completion(args, parser, cli_print))
# === ANCHOR: CLI_COMPLETION_REGISTER_COMPLETION_COMMAND_END ===


# === ANCHOR: CLI_COMPLETION_PARSE_COMMANDS_START ===
def parse_commands(parser):
    subparsers_action = None
    for action in parser._subparsers._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            break

    commands = []
    cmd_opts = {}
    if subparsers_action:
        for cmd_name, cmd_parser in subparsers_action.choices.items():
            commands.append(cmd_name)
            opts = []
            for act in cmd_parser._actions:
                for opt in act.option_strings:
                    if opt.startswith("--"):
                        opts.append(opt)
            cmd_opts[cmd_name] = opts
    return commands, cmd_opts
# === ANCHOR: CLI_COMPLETION_PARSE_COMMANDS_END ===


# === ANCHOR: CLI_COMPLETION_MANUAL_TOPICS_START ===
def manual_topics() -> str:
    try:
        from vibelign.commands.vib_manual_cmd import MANUAL

        return " ".join(MANUAL.keys())
    except Exception:
        return ""
# === ANCHOR: CLI_COMPLETION_MANUAL_TOPICS_END ===


POSITIONAL_COMPLETIONS: dict[str, list[str]] = {
    "export": ["claude", "opencode", "cursor", "antigravity"],
}


# === ANCHOR: CLI_COMPLETION_GENERATE_COMPLETION_SCRIPT_START ===
def generate_completion_script(parser) -> str:
    commands, cmd_opts = parse_commands(parser)
    cmds_str = " ".join(commands)
    topics = manual_topics()

    case_lines = []
    for cmd in commands:
        opts_str = " ".join(cmd_opts[cmd])
        if cmd == "manual":
            all_completions = f"{topics} {opts_str}".strip()
            case_lines.append(f'        manual) opts="{all_completions}" ;;')
        elif cmd in POSITIONAL_COMPLETIONS:
            positional_str = " ".join(POSITIONAL_COMPLETIONS[cmd])
            all_completions = f"{positional_str} {opts_str}".strip()
            case_lines.append(f'        {cmd}) opts="{all_completions}" ;;')
        else:
            case_lines.append(f'        {cmd}) opts="{opts_str}" ;;')
    case_block = "\n".join(case_lines)

    return f'''# VibeLign (vib) 쉘 자동완성
# 이 스크립트는 vib completion 으로 자동 생성되었습니다.
# === ANCHOR: CLI_COMPLETION_GENERATE_COMPLETION_SCRIPT_END ===

if [ -n "${{ZSH_VERSION:-}}" ]; then
    autoload -Uz compinit 2>/dev/null
    if ! type compdef &>/dev/null; then
        compinit -i 2>/dev/null
    fi
    _vib_zsh() {{
        local -a commands
        commands=({cmds_str})

        if (( CURRENT == 2 )); then
            compadd -a commands
            return
        fi

        local opts
        case "${{words[2]}}" in
{case_block}
            *) opts="" ;;
        esac

        compadd -- ${{(s: :)opts}}
    }}
    compdef _vib_zsh vib
else
    _vib_completions() {{
        local cur prev commands opts
        COMPREPLY=()
        cur="${{COMP_WORDS[COMP_CWORD]}}"
        prev="${{COMP_WORDS[COMP_CWORD-1]}}"
        commands="{cmds_str}"

        if [[ ${{COMP_CWORD}} -eq 1 ]]; then
            COMPREPLY=( $(compgen -W "${{commands}}" -- "${{cur}}") )
            return 0
        fi

        case "${{COMP_WORDS[1]}}" in
{case_block}
            *) opts="" ;;
        esac

        COMPREPLY=( $(compgen -W "${{opts}}" -- "${{cur}}") )
        return 0
    }}
    complete -F _vib_completions vib
fi
'''


# === ANCHOR: CLI_COMPLETION_GENERATE_POWERSHELL_SCRIPT_START ===
def generate_powershell_script(parser) -> str:
    commands, cmd_opts = parse_commands(parser)
    topics = manual_topics().split()

    cmds_ps = ", ".join(f"'{c}'" for c in commands)

    opts_lines = []
    for cmd in commands:
        base_opts = cmd_opts.get(cmd, [])
        if cmd == "manual":
            all_items = topics + base_opts
        elif cmd in POSITIONAL_COMPLETIONS:
            all_items = POSITIONAL_COMPLETIONS[cmd] + base_opts
        else:
            all_items = base_opts
        if all_items:
            opts_ps = ", ".join(f"'{o}'" for o in all_items)
            opts_lines.append(f"    '{cmd}' = @({opts_ps})")
        else:
            opts_lines.append(f"    '{cmd}' = @()")
    opts_block = "\n".join(opts_lines)

    return f"""# VibeLign (vib) PowerShell 탭 자동완성
# 이 스크립트는 vib completion --install 로 자동 추가되었습니다.
# === ANCHOR: CLI_COMPLETION_GENERATE_POWERSHELL_SCRIPT_END ===

Register-ArgumentCompleter -Native -CommandName vib -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)

    $commands = @({cmds_ps})
    $cmdOpts = @{{
{opts_block}
    }}

    $words = $commandAst.CommandElements
    $first = ($words[0].Value).ToLowerInvariant()
    $startIdx = if ($first -eq "vib" -or $first -eq "vib.exe") {{ 1 }} else {{ 0 }}
    $completeCount = $words.Count - (if ($wordToComplete -ne "") {{ 1 }} else {{ 0 }})

    if ($completeCount -le $startIdx) {{
        $commands | Where-Object {{ $_ -like "$wordToComplete*" }} |
            ForEach-Object {{
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
            }}
    }} else {{
        $cmd = $words[$startIdx].Value
        if ($cmd -and $cmdOpts.ContainsKey($cmd)) {{
            $cmdOpts[$cmd] | Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
                }}
        }}
    }}
}}
"""


# === ANCHOR: CLI_COMPLETION_RUN_COMPLETION_START ===
def run_completion(args, parser, print_fn) -> None:
    import os
    import sys
    from vibelign.terminal_render import (
        clack_info,
        clack_intro,
        clack_outro,
        clack_success,
        clack_warn,
    )

    is_windows = sys.platform == "win32"

    if getattr(args, "install", False):
        if is_windows:
            install_completion_powershell(parser, clack_info, clack_success, clack_warn)
        else:
            install_completion_posix(parser, clack_info, clack_success, clack_warn)
        return

    clack_intro("VibeLign 탭 자동완성 설정")
    clack_info("방법 1 (자동 설정, 추천):")
    clack_info("  vib completion --install")
    clack_info("")
    if is_windows:
        clack_info("방법 2 (수동 설정 - PowerShell):")
        clack_info("  $PROFILE 파일에 아래를 추가하세요:")
        clack_info("  Invoke-Expression (vib completion)")
    else:
        clack_info("방법 2 (수동 설정 - zsh/bash):")
        clack_info("  아래 명령어를 ~/.zshrc 또는 ~/.bashrc 에 추가하세요:")
        clack_info('  eval "$(vib completion)"')
    clack_outro("설정 후 새 터미널을 열면 vib + 탭키가 작동해요!")
# === ANCHOR: CLI_COMPLETION_RUN_COMPLETION_END ===


# === ANCHOR: CLI_COMPLETION_INSTALL_COMPLETION_POSIX_START ===
def install_completion_posix(parser, clack_info, clack_success, clack_warn):
    import os

    script = generate_completion_script(parser)
    shell = os.environ.get("SHELL", "")

    if "zsh" in shell:
        profile = os.path.expanduser("~/.zshrc")
    elif "bash" in shell:
        profile = os.path.expanduser("~/.bashrc")
        if not os.path.exists(profile):
            profile = os.path.expanduser("~/.bash_profile")
    else:
        clack_warn("지원하지 않는 쉘이에요. 아래 스크립트를 직접 추가해주세요.")
        print(script)
        return

    comp_dir = os.path.expanduser("~/.vibelign")
    os.makedirs(comp_dir, exist_ok=True)
    comp_file = os.path.join(comp_dir, "completion.sh")

    with open(comp_file, "w", encoding="utf-8") as file:
        file.write(script)

    source_line = f'[ -f "{comp_file}" ] && source "{comp_file}"'

    profile_text = ""
    if os.path.exists(profile):
        profile_text = open(profile, encoding="utf-8", errors="ignore").read()

    if comp_file in profile_text:
        clack_success("자동완성 스크립트를 갱신했어요! 새 터미널을 열면 적용돼요.")
    else:
        with open(profile, "a", encoding="utf-8") as file:
            file.write(f"\n# VibeLign 탭 자동완성\n{source_line}\n")
        clack_success(f"자동완성 설정 완료! ({profile}에 추가)")
        clack_info("새 터미널을 열면 vib + 탭키로 명령어가 자동 완성돼요.")
        clack_info(f"지금 바로 쓰려면: source {profile}")
# === ANCHOR: CLI_COMPLETION_INSTALL_COMPLETION_POSIX_END ===


# === ANCHOR: CLI_COMPLETION_INSTALL_COMPLETION_POWERSHELL_START ===
def install_completion_powershell(parser, clack_info, clack_success, clack_warn):
    import os
    import sys
    from pathlib import Path

    # === ANCHOR: CLI_COMPLETION_RESOLVE_VIB_DIR_START ===
    def resolve_vib_dir() -> Path:
        argv0 = Path(sys.argv[0])
        try_paths = [argv0, argv0.with_suffix(".exe")]
        if argv0.is_absolute():
            try_paths.append(argv0.parent)
        try_paths = [path for path in try_paths if str(path)]

        for path in try_paths:
            try:
                if path.exists() and path.is_file():
                    return path.resolve().parent
            except Exception:
                pass

        return Path.cwd().resolve()
    # === ANCHOR: CLI_COMPLETION_RESOLVE_VIB_DIR_END ===

    script = generate_powershell_script(parser)

    comp_dir = Path.home() / ".vibelign"
    comp_dir.mkdir(exist_ok=True)
    comp_file = comp_dir / "completion.ps1"
    comp_file.write_text(script, encoding="utf-8")

    ps7_profile = (
        Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    )
    ps5_profile = (
        Path.home()
        / "Documents"
        / "WindowsPowerShell"
        / "Microsoft.PowerShell_profile.ps1"
    )
    profile = ps7_profile if ps7_profile.parent.exists() else ps5_profile

    profile.parent.mkdir(parents=True, exist_ok=True)

    source_line = f'. "{comp_file}"'
    vib_dir = resolve_vib_dir()
    path_bootstrap_line = f'$env:Path = "{vib_dir};$env:Path"'
    try:
        current_path = os.environ.get("PATH", "")
        if str(vib_dir).lower() not in current_path.lower().split(";"):
            import subprocess

            from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS

            new_path = current_path.rstrip(";") + ";" + str(vib_dir)
            _ = subprocess.run(
                ["setx", "PATH", new_path],
                capture_output=True,
                text=True,
                creationflags=WINDOWS_SUBPROCESS_FLAGS,
            )
    except Exception:
        pass

    profile_text = (
        profile.read_text(encoding="utf-8", errors="ignore") if profile.exists() else ""
    )

    if str(comp_file) in profile_text and path_bootstrap_line in profile_text:
        clack_success(
            "자동완성 스크립트를 갱신했어요! 새 PowerShell 창을 열면 적용돼요."
        )
    else:
        with open(profile, "a", encoding="utf-8") as file:
            file.write("\n# VibeLign PATH/탭 자동완성\n")
            if path_bootstrap_line not in profile_text:
                file.write(f"{path_bootstrap_line}\n")
            if str(comp_file) not in profile_text:
                file.write(f"{source_line}\n")
        clack_success(f"자동완성 설정 완료! ({profile}에 추가)")
# === ANCHOR: CLI_COMPLETION_INSTALL_COMPLETION_POWERSHELL_END ===
        clack_info("새 PowerShell 창을 열면 vib + 탭키로 명령어가 자동 완성돼요.")
        clack_info(f"지금 바로 쓰려면: . {profile}")
# === ANCHOR: CLI_COMPLETION_END ===
