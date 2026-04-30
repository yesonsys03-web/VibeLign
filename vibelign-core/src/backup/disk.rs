use std::path::Path;

pub const MIN_FREE_BYTES: u64 = 1024 * 1024 * 1024;

pub fn ensure_min_free_space(root: &Path) -> Result<(), String> {
    let available = fs2::available_space(root).map_err(|error| error.to_string())?;
    if has_enough_space(available, MIN_FREE_BYTES) {
        return Ok(());
    }
    Err("not enough free disk space for safe backup operation".to_string())
}

fn has_enough_space(available: u64, required: u64) -> bool {
    available >= required
}

#[cfg(test)]
mod tests {
    use super::{has_enough_space, MIN_FREE_BYTES};

    #[test]
    fn checks_required_free_space_boundary() {
        assert!(has_enough_space(MIN_FREE_BYTES, MIN_FREE_BYTES));
        assert!(!has_enough_space(MIN_FREE_BYTES - 1, MIN_FREE_BYTES));
    }
}
