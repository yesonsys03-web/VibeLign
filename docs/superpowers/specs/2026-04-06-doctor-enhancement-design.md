# Doctor 기능 개선 설계 (Phase 1: 진단 강화)

## 개요

VibeLign doctor의 진단 능력을 확대하여 보안, 의존성, 코드 품질, 프로젝트 설정까지 검사한다.
기존 구조 분석(파일 길이, 앵커, 코드 혼합)은 유지하고, 4개 카테고리를 추가한다.
Phase 2에서 자동 수정(split_file, 코드 분리)을 확장할 기반이 된다.

## 대상 사용자

초보자부터 시니어까지 모든 레벨. 진단 결과 메시지는 한국어로 쉽게 표현한다.

## 아키텍처

### 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `vibelign/core/risk_analyzer.py` | 4개 신규 검사 모듈 호출 통합 |
| `vibelign/core/checks/security.py` | (신규) 보안 검사 |
| `vibelign/core/checks/dependency.py` | (신규) 의존성 검사 |
| `vibelign/core/checks/quality.py` | (신규) 코드 품질 검사 |
| `vibelign/core/checks/project_config.py` | (신규) 프로젝트 설정 검사 |
| `vibelign/core/checks/__init__.py` | (신규) 패키지 초기화 |
| `vibelign/core/doctor_v2.py` | 카테고리별 가중 점수 체계 적용 |

### 검사 모듈 인터페이스

각 검사 모듈은 동일한 인터페이스를 따른다:

```python
def check(root: Path, file_entries: list[dict], strict: bool = False) -> list[Issue]
```

`Issue`는 기존 `risk_analyzer.py`의 이슈 딕셔너리 포맷을 따른다:
```python
{
    "category": str,      # "security" | "dependency" | "quality" | "config"
    "severity": str,      # "high" | "medium" | "low"
    "file": str,          # 대상 파일 상대경로 (없으면 "")
    "found": str,         # 사람이 읽을 수 있는 설명
    "next_step": str,     # 권장 해결 방법
}
```

## 섹션 1: 보안 검사 (`checks/security.py`)

| 검사 | 감지 방법 | 심각도 |
|------|----------|--------|
| 하드코딩된 API 키/비밀번호 | 정규식 패턴 (AWS, OpenAI, 일반 패턴) | high |
| `.env` 파일이 `.gitignore`에 없음 | gitignore 파싱 | high |
| 보호 대상 파일이 보호 안 됨 | `.vibelign_protected` vs 민감 파일 목록 비교 | medium |

기존 `secret_scan.py`의 패턴을 재활용한다. `secret_scan.py`에서 패턴 상수를 import하여 중복을 피한다.

## 섹션 2: 의존성 검사 (`checks/dependency.py`)

| 검사 | 감지 방법 | 심각도 |
|------|----------|--------|
| 미사용 import (정밀) | AST 파싱으로 실제 사용 여부 확인 (Python/JS) | low |
| 순환 참조 (깊이 확장) | N단계 그래프 탐색 (기존 2단계에서 확장) | medium |
| 존재하지 않는 모듈 import | import 경로를 실제 파일시스템과 대조 | high |
| 중복 import | 같은 모듈을 다른 이름으로 여러 번 import | low |

Python은 `ast` 모듈, JS/TS는 정규식 기반으로 분석한다.
기존 `risk_analyzer.py`의 순환 참조/미사용 import 로직을 이 모듈로 이전한다.

## 섹션 3: 코드 품질 (`checks/quality.py`)

| 검사 | 감지 방법 | 심각도 |
|------|----------|--------|
| 중복 코드 블록 | 해시 기반 유사 블록 탐지 (5줄 이상 동일) | medium |
| 복잡도 높은 함수 | 중첩 깊이(4+) 또는 분기 수(10+) 카운트 | medium |
| 네이밍 규칙 위반 | Python: snake_case, JS/TS: camelCase 일관성 체크 | low |
| 빈 except/catch 블록 | AST/정규식으로 감지 | medium |
| TODO/FIXME/HACK 잔존 | 정규식 스캔 + 개수 보고 | low |

복잡도 분석은 AST 기반, 중복 탐지는 해시 비교로 외부 의존성 없이 구현한다.

## 섹션 4: 프로젝트 설정 (`checks/project_config.py`)

| 검사 | 감지 방법 | 심각도 |
|------|----------|--------|
| `.gitignore` 누락 | 프로젝트 루트에 파일 존재 여부 | high |
| `.gitignore`에 필수 항목 누락 | `node_modules`, `__pycache__`, `.env`, `dist` 등 | medium |
| README 부재 | `README.md` 또는 `README` 존재 여부 | low |
| 패키지 설정 불일치 | `pyproject.toml`/`package.json` 존재 + 기본 필드 확인 | low |
| `.vibelign/` 초기화 상태 | `project_map.json` 존재 + 최신 여부 | medium |

언어별 필수 항목은 프로젝트에서 감지된 언어에 맞춰 동적으로 판단한다.

## 섹션 5: 점수 체계 개편

기존: `100 - (legacy_score × 4)` 단순 감점.
변경: 카테고리별 가중 평균.

| 카테고리 | 비중 | 내용 |
|----------|------|------|
| 보안 | 30% | 비밀 노출, gitignore |
| 구조 | 30% | 파일 길이, 앵커, 코드 혼합 (기존) |
| 의존성 | 15% | 순환 참조, 미사용 import |
| 품질 | 15% | 중복, 복잡도, 네이밍 |
| 설정 | 10% | gitignore, README, 패키지 설정 |

각 카테고리 내에서 0~100점. 가중 평균으로 총점 산출.
STATUS_LEVELS 임계값은 기존과 동일 (85/70/50/30).

`doctor_v2.py`의 `DoctorV2Report`에 `category_scores: dict[str, int]` 필드를 추가하여 카테고리별 점수를 노출한다.

## 출력 형식 변경

### 텍스트 출력 (기본)
```
프로젝트 점수: 72 / 100 (괜찮은 편이에요)
  보안: 85  구조: 60  의존성: 80  품질: 70  설정: 90

먼저 보면 좋은 점:
1. [보안·높음] .env 파일이 .gitignore에 없습니다
2. [구조·높음] vibelign/vib_cli.py 파일이 너무 깁니다 (1025줄)
3. [품질·중간] vibelign/core/utils.py에 빈 except 블록이 3개 있습니다
```

### JSON 출력 (`--json`)
기존 envelope 포맷에 `category_scores`와 `issue.category`, `issue.severity` 필드를 추가한다.

## Phase 2 연결점 (자동 수정 확대)

이 진단 강화가 완료되면:
- `split_file`: 품질/구조 진단 결과를 기반으로 AI가 분할 계획을 생성
- `separate_concerns`: 코드 혼합 진단 결과를 기반으로 UI/비즈니스 로직 분리
- 각각 `action_engine`에 새로운 executor를 추가

## 테스트 계획

- 각 검사 모듈별 단위 테스트 (알려진 패턴이 포함된 fixture 파일)
- 점수 체계 테스트 (카테고리별 점수 → 총점 계산 검증)
- 기존 `vib doctor` 출력과의 호환성 테스트 (`--json` 포맷)
- `--strict` 모드에서 임계값이 더 엄격하게 적용되는지 검증
