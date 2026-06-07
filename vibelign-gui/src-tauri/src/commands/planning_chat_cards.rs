// === ANCHOR: PLANNING_CHAT_CARDS_START ===
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

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
}
// === ANCHOR: PLANNING_CHAT_CARDS_END ===
