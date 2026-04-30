use crate::backup::checkpoint;
use crate::backup::disk;
use std::path::Path;

pub fn restore_full(root: &Path, checkpoint_id: &str) -> Result<(), String> {
    disk::ensure_min_free_space(root)?;
    checkpoint::restore(root, checkpoint_id)
}
