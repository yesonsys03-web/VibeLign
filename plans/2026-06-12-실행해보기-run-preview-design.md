# 실행해보기 (Run & Preview) — 설계 (design)

> 작성 2026-06-12 · 브레인스토밍 세션에서 사용자와 단계별 승인
> 근거: 작업방(Tier 1)이 "코드 작성·검증"까지 해결했지만, 초보는 **완성된 코드를 어떻게 켜는지** 모른다("npm install && npm start"는 외계어). 제품의 마지막 빈칸 = "그래서 이걸 어떻게 써?"
> 선행: 작업방 Tier 1(plans/2026-06-12-작업방-tier1-design.md) · 가이드레이어(2026-06-10) 5️⃣ 결과 검증

## 0. 한 줄 정의

**"빌드해서 배포"가 아니라 "실행해서 확인"을 먼저 — 버튼 하나로 dev 모드 실행, 웹은 앱 내 미리보기, 실패하면 작업방으로 넘겨 AI가 고치는 루프를 닫는다.**

빌드보다 가볍고 즉각적이며, 작업방 러너·watch 수명주기 인프라를 재사용한다. "빌드/배포"는 정체성(안전 코딩 도구) 밖이라 MVP에서 제외한다.

## 1. 확정 결정 (브레인스토밍 승인 이력)

| 결정 | 선택 | 기각 대안 · 이유 |
|---|---|---|
| 1순위 | **실행(dev run)** | 빌드 우선 — 타입별 빌드 파이프라인 폭발, 실패 시 더 막막, 수정 루프에 무거움. 빌드는 "완성 후 공유" 후속 단계 |
| 프로젝트 타입 | **자동 감지로 둘 다** — 웹(webview)·Electron(외부 창) | 단일 타입 — 알람앱은 Electron, 그러나 웹앱이 더 흔하고 미리보기가 쉬움. 감지로 양쪽 수용 |
| 의존성 설치 | **자동 설치 후 실행** — node_modules 없으면 npm install 먼저 | 안내만 — 초보는 npm install 도 모름. 진행 표시하며 한 번에 이어지게 |
| 실행 실패 | **AI가 고치게 작업방으로 넘기기** | 표시만 — 초보는 에러 로그를 못 읽음. "만들기→실행→고치기" 루프 완성 |
| MVP 범위 | **"실행해보기"만** | 실행+내보내기 — 빌드는 타입별로 무겁고 정체성 밖. 수요 확인 후 후속 |
| 러너 구조 | **watch 장기 프로세스 패턴 + 작업방 스트리밍 결합** | 독립 러너(중복) / 터미널 노출(Tier 0 재림, 안전 배선 우회) |

## 2. 사용자 여정 — 가이드 5️⃣에 연결

가이드 5️⃣(결과 검증)는 지금 guard 만 본다. **guard = 코드가 안전한가, 실행 = 진짜 작동하는가** — 둘은 검증의 두 축이다.

| 단계 | 현재 | 실행해보기 도입 후 |
|---|---|---|
| 4️⃣ AI 작업 | 작업방에서 코드 생성·테스트 | (변화 없음) |
| 5️⃣ 검증 | 홈/작업방의 guard 자동 검사 | guard(안전) + **▶ 실행해보기(작동)** 두 축. 웹은 앱 내 미리보기로 즉시 확인 |
| 실패 시 | 백업에서 되돌리기 | **"이 실행 에러 고쳐줘 →"** 로 작업방 재진입 — 루프가 닫힌다 |

작업방 결과 화면(guard pass 후)에 "▶ 실행해보기" 주행동을 노출한다. "내가 만든 게 진짜 돌아간다"는 성취가 첫 사이클 완주 축하(🎉)와 만난다.

## 3. 아키텍처 — 재사용 자산 + 신규

작업방에서 이미 만들어 검증한 인프라를 그대로 확장한다.

| 능력 | 소스 | 재사용 방식 |
|---|---|---|
| 장기 프로세스 수명주기(시작/중지/트리 kill/앱종료 정리) | `watch.rs` — `WatchState`/`Arc<Mutex<Runtime>>`, `kill_watch_child`(트리 kill), `Drop`, `stop_for_exit` | 패턴 복제 → `RunState`. dev 서버는 watch 처럼 "안 끝나는" 프로세스라 정확히 맞다 |
| 라인 스트리밍 → UI | `work_room.rs` `spawn_output_thread` → `app.emit` | 그대로 — install·실행 출력을 `run-output` 이벤트로 |
| CLI 탐지(.cmd/.exe 셔임) | `planning_persona.rs` `find_executable` + `augmented_vib_path` | 그대로 — npm/node/electron 해석 |
| 명령 화이트리스트 | 작업방 `allowed_tools_value` 패턴 | 실행 명령(npm run dev/start)만 — 단, 여기선 VibeLign 이 직접 spawn 하므로 CLI 권한이 아니라 **러너 자체의 명령 고정**(임의 명령 자체를 안 받음) |
| 실행 로그 영속 | `work_room.rs` `work-room-last.jsonl` | 패턴 복제(선택) — 마지막 실행 로그 |

**신규(Rust ~250–350줄)**: `run_preview.rs`
- 타입 감지(`detect_run_recipe`): `package.json` 파싱 → (실행 명령, 미리보기 방식)
- 장기 러너(`run_start`/`run_stop`/`run_status`): 자동 install → 실행, 트리 kill, 동시 1개
- 포트 감지: 출력 라인에서 `localhost:PORT` → `run-preview-ready` 이벤트

**신규(프런트)**: `RunPanel.tsx` + webview 미리보기 배선

## 4. 타입 감지 + 실행 레시피

`package.json`만으로 판별(순수 함수, 테스트 용이). **표는 우선순위 순** — 위에서부터 처음 맞는 행을 택한다(electron 의존성이 있으면 `scripts.dev` 가 있어도 electron 으로 판정):

| 신호(deps/scripts) | 타입 | 실행 명령 | 미리보기 |
|---|---|---|---|
| `electron` in deps | electron | `npm start` (없으면 `npx electron .`) | 외부 OS 창(프로세스 자체) |
| `vite` in deps | web | `npm run dev` | webview, 포트 감지 |
| `next` in deps | web | `npm run dev` | webview(:3000) |
| `react-scripts` | web | `npm start` | webview(:3000) |
| `scripts.dev` 존재 | web(기본) | `npm run dev` | webview, 포트 감지 |
| `scripts.start` 만 | unknown | `npm start` | 로그만(포트 감지되면 webview) |
| 감지 실패 | — | 실행 버튼 비활성 + "실행 방법을 못 찾았어요" 안내 | — |

실행 명령은 **고정 셋**만 — 러너가 임의 명령 문자열을 받지 않는다(사용자·에이전트가 명령을 주입할 표면이 없음). 이게 작업방 화이트리스트보다 강한 안전 모델이다.

## 5. 수명주기 — 설치 → 실행 → 미리보기

```
[▶ 실행해보기]
  → node_modules 없으면: npm install (스트리밍 진행 "준비 중…", 트리 kill 가능)
  → 실행 명령 spawn (장기 프로세스, 출력 스트리밍)
  → 웹: 출력에서 localhost:PORT 감지 → 앱 내 webview 로드 ("미리보기" 패널)
     electron: 자체 OS 창이 뜸 → VibeLign 은 "앱 창이 열렸어요" + 로그
  → [■ 중지] 또는 앱 종료 시 트리 kill (고아 프로세스 0)
```

- **동시 1개** — 포트 충돌·자원 경쟁 방지. 작업방과도 동시 1개(둘 다 같은 워킹트리)
- **자동 install 은 1회성 판단** — node_modules 존재 시 건너뜀(매번 install 금지)
- **webview**: Tauri v2 `WebviewWindow`(별도 창) — 메인 창 분할보다 단순하고, 사용자가 미리보기를 따로 옮기거나 닫기 쉬움. 메인 앱과 생명주기 분리

## 6. 실행 실패 → 작업방 연계

- **시작 실패**(exit≠0 빠르게: 포트 점유·문법 에러로 dev 서버가 못 뜸) → 출력을 모아 작업방 지시문으로 넘기는 **"이 실행 에러 고쳐줘 →"** 버튼. 작업방이 그 에러 + 기존 기획안으로 재작업
- **런타임 에러**(서버는 살아있고 화면에 에러: vite 오버레이 등) → MVP 는 미리보기에 그대로 노출(사용자가 보고 판단). 자동 수집은 후속
- 실행 전 체크포인트는 불필요 — 실행은 코드를 바꾸지 않는다(읽기 전용 검증). install 은 node_modules(guard 이미 무시)·package-lock 을 생성/갱신할 수 있으나 이는 의존성 산출물이지 코드 로직 변경이 아니라 위험도가 낮다(guard 가 변경으로 잡아도 LOW). 실행은 5️⃣ 검증 후 단계라 guard 를 재실행하지 않는다

## 7. UI / 위치

- **진입점**: ① 작업방 결과 화면(guard pass 후) "▶ 실행해보기" ② 개발 단계 — 코드탐색/작업방과 같은 줄
- **RunPanel**: 타입 감지 결과("웹앱으로 감지됐어요") → [▶ 실행] → 설치/실행 로그(작업방 출력 블록 재사용) → 웹이면 [미리보기 열기] webview, 실행 중 [■ 중지]
- **가이드 스트립**: 실행 중 "5️⃣ 작동 확인 중 — 미리보기에서 직접 써보세요"

## 8. 정체성 가드레일

VibeLign 은 안전 바이브코딩 도구지 **배포 플랫폼이 아니다**. "실행"(개발 루프 내 작동 검증)은 정체성에 맞지만 "빌드/배포/호스팅"은 밖이다. MVP 를 실행으로 잠그는 이유: 타입별 빌드(코드사이닝·크로스플랫폼·정적 호스팅)를 떠안으면 scope 가 폭발하고, 빌드 실패가 초보에게 더 큰 좌절이 된다. 빌드는 "완성 후 공유" 수요가 측정되면 별도 트랙(흔한 타입부터: 웹 정적 → Electron).

## 9. 플랫폼 엣지케이스 — Windows 중심 (사용자 요청)

작업방 §10 의 전투 흔적을 기반으로, 실행 러너 고유의 Windows 위험을 짚는다. **P0 = 러너 설계에 반드시 반영.**

| P | 케이스 | 내용 · 대응 |
|---|---|---|
| P0 | **장기 프로세스 트리 kill (Win)** | dev 서버는 npm.cmd → node 손자를 만든다. plain kill 은 손자 생존(포트 점유 지속 → 재실행 시 충돌). 대응: `watch.rs kill_watch_child` 재사용 — `taskkill /PID /T /F`. 중지·앱종료·재실행 전 모두 트리 kill |
| P0 | **npm/node/electron 경로 해석 (Win)** | Windows 는 `npm.cmd`·`node.exe`·`electron.cmd`. 무확장 실행 불가. 대응: `find_executable`(작업방 검증済 .cmd/.exe 순서 해석) 재사용. PATH 는 `augmented_vib_path` |
| P0 | **콘솔 플래시 (Win)** | 장기 프로세스마다 cmd 창이 깜빡이면 안 됨. 대응: `CREATE_NO_WINDOW`(0x0800_0000) creation_flags — watch/work_room 동형 |
| P1 | **포트 감지 정규식 — OS 무관** | dev 서버 출력의 `http://localhost:PORT`·`127.0.0.1:PORT` 를 잡는다. vite/next/CRA 출력 형식이 달라 다중 패턴. ANSI 색코드 섞임 대비 `NO_COLOR=1`·`FORCE_COLOR=0` 강제(Win cp949 깨짐도 함께 차단, PYTHONUTF8 패턴 동형) |
| P1 | **nvm-windows / node 미설치** | Windows nvm 은 경로 체계가 다름(`%APPDATA%\nvm`). node 미탐지 시 "Node.js 가 필요해요" 안내 + 온보딩 연계(기존 도구 설치 도움 재사용) |
| P1 | **방화벽 첫 실행 팝업 (Win)** | dev 서버가 포트를 열면 Windows Defender 방화벽이 허용 팝업을 띄움 — 사용자 동작 필요. UI 에 "방화벽 허용을 물으면 '허용'을 눌러주세요" 사전 안내 |
| P1 | **install 시간·네트워크** | npm install 은 수십 초~분, 네트워크 필요. 진행 스트리밍 + 취소 가능 + 오프라인/실패 시 명확한 안내(무한 스피너 금지) |
| P2 | **포트 점유** | 이전 실행 좀비가 포트를 쥐면 새 실행이 실패 → 트리 kill(P0)로 예방. 그래도 충돌 시 "포트 사용 중" 안내 |
| P2 | **Electron Windows 창** | electron.cmd → electron.exe 가 자체 창. CREATE_NO_WINDOW 는 콘솔만 숨기고 앱 창엔 영향 없음(확인 필요) |
| — | 기성 해결済 | 한글·공백 경로 cwd(`current_dir`), GUI 셸 환경 미상속(augmented PATH) |

## 10. 마일스톤 (1인 기준 1~1.5주 MVP)

1. **감지 + 러너** (2–3일): `detect_run_recipe`(순수, 테스트 우선) + `run_start/stop/status`(watch 패턴) + 자동 install + 트리 kill
2. **포트 감지 + webview** (2일): localhost 다중 패턴 감지 → `run-preview-ready` → Tauri WebviewWindow 미리보기
3. **UI + 가이드 연계** (2일): RunPanel + 작업방 결과 화면 "▶ 실행해보기" + 실패→작업방 "에러 고쳐줘" 버튼 + 5️⃣ 카피
4. **검증** (1–2일): Win/mac 패키징 실기기 — 웹(vite/next/CRA)·Electron 각 1개, 중지/앱종료/포트충돌/방화벽 시나리오
5. **후속(별도 트랙)**: 런타임 에러 자동 수집 · 빌드/내보내기(수요 측정 후) · 비-node 스택(python 등)

## 11. 미결 (구현 전 결정 필요)

- webview 미리보기를 Tauri 별도 창 vs 메인 창 우측 분할 — 설계는 별도 창(단순), 구현 시 UX 재평가
- 자동 install 의 패키지 매니저 — npm 고정 vs lock 파일 감지(pnpm/yarn) — MVP 는 npm, lock 감지는 후속
- 실행 명령 커스터마이즈 허용 여부 — MVP 는 감지된 고정 명령만(안전), 고급 사용자 커스텀은 후속
