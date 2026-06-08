import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { PersonaProviderSelect, providerOptionLabel } from "./PersonaProviderSelect";

describe("providerOptionLabel", () => {
  it("plain when installed unknown (null)", () => {
    expect(providerOptionLabel("codex", null)).toBe("codex");
  });
  it("plain when installed", () => {
    expect(providerOptionLabel("codex", ["codex"])).toBe("codex");
  });
  it("marks uninstalled", () => {
    expect(providerOptionLabel("agy", ["codex"])).toBe("agy (미설치)");
  });
});

describe("PersonaProviderSelect", () => {
  it("renders the four providers and selects the effective one", () => {
    const { container } = render(
      <PersonaProviderSelect personaId="chloe" map={{ chloe: { provider: "codex" } }} installed={["codex"]} onChange={() => {}} />,
    );
    const select = container.querySelector("select") as HTMLSelectElement;
    expect(select.value).toBe("codex");
    expect(select.querySelectorAll("option")).toHaveLength(4);
  });
});
