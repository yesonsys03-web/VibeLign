// === ANCHOR: PLANNING_CHAT_CARDS_START ===
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use super::planning_chat_types::PlanningChatMessage;
use super::planning_persona::run_active_ai;

#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "lowercase")]
pub(crate) enum CardState {
    Draft,
    Held,
    Confirmed,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub(crate) struct Card {
    pub(crate) id: String,
    pub(crate) title: String,
    pub(crate) summary: String,
    pub(crate) reason: String,
    pub(crate) state: CardState,
    pub(crate) created_at: String,
    pub(crate) updated_at: String,
}

#[derive(Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct CardsFile {
    cards: Vec<Card>,
}

fn cards_path(session_dir: &Path) -> PathBuf {
    session_dir.join("cards.json")
}

pub(crate) fn read_cards(session_dir: &Path) -> Vec<Card> {
    let Ok(text) = std::fs::read_to_string(cards_path(session_dir)) else {
        return Vec::new();
    };
    serde_json::from_str::<CardsFile>(&text)
        .map(|file| file.cards)
        .unwrap_or_default()
}

#[derive(Debug, PartialEq, Eq)]
pub(crate) enum CardOp {
    Add {
        title: String,
        summary: String,
        reason: String,
    },
    Confirm {
        id: String,
    },
    Reject {
        id: String,
    },
    Hold {
        id: String,
    },
}

pub(crate) fn write_cards(session_dir: &Path, cards: &[Card]) -> Result<(), String> {
    let file = CardsFile {
        cards: cards.to_vec(),
    };
    let text = serde_json::to_string_pretty(&file).map_err(|error| error.to_string())?;
    std::fs::write(cards_path(session_dir), text + "\n").map_err(|error| error.to_string())
}

fn first_json_object(text: &str) -> Option<&str> {
    let start = text.find('{')?;
    let end = text.rfind('}')?;
    if end > start {
        Some(&text[start..=end])
    } else {
        None
    }
}

fn op_string(value: &serde_json::Value, key: &str) -> String {
    value
        .get(key)
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim()
        .to_string()
}

pub(crate) fn parse_card_ops(text: &str) -> Vec<CardOp> {
    let Some(json) = first_json_object(text) else {
        return Vec::new();
    };
    let Ok(value) = serde_json::from_str::<serde_json::Value>(json) else {
        return Vec::new();
    };
    let Some(items) = value.get("ops").and_then(|v| v.as_array()) else {
        return Vec::new();
    };
    items
        .iter()
        .filter_map(|item| {
            let op = item.get("op").and_then(|v| v.as_str())?;
            match op {
                "add" => {
                    let title = op_string(item, "title");
                    if title.is_empty() {
                        return None;
                    }
                    Some(CardOp::Add {
                        title,
                        summary: op_string(item, "summary"),
                        reason: op_string(item, "reason"),
                    })
                }
                "confirm" | "reject" | "hold" => {
                    let id = op_string(item, "id");
                    if id.is_empty() {
                        return None;
                    }
                    Some(match op {
                        "confirm" => CardOp::Confirm { id },
                        "reject" => CardOp::Reject { id },
                        _ => CardOp::Hold { id },
                    })
                }
                _ => None,
            }
        })
        .collect()
}

pub(crate) fn apply_card_ops(mut cards: Vec<Card>, ops: &[CardOp], now: &str) -> Vec<Card> {
    let mut add_index = 0usize;
    for op in ops {
        match op {
            CardOp::Add { title, summary, reason } => {
                cards.push(Card {
                    id: format!("card_{now}_{add_index}"),
                    title: title.clone(),
                    summary: summary.clone(),
                    reason: reason.clone(),
                    state: CardState::Draft,
                    created_at: now.to_string(),
                    updated_at: now.to_string(),
                });
                add_index += 1;
            }
            CardOp::Confirm { id } => set_state(&mut cards, id, CardState::Confirmed, now),
            CardOp::Hold { id } => set_state(&mut cards, id, CardState::Held, now),
            CardOp::Reject { id } => cards.retain(|card| &card.id != id),
        }
    }
    cards
}

fn set_state(cards: &mut [Card], id: &str, state: CardState, now: &str) {
    if let Some(card) = cards.iter_mut().find(|card| card.id == id) {
        card.state = state;
        card.updated_at = now.to_string();
    }
}

const CARD_RUBRIC: &str = r#"너는 기획 대화를 읽고 '결정'을 카드로 감지하는 추출기다.
이번 턴의 대화를 보고, 새로 생긴 결정만 카드로 추가하는 add 연산을 JSON으로 낸다.

규칙:
- 결정에만 반응한다. 인사·잡담·질문이면 ops는 빈 배열 [].
- 새 결정이 생기면 add (흐릿한 초안 카드 생성).
- 아래 '현재 카드'에 이미 있는 결정은 다시 add하지 않는다(중복 금지).
- 확정/거절/보류는 사용자가 버튼으로 직접 한다. 추출기는 confirm/reject/hold를 절대 내지 않는다. add만 낸다.

반드시 아래 JSON만 출력한다(설명 금지):
{ "ops": [
  { "op": "add", "title": "...", "summary": "...", "reason": "..." }
] }
"#;

fn build_card_prompt(current: &[Card], turn: &[PlanningChatMessage]) -> String {
    let mut prompt = String::from(CARD_RUBRIC);
    prompt.push_str("\n현재 카드:\n");
    if current.is_empty() {
        prompt.push_str("(없음)\n");
    } else {
        for card in current {
            prompt.push_str(&format!(
                "- id={} state={:?} 제목={}\n",
                card.id, card.state, card.title
            ));
        }
    }
    prompt.push_str("\n이번 턴 대화:\n");
    for message in turn {
        if message.status != "ok" {
            continue;
        }
        let speaker = if message.role == "user" { "사용자" } else { "AI" };
        prompt.push_str(speaker);
        prompt.push_str(": ");
        prompt.push_str(message.content.trim());
        prompt.push('\n');
    }
    prompt.push_str("\n위 턴에 대한 ops JSON을 출력해.");
    prompt
}

/// cards.json을 읽어 이번 턴으로 갱신하고 갱신된 카드를 반환. AI 없거나 변화 없으면 기존 유지.
pub(crate) fn extract_and_apply(
    project_dir: &Path,
    session_dir: &Path,
    all_messages: &[PlanningChatMessage],
    turn: &[PlanningChatMessage],
    now: &str,
) -> Vec<Card> {
    let current = read_cards(session_dir);
    let prompt = build_card_prompt(&current, turn);
    let Some(text) = run_active_ai(project_dir, all_messages, &prompt) else {
        return current;
    };
    let ops = parse_card_ops(&text);
    if ops.is_empty() {
        return current;
    }
    let updated = apply_card_ops(current, &ops, now);
    let _ = write_cards(session_dir, &updated);
    updated
}

fn action_to_op(action: &str, card_id: String) -> Option<CardOp> {
    match action {
        "confirm" => Some(CardOp::Confirm { id: card_id }),
        "hold" => Some(CardOp::Hold { id: card_id }),
        "reject" => Some(CardOp::Reject { id: card_id }),
        _ => None,
    }
}

#[derive(serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateCardRequest {
    pub(crate) project_dir: String,
    pub(crate) session_id: String,
    pub(crate) card_id: String,
    pub(crate) action: String,
}

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CardUpdateResponse {
    ok: bool,
    cards: Vec<Card>,
    error: Option<String>,
}

#[tauri::command]
pub(crate) async fn update_card(request: UpdateCardRequest) -> CardUpdateResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return CardUpdateResponse {
            ok: false,
            cards: Vec::new(),
            error: Some("projectDir must be absolute".to_string()),
        };
    }
    tauri::async_runtime::spawn_blocking(move || {
        let Some(op) = action_to_op(&request.action, request.card_id.clone()) else {
            return CardUpdateResponse {
                ok: false,
                cards: Vec::new(),
                error: Some(format!("unknown action: {}", request.action)),
            };
        };
        let session_dir =
            super::planning_chat_store::planning_dir(&project_dir).join(&request.session_id);
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.as_millis())
            .to_string();
        let cards = read_cards(&session_dir);
        let updated = apply_card_ops(cards, &[op], &now);
        if let Err(error) = write_cards(&session_dir, &updated) {
            return CardUpdateResponse {
                ok: false,
                cards: updated,
                error: Some(error),
            };
        }
        CardUpdateResponse {
            ok: true,
            cards: updated,
            error: None,
        }
    })
    .await
    .unwrap_or_else(|error| CardUpdateResponse {
        ok: false,
        cards: Vec::new(),
        error: Some(error.to_string()),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample(id: &str, state: CardState) -> Card {
        Card {
            id: id.to_string(),
            title: "제목".to_string(),
            summary: "설명".to_string(),
            reason: String::new(),
            state,
            created_at: "1".to_string(),
            updated_at: "1".to_string(),
        }
    }

    #[test]
    fn read_cards_returns_empty_when_file_missing() {
        let dir = tempfile::tempdir().expect("tempdir");
        assert!(read_cards(dir.path()).is_empty());
    }

    #[test]
    fn write_then_read_round_trips() {
        let dir = tempfile::tempdir().expect("tempdir");
        let cards = vec![sample("card_1", CardState::Draft)];
        write_cards(dir.path(), &cards).expect("write");
        let loaded = read_cards(dir.path());
        assert_eq!(loaded, cards);
        assert_eq!(loaded[0].state, CardState::Draft);
    }

    #[test]
    fn parse_ops_from_fenced_json() {
        let text = r#"좋아요:
```json
{ "ops": [
  { "op": "add", "title": "카드 발동", "summary": "결정마다 뜬다", "reason": "쾌감" },
  { "op": "confirm", "id": "card_1" },
  { "op": "reject", "id": "card_2" },
  { "op": "hold", "id": "card_3" }
] }
```"#;
        let ops = parse_card_ops(text);
        assert_eq!(ops.len(), 4);
        assert_eq!(
            ops[0],
            CardOp::Add {
                title: "카드 발동".to_string(),
                summary: "결정마다 뜬다".to_string(),
                reason: "쾌감".to_string(),
            }
        );
        assert_eq!(ops[1], CardOp::Confirm { id: "card_1".to_string() });
        assert_eq!(ops[2], CardOp::Reject { id: "card_2".to_string() });
        assert_eq!(ops[3], CardOp::Hold { id: "card_3".to_string() });
    }

    #[test]
    fn parse_ops_skips_unknown_op_and_missing_id() {
        let text = r#"{ "ops": [
          { "op": "frobnicate" },
          { "op": "confirm" },
          { "op": "add", "title": "t" }
        ] }"#;
        let ops = parse_card_ops(text);
        assert_eq!(ops.len(), 1);
        assert_eq!(
            ops[0],
            CardOp::Add {
                title: "t".to_string(),
                summary: String::new(),
                reason: String::new(),
            }
        );
    }

    #[test]
    fn parse_ops_returns_empty_on_broken_json() {
        assert!(parse_card_ops("미안, JSON 못 만들었어").is_empty());
        assert!(parse_card_ops(r#"{ "nope": 1 }"#).is_empty());
    }

    #[test]
    fn apply_add_creates_draft_with_generated_id() {
        let ops = vec![
            CardOp::Add { title: "A".to_string(), summary: "a".to_string(), reason: String::new() },
            CardOp::Add { title: "B".to_string(), summary: "b".to_string(), reason: String::new() },
        ];
        let cards = apply_card_ops(Vec::new(), &ops, "100");
        assert_eq!(cards.len(), 2);
        assert_eq!(cards[0].id, "card_100_0");
        assert_eq!(cards[1].id, "card_100_1");
        assert_eq!(cards[0].state, CardState::Draft);
        assert_eq!(cards[0].created_at, "100");
    }

    #[test]
    fn apply_confirm_hold_reject_change_or_remove() {
        let start = vec![
            sample("card_1", CardState::Draft),
            sample("card_2", CardState::Draft),
            sample("card_3", CardState::Draft),
        ];
        let ops = vec![
            CardOp::Confirm { id: "card_1".to_string() },
            CardOp::Hold { id: "card_2".to_string() },
            CardOp::Reject { id: "card_3".to_string() },
        ];
        let cards = apply_card_ops(start, &ops, "200");
        assert_eq!(cards.len(), 2);
        assert_eq!(cards[0].state, CardState::Confirmed);
        assert_eq!(cards[0].updated_at, "200");
        assert_eq!(cards[1].state, CardState::Held);
        assert!(cards.iter().all(|c| c.id != "card_3"));
    }

    #[test]
    fn apply_ignores_unknown_id() {
        let start = vec![sample("card_1", CardState::Draft)];
        let ops = vec![CardOp::Confirm { id: "ghost".to_string() }];
        let cards = apply_card_ops(start, &ops, "300");
        assert_eq!(cards.len(), 1);
        assert_eq!(cards[0].state, CardState::Draft);
    }

    #[test]
    fn action_to_op_maps_known_and_rejects_unknown() {
        assert_eq!(action_to_op("confirm", "c1".to_string()), Some(CardOp::Confirm { id: "c1".to_string() }));
        assert_eq!(action_to_op("hold", "c1".to_string()), Some(CardOp::Hold { id: "c1".to_string() }));
        assert_eq!(action_to_op("reject", "c1".to_string()), Some(CardOp::Reject { id: "c1".to_string() }));
        assert_eq!(action_to_op("frob", "c1".to_string()), None);
    }

    #[test]
    fn build_prompt_includes_rules_current_cards_and_turn() {
        let current = vec![sample("card_9", CardState::Draft)];
        let turn = vec![PlanningChatMessage {
            id: "m".to_string(),
            role: "user".to_string(),
            persona_id: None,
            content: "접기로 하자".to_string(),
            status: "ok".to_string(),
            created_at: "0".to_string(),
            provider_used: None,
        }];
        let prompt = build_card_prompt(&current, &turn);
        assert!(prompt.contains("ops"));
        assert!(prompt.contains("card_9"));
        assert!(prompt.contains("접기로 하자"));
        assert!(prompt.contains("add만 낸다"));
    }
}
// === ANCHOR: PLANNING_CHAT_CARDS_END ===
