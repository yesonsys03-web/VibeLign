import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { AdvancedHomeCards } from "../AdvancedHomeCards";

vi.mock("../../cards/analysis/GuardCard", () => ({
  default: () => <div>Guard card mock</div>,
}));

describe("AdvancedHomeCards", () => {
  afterEach(() => {
    cleanup();
  });

  test("renders_ordered_advanced_cards_with_drag_handles", () => {
    render(
      <AdvancedHomeCards
        projectDir="/tmp/demo"
        cardOrder={["guard"]}
        onCardOrderChange={() => undefined}
        hasAnyAiKey={false}
        aiKeyStatusLoaded={false}
        onNavigate={() => undefined}
        watchOn={false}
        onWatchChange={() => undefined}
        mapMode="manual"
        onMapModeChange={() => undefined}
        onGuardResult={() => undefined}
      />
    );

    expect(screen.getByText("Guard card mock")).toBeInTheDocument();
    expect(screen.getByTitle("드래그하여 카드 이동")).toBeInTheDocument();
  });

  test("ignores_removed_legacy_card_ids_from_saved_order", () => {
    render(
      <AdvancedHomeCards
        projectDir="/tmp/demo"
        cardOrder={["patch", "plan-structure", "guard"]}
        onCardOrderChange={() => undefined}
        hasAnyAiKey={false}
        aiKeyStatusLoaded={false}
        onNavigate={() => undefined}
        watchOn={false}
        onWatchChange={() => undefined}
        mapMode="manual"
        onMapModeChange={() => undefined}
        onGuardResult={() => undefined}
      />
    );

    expect(screen.getByText("Guard card mock")).toBeInTheDocument();
    expect(screen.getAllByTitle("드래그하여 카드 이동")).toHaveLength(1);
  });
});
