# Patch Accuracy C2 — Layer Routing Design (2026-04-12)

ICE round 1 에서 backlog 로 넘어간 C2 (F2 layer routing) 를 재측정 결과에 맞춰 재설계한 문서. 원래 ICE 스펙(`2026-04-11-patch-accuracy-ice-design.md`)의 F2 taxonomy 는 stale 판정 — 실제 실패 경로가 다르다. 이 스펙이 C2 의 canonical 설계.

---

## 1. Goal & Scope

### 목표
`add_email_domain_check` 시나리오(F2 잔존 실패, pinned-intent 샌드박스 기준)를 해소하면서 나머지 4 시나리오의 현상을 유지한다. 예상 점수 변화:

- files: **4/5 → 5/5** (det, ai 양쪽)
- anchor: **3/4 → 4/4** (det, ai 양쪽)
- recall@3: 유지

### 범위 제외
- **C4 (multi-fanout)** — `add_password_change` 는 이 스펙 밖. 별도 ICE 라운드 필요.
- **AI 경로 재설계** — C2 는 deterministic scoring 에 투입하고 `_ai_select_file` 은 건드리지 않는다. C6 deference 룰이 high-confidence 시 AI 스킵하므로 det 개선이 자동으로 ai 에도 반영됨.
- **전역 vocabulary 확장** — `_UI_REQUEST_KEYWORDS` 를 늘려 "플로우 요청"(회원가입/로그인) 을 UI 요청으로 재분류하는 접근은 드리프트 위험이 커서 채택하지 않는다. 대신 caller 그래프 기반 규칙으로 우회.

---

## 2. Root-cause 재진단

### 2.1 ICE 스펙이 기록한 F2 가설 (stale)

> "요청에 'email domain', 'password' 같은 명사가 들어가면 매처가 해당 이름의 **utility 함수 앵커**(`VALIDATORS_VALIDATE_EMAIL_DOMAIN`, `VALIDATORS_VALIDATE_PASSWORD`) 에 최고점을 주고, 실제로 수정해야 하는 **호출자 측**(`SIGNUP_HANDLE_SIGNUP`) 은 놓친다."

### 2.2 2026-04-12 실측 결과 (canonical)

pinned-intent 샌드박스 (`vibelign.commands.bench_fixtures.prepare_patch_sandbox`) 에서 `vibelign.core.patch_suggester.score_candidates` 로 `add_email_domain_check` 재측정:

```
score_candidates top 5 (request: "회원가입 시 허용된 이메일 도메인만 통과하도록 검사 추가"):
    19  api/auth.py          ← 실제 top1 (service layer)
    11  core/database.py
     4  core/validators.py   ← ICE 스펙이 top 이라 기록한 파일 (틀림)
     2  pages/signup.py      ← 정답
     0  api/users.py
```

`suggest_patch(root, req, use_ai=False).target_anchor` = `AUTH_REGISTER_USER`. `use_ai=True` 도 동일 (C6 deference 덕분).

### 2.3 실제 F2 메커니즘 (3중 복합)

**(a) `pages/` 분류 누락**
`vibelign/commands/vib_start_cmd.py:368` 의 `ui_tokens` = `["ui", "view", "views", "window", "dialog", "widget", "screen"]`. `"pages"`, `"routes"` 같은 웹 프레임워크 컨벤션이 빠져 있어 `pages/signup.py` 가 `ui_modules` 에 들어가지 않고 `classify_path(rel)` 이 `None` 을 반환한다.

**(b) UI/service gate 의 vocabulary 의존성**
`vibelign/core/patch_suggester.py:531-536` 의 layer-aware 보너스 (`+4 if ui_request and map_kind=="ui"`) 는 `_is_ui_request(request_tokens)` 가 True 일 때만 발화. `_UI_REQUEST_KEYWORDS` (line 323-348) 는 시각 요소 사전(`button`, `색상`, `화면`, `레이아웃` …)이라 **"회원가입 시 … 검사 추가"** 같은 **플로우 요청** 을 인식하지 못 한다. `_is_service_request` (line 442-446) 도 `{service, auth, login, api, worker, guard, schedule}` 만 봄 — 요청 토큰에 없어서 False. **→ layer 보너스 전부 dormant.**

**(c) Anchor 의미매치의 압도**
(a)+(b) 결과 layer 정보가 0 기여하는 상태에서, `api/auth.py` 는 path_tokens(`api`, `auth`) + `AUTH_REGISTER_USER` 앵커 이름의 `register ↔ 회원가입` 의미매치로 19점을 얻는다. `pages/signup.py` 는 path_token(`signup`) 매치의 +2 만 받음. 격차 19 vs 2.

### 2.4 empirical 검증

파트 1 단독으로 `pages/signup.py`, `pages/login.py`, `pages/profile.py` 를 `ui_modules` 에 재분류해 측정 → 모든 5 시나리오의 스코어가 **완전 동일**. `_is_ui_request = False` 인 한 UI 분류는 무관하다는 것을 empirically 확인. 파트 1 과 파트 2 를 반드시 함께 적용해야 효과가 나온다.

---

## 3. Design — 2 파트

### 3.1 파트 1 — `pages/`, `routes/` 를 `ui_modules` 로 분류

**변경 지점**: `vibelign/commands/vib_start_cmd.py:368`

```python
ui_tokens = [
    "ui", "view", "views", "window", "dialog", "widget", "screen",
    "pages",   # 추가
    "routes",  # 추가
]
```

**효과**:
- `pages/signup.py`, `pages/login.py`, `pages/profile.py`, 그리고 `routes/*.py` 가 `project_map.ui_modules` 에 들어감
- `files[rel].category` 가 `"ui"` 로 저장됨 (line 418-425 의 `category: str(data["category"])` 는 `scan_cache` 의 카테고리 — 별도 경로임에 주의. 이 값은 이 파트로 바뀌지 않음. `classify_path()` 는 `ui_modules` frozenset 을 우선 검사하므로 올바르게 `"ui"` 를 반환)
- `classify_path(rel)` → `"ui"` 반환
- `anchor_priority(rel)` → `+3`

**파트 1 단독 효과**: `score_candidates` 의 점수에는 0 영향 (§2.4 검증). 파트 1 의 목적은 파트 2 의 전제조건 — caller 그래프에서 "ui 층 caller" 를 식별하려면 분류가 먼저 있어야 한다.

**리스크**: `pages/` 디렉토리를 문서나 정적 리소스 용도로 쓰는 프로젝트에 false positive. 실제 리포에서는 거의 없고, `anchor_priority` 에서 +3 보너스가 붙더라도 그 파일에 앵커가 있어야 실제로 스코어 영향이 발생해서 impact 는 낮음.

### 3.2 파트 2 — Caller-routing 후처리 규칙

**변경 지점**: `vibelign/core/patch_suggester.py::score_candidates` 이후 후처리 단계. 또는 `score_candidates` 내부 마지막 단계로 삽입.

**설계 원칙**:
- C1 verb-aware scoring 결과 리스트를 받아 후처리 — base scoring pipeline 은 건드리지 않음
- 규칙은 **네 개 gate 모두 통과할 때만** 발화
- 하나라도 실패하면 원본 리스트를 그대로 반환 (null-safety)

**의사코드**:

```python
def _apply_layer_routing(
    candidates: list[tuple[Path, int]],
    request_tokens: list[str],
    project_map: ProjectMapSnapshot,
    root: Path,
) -> list[tuple[Path, int]]:
    if not candidates or project_map is None:
        return candidates

    top_path, top_score = candidates[0]
    top_rel = relpath_str(root, top_path)

    # Gate 1: top1 이 ui 층이 아니어야
    if project_map.classify_path(top_rel) == "ui":
        return candidates

    # Gate 2: 요청 verb cluster 가 ADD/CREATE/INTEGRATE 여야
    #          (MUTATE/FIX 는 utility/service 층 정당한 수정 가능성 → 보호)
    verb_cluster = _classify_request_verb(request_tokens)  # C1 재활용
    if verb_cluster not in {"ADD", "CREATE", "INTEGRATE"}:
        return candidates

    # Gate 3: top1 을 import 하는 ui 층 파일이 존재해야
    file_entry = project_map.files.get(top_rel, {})
    importers = file_entry.get("imported_by", [])
    ui_importers = [
        rel for rel in importers
        if project_map.classify_path(rel) == "ui"
    ]
    if not ui_importers:
        return candidates

    # Gate 4: ui importer 중 현재 candidates 에 score > 0 으로 존재하는 것이 있어야
    #          (request 와 전혀 무관한 caller 에 spray 방지)
    candidate_map = {relpath_str(root, p): (p, s) for p, s in candidates}
    positive_callers = [
        (rel, *candidate_map[rel])
        for rel in ui_importers
        if rel in candidate_map and candidate_map[rel][1] > 0
    ]
    if not positive_callers:
        return candidates

    # 발화: 최고 base score 를 가진 ui caller 를 선택
    positive_callers.sort(key=lambda item: item[2], reverse=True)
    _, best_path, best_base = positive_callers[0]

    # 점수 재배정 (값 근거는 §3.3)
    BOOST = 18
    PENALTY = 3

    new_candidates = []
    for path, score in candidates:
        if path == best_path:
            new_candidates.append((path, score + BOOST))
        elif path == top_path:
            new_candidates.append((path, score - PENALTY))
        else:
            new_candidates.append((path, score))
    new_candidates.sort(key=lambda item: item[1], reverse=True)
    return new_candidates
```

**Verb cluster 재활용**: C1 (`2026-04-11-patch-accuracy-c1-verb-aware-scoring.md`) 에서 도입한 동사 분류 모듈을 그대로 참조. ADD/CREATE/INTEGRATE 클러스터가 C1 에 없으면 이번 라운드에 추가 (C1 은 MUTATE vs READ 구분 중심). 클러스터 정의 예시:

- **ADD**: 추가, add, 끼워, 붙여, 삽입, insert, include, append
- **CREATE**: 만들, 생성, create, build, new, 신규
- **INTEGRATE**: 적용, apply, 연결, wire, 호출, integrate, 결합
- **MUTATE**: 수정, 변경, 고쳐, fix, 바꿔, update, change (C1 기존)
- **FIX**: 버그, bug, 오류, 문제, 고쳐, repair (C1 에 있으면 재활용)

### 3.3 스코어링 파라미터 근거

실측 격차: `api/auth.py` 19 vs `pages/signup.py` 2 (=17). 발화 후 caller 가 top1 을 이기려면 `(caller_base + BOOST) > (top1_base − PENALTY)` → `BOOST + PENALTY > 17`.

- **BOOST = 18**: `2 + 18 = 20` vs `19 − 3 = 16`. 4점 margin — C1 의 verb 보너스(+5) 한 번이 뒤에 붙어도 안전하게 유지됨. 이 격차는 벤치 샘플 프로젝트 기준이지만 실제 프로젝트에서도 anchor-name 의미매치로 발생할 수 있는 비슷한 규모의 격차를 커버하려는 의도.
- **PENALTY = 3**: 작게 유지. 이 규칙이 잘못 발화(false positive)했을 때 정당한 service/logic 층 수정을 3점만 깎으면 C1 verb 보너스 등 다른 신호로 원복 가능. PENALTY 를 키우면 false positive 피해가 커진다.

**민감도 노트**: 이 값들은 벤치 점수 분포에 맞춰 튜닝된 숫자. 파트 2 구현 중 단위 테스트에서 상수화하고 향후 측정치가 달라지면 재튜닝 대상임을 주석으로 명시할 것.

### 3.4 구현 파일 리스트

- `vibelign/commands/vib_start_cmd.py` — 파트 1 (ui_tokens 2 단어 추가)
- `vibelign/core/patch_suggester.py` — 파트 2 (`_apply_layer_routing` 후처리 함수 + `score_candidates` 꼬리에서 호출). verb cluster 상수 추가 (C1 모듈 재활용 가능 여부 확인)
- `tests/test_patch_anchor_priority.py` 또는 신규 `tests/test_layer_routing.py` — 단위 테스트
- `tests/test_patch_accuracy_scenarios.py` — 5 시나리오 통합 가드
- `tests/benchmark/patch_accuracy_baseline.json` — `vib bench --patch --update-baseline` 로 갱신

---

## 4. Regression Safety

### 4.1 Gate 별 보호 범위

| Gate | 보호 대상 |
|---|---|
| 1. top1 ui? | `change_error_msg`, `add_bio_length_limit` (이미 ui 로 라우팅됨) |
| 2. ADD verb? | `fix_login_lock_bug` (FIX/MUTATE verb), 임의의 "utility 버그 고쳐줘" 요청 |
| 3. ui importer 有? | 순수 backend 케이스 (importer 없는 server-only 유틸) |
| 4. positive caller 有? | request 와 무관한 caller (e.g., `app.py`) 에 boost spray 방지 |

### 4.2 5 시나리오 기대 결과

| 시나리오 | top1 layer | verb | ui caller? | 발화 | 결과 |
|---|---|---|---|---|---|
| change_error_msg | ui (pages/login.py) | MUTATE | - | ❌ | 유지 ✅ |
| add_email_domain_check | service (api/auth.py) | ADD | ✅ pages/signup.py (score 2) | **✅** | **flip → pages/signup.py ✅** |
| fix_login_lock_bug | service (api/auth.py) | FIX | ✅ pages/login.py | ❌ | 유지 ✅ |
| add_bio_length_limit | ui (pages/profile.py) | ADD | - | ❌ | 유지 ✅ |
| add_password_change | service (api/auth.py) | ADD | ✅ but no caller with score > 0 for "비밀번호" | ❌ | 유지 ❌ (C4 대기) |

### 4.3 단위 테스트 설계

`tests/test_layer_routing.py` (신규):

- **`test_gate1_ui_top1_does_not_fire`**: top1 이 이미 ui 로 분류된 mock project_map 에서 `_apply_layer_routing` 가 원본 리스트를 그대로 반환
- **`test_gate2_mutate_verb_does_not_fire`**: 요청 토큰에 "수정"/"fix" 가 있을 때 발화 안 함
- **`test_gate2_add_verb_fires`**: 요청 토큰에 "추가"/"add" 가 있을 때 발화 조건 충족 시 실제로 순위 변경
- **`test_gate3_no_ui_importer_does_not_fire`**: importers 리스트는 있지만 전부 non-ui 일 때 발화 안 함
- **`test_gate4_zero_score_caller_does_not_fire`**: ui importer 가 있지만 candidates 에 0점으로 존재할 때 발화 안 함
- **`test_scoring_flips_ranking`**: gate 모두 통과 시 BOOST/PENALTY 적용 후 top1 이 실제로 교체되는지

`tests/test_patch_accuracy_scenarios.py` 에 회귀 가드 보강:

- **`test_c2_email_domain_check_routes_to_signup`** — pinned-intent 샌드박스에서 `suggest_patch` 결과 `target_file == "pages/signup.py"` 및 `target_anchor == "SIGNUP_HANDLE_SIGNUP"` 단언
- 기존 4 시나리오의 회귀 단언 유지

`tests/test_bench_patch_command.py` 는 baseline diff 기반이라 baseline 업데이트만 하면 자동 반영.

### 4.4 False positive 모니터링 포인트

C2 적용 후 측정해야 할 시나리오 타입(현재 벤치에 없지만 추후 추가 고려):

- **"validate_email_domain 의 정규식 버그 고쳐줘"** — MUTATE verb 라 gate 2 에서 막혀야 함. 단위 테스트로 검증.
- **"backend 에 캐시 계층 추가"** — service/logic top1 + ADD verb 지만 ui caller 없음 → gate 3 에서 막혀야 함.
- **"특정 utility 함수 교체"** — top1 이 utility 인데 ui caller 가 있는 경우. verb 가 "교체"(REPLACE?)면 MUTATE 와 CREATE 경계. verb 클러스터 정의에서 명확히 해야 — 이번 라운드에서는 REPLACE 를 MUTATE 로 분류 (기본값 보수적).

---

## 5. Out of Scope

- **AI 경로 재설계** (`_ai_select_file`): C6 deference 가 high-confidence 일 때 det 결과를 그대로 쓰므로 자동 개선. 이 스펙 밖.
- **Multi-file fanout** (C4): `add_password_change` 는 이 스펙으로 고쳐지지 않음. 별도 라운드.
- **Vocabulary 확장**: `_UI_REQUEST_KEYWORDS` 에 "회원가입"/"로그인" 추가는 경계 케이스 드리프트 위험. caller 그래프 접근이 더 안전.
- **함수 수준 caller 그래프**: 현재 `imported_by` 는 파일 수준. F2 해소에는 충분하지만, 더 정교한 라우팅이 필요하면 추후 AST 기반 함수 참조 인덱스 필요.

---

## 6. Acceptance Criteria

1. `vib bench --patch --json` 실행 시:
   - `det.totals.files_ok == "5/5"`
   - `det.totals.anchor_ok == "4/4"`
   - `ai.totals.files_ok == "5/5"`
   - `ai.totals.anchor_ok == "4/4"`
   - `regressions == []`
2. `add_email_domain_check` 의 `det.target_file == "pages/signup.py"`, `target_anchor == "SIGNUP_HANDLE_SIGNUP"`
3. 신규 단위 테스트 6개 전부 통과
4. 기존 `tests/test_patch_accuracy_scenarios.py` + `tests/test_bench_patch_command.py` + `tests/test_patch_suggester_score_candidates.py` 회귀 없음
5. `vib bench --patch --update-baseline` 로 baseline 갱신, 커밋
6. `uv tool install --reinstall --force .` 재설치 후 end-to-end 재현 확인

---

## 7. ICE 점수 재계산

ICE round 1 당시 C2: `I=5, C=3, E=2` → 3.75.

2026-04-12 재측정 반영 후:

- **I=4**: F2 1 건 직접 해소. anchor 3/4 → 4/4.
- **C=5**: 실측으로 루트 원인 확인 (§2.2), 회귀 경로 게이트로 전부 보호 (§4), 데이터 인프라 완비 (§2 imported_by 검증).
- **E=4**: 반나절 (파트 1 30분, 파트 2 2 시간, 테스트 + baseline 1 시간).

`(4 × 5) / (6 − 4) = **10.0**`

C1 (8.33) 보다 높음 — 재측정이 원래 hidden risk 였던 C=3 을 해소했기 때문.

---

## 8. Next Step

이 스펙을 사용자가 리뷰한 후, `superpowers:writing-plans` 로 구현 plan (`docs/superpowers/plans/2026-04-12-patch-accuracy-c2-layer-routing.md`) 을 작성한다. Plan 에서는:

- 파트 1 → 파트 2 순서 (파트 1 단독 smoke test 로 회귀 없음 확인 후 파트 2 진입)
- verb cluster 모듈의 C1 재활용 가능성 우선 탐색, 필요 시 새 상수 추가
- baseline 업데이트는 마지막 단계 (파트 2 완료 + 회귀 가드 전부 green 이후)
