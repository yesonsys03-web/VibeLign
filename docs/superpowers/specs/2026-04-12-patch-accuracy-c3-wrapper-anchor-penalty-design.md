# C3: Wrapper Anchor Penalty — Design Spec

## §1 Problem Statement

`choose_anchor` picks file-level wrapper anchors (e.g., `SIGNUP`) over
more-specific leaf anchors (e.g., `SIGNUP_HANDLE_SIGNUP`) when the leaf
receives a verb-cluster mismatch penalty (-4) and the wrapper has no verb
signal (score 0).

This is the sole remaining anchor_ok failure in the patch-accuracy
benchmark: `add_email_domain_check` picks `SIGNUP` (score 0) instead of
`SIGNUP_HANDLE_SIGNUP` (score -4 due to CREATE↔MUTATE mismatch on
"handle").

**Impact**: anchor_ok stays at 3/4 instead of the achievable 4/4.

## §2 Root Cause Analysis

Wrapper anchors like `SIGNUP`, `LOGIN`, `AUTH`, `PROFILE` share a
structural pattern:

1. Single token after `_path_tokens()` — e.g., `{"signup"}`
2. That token appears in every sibling anchor's token set
3. No verb token → `_classify_anchor_verb` returns `None` → verb bonus is 0

Because verb mismatch gives -4 and the wrapper gets 0, any leaf with a
mismatched verb loses to the wrapper. This only matters when there is zero
keyword overlap (Korean request tokens vs English anchor tokens), which is
the case for `add_email_domain_check`.

### Why not fix "handle" classification?

"handle" is classified as MUTATE, and this is load-bearing:

- `change_error_msg`: LOGIN_HANDLE_LOGIN gets +5 from MUTATE↔MUTATE match
- `add_bio_length_limit`: PROFILE_HANDLE_PROFILE_UPDATE gets +5 from
  MUTATE↔MUTATE match (via "update", but "handle" confirms)

Removing or reclassifying "handle" breaks these two passing scenarios.

## §3 Design

### §3.1 Wrapper Detection

An anchor `A` is a **wrapper** when ALL of:

1. The file has ≥2 anchors
2. `_path_tokens(A)` has exactly 1 element
3. That element appears in `_path_tokens(other)` for every other anchor
   in the file

This detects file-scope container anchors without relying on naming
conventions or ordering.

### §3.2 Penalty

```python
_WRAPPER_ANCHOR_PENALTY = 5
```

Applied inside `choose_anchor`, after `_anchor_quality_penalty`:

```python
if _is_wrapper_anchor(anchor, anchors):
    score -= _WRAPPER_ANCHOR_PENALTY
```

### §3.3 `_is_wrapper_anchor` helper

```python
def _is_wrapper_anchor(anchor: str, all_anchors: list[str]) -> bool:
    if len(all_anchors) < 2:
        return False
    tokens = _path_tokens(anchor)
    if len(tokens) != 1:
        return False
    token = next(iter(tokens))
    return all(
        token in _path_tokens(other)
        for other in all_anchors
        if other != anchor
    )
```

Placed immediately before `choose_anchor` in `patch_suggester.py`.

### §3.4 Post-patch scoring

| Scenario | Wrapper | Wrapper score | Correct leaf | Leaf score | Winner |
|---|---|---|---|---|---|
| change_error_msg | LOGIN | 0-5 = **-5** | LOGIN_HANDLE_LOGIN | **+5** | ✓ leaf |
| add_email_domain_check | SIGNUP | 0-5 = **-5** | SIGNUP_HANDLE_SIGNUP | **-4** | ✓ leaf |
| fix_login_lock_bug | AUTH | 0-5 = **-5** | AUTH_LOGIN_USER | **+3** | ✓ leaf |
| add_bio_length_limit | PROFILE | 0-5 = **-5** | PROFILE_HANDLE_PROFILE_UPDATE | **+5** | ✓ leaf |

All 4 scenarios route to the correct anchor. Zero regressions.

### §3.5 Edge cases

- **Single-anchor file** (e.g., `CONFIG`): condition 1 fails → no penalty.
  Correct: the only anchor should always be selected.
- **Two-token wrapper** (e.g., `APP_MAIN` alongside `APP_MAIN_RUN`):
  condition 2 fails → no penalty. Correct: `APP_MAIN` is already specific
  enough to be a valid target.
- **Multiple wrapper-like anchors**: impossible if condition 3 requires
  the single token to appear in ALL siblings. Only one anchor per file
  can satisfy this.

## §4 Scope

### In scope
- `_is_wrapper_anchor` helper function
- `_WRAPPER_ANCHOR_PENALTY` constant
- Penalty insertion in `choose_anchor`
- Unit tests for wrapper detection and penalty effect
- Scenario regression guard update (`add_email_domain_check` anchor tightened)
- Baseline update via `vib bench --patch --update-baseline`

### Out of scope
- Verb cluster reclassification (no changes to `_ANCHOR_VERB_TOKENS`)
- `_apply_layer_routing` (C2, already complete)
- `add_password_change` (C4, multi-fanout)
- anchor_meta population in sandbox fixtures

## §5 Acceptance Criteria

1. `vib bench --patch`: det/ai `anchor_ok == "4/4"`, `files_ok == "5/5"`, `recall@3 == "5/5"`
2. `regressions == []`
3. Full test suite passes (607+ tests)
4. `test_add_email_domain_check_routes_to_signup_page` tightened from
   `startswith("SIGNUP")` to exact `== "SIGNUP_HANDLE_SIGNUP"`
5. New unit tests for `_is_wrapper_anchor` (at least 4 cases)

## §6 Files to Modify

| File | Change |
|---|---|
| `vibelign/core/patch_suggester.py` | Add `_WRAPPER_ANCHOR_PENALTY`, `_is_wrapper_anchor`, modify `choose_anchor` |
| `tests/test_patch_accuracy_scenarios.py` | Tighten anchor assertion |
| `tests/test_wrapper_anchor_penalty.py` | New: unit tests for detection + scoring |
| `tests/benchmark/patch_accuracy_baseline.json` | Updated via CLI |
