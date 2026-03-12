Recommended smoke tests before publishing:
- python -m compileall vibeguard
- vibeguard doctor
- vibeguard anchor --dry-run
- vibeguard patch add progress bar --json
- vibeguard explain --json
- vibeguard guard --json
- vibeguard export claude
- vibeguard watch  # after installing watchdog
