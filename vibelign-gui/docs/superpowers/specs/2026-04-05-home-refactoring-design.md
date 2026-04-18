# Home.tsx 리팩토링 설계

**날짜:** 2026-04-05  
**범위:** `vibelign-gui/src/pages/Home.tsx` 분리  
**목표:** 1954줄 단일 파일 → 레이아웃 셸 + 카드 컴포넌트 13개

---

## 배경

`Home.tsx`가 1954줄로 비대해져 유지보수가 어렵고, 향후 카드 드래그앤드롭 기능 추가를 위한 사전 작업으로 리팩토링이 필요하다.

---

## 파일 구조

```
src/
  pages/
    Home.tsx                  ← 레이아웃·라우팅·뷰 전환만 (~200줄)
  components/
    cards/
      backup/
        CheckpointCard.tsx    ← checkpoint (입력창 포함)
        HistoryCard.tsx       ← history
        UndoCard.tsx          ← undo
      analysis/
        GuardCard.tsx         ← guard
        CodemapCard.tsx       ← scan + watch 통합
        AnchorCard.tsx        ← anchor
      ai/
        PatchCard.tsx         ← patch
        AskCard.tsx           ← ask
        ExplainCard.tsx       ← explain
      transfer/
        TransferCard.tsx      ← transfer
        ExportCard.tsx        ← export
      security/
        SecretsCard.tsx       ← secrets
        ProtectCard.tsx       ← protect
```

---

## 카드 인터페이스

모든 카드 공통 props:

```typescript
interface CardProps {
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
}
```

추가 props가 필요한 카드:
- **CheckpointCard**: `onNavigate: (page: "checkpoints") => void`
- **CodemapCard**: `watchOn: boolean`, `setWatchOn: (v: boolean) => void`, `mapMode: "manual" | "auto"`, `setMapMode: (v: "manual" | "auto") => void`
  - watch/mapMode 상태는 앱 레벨(Home.tsx)에서 유지 (페이지 전환 시 상태 보존 필요)
- **GuardCard**: `onGuardResult: (result: GuardResult) => void`
  - Guard 결과 모달은 Home.tsx에 fixed overlay로 유지. GuardCard는 실행 완료 후 결과를 콜백으로 전달만 함

---

## 상태 관리 원칙

- 각 카드가 자신의 `loading`, `output`, `error` 상태를 직접 관리
- Home.tsx는 카드 상태를 들고 있지 않음
- 예외: CodemapCard의 `watchOn`, `mapMode`는 Home.tsx에서 관리 후 props로 전달

---

## 추출 원칙

1. **로직 이동 금지** — 구조 분리만, 기능 변경 없음
2. **카드 하나씩 순차 추출** — 추출 후 동작 확인, 다음 카드
3. **각 카드 파일에 ANCHOR 포함** — `ANCHOR: CARDNAME_START / CARDNAME_END`
4. **Home.tsx ANCHOR 유지** — `HOME_START / HOME_END`

---

## 추출 순서

상태가 단순한 카드부터 시작해 위험을 최소화한다.

| 순서 | 카드 | 이유 |
|------|------|------|
| 1 | UndoCard | 상태 단순, 버튼 하나 |
| 2 | AnchorCard | 상태 단순 |
| 3 | ExplainCard | 상태 단순 |
| 4 | AskCard | 상태 단순 |
| 5 | ExportCard | 상태 단순 |
| 6 | ProtectCard | 상태 단순 |
| 7 | SecretsCard | 상태 단순 |
| 8 | HistoryCard | 출력 블록 포함 |
| 9 | GuardCard | 출력 + 모달 연결 |
| 10 | PatchCard | AI 환경변수 필요 |
| 11 | TransferCard | 옵션 플래그 복수 |
| 12 | CheckpointCard | 입력창 + onNavigate |
| 13 | CodemapCard | watch 상태 복잡, 마지막 |

---

## 검증 계획

각 카드 추출 후 다음을 확인한다:
- 버튼 클릭 시 vib CLI 실행 정상 동작
- 로딩/완료/오류 상태 표시 정상
- 출력 결과 표시 정상
- 이전과 동일한 UI 렌더링

전체 추출 완료 후:
- 홈 화면 전체 카드 렌더링 확인
- 체크포인트 저장 → 목록 이동 플로우 확인
- CodemapCard watch 시작/중지 확인
- 앱 재시동 후 상태 초기화 정상 확인

---

## 이번 범위 제외

- `Doctor.tsx` 리팩토링 → 별도 작업
- 카드 드래그앤드롭 → 리팩토링 완료 후 별도 작업
