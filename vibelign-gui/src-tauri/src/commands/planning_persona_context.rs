// === ANCHOR: PLANNING_PERSONA_CONTEXT_START ===
use super::planning_persona::PlanningChatLine;

/// 페르소나 프롬프트에 넣을 대화 맥락의 최근 줄 상한.
/// 한 턴에 페르소나가 여럿 답하므로(최대 4) 약 최근 3~4턴에 해당한다.
pub(crate) const RECENT_CONTEXT_LINES: usize = 16;

/// 대화가 길어져도 매 호출마다 전체를 재전송하지 않도록 최근 N줄로 창을 자른다.
/// 단, 첫 사용자 메시지(원래 아이디어)는 의도 앵커로 항상 앞에 포함한다.
/// 잘라낼 게 없으면(전체가 창 안) 원본을 그대로 참조로 돌려준다.
pub(crate) fn recent_lines<'a, 'b>(
    lines: &'b [PlanningChatLine<'a>],
    max_recent: usize,
) -> Vec<&'b PlanningChatLine<'a>> {
    if lines.len() <= max_recent {
        return lines.iter().collect();
    }
    let tail_start = lines.len() - max_recent;
    let mut out: Vec<&PlanningChatLine<'a>> = Vec::new();
    // 첫 사용자 메시지가 창 밖(앞쪽)이면 맥락 앵커로 끌어와 맨 앞에 둔다.
    if let Some(idx) = lines.iter().position(|line| line.role == "user") {
        if idx < tail_start {
            out.push(&lines[idx]);
        }
    }
    out.extend(lines[tail_start..].iter());
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn line(role: &'static str, content: &'static str) -> PlanningChatLine<'static> {
        PlanningChatLine { role, persona_id: None, content }
    }

    #[test]
    fn returns_all_when_within_window() {
        let lines = vec![line("user", "a"), line("assistant", "b")];
        let kept = recent_lines(&lines, 16);
        assert_eq!(kept.len(), 2);
    }

    #[test]
    fn trims_to_tail_but_keeps_first_user_idea() {
        let mut lines = vec![line("user", "원래 아이디어")];
        for _ in 0..30 {
            lines.push(line("assistant", "잡담"));
        }
        let kept = recent_lines(&lines, 5);
        // 첫 사용자 메시지 + 최근 5줄 = 6
        assert_eq!(kept.len(), 6);
        assert_eq!(kept[0].content, "원래 아이디어");
        assert_eq!(kept[0].role, "user");
    }

    #[test]
    fn does_not_duplicate_first_user_when_inside_window() {
        // 첫 사용자 메시지가 이미 tail 창 안이면 중복으로 끌어오지 않는다.
        let lines = vec![
            line("assistant", "0"),
            line("assistant", "1"),
            line("user", "아이디어"),
            line("assistant", "3"),
        ];
        let kept = recent_lines(&lines, 3); // tail_start = 1, user idx = 2 (창 안)
        assert_eq!(kept.len(), 3);
        assert_eq!(kept[0].content, "1");
    }
}
// === ANCHOR: PLANNING_PERSONA_CONTEXT_END ===
