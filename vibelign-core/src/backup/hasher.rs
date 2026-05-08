// === ANCHOR: HASHER_START ===
#[allow(dead_code)]
pub fn blake3_hex(bytes: &[u8]) -> String {
    blake3::hash(bytes).to_hex().to_string()
}
// === ANCHOR: HASHER_END ===
