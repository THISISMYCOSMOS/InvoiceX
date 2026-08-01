export type WalletConnectionStatus = "DISCONNECTED" | "CONNECTING" | "CONNECTED" | "ERROR";

export function shortenWalletAddress(address: string): string {
  return address.length <= 10 ? address : `${address.slice(0, 4)}...${address.slice(-4)}`;
}

export function walletErrorMessage(error: unknown): string {
  const message = error instanceof Error ? error.message.toLowerCase() : "";

  if (/(reject|declin|cancel)/.test(message)) {
    return "지갑 연결 요청이 취소되었습니다.";
  }

  if (/(not ready|not detected|not found|install)/.test(message)) {
    return "지원하는 Solana 지갑을 설치한 뒤 다시 시도해 주세요.";
  }

  return "지갑 연결 중 오류가 발생했습니다. 다시 시도해 주세요.";
}
