use crate::backup::checkpoint;
use std::path::Path;

pub fn restore_full(root: &Path, checkpoint_id: &str) -> Result<(), String> {
    checkpoint::restore(root, checkpoint_id)
}
