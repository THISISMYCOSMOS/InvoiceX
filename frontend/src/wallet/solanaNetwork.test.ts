import { describe, expect, test } from "vitest";
import { resolveSolanaNetwork } from "./solanaNetwork";

describe("Solana network configuration", () => {
  test("defaults to devnet", () => {
    expect(resolveSolanaNetwork()).toBe("devnet");
    expect(resolveSolanaNetwork(" devnet ")).toBe("devnet");
  });

  test("allows an explicit testnet override", () => {
    expect(resolveSolanaNetwork(" testnet ")).toBe("testnet");
  });

  test("rejects unsupported clusters", () => {
    expect(() => resolveSolanaNetwork("mainnet-beta")).toThrow("Unsupported VITE_SOLANA_NETWORK");
  });
});
