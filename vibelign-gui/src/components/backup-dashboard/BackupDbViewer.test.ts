// === ANCHOR: BACKUPDBVIEWER_TEST_START ===
import { describe, expect, test } from "vitest";

import {
  buildMaintenanceHintText,
  canRunBackupDbMaintenance,
} from "./BackupDbViewer";

describe("BackupDbViewer maintenance copy", () => {
  test("explains_large_db_when_maintenance_has_no_action", () => {
    const text = buildMaintenanceHintText({
      dbTotalBytes: 119_689_216,
      maintenancePlannedAction: "noop",
      showCriticalMaintenance: false,
    });

    expect(text).toContain("현재 114 MB");
    expect(text).toContain("추가 압축할 빈 공간이 거의 없어요");
  });

  test("does_not_offer_maintenance_button_for_noncritical_noop", () => {
    expect(
      canRunBackupDbMaintenance({
        showMaintenanceHint: true,
        showCriticalMaintenance: false,
        maintenancePlannedAction: "noop",
        blockers: [],
      }),
    ).toBe(false);
  });

  test("waits_for_maintenance_plan_before_offering_noncritical_button", () => {
    expect(
      canRunBackupDbMaintenance({
        showMaintenanceHint: true,
        showCriticalMaintenance: false,
        maintenancePlannedAction: null,
        blockers: [],
      }),
    ).toBe(false);
  });

  test("keeps_cleanup_available_for_critical_database", () => {
    expect(
      canRunBackupDbMaintenance({
        showMaintenanceHint: true,
        showCriticalMaintenance: true,
        maintenancePlannedAction: "noop",
        blockers: [],
      }),
    ).toBe(true);
  });
});
// === ANCHOR: BACKUPDBVIEWER_TEST_END ===
