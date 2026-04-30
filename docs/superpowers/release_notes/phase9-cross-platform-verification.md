# Phase 9 Cross-platform Backup Verification

Phase 9 verifies the backup engine before release on macOS and Windows.

Manual release checks:

```bash
cargo test --manifest-path vibelign-core/Cargo.toml
python -m pytest tests/test_cross_platform_paths.py tests/test_checkpoint_cmd_wrapper.py tests/test_mcp_checkpoint_handlers.py -q
npm run build --prefix vibelign-gui
```

Windows notes:

- Long paths may require the Windows `LongPathsEnabled` registry setting for very deep project trees.
- Drive-letter and UNC-style inputs are treated as unsafe restore targets unless they are safely resolved under the project root.
- Locked-file behavior must be reported as a partial read/restore problem, not a silent success.

macOS notes:

- Unicode filenames are normalized for comparison while keeping the original source path for reading.
- Symlinks are not followed during snapshot collection.
- Executable-bit metadata is not surfaced as a user-facing restore promise in the v2 MVP.

Dashboard date grouping:

- `tests/fixtures/timezone_dst_dashboard_fixture.json` captures backups around a DST jump.
- Dashboard grouping should use the local calendar day from the timestamp offset, not UTC midnight.
