import { WalletAdapterNetwork } from "@solana/wallet-adapter-base";

export type InvoiceXSolanaNetwork = "devnet" | "testnet";

export function resolveSolanaNetwork(value?: string): InvoiceXSolanaNetwork {
  const normalized = value?.trim().toLowerCase();
  if (!normalized || normalized === "devnet") return "devnet";
  if (normalized === "testnet") return "testnet";
  throw new Error(`Unsupported VITE_SOLANA_NETWORK: ${value}`);
}

export const solanaNetwork = resolveSolanaNetwork(import.meta.env.VITE_SOLANA_NETWORK);
export const solanaAdapterNetwork = solanaNetwork === "testnet"
  ? WalletAdapterNetwork.Testnet
  : WalletAdapterNetwork.Devnet;
export const solanaNetworkLabel = solanaNetwork === "testnet" ? "Solana Testnet" : "Solana Devnet";
export const solanaRpcEndpoint = import.meta.env.VITE_SOLANA_RPC_URL?.trim()
  || `https://api.${solanaNetwork}.solana.com`;
