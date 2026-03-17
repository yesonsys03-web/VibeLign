# VibeLign 개선 로드맵

> 이 문서는 코드 리뷰와 대화를 기반으로 정리한 문제점과 해결 방안입니다.
> 수정이 완료되면 체크박스에 표시하세요.

---

## ✅ 1순위: 앵커 + 코드맵 통합 — 완료

**현재 문제:**
`project_map.py`의 코드맵은 파일을 entry/ui/service/core/large로 분류하지만, 각 파일의 앵커 정보가 포함되지 않는다. AI가 코드맵을 읽어도 앵커를 보려면 각 파일을 따로 열어야 하므로 토큰이 낭비되고, 코알못이 AI에게 수정을 시킬 때 코드맵 하나로 전체 구조를 파악할 수 없다.

**왜 중요한가:**
코알못이 AI에게 "장바구니 수정해줘"라고 할 때, AI가 코드맵 하나만 읽으면 어떤 파일에 어떤 앵커가 있고, 뭐가 뭐랑 연결되어 있는지 한 번에 파악할 수 있어야 한다. 지금은 코드맵 → 파일 열기 → 앵커 확인이라는 3단계가 필요해서 토큰 소모가 크고 정확도가 떨어진다.

**해결 방안:**

- [x] `project_map.py`의 `ProjectMapSnapshot`에 앵커 인덱스 필드 추가
  - 각 파일별로 포함된 앵커 이름 목록을 코드맵 JSON에 포함
  - 예: `"anchor_index": {"pages/login.js": ["LOGIN_FORM", "LOGIN_FORM_HANDLE_SUBMIT"], ...}`

- [x] 코드맵 생성 시 `anchor_tools.py`의 `collect_anchor_index()`를 호출하여 앵커 정보를 자동 수집

- [x] 코드맵 JSON 출력에 앵커 요약 섹션 추가 (`files` 필드)
  - 파일 경로 + 분류(ui/service/core) + 앵커 목록 + line_count가 한눈에 보이는 구조
  - AI가 이 파일 하나만 읽으면 전체 프로젝트를 이해할 수 있도록 설계

- [x] `vib_start_cmd.py`에서 코드맵 생성 시 앵커 통합 버전이 자동으로 만들어지도록 연결

- [x] 코드맵에 프로젝트 트리 구조 포함 (`tree` 필드)
  - AI가 코드맵 하나만 읽으면 폴더/파일 구조를 즉시 파악할 수 있도록 트리 섹션 추가
  - AI의 토큰 소모를 줄이는 핵심 전략: 디렉토리 탐색 없이 "목차"로 바로 작업 대상 특정 가능
  - `node_modules`, `.git`, `__pycache__` 등 불필요한 폴더 자동 제외 필터링 완료
  - Python `pathlib` 기반 walk 구현 (fd 없어도 동작)

**목표 출력 형태:**
```json
{
  "schema_version": 2,
  "project_name": "my-app",
  "tree": [
    "src/",
    "  pages/",
    "    login.js",
    "    signup.js",
    "  api/",
    "    auth.js",
    "  utils/",
    "    helpers.js"
  ],
  "files": {
    "pages/login.js": {
      "category": "ui",
      "anchors": ["LOGIN_FORM_START", "LOGIN_FORM_HANDLE_SUBMIT"],
      "line_count": 85
    },
    "api/auth.js": {
      "category": "service",
      "anchors": ["AUTH_LOGIN", "AUTH_TOKEN_REFRESH"],
      "line_count": 120,
      "warning": "수정 시 LOGIN_FORM에 영향"
    }
  }
}
```

---

## ✅ 2순위: 글로벌 디바운싱 (watch 개선) — 완료

**현재 문제:**
`watch_engine.py`의 디바운싱이 **파일별**로 작동한다. `_debounced()` 메서드가 개별 파일의 마지막 이벤트 시간만 체크하므로, AI가 파일 5개를 연달아 수정하면 코드맵 갱신 같은 작업이 5번 실행될 수 있다. 중간 상태의 불완전한 처리가 발생할 위험이 있다.

**왜 중요한가:**
AI가 한 번의 작업에서 여러 파일을 동시에 수정하는 건 매우 흔한 패턴이다. 파일별 디바운싱만으로는 "AI의 작업이 끝날 때까지 기다렸다가 한 번만 처리"하는 것이 불가능하다.

**해결 방안:**

- [x] `watch_engine.py`에 글로벌 디바운싱 타이머 추가
  - 파일별 디바운싱은 유지하되, 별도의 글로벌 타이머를 둬서 "마지막 파일 변경 후 N초간 변경 없으면 한 번만 실행"하는 로직 추가
  - `threading.Timer`를 활용하여 이전 타이머를 취소하고 새 타이머를 시작하는 방식

- [x] 글로벌 디바운싱 후 실행할 작업 정의
  - 코드맵 자동 갱신 (`_refresh_project_map`)
  - 앵커 재스캔 포함 (`collect_anchor_index`)
  - `pending_changes` 목록으로 변경 파일 일괄 수집

- [x] `--debounce-ms` 옵션을 글로벌 디바운싱에도 적용되도록 확장

**핵심 로직:**
```python
import threading

class VibeLignWatchHandler(FileSystemEventHandler):
    def __init__(self, ...):
        ...
        self.global_timer = None
        self.pending_changes = []  # 변경된 파일 경로 축적
    
    def _schedule_global_update(self, rel_path):
        self.pending_changes.append(rel_path)
        if self.global_timer:
            self.global_timer.cancel()
        self.global_timer = threading.Timer(
            self.debounce_ms / 1000.0,
            self._run_global_update
        )
        self.global_timer.start()
    
    def _run_global_update(self):
        changed = list(set(self.pending_changes))
        self.pending_changes.clear()
        # 여기서 코드맵 갱신, 앵커 재스캔 등 한 번만 실행
```

---

## ✅ 3순위: codespeak 한국어 지원 — 완료

**현재 문제:**
`codespeak.py`의 `ACTION_MAP`, `LAYER_MAP`, `STOPWORDS`가 전부 영어 기반이다. `tokenize_request()`가 `[a-zA-Z_]+` 패턴으로 토큰을 추출하므로 한국어 입력은 아예 토큰화되지 않는다. 코알못이 "로그인 버튼 크기 키워줘"라고 입력하면 빈 토큰 리스트가 반환되어 모든 추론이 실패한다.

**왜 중요한가:**
한국어 사용자가 주 타겟인데, codespeak의 핵심 기능인 자연어→구조화 변환이 한국어에서 작동하지 않는다.

**해결 방안:**

- [x] `tokenize_request()`에 한국어 토큰 추출 로직 추가
  - 정규식을 `[a-zA-Z_가-힣]+`로 확장하여 한글 단어도 추출되도록 수정

- [x] `ACTION_MAP`에 한국어 동작어 추가
  ```python
  ACTION_MAP = {
      "add": ["add", "insert", "create", ..., "추가", "넣어", "만들어", "생성"],
      "remove": ["remove", "delete", ..., "삭제", "제거", "지워", "없애"],
      "fix": ["fix", "repair", ..., "수정", "고쳐", "해결", "버그"],
      "update": ["update", "change", ..., "변경", "수정", "바꿔", "키워", "줄여"],
      ...
  }
  ```

- [x] `LAYER_MAP`에 한국어 키워드 추가
  ```python
  LAYER_MAP = {
      "ui": ["button", "window", ..., "버튼", "화면", "창", "레이아웃", "메뉴"],
      "service": ["login", "auth", ..., "로그인", "인증", "회원", "비밀번호"],
      ...
  }
  ```

- [x] `STOPWORDS`에 한국어 불용어 추가
  ```python
  STOPWORDS = {"a", "an", "the", ..., "을", "를", "이", "가", "에", "에서", "좀", "해줘", "줘"}
  ```

- [ ] (선택) 규칙 기반 대신 Gemini API를 활용한 하이브리드 방식 검토
  - 규칙 매칭 실패 시 `ai_codespeak.py`의 AI 변환으로 폴백
  - 이미 `ai_codespeak.py` 파일이 존재하므로 이를 활용

---

## ✅ 4순위: 코드맵 자동 갱신 연동 — 완료

**현재 문제:**
`watch_engine.py`는 파일 변경 감지 시 경고/상태만 출력하고, 코드맵 갱신은 하지 않는다. 코알못이 AI에게 코드를 수정시킨 후 코드맵을 수동으로 갱신해야 한다. 까먹으면 코드맵이 낡은 상태가 되어 다음 AI가 잘못된 정보를 참조한다.

**왜 중요한가:**
코알못은 "코드맵 갱신"이라는 개념 자체를 인지하기 어렵다. watch가 자동으로 코드맵을 최신 상태로 유지해야 코알못이 아무것도 신경 쓰지 않아도 된다.

**해결 방안:**

- [x] 글로벌 디바운싱(2순위)의 `_run_global_update()` → `_refresh_project_map()` 연결

- [x] 코드맵 갱신 중 잠금(lock) 메커니즘 추가 (tmp_path 원자 교체 방식)

- [x] 코드맵 상단에 갱신 시각 메타데이터 추가 (`updated_at`)
  ```json
  {
    "updated_at": "2026-03-16T14:32:05Z",
    "files_tracked": 12,
    "status": "최신"
  }
  ```

---

## 🟡 5순위: 앵커에 의도(intent) 정보 추가

**현재 문제:**
현재 앵커는 `ANCHOR: MODULE_NAME_START/END` 형태로 위치만 표시한다. "이 코드가 무엇을 하는지", "왜 이렇게 만들었는지", "어디에 영향을 주는지" 같은 의도 정보가 없다.

**왜 중요한가:**
코알못이 "아까 그 회원가입 화면"이라고 하면, AI가 `SIGNUP_FORM`이라는 앵커 이름만으로는 매칭하기 어렵다. 하지만 앵커에 "이메일/비밀번호로 회원가입하는 폼"이라는 의도가 적혀 있으면 자연어 매칭이 가능하다. 또한 AI가 수정할 때 연결 관계를 모르면 다른 기능을 망가뜨리는 문제도 의도 앵커로 줄일 수 있다.

**해결 방안:**

- [ ] 앵커 형식 확장 설계
  - 현재: `# === ANCHOR: MODULE_START ===`
  - 확장안 검토: 의도/연결 정보를 주석 블록으로 추가할지, 별도 메타데이터 파일로 관리할지 결정
  - 코드 내부 주석 방식의 예:
    ```python
    # === ANCHOR: LOGIN_FORM_START ===
    # @INTENT: 이메일/비밀번호 입력받아 로그인 처리
    # @CONNECTS: AUTH_API, USER_DB
    # @WARNING: 수정 시 AUTH_API에 영향
    ```
  - 별도 메타데이터 파일 방식의 예:
    `.vibelign/anchor_meta.json`에 의도 정보를 저장

- [ ] 의도 정보 자동 생성 방안 결정
  - Gemini API를 사용하여 코드 분석 후 의도를 자동 추론하는 방식 검토
  - `ask` 커맨드의 기존 AI 연동을 활용 가능

- [ ] `anchor_tools.py`의 `insert_module_anchors()`, `insert_python_symbol_anchors()`, `insert_js_symbol_anchors()`에 의도 정보 삽입 로직 추가

- [ ] `patch_suggester.py`에서 의도 정보를 활용한 매칭 정확도 향상

---

## ✅ 6순위: 명령어 통합 (anchor + map 하나로) — 완료

**현재 문제:**
앵커 생성과 코드맵 생성이 별도 명령어이다. 코알못이 두 명령어를 순서대로 실행해야 하는 것 자체가 부담이다.

**왜 중요한가:**
코알못은 "앵커 먼저 돌리고, 그다음 코드맵"이라는 워크플로우를 기억하고 관리하는 것 자체가 어렵다. 하나의 명령어로 통합되어야 한다.

**해결 방안:**

- [x] `vib scan` 명령어 구현 — 앵커 스캔 + 앵커 인덱스 갱신 + 코드맵 재생성 한 번에 수행
  - `vib scan`: 앵커 추천 + 코드맵 갱신
  - `vib scan --auto`: 앵커 자동 삽입 + 코드맵 갱신
  - `vib start --quickstart`: start + anchor --auto 통합 실행

- [x] `watch` 모드에서 자동 갱신 시에도 통합 로직이 실행되도록 연결 (watch_engine)

---

## ✅ 7순위: watch 모드에서 코드맵 갱신 상태 표시 — 완료

**현재 문제:**
watch가 파일 변경을 감지하면 경고만 출력한다. 코알못은 "지금 코드맵이 최신인지" 알 수 없다.

**해결 방안:**

- [x] watch 출력에 코드맵 갱신 상태 메시지 추가
  - `✅ 파일 N개 변경 감지 → 코드맵 자동 갱신 완료`

- [x] 코드맵이 갱신 중일 때는 상태 표시
  - `⏳ 코드맵 갱신 중... (파일 N개 변경)`

---

## ✅ 8순위: codespeak 변환에서 앵커 활용 — 완료

**현재 문제:**
`patch_suggester.py`는 앵커 메타데이터를 활용하여 수정 대상 파일과 앵커를 추천하지만, `codespeak.py`의 변환 결과에는 앵커 정보가 포함되지 않는다. 두 시스템이 분리되어 있다.

**왜 중요한가:**
codespeak 변환 결과에 "이 앵커를 수정하세요"라는 정보가 포함되면, 코알못이 AI에게 붙여넣을 때 AI가 바로 정확한 위치를 찾을 수 있다.

**해결 방안:**

- [x] `codespeak.py`의 `build_codespeak()` 결과에 `patch_suggester.py`의 추천 앵커 정보를 통합
  - `CodeSpeakResult`에 `target_file`, `target_anchor` 필드 구현 완료

- [x] patch 커맨드 출력에 codespeak + 앵커 위치가 함께 표시되도록 개선 (1.5.7)

---

## ✅ 9순위: 고속 검색 도구 통합 (fd, ripgrep, ast-grep) — 완료 (fd/rg)

**현재 문제:**
코드맵 생성 시 파일 수집은 Python의 `os.walk`, 앵커 스캔은 파일별 정규식 매칭, 심볼 감지는 Python AST 파싱을 사용한다. 프로젝트 규모가 커지면 이 과정이 느려지며, AI 코딩 도구들(Claude Code, OpenCode 등)이 이미 활용하는 고속 Rust 기반 도구들을 활용하지 않고 있다.

**왜 중요한가:**
코알못이 `vibelign start`를 실행하거나 `watch` 모드에서 코드맵이 자동 갱신될 때, 수천 개 파일을 빠르게 처리해야 한다. 트리 구조 생성, 앵커 스캔, 심볼 감지가 빨라야 코알못이 기다리지 않고 바로 작업에 들어갈 수 있다.

**도구별 활용 방안:**

- [x] **fd** → `iter_source_files()`에서 fd 우선 사용, 없으면 `os.walk` 폴백
  - `.gitignore` 자동 존중, 숨김 파일/바이너리 자동 제외

- [x] **ripgrep (rg)** → `collect_anchor_index()`에서 rg 우선 사용, 없으면 Python 폴백
  - 전체 프로젝트 앵커를 한 번에 수집

- [ ] **ast-grep** → 스킵 결정
  - fd/rg로 속도 문제 해결 완료. ast-grep은 "심볼 감지 정확도" 이슈로 별도 판단 필요
  - 엣지 케이스(데코레이터 중첩, TypeScript 제네릭 등)에서만 차이 발생

**설치 전략 (코알못 친화적):**

- [x] `vibelign start` 실행 시 고속 도구 자동 감지
  - `has_fd()`, `has_rg()` 체크 → 없으면 안내 메시지 출력
  - 없어도 Python 폴백으로 정상 작동 (속도 차이만)

- [x] 내부 래퍼 모듈 `fast_tools.py` 구현
  - `iter_source_files`: fd → os.walk 폴백
  - `collect_anchor_index`: rg → Python 폴백

**참고:** 이 항목은 1순위(트리 구조), 2순위(글로벌 디바운싱), 4순위(코드맵 자동 갱신)의 성능을 모두 끌어올리는 인프라 역할을 한다.

---

## ✅ 10순위: 증분 스캔 + 캐시 전략 — 완료

**현재 문제:**
코드맵 갱신 시 매번 전체 프로젝트를 처음부터 다시 스캔한다. 파일이 1,000개인 프로젝트에서 1개만 바뀌어도 1,000개를 전부 다시 읽는다. 프로젝트가 커질수록 갱신 시간이 선형으로 증가한다.

**왜 중요한가:**
watch 모드에서 코드맵 자동 갱신(4순위)이 구현되면, 파일 변경 때마다 전체 스캔을 돌리면 불필요한 부하가 생긴다. 변경된 파일만 다시 스캔하면 프로젝트 규모와 관계없이 갱신 시간이 일정하게 유지된다.

**해결 방안:**

- [x] `.vibelign/scan_cache.json` — 파일별 mtime + size + anchors + category + line_count 캐시
  - mtime/size 동일하면 캐시 재사용, 다르면 해당 파일만 재스캔

- [x] 캐시 무효화 3단계 전략
  - **watch 이벤트 감지 시** → `invalidated=set(changed)` 로 즉시 무효화
  - **일반 스캔 시** → mtime+size 비교로 변경 파일만 재스캔
  - **강제 스캔 시** → `force=True` 로 전체 재스캔

- [x] 새 파일 / 삭제된 파일 자동 감지
  - 캐시에 없는 파일 → 새 파일로 무조건 스캔
  - 디스크에 없는 캐시 항목 → 자동 제거

- [x] `scan_cache.py` 신규 구현, `meta_paths.py`에 `scan_cache_path` 추가
- [x] `scan_cache.json` → `.gitignore` 자동 추가 (팀 협업 시 mtime 충돌 방지)
- [x] `watch_engine.py` → `incremental_scan(invalidated=set(changed))` 연동 완료

**기대 효과:**
- 파일 1,000개 프로젝트에서 1개 변경 시: 전체 스캔 대비 약 100~1,000배 빠른 갱신
- watch 모드에서 코드맵 갱신이 프로젝트 규모와 무관하게 거의 즉시 완료
- 9순위(고속 검색 도구)와 결합하면 대규모 프로젝트에서도 실시간 코드맵 유지 가능

**참고:** 이 항목은 4순위(코드맵 자동 갱신)와 2순위(글로벌 디바운싱)가 구현된 후에 적용하면 효과가 극대화된다.

---

## 📋 참고: 현재 기능 상태 전체 정리

| 기능 | 커맨드 | 상태 | 비고 |
|------|--------|------|------|
| 프로젝트 초기 설정 | `start` | ✅ 완성 | |
| 업데이트/재설치 | `init` | ✅ 완성 | |
| 앵커 삽입 | `anchor` | ✅ 완성 | Python, JS/TS 지원 |
| 코드맵 생성 | (start/init 내) | ✅ 완성 | tree + files(category/anchors/line_count) 통합 완료 |
| 패치 프롬프트 | `patch` | ✅ 완성 | AI 전달 블록 간소화 완료, codespeak 한국어 지원 완료 |
| 코드 설명 (AI) | `ask` | ✅ 완성 | 5개 AI provider 지원 |
| 변경사항 설명 | `explain` | ✅ 완성 | 중학생 레벨 설명 |
| 프로젝트 진단 | `doctor` | ✅ 완성 | 점수제 + 해결책 제공 |
| 안전 리포트 | `guard` | ✅ 완성 | doctor + explain 통합 |
| 체크포인트 저장 | `checkpoint` | ✅ 완성 | SHA256 + 보존 정책 |
| 되돌리기 | `undo` | ✅ 완성 | |
| 이력 보기 | `history` | ✅ 완성 | |
| 파일 보호 | `protect` | ✅ 완성 | |
| 실시간 감시 | `watch` | ✅ 완성 | 글로벌 디바운싱 완료 |
| 템플릿 내보내기 | `export` | ✅ 완성 | claude, opencode, cursor, antigravity |
| API 설정 | `config` | ✅ 완성 | |
| 설치 안내 | (epilog) | ✅ 완성 | uv/pip 모두 지원 |

---

## 📋 작업 순서 요약

| 순위 | 작업 | 영향도 | 난이도 |
|------|------|--------|--------|
| ✅ 1 | 앵커 + 코드맵 통합 (트리 구조 포함) | 매우 높음 | 중간 |
| ✅ 2 | codespeak 한국어 지원 | 높음 | 중간 |
| ✅ 3 | 글로벌 디바운싱 | 높음 | 낮음 |
| ✅ 4 | 코드맵 자동 갱신 연동 | 높음 | 중간 |
| 🔴 5 | 앵커 의도(intent) 정보 | 중간 | 높음 |
| ✅ 6 | 명령어 통합 (`vib scan`) | 중간 | 낮음 |
| ✅ 7 | watch 상태 표시 | 낮음 | 낮음 |
| ✅ 8 | codespeak + 앵커 연동 | 중간 | 중간 |
| ✅ 9 | 고속 검색 도구 통합 (fd/rg) | 높음 | 낮음 |
| ✅ 10 | 증분 스캔 + 캐시 전략 | 높음 | 중간 |

---

## ✅ 완료된 개선 이력

| 날짜 | 버전 | 작업 내용 |
|------|------|-----------|
| 2026-03-17 | 1.5.7 | `vib patch` AI 전달 블록 간소화 — 중복/불필요 항목 제거, "📋 복사 안내" 구분선 추가, 8순위 일부 달성 |
| 2026-03-17 | 1.5.8 | codespeak 한국어 지원 완료 — LAYER_MAP UI 키워드 보강, STOPWORDS 한국어 추가, `_infer_subject` action 복합어 제거, `CODESPEAK_V0_RE` 한국어 subject 허용 |
| 2026-03-17 | 1.5.8 | 글로벌 디바운싱 완료 확인 — `watch_engine.py`에 `global_timer`, `pending_changes`, `_schedule_global_update`, `_run_global_update`, `_refresh_project_map` 구현 완료 (파일별 디바운싱과 병행, `--debounce-ms` 적용) |
| 2026-03-17 | 1.5.9 | 앵커 + 코드맵 통합 완료 — `files` 필드(category/anchors/line_count)와 `tree` 필드(디렉토리 구조) 추가, `ProjectMapSnapshot`에 `tree`/`files` 반영, watch 엔진 갱신 시 `files` anchors 자동 동기화 |
| 2026-03-17 | 1.5.9 | 4·6·7·8순위 기구현 확인 — 코드맵 자동 갱신(watch), `vib scan` 통합 명령어, watch 상태 메시지, codespeak+앵커 연동 모두 이미 완료 상태 |
| 2026-03-17 | 1.5.10~13 | 9순위 완료 — `fast_tools.py` 구현, `iter_source_files`(fd폴백), `collect_anchor_index`(rg폴백), `vib start` 실행 시 도구 감지 안내 |
| 2026-03-17 | 1.5.14~16 | 10순위 완료 — `scan_cache.py` 증분 스캔, `scan_cache.json` gitignore 자동 추가, watch 엔진 incremental_scan 연동 |
| 2026-03-17 | 1.5.14 | `strip_anchors()` 추가, `vib scan --auto` 앵커 문제 파일 자동 재삽입 구현 |
| 2026-03-17 | 1.5.15 | `vib scan` 순서 개선 — 앵커 수정 후 코드맵 갱신, 중복 스캔 제거 |
| 2026-03-17 | 1.5.16 | `anchor_index.json` 포맷 통일 (schema_version/anchors/files), watch 중 자동 갱신 추가 |

---

> 💡 **참고**: 이 문서는 2026년 3월 16일 Claude와의 대화를 기반으로 작성되었습니다.
> 2026년 3월 17일: 1순위에 트리 구조 포함, 9순위 고속 검색 도구 통합, 10순위 증분 스캔 + 캐시 전략 추가.
> 2026년 3월 17일: codespeak 한국어 지원을 2순위로 상향 (주 타겟이 한국어 사용자이므로 코어 기능 우선).
> 각 항목은 독립적으로 작업 가능하지만, 1순위→3순위→4순위는 순서를 지키는 것을 권장합니다.
> 9순위는 독립적이나, 1·3·4순위 작업의 성능을 끌어올리므로 조기 도입을 권장합니다.
> 10순위는 3순위→4순위 이후에 적용하면 효과가 극대화됩니다.
