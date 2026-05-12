// === ANCHOR: LIB_START ===
//! Library entry for `vibelign-core`. The 1-shot CLI binary (`vibelign-engine`)
//! and the long-running daemon both live in `main.rs` — they consume this crate
//! as a normal library. Tauri (vibelign-gui) is the second consumer: Phase 3 of
//! the rust engine utilization plan replaces the GUI's `vib` Python sidecar
//! call with a direct in-process call to `vibelign_core::ipc::handler::handle`.
//!
//! Public surface intentionally minimal:
//! - [`ipc::protocol`] — `EngineRequest`/`EngineResponse` types
//! - [`ipc::handler::handle`] — single dispatch entry point
//! - [`ipc::daemon`] — daemon lifecycle for the binary
//!
//! Other modules stay private to enforce the IPC contract as the only seam.

mod anchor_meta;
mod backup;
mod config;
mod constants;
mod db;
pub mod ipc;
mod project_scan;
mod secret_scan;
mod security;
// === ANCHOR: LIB_END ===
