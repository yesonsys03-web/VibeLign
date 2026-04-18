# VibeLign 1.x → 2.0 마이그레이션 가이드

VibeLign 2.0 은 대부분의 1.x 사용자에게 **무중단 업그레이드** 입니다.
`pip install -U vibelign` 만으로 끝나고, CLI 명령 (`vib doctor`, `vib anchor`, `vib patch`, …) 시그니처는 호환됩니다.

이 문서는 **호환되지 않는 지점** 만 짧게 정리합니다.

---

## TL;DR

| 항목 | 1.x | 2.0 | 영향 |
| --- | --- | --- | --- |
| `vib` CLI 명령 | — | — | ✅ 그대로 |
| `vib` 설치/실행 | `pip install vibelign` | 동일 | ✅ 그대로 |
| MCP 서버 바이너리 | `vibelign-mcp` | 동일 | ✅ 그대로 |
| Python 모듈 임포트 경로 | `vibelign.vib_cli` | `vibelign.cli.vib_cli` | ⚠️ 변경 |
| MCP 모듈 임포트 경로 | `vibelign.mcp_server` | `vibelign.mcp.mcp_server` | ⚠️ 변경 |
| `anchor_meta.json` 포맷 | `intent` / `aliases` 만 | `_source` 필드 추가 | ✅ 자동 업그레이드 |
| AI 보강 consent UI | 런타임 확인 프롬프트 | 설정 토글로 일원화 | ⚠️ 재설정 |
| 데스크톱 GUI | 없음 | Tauri 앱 (macOS/Windows) | 🆕 선택 사항 |

---

## 1. Python 모듈 임포트 경로 이동 (BREAKING)

코드/테스트에서 `vibelign` 을 직접 임포트하는 경우에만 해당합니다.
`vib` CLI 만 쓰는 사용자는 영향 없음.

```python
# 1.x
from vibelign.vib_cli import main
from vibelign.mcp_server import run_server

# 2.0
from vibelign.cli.vib_cli import main
from vibelign.mcp.mcp_server import run_server
```

`pyproject.toml` 의 console-script 진입점은 내부적으로 이미 2.0 경로로 갱신돼 있어
`vib`, `vibelign-mcp` 바이너리는 그대로 동작합니다.

### 왜 옮겼나

- `vibelign/cli/` 아래 CLI 런타임/명령/자동완성이 분리되면서 진입 파일을 같은 패키지로 통합
- `vibelign/mcp/` 아래 dispatch / handlers / tool_specs / state_store 가 분리되면서 `mcp_server.py` 도 동일 패키지로 이동

---

## 2. Anchor 메타데이터 `_source` 필드 도입

`.vibelign/anchor_meta.json` 의 각 앵커 엔트리에 `_source` 필드가 추가됐습니다.

```json
{
  "src/main.py::MAIN_LOOP": {
    "intent": "...",
    "aliases": ["..."],
    "_source": "code"     // code | ai | manual | ai_failed
  }
}
```

### 동작

- 기존 1.x 엔트리는 `_source` 가 없으므로 **`code` 로 간주** 됩니다.
- `vib anchor --auto-intent` 는 `_source="code"` 엔트리만 덮어씁니다.
- `_source` 가 `ai` / `manual` / `ai_failed` 인 엔트리는 **`--force` 플래그 없이는 보존** 됩니다.
- GUI 앵커카드 / Doctor APPLY AI 보강 결과는 `_source="ai"` 로 기록돼, 다음번 `doctor --apply` 실행 때 자동으로 덮어쓰이지 않습니다.

### 마이그레이션 액션

특별히 할 일 없습니다. 2.0 을 처음 실행하면 다음 `vib anchor` / `vib doctor --apply` 시점에 자동으로 `_source` 가 채워집니다.

기존에 **수작업으로 편집한 intent/aliases 를 보호** 하고 싶으면, 해당 엔트리에 `"_source": "manual"` 을 수동으로 넣어 두세요.

---

## 3. AI 보강 옵트인 체계 변경

1.x 에서는 AI 호출 직전에 consent 프롬프트가 떴습니다.
2.0 은 **전역 옵트인 토글** 로 일원화됐습니다.

### 바뀐 점

- consent 확인 UI 삭제
- GUI: `설정` 탭 → `AI 보강` 토글 (off 기본)
- CLI: `vib ai-enhance enable` / `vib ai-enhance disable`
- `~/.vibelign/api_keys` 파일 권한이 `0600` 으로 제한됨

### 마이그레이션 액션

1.x 에서 AI 보강을 썼다면 2.0 설치 후 **한 번은** 토글을 다시 켜야 합니다.

```bash
vib ai-enhance enable --provider anthropic
# 또는 GUI 설정 페이지에서 토글 on
```

API 키 위치 (`~/.vibelign/api_keys`) 는 동일합니다.

---

## 4. 데스크톱 GUI (선택 사항, 신규)

2.0 부터 macOS / Windows 데스크톱 앱이 함께 제공됩니다.
[릴리즈 페이지](https://github.com/yesonsys03-web/VibeLign/releases/latest) 에서 `.dmg` / `.exe` / `.msi` 를 받아 설치하세요.

GUI 는 내부적으로 `vib` CLI 를 호출하므로 **CLI-only 워크플로와 100% 호환** 됩니다.
기존 `.vibelign/` 저장소는 그대로 열립니다.

---

## 5. Doctor 출력 포맷 변경

`vib doctor --json` 응답의 필드 구조가 일부 재정렬됐습니다.

- `score` / `status` / `issues[].severity` 필드가 명시화됨
- CI 에서 `vib doctor --json` 결과를 파싱하는 경우 필드 이름/타입 변경을 한 번 확인하세요.

---

## 6. 체크포인트 / 패치 호환성

- `.vibelign/checkpoints/` 디렉토리는 1.x 와 동일한 포맷입니다. 기존 체크포인트를 그대로 복원할 수 있습니다.
- `vib patch` 는 2.0 에서 `target_anchor` 기반 소형 패치를 우선합니다.
  전면 재작성 요청은 거부되거나 여러 앵커 패치로 분할됩니다 (의도된 변경).

---

## 문제 보고

마이그레이션 중 예상치 못한 동작이 있으면
[GitHub Issues](https://github.com/yesonsys03-web/VibeLign/issues) 에 `migration-v2` 라벨로 올려주세요.
