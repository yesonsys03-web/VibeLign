# Phase 0 Evidence — Claude Code Onboarding Install/Removal/Auth

> Status: pending real-machine confirmation
>
> This file is the required Phase 0 evidence artifact referenced by `docs/superpowers/specs/2026-04-15-vibelign-onboarding-claude-install-design.md`.
> Install/auth/uninstall implementation is blocked until this document is filled with real-machine results.

## Purpose

Record the verified, current behavior of Claude Code official setup/removal/auth flows on real machines.

This document must fix three implementation blockers:

- Gate A — official removal path
- Gate B — login success verification path
- Gate C — credential storage naming

## Source of truth

- Official setup/removal docs: https://code.claude.com/docs/en/setup

## Evidence rules

- Use only real-machine confirmation for Gate A/B/C values.
- Do not fill placeholders with guesses.
- If behavior differs by OS, shell, or install channel, record that difference explicitly.
- If an official uninstall command does not exist, record the exact manual removal procedure documented by the official setup page.
- For Gate B, prefer an official non-interactive auth/status command if it exists. If none exists, record `PTY probe` as the chosen path with observed evidence.
- For Gate C, record the actual credential store name/path exactly as observed on the machine.

## Gate A — Removal path evidence

### Questions to answer

- Does an official dedicated uninstall command exist?
- If yes, what is the exact command per platform?
- If no, what exact manual removal steps are documented officially?
- What are the confirmed removal targets per platform?

### Decision

- Dedicated uninstall command exists: no dedicated cross-platform `claude uninstall` command is documented on the setup page.
- Decision date: 2026-04-15
- Verified against setup docs revision/date: verified against `https://code.claude.com/docs/en/setup` fetched on 2026-04-15.

### Branch rule

- If dedicated uninstall command exists:
  - Use it as the primary uninstall path.
  - Run confirmed removal-target cleanup as secondary cleanup.
- If dedicated uninstall command does not exist:
  - Wrap the official documented manual removal procedure in the GUI uninstall flow.
  - Run confirmed removal-target cleanup as secondary cleanup.

### Confirmed removal commands / procedures

#### macOS / Linux / WSL

- Official uninstall command: none documented for native install.
- Official manual removal procedure: remove `~/.local/bin/claude` and `~/.local/share/claude`; optionally remove `~/.claude`, `~/.claude.json`, project `.claude`, and `.mcp.json` to remove configuration files.
- Notes / caveats: setup docs split uninstall into native binary/data removal and a separate “Remove configuration files” section.

#### Windows

- Official uninstall command: none documented for native install.
- Official manual removal procedure: remove `$env:USERPROFILE\.local\bin\claude.exe` and `$env:USERPROFILE\.local\share\claude`; optionally remove `$env:USERPROFILE\.claude`, `$env:USERPROFILE\.claude.json`, project `.claude`, and `.mcp.json` to remove configuration files.
- Notes / caveats: setup docs provide PowerShell removal commands for native install and a separate configuration-file removal section.

### Confirmed removal targets

| Category | macOS / Linux / WSL | Windows | Evidence note |
|---|---|---|---|
| Binary | `~/.local/bin/claude` | `%USERPROFILE%\.local\bin\claude.exe` (documented), but observed VM produced `C:\Users\topye\claude` placeholder during failed install | `setup` uninstall section documents native-install paths, but Windows VM evidence shows a failed install can leave a non-documented artifact. |
| Native data | `~/.local/share/claude` | `%USERPROFILE%\.local\share\claude` | `setup` uninstall section documents these native-install data paths. |
| User config/state | `~/.claude`, `~/.claude.json` | `%USERPROFILE%\.claude`, `%USERPROFILE%\.claude.json` | `setup` remove-configuration-files section documents these paths. |
| Project config | `.claude`, `.mcp.json` | `.claude`, `.mcp.json` | `setup` remove-configuration-files section documents these paths. |
| Shell rc / PATH mutation target | not explicitly documented | user PATH behavior implied, but exact mutation target not documented | requires real-machine confirmation. |
| Shortcut / launcher | not documented | not documented | requires real-machine confirmation. |
| Credential store | not documented | not documented | docs do not specify credential store naming/path; Gate C remains machine-only. |

## Gate B — Login success verification path evidence

### Questions to answer

- Does Claude Code expose an official non-interactive auth/status verification command?
- If yes, what exact command and what output indicates success?
- If no, can a PTY-based REPL probe be used reliably for v1 success detection?

### Decision

- Primary verification path: `PTY probe` unless a real-machine check proves one of the candidate commands is officially supported and reliable.
- Decision date: 2026-04-15
- Verified against setup docs revision/date: verified against `https://code.claude.com/docs/en/setup` fetched on 2026-04-15.

### Official command check

| Candidate command | Exists? | Observed behavior | Success signal | Failure signal | Evidence |
|---|---|---|---|---|---|
| `claude --print` | not documented on setup page; observed on macOS machine | returns `Input must be provided either through stdin or as a prompt argument when using --print` when run without stdin/prompt | command is recognized; success criteria still need prompt-bearing verification | exits with mode-usage error when no input is supplied | macOS machine check on 2026-04-15 |
| `claude --headless` | not documented on setup page; not recognized on macOS machine | returns `unknown option '--headless'` | none observed | option rejected immediately | macOS machine check on 2026-04-15 |
| `claude auth status` | not documented on setup page; observed on macOS machine | returns structured JSON with `loggedIn`, `authMethod`, `apiProvider`, `email`, `orgId`, `orgName`, `subscriptionType` | `loggedIn: true` in JSON is a strong candidate success signal for Claude.ai auth on macOS | unauthenticated behavior still needs confirmation on a logged-out or fresh machine; Windows VM could not reach this stage because install failed | macOS machine check on 2026-04-15; Windows VM failure on 2026-04-15 |
| Other official command | setup page documents `claude` interactive login only | run `claude` and follow browser prompts | interactive session starts and login/browser prompts appear | install succeeds but interactive login or session start fails | documented in setup page Authenticate section |

### PTY probe evidence

- PTY backend used during verification: machine confirmation pending.
- Prompt detection signal: machine confirmation pending.
- Test prompt used: machine confirmation pending.
- First token received signal: machine confirmation pending.
- Timeout behavior observed: machine confirmation pending.
- Retry behavior observed: machine confirmation pending.
- Notes / caveats: the setup page documents login by running `claude` and following browser prompts, but does not document a non-interactive auth success command.

### Success/failure classification evidence

| Classification | Detection signal | Confirmed on machine? | Notes |
|---|---|---|---|
| PTY spawn failure | `[fill]` | `[yes/no]` | `[fill]` |
| Stuck at login prompt | `[fill]` | `[yes/no]` | `[fill]` |
| No response after login | `[fill]` | `[yes/no]` | `[fill]` |
| Insufficient account permission | `[fill]` | `[yes/no]` | `[fill]` |

## Gate C — Credential storage naming evidence

### Questions to answer

- What exact credential entry name appears in macOS Keychain?
- What exact credential entry name appears in Windows Credential Manager?
- What exact credential file path and format are used on Linux / WSL?

### Confirmed credential storage

| Platform | Store type | Exact name / path | Format | Removal default | Evidence |
|---|---|---|---|---|---|
| macOS | not documented | not documented | not documented | docs do not explicitly specify; keep as unresolved until machine verification | official setup page does not name a Keychain item |
| Windows | not documented | not documented | not documented | docs do not explicitly specify; keep as unresolved until machine verification | official setup page does not name a Credential Manager item |
| Linux | not documented | not documented | not documented | docs do not explicitly specify; keep as unresolved until machine verification | official setup page does not name a credential file |
| WSL | not documented | not documented | not documented | docs do not explicitly specify; keep as unresolved until machine verification | official setup page does not name a credential file |

## Required machine matrix

Fill one row per verified environment.

| Machine | OS | Shell | Install path | Removal path (Gate A) | Auth/status path (Gate B) | Credential store name (Gate C) | Result |
|---|---|---|---|---|---|---|---|
| `usabatch’s Mac Pro (5)` | `macOS 26.2 (25C56)` | `zsh` | `pre-existing non-native/global install observed; binary resolves to /Applications/cmux.app/Contents/Resources/bin/claude` | `native uninstall doc paths do not match this machine layout; Gate A not confirmed from this machine alone` | `claude auth status` returns JSON with `loggedIn: true`; `claude --print` exists but needs input; `--headless` unsupported` | `[pending direct credential-store confirmation]` | `partial pass: useful for Gate B, not a clean native-install Gate A machine` |
| `topye Windows VM` | `Windows NT 10.0.22621.0` | `PowerShell 5.1` | `irm https://claude.ai/install.ps1 | iex` first ran without Git and left unusable state; after Git install, rerun failed with Bun out-of-memory during native build install` | `Gate A native uninstall cannot be confirmed because native install never completed successfully` | `Gate B blocked: no working claude binary after install attempts` | `no Claude credential entry observed before auth could begin` | `fail: official install path reported success but did not yield runnable Claude on this VM` |

## Raw evidence log

### macOS

- Machine: `usabatch’s Mac Pro (5)`
- OS version: `macOS 26.2 (25C56)`
- Shell(s): `/bin/zsh`
- Commands run:
  - `date`
  - `sw_vers`
  - `uname -m`
  - `echo "$SHELL"`
  - `which claude`
  - `claude --version`
  - `claude --help`
  - `claude doctor`
  - `claude auth --help`
  - `claude doctor --help`
  - `ls -la ~/.local/bin/claude ~/.local/share/claude ~/.claude ~/.claude.json`
  - `claude auth status`
  - `claude --print`
  - `claude --headless`
  - `scutil --get ComputerName`
  - `sysctl -n machdep.cpu.brand_string`
- Output excerpts:
  - `which claude` → `/Applications/cmux.app/Contents/Resources/bin/claude`
  - `claude --version` → `2.1.109 (Claude Code)`
  - `claude doctor` → failed in this non-TTY shell with `Raw mode is not supported on the current process.stdin...`
  - `claude auth --help` → shows `login`, `logout`, `status` subcommands
  - `ls ~/.local/bin/claude ~/.local/share/claude` → both paths absent on this machine
  - `claude auth status` → JSON output including `"loggedIn": true`, `"authMethod": "claude.ai"`, `"apiProvider": "firstParty"`, `"subscriptionType": "max"`
  - `claude --print` → `Input must be provided either through stdin or as a prompt argument when using --print`
  - `claude --headless` → `error: unknown option '--headless'`
  - `~/.claude.json` → includes `"installMethod": "global"`
- Notes:
  - Gate A decision: this machine does not match the native-install doc layout, so it is not sufficient to confirm native uninstall behavior by itself.
  - Gate B decision: `claude auth status` is now a strong machine-observed candidate for non-interactive login verification on macOS, but unauthenticated behavior and cross-platform behavior are still pending.
  - Gate C decision: not yet checked directly on this machine; credential store naming remains unresolved.

### Windows

- Machine: `topye Windows VM`
- OS version: `Microsoft Windows NT 10.0.22621.0`
- Shell(s): `PowerShell 5.1`
- Commands run:
  - `Get-Date`
  - `[System.Environment]::OSVersion.VersionString`
  - `$env:PROCESSOR_ARCHITECTURE`
  - `$PSVersionTable.PSVersion`
  - `Get-Command git -ErrorAction SilentlyContinue`
  - `Get-Command claude -ErrorAction SilentlyContinue`
  - `wsl --status`
  - `irm https://claude.ai/install.ps1 | iex` (before Git install)
  - `claude --version`
  - `claude doctor`
  - `claude --help`
  - `claude auth --help`
  - `claude auth status`
  - `claude --print`
  - `Get-ChildItem "$HOME\.local\bin\claude*" -ErrorAction SilentlyContinue`
  - `Get-ChildItem "$HOME\.local\share\claude" -Force -ErrorAction SilentlyContinue`
  - `Get-ChildItem "$HOME\.claude" -Force -ErrorAction SilentlyContinue`
  - `Get-Item "$HOME\.claude.json" -ErrorAction SilentlyContinue`
  - `[Environment]::GetEnvironmentVariable("Path", "User")`
  - `cmdkey /list`
  - `Get-ChildItem $HOME -Force | Where-Object { $_.Name -like '.claude*' }`
  - `Get-ChildItem "$HOME\.claude" -Recurse -ErrorAction SilentlyContinue`
  - `Get-Content "$HOME\.claude.json"`
  - `Get-ChildItem "$HOME\AppData\Local\Programs" -Force | Where-Object { $_.Name -match 'Claude|Anthropic' }`
  - `$env:Path`
  - `Get-Command claude -All -ErrorAction SilentlyContinue`
  - `Microsoft.PowerShell.Management\Get-Item "C:\Users\topye\claude" | Format-List *`
  - `cmd /c dir C:\Users\topye\claude`
  - `Get-Command git`
  - `Remove-Item "C:\Users\topye\claude" -Force -ErrorAction SilentlyContinue`
  - `irm https://claude.ai/install.ps1 | iex` (after Git install)
  - `Get-Command claude`
  - `where.exe claude`
- Output excerpts:
  - Before Git install, installer printed `Claude Code on Windows requires git-bash` and still ended with `✅ Installation complete!`
  - Before Git install, `claude` was not runnable and PowerShell reported `CommandNotFoundException`
  - `Get-ChildItem "$HOME\.claude"` showed only `.claude\downloads`
  - `Get-Item "$HOME\.claude.json"` existed and initially contained only `{"firstStartTime": "2026-04-15T06:34:25.713Z"}`
  - User PATH did not include a Claude install directory; it included `C:\Users\topye\AppData\Local\Programs\VibeLign` and `C:\Users\topye`
  - `Get-Command claude -All` resolved to `C:\Users\topye\claude`
  - `Get-Item "C:\Users\topye\claude"` showed a `Length` of `0` bytes
  - `cmd /c dir C:\Users\topye\claude` confirmed a `0` byte file
  - After Git install, rerunning the PowerShell installer printed `Installing Claude Code native build latest...` and then `oh no: Bun has run out of memory.` but still ended with `✅ Installation complete!`
  - After the Git-backed reinstall attempt, `Get-Command claude` failed and `where.exe claude` found no Claude binary
  - `cmdkey /list` showed no obvious Claude-related credential entry before auth began
- Notes:
  - Gate A decision: native uninstall behavior cannot be confirmed on this VM because native install never completed successfully.
  - Gate B decision: blocked on Windows for this VM; no working Claude binary survived install attempts, so `claude auth status` could not be validated.
  - Gate C decision: no Claude credential store entry was observed before auth; final credential naming remains unresolved.
  - Important failure mode: the official PowerShell installer can print success even when prerequisites are missing or the native build install crashes with Bun out-of-memory.

### Linux / WSL

- Machine: `[fill]`
- OS version: `[fill]`
- Shell(s): `[fill]`
- Commands run: `[fill]`
- Output excerpts: `[fill]`
- Notes: `[fill]`

## Real-machine verification checklist

Use this checklist while filling the evidence tables above. Record exact commands and output excerpts in the raw evidence log.

### Common checklist

- [ ] Confirm the current official setup page still matches the install commands referenced in the spec.
- [ ] Record test date, machine name/model, OS version, shell, and architecture.
- [ ] Confirm whether Claude Code was already installed before the test.
- [ ] Record whether Git for Windows is installed on native Windows.
- [ ] Record whether WSL is already enabled and usable.
- [ ] Save output excerpts for every command that influences Gate A, Gate B, or Gate C.

### macOS checklist

#### Environment

- [ ] Record macOS version.
- [ ] Record architecture with `uname -m`.
- [ ] Record available shells with `echo $SHELL` and note whether both zsh and bash are present.

#### Install path confirmation

- [ ] Run: `curl -fsSL https://claude.ai/install.sh | bash`
- [ ] Open a fresh zsh session and run: `claude --version`
- [ ] Open a fresh zsh session and run: `claude doctor`
- [ ] Open a fresh bash session and run: `claude --version`

#### Gate A — removal confirmation

- [ ] Check whether an official uninstall command exists in docs or CLI help.
- [ ] If a command exists, run it and record exact behavior.
- [ ] If no command exists, follow the official documented manual removal steps and record them exactly.
- [ ] Confirm the actual binary path on disk.
- [ ] Confirm actual native data path, user config/state path, and any shell rc mutation.

#### Gate B — auth/status confirmation

- [ ] Test candidate official commands from the Gate B table.
- [ ] If none provide a reliable non-interactive success signal, record `PTY probe` as the primary path.
- [ ] Launch `claude`, complete browser login, and record the observed prompt signal.
- [ ] Send one short test message and record first-token receipt.
- [ ] Record timeout/failure behavior if login stalls or no response arrives.

#### Gate C — credential confirmation

- [ ] Inspect Keychain after login and record the exact item name.
- [ ] Record whether any additional config/token files appear in the user directory.

### Windows checklist

#### Environment

- [ ] Record Windows edition/version/build.
- [ ] Record architecture.
- [ ] Confirm whether Git for Windows is installed.
- [ ] Confirm whether PowerShell, CMD, and WSL are all available.

#### Install path confirmation

- [ ] First try PowerShell official install: `irm https://claude.ai/install.ps1 | iex`
- [ ] If ExecutionPolicy blocks it, record the exact prompt/error and whether a session-scoped bypass would be needed.
- [ ] If PowerShell is blocked, run CMD fallback: `curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd`
- [ ] Open a fresh PowerShell session and run: `claude --version`
- [ ] Open a fresh CMD session and run: `claude --version`
- [ ] Run: `claude doctor`

#### Gate A — removal confirmation

- [ ] Check whether an official uninstall command exists in docs or CLI help.
- [ ] If a command exists, run it and record exact behavior.
- [ ] If no command exists, follow the official documented manual removal steps and record them exactly.
- [ ] Confirm the actual binary path on disk.
- [ ] Confirm actual native data path, user config/state path, user PATH entry mutation, and any shortcuts/launchers.

#### Gate B — auth/status confirmation

- [ ] Test candidate official commands from the Gate B table.
- [ ] If none provide a reliable non-interactive success signal, record `PTY probe` as the primary path.
- [ ] Launch `claude`, complete browser login, and record the observed prompt signal.
- [ ] Send one short test message and record first-token receipt.
- [ ] Record timeout/failure behavior for each required failure class if encountered.

#### Gate C — credential confirmation

- [ ] Inspect Credential Manager after login and record the exact credential item name.
- [ ] Record whether any additional config/token files appear in the user directory.

### WSL checklist

#### Environment

- [ ] Record whether WSL was already enabled before testing.
- [ ] Record distro name/version with `cat /etc/os-release`.
- [ ] Record shell with `echo $SHELL`.

#### Install path confirmation

- [ ] Run inside WSL: `curl -fsSL https://claude.ai/install.sh | bash`
- [ ] Open a fresh WSL shell and run: `claude --version`
- [ ] Run: `claude doctor`

#### Gate A — removal confirmation

- [ ] Check whether an official uninstall command exists in docs or CLI help.
- [ ] If a command exists, run it and record exact behavior.
- [ ] If no command exists, follow the official documented manual removal steps and record them exactly.
- [ ] Confirm the actual binary path on disk.
- [ ] Confirm actual native data path, user config/state path, and shell rc mutation.

#### Gate B — auth/status confirmation

- [ ] Test candidate official commands from the Gate B table.
- [ ] If none provide a reliable non-interactive success signal, record `PTY probe` as the primary path.
- [ ] Launch `claude`, complete browser login, and record the observed prompt signal.
- [ ] Send one short test message and record first-token receipt.
- [ ] Record timeout/failure behavior if login stalls or no response arrives.

#### Gate C — credential confirmation

- [ ] Record the exact credential file path and format used after login.
- [ ] Record whether WSL stores credentials separately from native Windows.

### Evidence capture format

For every platform, capture at least:

- Exact command run
- Full or excerpted stdout/stderr
- File paths observed on disk
- Whether the result was success, failure, or ambiguous
- What row/table in this document was updated from that evidence

## Platform runbooks

Run these in order while filling the evidence document. Keep the exact output snippets in the Raw evidence log.

### macOS runbook

#### 1) Record environment

```bash
date
sw_vers
uname -m
echo "$SHELL"
which zsh || true
which bash || true
which claude || true
```

Record:

- machine name/model
- macOS version
- architecture
- default shell
- whether `claude` already existed before install

#### 2) Install and verify in fresh shells

```bash
curl -fsSL https://claude.ai/install.sh | bash
zsh -lc 'which claude; claude --version'
zsh -lc 'claude doctor'
bash -lc 'which claude; claude --version'
```

Record:

- install output excerpt
- resolved `claude` binary path
- whether zsh verification passed
- whether bash verification passed

#### 3) Gate A — removal path

```bash
zsh -lc 'claude --help'
zsh -lc 'claude help' || true
ls -la ~/.local/bin/claude ~/.claude ~/.claude.json 2>/dev/null
grep -n "claude\|vibelign\|local/bin" ~/.zshrc ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null
```

Then compare the observed state with the official setup/removal docs and record either:

- an official uninstall command, or
- the official manual removal steps

#### 4) Gate B — auth/status path

```bash
zsh -lc 'claude --print' || true
zsh -lc 'claude --headless' || true
zsh -lc 'claude auth status' || true
zsh -lc 'claude'
```

Record:

- which candidate commands exist or fail
- whether any official non-interactive command gives a reliable success signal
- if not, the observed prompt/login/first-token sequence from interactive `claude`

#### 5) Gate C — credential storage

```bash
security find-generic-password -a "$USER" -s "claude" 2>/dev/null || true
security dump-keychain -d login.keychain-db 2>/dev/null | grep -i "claude" -n || true
ls -la ~ | grep "\.claude" || true
find ~/.claude -maxdepth 2 -type f 2>/dev/null || true
```

Record the exact Keychain item name or file path actually used.

### Windows runbook

#### 1) Record environment

PowerShell:

```powershell
Get-Date
[System.Environment]::OSVersion.VersionString
$env:PROCESSOR_ARCHITECTURE
$PSVersionTable.PSVersion
Get-Command git -ErrorAction SilentlyContinue
Get-Command claude -ErrorAction SilentlyContinue
wsl --status
```

CMD:

```cmd
ver
where claude
where git
```

Record:

- Windows edition/version/build
- architecture
- PowerShell version
- whether Git for Windows is installed
- whether WSL is available before testing
- whether `claude` already existed before install

#### 2) Install and verify in fresh shells

PowerShell first:

```powershell
irm https://claude.ai/install.ps1 | iex
```

If blocked, record the exact error and then test CMD fallback:

```cmd
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

Fresh-shell verification:

PowerShell:

```powershell
Get-Command claude
claude --version
claude doctor
```

CMD:

```cmd
where claude
claude --version
```

Record:

- install output excerpt
- whether PowerShell verification passed
- whether CMD verification passed
- exact binary path

#### 3) Gate A — removal path

PowerShell:

```powershell
claude --help
Get-ChildItem $HOME\.local\bin\claude* -ErrorAction SilentlyContinue
Get-ChildItem $HOME\.claude -Force -ErrorAction SilentlyContinue
Get-Item $HOME\.claude.json -ErrorAction SilentlyContinue
[Environment]::GetEnvironmentVariable("Path", "User")
```

CMD:

```cmd
where claude
echo %USERPROFILE%
```

Then compare the observed state with the official setup/removal docs and record either:

- an official uninstall command, or
- the official manual removal steps

#### 4) Gate B — auth/status path

PowerShell:

```powershell
claude --print
claude --headless
claude auth status
claude
```

Use `2>$null` or `-ErrorAction SilentlyContinue` only when re-running noisy checks after you have already captured the primary failure once.

Record:

- which candidate commands exist or fail
- whether any official non-interactive command gives a reliable success signal
- if not, the observed prompt/login/first-token sequence from interactive `claude`

#### 5) Gate C — credential storage

PowerShell:

```powershell
cmdkey /list
Get-ChildItem $HOME -Force | Where-Object { $_.Name -like '.claude*' }
Get-ChildItem $HOME\.claude -Recurse -ErrorAction SilentlyContinue
```

Record the exact Credential Manager entry name or file path actually used.

### WSL runbook

#### 1) Record environment

```bash
date
cat /etc/os-release
uname -m
echo "$SHELL"
which claude || true
```

Record:

- distro name/version
- architecture
- shell
- whether `claude` already existed before install

#### 2) Install and verify in a fresh WSL shell

```bash
curl -fsSL https://claude.ai/install.sh | bash
bash -lc 'which claude; claude --version'
bash -lc 'claude doctor'
```

Record:

- install output excerpt
- exact binary path
- whether verification passed

#### 3) Gate A — removal path

```bash
bash -lc 'claude --help'
ls -la ~/.local/bin/claude ~/.claude ~/.claude.json 2>/dev/null
grep -n "claude\|vibelign\|local/bin" ~/.bashrc ~/.profile 2>/dev/null
```

Then compare the observed state with the official setup/removal docs and record either:

- an official uninstall command, or
- the official manual removal steps

#### 4) Gate B — auth/status path

```bash
bash -lc 'claude --print' || true
bash -lc 'claude --headless' || true
bash -lc 'claude auth status' || true
bash -lc 'claude'
```

Record:

- which candidate commands exist or fail
- whether any official non-interactive command gives a reliable success signal
- if not, the observed prompt/login/first-token sequence from interactive `claude`

#### 5) Gate C — credential storage

```bash
ls -la ~ | grep "\.claude" || true
find ~/.claude -maxdepth 2 -type f 2>/dev/null || true
grep -R "token\|auth\|claude" ~/.claude 2>/dev/null || true
```

Record the exact credential file path and format actually used.

## Suggested execution order

Use this order to reduce ambiguity when multiple environments are available:

1. macOS machine
2. native Windows PowerShell/CMD on one machine
3. WSL on the same Windows machine if available

Reason:

- macOS usually gives the cleanest baseline for shell/path behavior.
- native Windows exposes the main policy/PATH/Git complications.
- WSL should be verified after native Windows so shared-vs-separate credential questions are easier to answer.

## Fill-ready evidence entry formats

Use these blocks as copy-paste templates when converting raw command output into the final evidence sections above.

### macOS example entry format

#### Machine matrix row

| Machine | OS | Shell | Install path | Removal path (Gate A) | Auth/status path (Gate B) | Credential store name (Gate C) | Result |
|---|---|---|---|---|---|---|---|
| `[Mac model / hostname]` | `[macOS version]` | `zsh / bash` | `curl -fsSL https://claude.ai/install.sh \| bash` | `[official uninstall command OR official manual removal steps summary]` | `[official command OR PTY probe]` | `[exact Keychain item name or file path]` | `[pass/fail + short reason]` |

#### Raw evidence log entry

```md
### macOS

- Machine: [fill]
- OS version: [fill]
- Shell(s): [fill]
- Architecture: [fill]
- Claude preinstalled before test?: [yes/no]
- Commands run:
  - `curl -fsSL https://claude.ai/install.sh | bash`
  - `zsh -lc 'which claude; claude --version'`
  - `zsh -lc 'claude doctor'`
  - `bash -lc 'which claude; claude --version'`
  - `zsh -lc 'claude --print'`
  - `zsh -lc 'claude --headless'`
  - `zsh -lc 'claude auth status'`
  - `zsh -lc 'claude'`
  - `security dump-keychain -d login.keychain-db | grep -i "claude" -n`
- Output excerpts:
  - Install: `[fill]`
  - zsh verify: `[fill]`
  - bash verify: `[fill]`
  - doctor: `[fill]`
  - auth/status probes: `[fill]`
  - interactive login/result: `[fill]`
  - keychain/file evidence: `[fill]`
- Notes:
  - Gate A decision: `[fill]`
  - Gate B decision: `[fill]`
  - Gate C decision: `[fill]`
```

### Windows example entry format

#### Machine matrix row

| Machine | OS | Shell | Install path | Removal path (Gate A) | Auth/status path (Gate B) | Credential store name (Gate C) | Result |
|---|---|---|---|---|---|---|---|
| `[PC model / hostname]` | `[Windows version/build]` | `PowerShell / CMD` | `irm https://claude.ai/install.ps1 \| iex` or `curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd` | `[official uninstall command OR official manual removal steps summary]` | `[official command OR PTY probe]` | `[exact Credential Manager entry or file path]` | `[pass/fail + short reason]` |

#### Raw evidence log entry

```md
### Windows

- Machine: [fill]
- OS version: [fill]
- Shell(s): [fill]
- Architecture: [fill]
- Git for Windows installed?: [yes/no]
- WSL available before test?: [yes/no]
- Claude preinstalled before test?: [yes/no]
- Commands run:
  - `irm https://claude.ai/install.ps1 | iex`
  - `curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd`
  - `Get-Command claude`
  - `claude --version`
  - `claude doctor`
  - `where claude`
  - `claude --print`
  - `claude --headless`
  - `claude auth status`
  - `claude`
  - `cmdkey /list`
- Output excerpts:
  - PowerShell install: `[fill]`
  - CMD fallback install: `[fill if used]`
  - PowerShell verify: `[fill]`
  - CMD verify: `[fill]`
  - doctor: `[fill]`
  - auth/status probes: `[fill]`
  - interactive login/result: `[fill]`
  - credential/file evidence: `[fill]`
- Notes:
  - ExecutionPolicy/AMSI behavior: `[fill]`
  - Gate A decision: `[fill]`
  - Gate B decision: `[fill]`
  - Gate C decision: `[fill]`
```

### WSL example entry format

#### Machine matrix row

| Machine | OS | Shell | Install path | Removal path (Gate A) | Auth/status path (Gate B) | Credential store name (Gate C) | Result |
|---|---|---|---|---|---|---|---|
| `[Windows host + distro name]` | `[WSL distro/version]` | `bash` | `curl -fsSL https://claude.ai/install.sh \| bash` | `[official uninstall command OR official manual removal steps summary]` | `[official command OR PTY probe]` | `[exact credential file path / store name]` | `[pass/fail + short reason]` |

#### Raw evidence log entry

```md
### Linux / WSL

- Machine: [fill]
- OS version: [fill]
- Shell(s): [fill]
- Architecture: [fill]
- WSL already enabled before test?: [yes/no]
- Claude preinstalled before test?: [yes/no]
- Commands run:
  - `curl -fsSL https://claude.ai/install.sh | bash`
  - `bash -lc 'which claude; claude --version'`
  - `bash -lc 'claude doctor'`
  - `bash -lc 'claude --print'`
  - `bash -lc 'claude --headless'`
  - `bash -lc 'claude auth status'`
  - `bash -lc 'claude'`
  - `find ~/.claude -maxdepth 2 -type f`
- Output excerpts:
  - Install: `[fill]`
  - verify: `[fill]`
  - doctor: `[fill]`
  - auth/status probes: `[fill]`
  - interactive login/result: `[fill]`
  - credential/file evidence: `[fill]`
- Notes:
  - Gate A decision: `[fill]`
  - Gate B decision: `[fill]`
  - Gate C decision: `[fill]`
  - Separate from native Windows credentials?: `[yes/no/unclear]`
```

### Gate decision summary format

Use this shorter format after each platform is verified to keep the top sections consistent.

```md
- Gate A final decision: [fill]
- Gate B final decision: [fill]
- Gate C final decision: [fill]
- Evidence source(s): [machine names + dates]
```

## Implementation release gate

Implementation may begin only when all items below are true:

- [ ] Gate A decision is filled and removal branch rule is fixed.
- [ ] Gate B decision is filled and the success detection path is fixed.
- [ ] Gate C credential store names/paths are fixed from real-machine evidence.
- [ ] Required machine matrix includes confirmed Windows, macOS, and WSL coverage.
- [ ] All placeholders in this file are replaced with evidence-backed values.
