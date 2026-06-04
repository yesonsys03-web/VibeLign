export type SafetyAutomationCopy = {
  readonly title: string;
  readonly detail: string;
};

type SafetyAutomationNoticeProps = {
  readonly rawError: string | null;
  readonly onRetry: () => void;
};

const WATCH_FAILURE_COPY = {
  title: "자동 안전장치 일부가 꺼져 있어요",
  detail: "파일 변경 감시를 시작하지 못했어요. 프로젝트 상태 확인은 계속 사용할 수 있어요.",
} as const satisfies SafetyAutomationCopy;

const WATCH_ERROR_PATTERNS = [
  {
    pattern: /permission denied|access denied|권한/i,
    copy: {
      title: "폴더 권한을 확인해야 해요",
      detail: "파일 변경 감시에 필요한 권한이 부족해요. 폴더 접근 권한을 확인한 뒤 다시 시도하세요.",
    },
  },
  {
    pattern: /command not found|not found|ENOENT/i,
    copy: {
      title: "감시 도구를 찾지 못했어요",
      detail: "파일 변경 감시를 시작하는 도구가 준비되지 않았어요. VibeLign 시작 설정을 다시 확인하세요.",
    },
  },
  {
    pattern: /timeout|timed out|시간 초과/i,
    copy: {
      title: "감시 시작이 오래 걸리고 있어요",
      detail: "프로젝트가 크거나 시스템이 바빠서 자동 감시가 제때 시작되지 않았어요. 잠시 후 다시 시도하세요.",
    },
  },
] as const satisfies ReadonlyArray<{
  readonly pattern: RegExp;
  readonly copy: SafetyAutomationCopy;
}>;

export function humanizeAutomationError(rawError: string | null): SafetyAutomationCopy | null {
  const normalizedError = rawError?.trim();
  if (!normalizedError) return null;
  const matchedPattern = WATCH_ERROR_PATTERNS.find((entry) => entry.pattern.test(normalizedError));
  if (matchedPattern) return matchedPattern.copy;
  return WATCH_FAILURE_COPY;
}

export function SafetyAutomationNotice({ rawError, onRetry }: SafetyAutomationNoticeProps) {
  const copy = humanizeAutomationError(rawError);
  if (!copy) return null;

  return (
    <section
      style={{
        background: "#FFF2C2",
        border: "2px solid #1A1A1A",
        padding: 14,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 900, lineHeight: 1.35 }}>{copy.title}</div>
        <div style={{ marginTop: 4, fontSize: 12, color: "#555", lineHeight: 1.55 }}>{copy.detail}</div>
      </div>
      <button className="btn btn-black btn-sm" type="button" onClick={onRetry} style={{ flexShrink: 0, fontSize: 11 }}>
        다시 시도
      </button>
    </section>
  );
}
