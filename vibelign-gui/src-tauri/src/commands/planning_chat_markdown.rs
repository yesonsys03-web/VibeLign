// === ANCHOR: PLANNING_CHAT_MARKDOWN_START ===
use super::planning_chat_cards::{Card, CardState};
use super::planning_chat_contract::PlanningContract;
use super::planning_chat_readiness::{ReadinessReport, ReadinessStatus, RequirementReadiness, Verdict};
use super::planning_chat_store::StoredPlanningChatSession;
use super::planning_chat_types::PlanningChatMessage;

#[derive(Default)]
struct PlanningSections {
    features: Vec<String>,
    flows: Vec<String>,
    exclusions: Vec<String>,
    questions: Vec<String>,
}

pub(crate) fn synthesize_planning_markdown(
    session: &StoredPlanningChatSession,
    messages: &[PlanningChatMessage],
    cards: &[Card],
    contract: Option<&PlanningContract>,
) -> String {
    let title = title_from_idea(&session.idea);
    let sections = PlanningSections::from_messages(messages);
    let mut markdown = String::new();
    push_section(&mut markdown, &format!("# {title}"));
    push_section(&mut markdown, "## 한 줄 목표");
    push_section(&mut markdown, session.idea.trim());
    markdown.push_str(&readiness_header(session.readiness.as_ref()));
    markdown.push_str(&contract_section(contract));
    push_section(&mut markdown, "## 확정된 결정");
    push_confirmed_decisions(&mut markdown, cards);
    push_section(&mut markdown, "## 대상 사용자");
    push_section(
        &mut markdown,
        "- 기획방 대화에서 대상 사용자를 구체화합니다.",
    );
    push_section(&mut markdown, "## 핵심 문제");
    push_section(
        &mut markdown,
        "- 사용자가 처음 말한 목표와 이후 페르소나 검토를 기준으로 확정합니다.",
    );
    push_section(&mut markdown, "## 핵심 기능");
    push_bullets_or_default(
        &mut markdown,
        &sections.features,
        "- 기획방 대화에서 합의된 기능을 구현 전에 우선순위로 정리합니다.",
    );
    push_section(&mut markdown, "## 사용자 흐름");
    push_bullets_or_default(
        &mut markdown,
        &sections.flows,
        "- 대화에서 정리된 화면 흐름과 저장 흐름을 기준으로 작성합니다.",
    );
    push_section(&mut markdown, "## 기획방 대화 정리");
    append_conversation(&mut markdown, messages);
    push_section(&mut markdown, "## 제외할 것");
    push_bullets_or_default(
        &mut markdown,
        &sections.exclusions,
        "- 아직 명시적으로 결정되지 않았습니다.",
    );
    push_section(&mut markdown, "## 아직 결정이 필요한 질문");
    push_bullets_or_default(
        &mut markdown,
        &sections.questions,
        "- 첫 구현 범위와 우선순위를 확정해야 합니다.\n- 화면 진입 후 저장/공유 흐름을 확정해야 합니다.",
    );
    push_section(&mut markdown, "## 구현 전에 AI가 알아야 할 맥락");
    push_section(
        &mut markdown,
        &format!(
            "- 이 문서는 기획방 대화를 기반으로 결정적으로 생성되었습니다.\n- 원본 대화는 `.vibelign/planning/{}/messages.json` 에 저장됩니다.",
            session.session_id
        ),
    );
    markdown
}

impl PlanningSections {
    fn from_messages(messages: &[PlanningChatMessage]) -> Self {
        let mut sections = Self::default();
        for message in messages {
            if message.role == "user" || message.status != "ok" {
                continue;
            }
            sections.collect_message(&message.content);
        }
        sections
    }

    fn collect_message(&mut self, content: &str) {
        for line in content.lines() {
            let Some((label, value)) = labeled_value(line) else {
                continue;
            };
            if matches_label(label, &["핵심 기능", "기능", "features", "feature"]) {
                push_unique(&mut self.features, value);
            } else if matches_label(label, &["사용자 흐름", "흐름", "flow", "user flow"]) {
                push_unique(&mut self.flows, value);
            } else if matches_label(
                label,
                &["제외할 것", "제외", "하지 않을 것", "out of scope"],
            ) {
                push_unique(&mut self.exclusions, value);
            } else if matches_label(
                label,
                &["질문", "결정", "결정 필요", "확인 필요", "question"],
            ) {
                push_unique(&mut self.questions, value);
            }
        }
    }
}

fn labeled_value(line: &str) -> Option<(&str, String)> {
    let trimmed = line.trim().trim_start_matches(['-', '*']).trim();
    let (label, value) = trimmed
        .split_once(':')
        .or_else(|| trimmed.split_once('：'))?;
    let value = value.trim();
    if label.trim().is_empty() || value.is_empty() {
        return None;
    }
    Some((label.trim(), value.to_string()))
}

fn matches_label(label: &str, candidates: &[&str]) -> bool {
    let normalized = label.trim().to_lowercase();
    candidates.iter().any(|candidate| normalized == *candidate)
}

fn push_unique(items: &mut Vec<String>, value: String) {
    if !items.iter().any(|item| item == &value) {
        items.push(value);
    }
}

/// 사용자가 버튼으로 확정(Confirmed)한 카드를 '확정된 결정' 섹션 불릿으로 박는다.
/// 확정 카드가 없으면 그 사실을 솔직히 적는다.
fn push_confirmed_decisions(markdown: &mut String, cards: &[Card]) {
    let confirmed: Vec<&Card> = cards
        .iter()
        .filter(|card| card.state == CardState::Confirmed)
        .collect();
    if confirmed.is_empty() {
        push_section(markdown, "- 아직 버튼으로 확정한 결정이 없습니다.");
        return;
    }
    let bullets = confirmed
        .iter()
        .map(|card| {
            let title = card.title.trim();
            let summary = card.summary.trim();
            if summary.is_empty() {
                format!("- **{title}**")
            } else {
                format!("- **{title}** — {summary}")
            }
        })
        .collect::<Vec<_>>()
        .join("\n");
    push_section(markdown, &bullets);
}

fn push_bullets_or_default(markdown: &mut String, items: &[String], fallback: &str) {
    if items.is_empty() {
        push_section(markdown, fallback);
        return;
    }
    let bullets = items
        .iter()
        .map(|item| format!("- {}", item.trim()))
        .collect::<Vec<_>>()
        .join("\n");
    push_section(markdown, &bullets);
}

fn append_conversation(markdown: &mut String, messages: &[PlanningChatMessage]) {
    if messages.is_empty() {
        push_section(markdown, "- 아직 저장된 대화가 없습니다.");
        return;
    }
    for message in messages {
        let label = message_label(message);
        push_section(markdown, &format!("### {label}"));
        if message.status != "ok" {
            push_section(markdown, &format!("- 응답 상태: {}", message.status));
        }
        push_section(markdown, &quote_block(&message.content));
    }
}

fn title_from_idea(idea: &str) -> String {
    let trimmed = idea.trim();
    if trimmed.is_empty() {
        "기획안".to_string()
    } else {
        trimmed
            .lines()
            .next()
            .unwrap_or("기획안")
            .trim()
            .to_string()
    }
}

fn message_label(message: &PlanningChatMessage) -> String {
    if message.role == "user" {
        return "사용자".to_string();
    }
    match message.persona_id.as_deref() {
        Some("chloe") => "클로이의 정리".to_string(),
        Some("gio") => "지오의 검토".to_string(),
        Some("mina") => "미나의 탐색".to_string(),
        Some("deepseek") => "딥시기의 설명".to_string(),
        Some(persona_id) => format!("{persona_id}의 답변"),
        None => "AI 답변".to_string(),
    }
}

fn quote_block(content: &str) -> String {
    let trimmed = content.trim();
    if trimmed.is_empty() {
        return "> (내용 없음)".to_string();
    }
    trimmed
        .lines()
        .map(|line| {
            if line.trim().is_empty() {
                ">".to_string()
            } else {
                format!("> {}", line.trim_end())
            }
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn verdict_icon(verdict: Verdict) -> &'static str {
    match verdict {
        Verdict::Green => "🟢",
        Verdict::Red => "🔴",
        Verdict::Na => "⚪",
    }
}

fn requirement_red_notes(requirement: &RequirementReadiness) -> Vec<(&'static str, &str)> {
    let checks = &requirement.checks;
    [
        ("발동", &checks.trigger),
        ("데이터", &checks.data),
        ("판정", &checks.logic),
        ("수용", &checks.acceptance),
        ("엣지", &checks.edge),
        ("플랫폼", &checks.platform),
    ]
    .into_iter()
    .filter(|(_, check)| check.verdict == Verdict::Red)
    .map(|(label, check)| (label, check.note.as_str()))
    .collect()
}

/// report가 있으면 문서 맨 위에 박을 판정 헤더를 만든다. 없으면 빈 문자열.
pub(crate) fn readiness_header(report: Option<&ReadinessReport>) -> String {
    let Some(report) = report else {
        return String::new();
    };
    if matches!(report.status, ReadinessStatus::Unavailable) {
        return "## 구현 준비 상태: 확인 못 함 (활성 AI 없음)\n\n".to_string();
    }
    let mut green = 0usize;
    let mut red = 0usize;
    let mut core_red_lines = Vec::new();
    for requirement in &report.requirements {
        let reds = requirement_red_notes(requirement);
        if reds.is_empty() {
            green += 1;
        } else {
            red += 1;
        }
        if requirement.core {
            for (label, note) in reds {
                core_red_lines.push(format!("- 🔴 [핵심] {} {} — {}", requirement.title, label, note));
            }
        }
    }
    let mut header = format!(
        "## 구현 준비 상태: 🟢 {green} / 🔴 {red}\n> 이 기획안은 구현 도구가 그대로 읽는 지시서입니다. 🔴 항목은 명세에 없어 도구가 임의로 채웁니다.\n"
    );
    for line in &core_red_lines {
        header.push_str(line);
        header.push('\n');
    }
    header.push('\n');
    header.push_str("## 요구사항별 명세\n\n");
    for requirement in &report.requirements {
        let c = &requirement.checks;
        header.push_str(&format!(
            "### {}  (발동{} 데이터{} 판정{} 수용{} 엣지{} 플랫폼{})\n\n",
            requirement.title,
            verdict_icon(c.trigger.verdict),
            verdict_icon(c.data.verdict),
            verdict_icon(c.logic.verdict),
            verdict_icon(c.acceptance.verdict),
            verdict_icon(c.edge.verdict),
            verdict_icon(c.platform.verdict),
        ));
        if !requirement.summary.is_empty() {
            header.push_str(&format!("{}\n\n", requirement.summary));
        }
    }
    header
}

/// 작업 계약 섹션 — 읽기 전용 노출(spec §1 Q3). 실패 카피는 원인 중립(외부 리뷰 M1):
/// AI 미설정·CLI 실패·파싱 실패를 사용자에게 구분해 보일 수 없으므로 원인을 단정하지 않는다.
pub(crate) fn contract_section(contract: Option<&PlanningContract>) -> String {
    let Some(contract) = contract else {
        return "## 작업 계약: 이번 저장에서는 추출하지 못했어요\n\n".to_string();
    };
    let mut out = String::from(
        "## 작업 계약\n> 이 블록은 외부 AI 도구에게 주는 지시문에 그대로 들어갑니다.\n\n",
    );
    out.push_str(&format!("- 목표: {}\n", contract.goal));
    if contract.scope.is_empty() {
        out.push_str("- 손댈 범위: 추출하지 못함 — 작업 도구가 코드를 읽고 스스로 정합니다\n");
    } else {
        out.push_str("- 손댈 범위 후보:\n");
        for entry in &contract.scope {
            if entry.reason.is_empty() {
                out.push_str(&format!("  - `{}`\n", entry.path));
            } else {
                out.push_str(&format!("  - `{}` — {}\n", entry.path, entry.reason));
            }
        }
    }
    for exclusion in &contract.exclusions {
        out.push_str(&format!("- 건드리지 말 것: {exclusion}\n"));
    }
    for criteria in &contract.done_criteria {
        out.push_str(&format!("- 완료 기준: {criteria}\n"));
    }
    out.push('\n');
    out
}

fn push_section(markdown: &mut String, section: &str) {
    markdown.push_str(section);
    markdown.push_str("\n\n");
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::commands::planning_chat_contract::{PlanningContract, ScopeEntry, ScopeKind};
    use crate::commands::planning_chat_readiness::{
        ReadinessChecks, ReadinessCheck, ReadinessReport, ReadinessStatus, RequirementReadiness, Verdict,
    };

    fn sample_contract() -> PlanningContract {
        PlanningContract {
            version: 1,
            extracted_at: "1".to_string(),
            goal: "예약 화면을 만든다".to_string(),
            scope: vec![ScopeEntry {
                path: "src/pages/".to_string(),
                kind: ScopeKind::Dir,
                reason: "화면이 모인 곳".to_string(),
            }],
            exclusions: vec!["결제는 건드리지 않음".to_string()],
            done_criteria: vec!["예약 버튼이 동작한다".to_string()],
        }
    }

    #[test]
    fn contract_section_renders_all_fields() {
        let section = contract_section(Some(&sample_contract()));
        assert!(section.contains("## 작업 계약"));
        assert!(section.contains("목표: 예약 화면을 만든다"));
        assert!(section.contains("`src/pages/` — 화면이 모인 곳"));
        assert!(section.contains("건드리지 말 것: 결제는 건드리지 않음"));
        assert!(section.contains("완료 기준: 예약 버튼이 동작한다"));
    }

    #[test]
    fn contract_section_is_honest_when_missing_or_scopeless() {
        // 원인 중립 카피(외부 리뷰 M1) — "활성 AI 없음" 같은 원인 단정 금지.
        assert!(contract_section(None).contains("이번 저장에서는 추출하지 못했어요"));
        assert!(!contract_section(None).contains("활성 AI 없음"));
        let mut scopeless = sample_contract();
        scopeless.scope.clear();
        assert!(contract_section(Some(&scopeless)).contains("추출하지 못함"));
    }

    fn check(v: Verdict) -> ReadinessCheck {
        ReadinessCheck { verdict: v, note: String::new() }
    }

    fn judged_report() -> ReadinessReport {
        ReadinessReport {
            status: ReadinessStatus::Judged,
            requirements: vec![RequirementReadiness {
                title: "카드 발동".to_string(),
                summary: "결정마다 카드가 뜬다".to_string(),
                core: true,
                checks: ReadinessChecks {
                    trigger: ReadinessCheck { verdict: Verdict::Red, note: "감지 미정".to_string() },
                    data: check(Verdict::Red),
                    logic: check(Verdict::Green),
                    acceptance: check(Verdict::Green),
                    edge: check(Verdict::Green),
                    platform: check(Verdict::Na),
                },
            }],
        }
    }

    #[test]
    fn header_for_judged_report_shows_counts_and_core_gaps() {
        let header = readiness_header(Some(&judged_report()));
        assert!(header.contains("구현 준비 상태"));
        assert!(header.contains("🔴"));
        assert!(header.contains("카드 발동"));
        assert!(header.contains("감지 미정"));
    }

    #[test]
    fn header_for_unavailable_is_honest() {
        let header = readiness_header(Some(&ReadinessReport::unavailable()));
        assert!(header.contains("확인 못 함"));
        assert!(!header.contains("🟢"));
    }

    #[test]
    fn header_is_empty_when_no_report() {
        assert_eq!(readiness_header(None), "");
    }
}
// === ANCHOR: PLANNING_CHAT_MARKDOWN_END ===
