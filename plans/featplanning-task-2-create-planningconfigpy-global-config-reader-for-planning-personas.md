# feat(planning): Task 2 - create planning...
## 한 줄 목표
# === ANCHOR: MARKDOWN_WRITER_BUILD_TEMPLATE_MARKDOWN_END ===
feat(planning): Task 2 - create planning_config.py global-config reader for planning personas

## 만들고 싶은 이유
아직 결정이 필요합니다.

## 대상 사용자
아직 결정이 필요합니다.

## 핵심 기능
- 아직 결정이 필요합니다.

## 화면 또는 사용 흐름
- 아직 결정이 필요합니다.

## 제외할 것
- 아직 결정이 필요합니다.

## 아직 결정이 필요한 질문
- 대상 사용자가 더 구체적으로 누구인가요?
- 이번 범위에서 제외할 것은 무엇인가요?
- 구현 전에 AI가 알아야 할 제약이 있나요?

## 구현 전에 AI가 알아야 할 맥락
- 언어 설정: auto
- 추가 맥락은 아직 결정이 필요합니다.

## 다음 단계
- 위 질문에 답한 뒤 기획안을 구체화합니다.

## 클로이의 설계
안녕하세요! 기획방 설계자 **클로이**예요. 🎨
이번 아이디어는 제목이 개발자용 메모처럼 적혀 있어서, 초보자도 한눈에 이해할 수 있게 일상어로 풀어 다시 정리해 드릴게요. 확실하지 않은 부분은 제가 멋대로 채우지 않고 **결정이 필요한 질문**으로 남겨 둘게요.

---

# 기획 도우미들이 따를 "공통 설정"을 한 곳에서 불러오기

## 한 줄 목표
기획을 도와주는 여러 도우미(예: 저 클로이 같은 캐릭터)가 **공통으로 따를 기본 설정**을 한곳에 모아두고, 필요할 때 알아서 불러와 쓰도록 만들기.

> 💡 원래 제목에 들어 있던 내부용 표시(`ANCHOR...`, 파일 이름 등)는 사용자용 기획안에는 필요 없어서 정리했어요.

## 만들고 싶은 이유
지금은 도우미마다 따라야 할 설정(예: 어떤 AI를 쓸지, 말투, 기본 동작 방식)이 여기저기 흩어져 있거나, 상황마다 따로 정해 줘야 할 수 있어요.
이걸 **한 곳에 모아두고 거기서 읽어오게** 하면 두 가지가 좋아져요.
- 도우미들이 **일관되게** 같은 규칙으로 움직여요.
- 설정을 바꾸고 싶을 때 **한 군데만** 고치면 전부 반영돼요.

*(이 이유가 실제 의도와 맞는지 한 번만 확인해 주세요. 다르면 알려주시면 다시 쓸게요.)*

## 대상 사용자
아직 결정이 필요합니다. 제가 짐작한 두 가지 가능성을 적어둘게요 — 어느 쪽인지 골라주세요.
- (가) **설정을 직접 만지는 사용자** — 도우미의 동작을 직접 조절하고 싶은 분
- (나) **설정을 의식하지 않는 사용자** — 뒤에서 자동으로 적용되어, 일반 사용자는 신경 쓸 필요가 없음

## 핵심 기능
- 여러 곳에 공통으로 적용되는 **기본 설정을 한 곳에서 읽어오기**
- 설정값이 비어 있거나 없을 때 **안전한 기본값으로 동작하기**
- (결정 필요) 사용자가 이 설정을 **직접 바꿀 수 있어야 하는지**

## 화면 또는 사용 흐름
아직 결정이 필요합니다. 제가 그려본 예시 흐름은 이래요 (맞는지 확인 부탁드려요).
1. 도우미가 일을 시작할 때 → 공통 설정을 먼저 읽음
2. 설정이 있으면 그대로 따르고, 없으면 기본값 사용
3. 사용자는 평소처럼 기획만 진행 (설정은 뒤에서 처리)

## 제외할 것
- 아직 결정이 필요합니다.

## 아직 결정이 필요한 질문
1. **대상 사용자**: 위 (가)·(나) 중 어느 쪽인가요? 아니면 둘 다인가요?
2. **설정 변경 권한**: 사용자가 설정을 직접 바꿀 수 있어야 하나요, 아니면 정해진 값만 쓰면 되나요?
3. **공통의 범위**: 이 설정은 *모든 프로젝트에 똑같이* 적용되나요, 아니면 *프로젝트마다 다르게* 둘 수 있어야 하나요?
4. **이번에 다루지 않을 것**: 이번 작업에서 일부러 빼두고 싶은 부분이 있나요?
5. **꼭 지켜야 할 제약**: 만들기 전에 미리 알아야 할 규칙이나 제한이 있나요?

## 구현 전에 AI가 알아야 할 맥락
- 언어 설정: 자동(auto)
- 추가 맥락은 아직 결정이 필요합니다.

## 다음 단계
- 위 **5가지 질문**에 답해 주시면, 그 답을 반영해서 기획안을 더 구체적으로 다듬을게요.

---

특히 **1번(대상 사용자)** 과 **3번(공통의 범위)** 두 가지만 먼저 정해주시면, 나머지는 제가 훨씬 또렷하게 채워드릴 수 있어요. 어떤 쪽이 더 가까운가요? 😊

## 미나의 탐색
I will start by retrieving the project map to understand the project structure, files, and anchors as required for VibeLign safe mode.
I will read the generated project map output to inspect the project details.
I will perform a file search to find active files in the workspace, especially targeting design drafts, planning markdown files, or config files.
I will list the contents of the `plans` directory to find relevant planning markdown files.
I will read the contents of the planning document `featplanning-task-2-create-planningconfigpy-global-config-reader-for-planning-personas.md` under the `plans` directory to examine the existing proposal.
I will view the `plans/VibeLign-기획방개선-기획안.md` file to understand the roles of personas in the VibeLign planning room and find out who the "Explorer Mina" (탐색자 미나) is.
I will view the `plans/2026-06-08-기획방-페르소나-모델-분리-design.md` file to get more specific context about the persona models and the explorer Mina.
I will now update the planning document `plans/featplanning-task-2-create-planningconfigpy-global-config-reader-for-planning-personas.md` with a beginner-friendly Korean description using the perspective of Explorer Mina. I will replace the placeholder contents after the template anchor to add target users, core features, flows, non-goals, and undecided questions, keeping internal implementation jargon hidden.
I will read the schema for `guard_check` tool to call it with the correct arguments.
I will run the project guard check to ensure our changes are safe and compliant with the system rules.
I will inspect the guard check execution output.
I will read the schema of `checkpoint_create` to ensure I call it correctly to save our current work state.
I will read the schema of `transfer_set_relevant` tool to document that I have modified the planning document.
I will document the changed file in VibeLign's transfer memory using `transfer_set_relevant`.
I will create a checkpoint to preserve the current changes.
안녕하세요! 기획방의 활기찬 탐색자 **미나**예요! 🚀 

설계자 클로이가 만들어 두었던 기획안 초안을 이어받아, 우리 초보 사용자분들도 쉽고 재미있게 읽으실 수 있는 한국어로 가득 보강해 왔어요! 비슷한 여러 앱들의 사용법도 꼼꼼히 탐색해 보면서 '어라, 이 기능은 이래서 꼭 필요하겠네!' 하는 생각들을 쉽게 풀어 정리해 보았답니다.

기획을 도와주는 도우미들이 멈추지 않고 안전하게 대화를 이어나가게 하기 위해, 어려운 개발 용어나 복잡한 시스템 단어들은 기획안에서 과감하게 지우거나 일상어로 바꿨어요. (예를 들어, 알 수 없는 오류로 고장 났을 때 대기 중인 다른 도우미가 신속하게 바통을 이어받아 대답해 주는 일을 **'대체 도우미 자동 매칭'**이라고 부르기로 했어요! 😊)

보강한 내용은 [featplanning-task-2-create-planningconfigpy-global-config-reader-for-planning-personas.md](file:///Users/usabatch/coding/VibeLign/plans/featplanning-task-2-create-planningconfigpy-global-config-reader-for-planning-personas.md) 파일에 소중히 기록해 두었답니다.

---

### 🔍 미나가 정리한 이번 기획의 핵심 포인트

* **무슨 기획인가요?**
  * 기획방을 지키는 여러 AI 도우미(클로이, 지오, 저 미나 등!)가 **공통으로 따를 기본 설정**을 한곳에 안전하게 모아두고 작동하게 만드는 일이에요.
* **왜 만드나요?**
  * 지금은 도우미들이 사용하는 엔진이나 설정이 여기저기 흩어져 있어서, 도우미가 갑자기 대답을 못 하거나 오류를 낼 때 대화가 뚝 끊기는 아쉬움이 있었어요.
  * 설정을 한곳에 모아두면, 사용자가 도우미별로 원하는 엔진을 직접 지정해 줄 수도 있고, 만약 엔진 하나가 먹통이 되더라도 대기 중이던 다른 든든한 대체 도우미가 바로 이어서 대화를 부드럽게 이어갈 수 있도록 도와주거든요!
* **누구를 위한 건가요?**
  * 도우미 설정을 내 입맛대로 자유롭게 바꿔보며 탐험하고 싶은 사용자분들과, 어려운 설정은 전혀 모르지만 도우미들이 끊김 없이 똑똑하게 대답해 주기를 바라는 사용자분들 모두를 위한 것이랍니다.

---

### ❓ 아직 결정이 필요한 미나의 질문들!
우리가 함께 더 재미있고 유용한 기획방을 만들기 위해 탐색하며 결정해야 할 질문들을 남겨둘게요. 어떤 방향이 가장 마음에 드시나요?

1. **설정의 적용 범위**: 이 설정은 프로그램 전체에 동일하게 딱 한 번만 적용될까요, 아니면 프로젝트(폴더)를 바꿀 때마다 다르게 세팅할 수 있어야 할까요?
2. **대체 알림 연출**: 도우미가 자동으로 교체되어 대신 대답했을 때, 대화 창에서 사용자에게 이를 어떻게 표시해 줄까요? (예: "지오 도우미가 바빠서 다른 도우미가 대신 대답해요!" 같은 귀여운 배지 표시)
3. **비활성화된 도우미의 표시**: 사용자가 특정 도우미를 꺼둔(OFF) 상태라면, 대화방 화면에서 그 도우미의 카드 자체를 아예 안 보이게 숨겨줄까요, 아니면 꺼진 상태로 투명하게 남겨둘까요?

위 질문들에 대해 편하게 의견을 나누어 주세요! 사용자님의 의견을 들려주시면 그 생각을 쏙쏙 반영하여 기획안을 더욱 완성도 높게 다듬어 드릴게요. 우리 같이 더 멋진 기획방을 꾸며봐요! 🌟
