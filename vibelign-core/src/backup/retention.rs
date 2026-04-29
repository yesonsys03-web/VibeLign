#[allow(dead_code)]
#[derive(Debug, Clone, Copy)]
pub struct RetentionPolicy {
    pub keep_latest: u32,
    pub keep_daily_days: u32,
    pub keep_weekly_weeks: u32,
    pub max_total_size_bytes: u64,
    pub max_age_days: u32,
    pub min_keep: u32,
}

impl Default for RetentionPolicy {
    fn default() -> Self {
        Self {
            keep_latest: 30,
            keep_daily_days: 14,
            keep_weekly_weeks: 8,
            max_total_size_bytes: 2 * 1024 * 1024 * 1024,
            max_age_days: 180,
            min_keep: 10,
        }
    }
}
