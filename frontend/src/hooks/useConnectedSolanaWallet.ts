import { useWallet } from "@solana/wallet-adapter-react";
import { solanaNetwork, type InvoiceXSolanaNetwork } from "../wallet/solanaNetwork";

export interface ConnectedWalletState {
  connected: boolean;
  connecting: boolean;
  publicKey: string | null;
  walletName: string | null;
  network: InvoiceXSolanaNetwork;
}

/** Exposes only connection information; it never signs or sends transactions. */
export function useConnectedSolanaWallet(): ConnectedWalletState {
  const { connected, connecting, publicKey, wallet } = useWallet();

  return {
    connected,
    connecting,
    publicKey: publicKey?.toBase58() ?? null,
    walletName: wallet?.adapter.name ?? null,
    network: solanaNetwork,
  };
}
