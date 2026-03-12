# VibeGuard Final Release Test Notes

This final release includes fixes for the pre-release blockers:

## Fixed

### 1. `watchdog` import no longer breaks the whole CLI
Only `vibeguard watch` requires `watchdog`.
All other commands run without it.

### 2. Patch suggestion deprioritizes bad candidates
Examples:
- `__init__.py`
- tests
- docs
- cache folders

### 3. Fallback explain / guard is quieter
Freshly created repos are less likely to be marked HIGH immediately.

### 4. Doctor paths are relative
User-facing issue messages now show relative paths where possible.

### 5. Anchor default target set is narrower
Default behavior avoids:
- tests
- docs
- `.github`
- virtualenvs
- dependency folders
