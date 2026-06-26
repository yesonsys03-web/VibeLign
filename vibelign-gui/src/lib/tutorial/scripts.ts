// ANCHOR: TUTORIAL_SCRIPTS_START
import type { Tutorial, TutorialId } from "./types";

const TODO: Tutorial = {
  id: "todo",
  title: "나만의 할 일 목록 앱 만들기",
  emoji: "✅",
  goal: "할 일을 적고, 다 하면 체크해서 지우는 나만의 웹앱",
  steps: [
    {
      id: "todo-1-copy",
      kind: "copy",
      say: "AI에게 이렇게 말해볼게요. 아래 문장을 복사하세요.",
      why: "기획방은 AI에게 '무엇을 만들지' 설명하는 곳이에요.",
      goPage: "planning",
      done: "copy",
      copyText:
        "할 일을 입력해 추가하고, 목록으로 보여주고, 체크하면 지워지는 간단한 '할 일 목록' 웹앱을 HTML 파일 하나로 만들어줘.",
    },
    {
      id: "todo-2-send",
      kind: "pasteSend",
      say: "기획방 입력칸에 붙여넣고 보내보세요.",
      why: "AI가 무엇을 만들지 계획을 먼저 세워줘요.",
      target: "planning-send",
      goPage: "planning",
      done: "planResponded",
    },
    {
      id: "todo-3-checkpoint",
      kind: "click",
      say: "작업을 시키기 전에, 먼저 현재 상태를 저장해요. [체크포인트 저장]을 누르세요.",
      why: "AI에게 시키기 전에 저장해두면, 마음에 안 들 때 한 번에 되돌릴 수 있어요. VibeLign의 핵심 안전장치예요.",
      target: "checkpoint-save",
      goPage: "backups",
      done: "checkpoint",
    },
    {
      id: "todo-4-work",
      kind: "click",
      say: "이제 [AI에게 작업 시키기]를 누르세요.",
      why: "AI가 방금 세운 계획대로 실제 코드를 만들어요.",
      target: "work-run-ai",
      goPage: "work",
      done: "changedFiles",
    },
    {
      id: "todo-5-guard",
      kind: "click",
      say: "AI가 만든 게 안전한지 검사해요. [상태 확인]을 누르세요.",
      why: "VibeLign이 AI가 건드리면 안 되는 곳을 안 건드렸는지 확인해줘요.",
      target: "home-guard-check",
      goPage: "home",
      done: "guardChecked",
    },
    {
      id: "todo-6-run",
      kind: "click",
      say: "이제 진짜 실행해볼 차례! [실행해보기]를 누르세요.",
      why: "방금 만든 앱이 실제로 돌아가는지 직접 봐요.",
      target: "run-app",
      goPage: "run",
      done: "runVerified",
    },
    {
      id: "todo-7-try",
      kind: "confirm",
      say: "할 일을 직접 하나 추가해보세요. 목록에 떴나요?",
      why: "이게 바로 당신이 만든 앱이에요. 직접 써보는 게 완성의 증거예요.",
      target: "run-app",
      goPage: "run",
      done: "manual",
    },
    {
      id: "todo-8-save",
      kind: "confirm",
      say: "마음에 들면 저장! [체크포인트 저장]을 다시 누르세요.",
      why: "좋은 상태를 저장해두면 다음에 또 여기서 시작할 수 있어요.",
      target: "checkpoint-save",
      goPage: "backups",
      done: "manual",
    },
    {
      id: "todo-9-undo",
      kind: "confirm",
      say: "혹시 잘못 만들어도 괜찮아요. 여기 [되돌리기]를 누르면 저장 시점으로 언제든 돌아가요. 확인했으면 [알겠어요].",
      why: "되돌릴 수 있다는 안심 — 이게 VibeLign으로 겁 없이 AI 코딩하는 비결이에요.",
      target: "checkpoint-restore",
      goPage: "backups",
      done: "manual",
    },
  ],
};

const GUESTBOOK: Tutorial = {
  id: "guestbook",
  title: "방명록 웹페이지 만들기",
  emoji: "📖",
  goal: "누가 와서 이름과 한마디를 남길 수 있는 나만의 방명록 페이지",
  steps: [
    { id: "gb-1-copy", kind: "copy", say: "AI에게 이렇게 말해볼게요. 아래 문장을 복사하세요.", why: "기획방은 AI에게 무엇을 만들지 설명하는 곳이에요.", goPage: "planning", done: "copy",
      copyText: "이름과 한마디를 입력해 남기면 아래 목록에 계속 쌓이는 간단한 '방명록' 웹페이지를 HTML 파일 하나로 만들어줘." },
    { id: "gb-2-send", kind: "pasteSend", say: "기획방 입력칸에 붙여넣고 보내보세요.", why: "AI가 무엇을 만들지 계획을 세워줘요.", target: "planning-send", goPage: "planning", done: "planResponded" },
    { id: "gb-3-checkpoint", kind: "click", say: "작업 전에 먼저 저장! [체크포인트 저장]을 누르세요.", why: "시키기 전에 저장해두면 언제든 되돌릴 수 있어요.", target: "checkpoint-save", goPage: "backups", done: "checkpoint" },
    { id: "gb-4-work", kind: "click", say: "[AI에게 작업 시키기]를 누르세요.", why: "AI가 계획대로 방명록을 만들어요.", target: "work-run-ai", goPage: "work", done: "changedFiles" },
    { id: "gb-5-guard", kind: "click", say: "안전한지 검사해요. [상태 확인]을 누르세요.", why: "건드리면 안 되는 곳을 안 건드렸는지 확인해줘요.", target: "home-guard-check", goPage: "home", done: "guardChecked" },
    { id: "gb-6-run", kind: "click", say: "[실행해보기]를 눌러 직접 봐요.", why: "방명록이 실제로 뜨는지 확인해요.", target: "run-app", goPage: "run", done: "runVerified" },
    { id: "gb-7-try", kind: "confirm", say: "이름과 한마디를 직접 남겨보세요. 목록에 떴나요?", why: "직접 써보는 게 완성의 증거예요.", target: "run-app", goPage: "run", done: "manual" },
    { id: "gb-8-save", kind: "confirm", say: "마음에 들면 [체크포인트 저장]을 다시 누르세요.", why: "좋은 상태를 저장해두면 다음에 또 시작할 수 있어요.", target: "checkpoint-save", goPage: "backups", done: "manual" },
    { id: "gb-9-undo", kind: "confirm", say: "잘못돼도 괜찮아요. [되돌리기]로 저장 시점으로 돌아갈 수 있어요. [알겠어요].", why: "되돌릴 수 있다는 안심이 겁 없이 만드는 비결이에요.", target: "checkpoint-restore", goPage: "backups", done: "manual" },
  ],
};

const QUIZ: Tutorial = {
  id: "quiz",
  title: "퀴즈 게임 만들기",
  emoji: "🎯",
  goal: "문제를 풀면 점수가 올라가는 나만의 퀴즈 게임",
  steps: [
    { id: "qz-1-copy", kind: "copy", say: "AI에게 이렇게 말해볼게요. 아래 문장을 복사하세요.", why: "기획방은 AI에게 무엇을 만들지 설명하는 곳이에요.", goPage: "planning", done: "copy",
      copyText: "객관식 문제 3개를 풀면 맞힌 개수만큼 점수가 나오는 간단한 '퀴즈 게임'을 HTML 파일 하나로 만들어줘." },
    { id: "qz-2-send", kind: "pasteSend", say: "기획방 입력칸에 붙여넣고 보내보세요.", why: "AI가 무엇을 만들지 계획을 세워줘요.", target: "planning-send", goPage: "planning", done: "planResponded" },
    { id: "qz-3-checkpoint", kind: "click", say: "작업 전에 먼저 저장! [체크포인트 저장]을 누르세요.", why: "시키기 전에 저장해두면 언제든 되돌릴 수 있어요.", target: "checkpoint-save", goPage: "backups", done: "checkpoint" },
    { id: "qz-4-work", kind: "click", say: "[AI에게 작업 시키기]를 누르세요.", why: "AI가 계획대로 퀴즈를 만들어요.", target: "work-run-ai", goPage: "work", done: "changedFiles" },
    { id: "qz-5-guard", kind: "click", say: "안전한지 검사해요. [상태 확인]을 누르세요.", why: "건드리면 안 되는 곳을 안 건드렸는지 확인해줘요.", target: "home-guard-check", goPage: "home", done: "guardChecked" },
    { id: "qz-6-run", kind: "click", say: "[실행해보기]를 눌러 직접 봐요.", why: "퀴즈가 실제로 도는지 확인해요.", target: "run-app", goPage: "run", done: "runVerified" },
    { id: "qz-7-try", kind: "confirm", say: "직접 퀴즈를 풀어보세요. 점수가 나왔나요?", why: "직접 해보는 게 완성의 증거예요.", target: "run-app", goPage: "run", done: "manual" },
    { id: "qz-8-save", kind: "confirm", say: "마음에 들면 [체크포인트 저장]을 다시 누르세요.", why: "좋은 상태를 저장해두면 다음에 또 시작할 수 있어요.", target: "checkpoint-save", goPage: "backups", done: "manual" },
    { id: "qz-9-undo", kind: "confirm", say: "잘못돼도 괜찮아요. [되돌리기]로 저장 시점으로 돌아갈 수 있어요. [알겠어요].", why: "되돌릴 수 있다는 안심이 겁 없이 만드는 비결이에요.", target: "checkpoint-restore", goPage: "backups", done: "manual" },
  ],
};

export const TUTORIALS: Tutorial[] = [TODO, GUESTBOOK, QUIZ];

export function getTutorial(id: TutorialId): Tutorial | undefined {
  return TUTORIALS.find((t) => t.id === id);
}
// ANCHOR: TUTORIAL_SCRIPTS_END
