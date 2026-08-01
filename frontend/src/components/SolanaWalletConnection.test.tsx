import { describe, expect, test } from "vitest";
import { shortenWalletAddress, walletErrorMessage } from "../wallet/walletConnectionUtils";

describe("Solana wallet connection helpers", () => {
  test("shortens connected public keys for display", () => {
    expect(shortenWalletAddress("8xK2f7yZQmP8Y5BwL9Vx3dTs7cR2nJ6p91Q")).toBe("8xK2...p91Q");
  });

  test("returns user-facing messages instead of raw wallet errors", () => {
    expect(walletErrorMessage(new Error("User rejected the request"))).toBe("지갑 연결 요청이 취소되었습니다.");
    expect(walletErrorMessage(new Error("Wallet not ready"))).toBe("지원하는 Solana 지갑을 설치한 뒤 다시 시도해 주세요.");
    expect(walletErrorMessage(new Error("Unexpected provider failure"))).toBe("지갑 연결 중 오류가 발생했습니다. 다시 시도해 주세요.");
  });
});
