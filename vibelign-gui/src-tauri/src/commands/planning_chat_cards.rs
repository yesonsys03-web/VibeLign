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

pub(crate) fn write_cards(session_dir: &Path, cards: &[Card]) -> Result<(), String> {
    let file = CardsFile {
        cards: cards.to_vec(),
    };
    let text = serde_json::to_string_pretty(&file).map_err(|error| error.to_string())?;
    std::fs::write(cards_path(session_dir), text + "\n").map_err(|error| error.to_string())
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
}
// === ANCHOR: PLANNING_CHAT_CARDS_END ===
