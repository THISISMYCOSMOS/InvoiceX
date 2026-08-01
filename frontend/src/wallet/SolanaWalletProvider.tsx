import { WalletAdapterNetwork } from "@solana/wallet-adapter-base";
import { ConnectionProvider, WalletProvider } from "@solana/wallet-adapter-react";
import { PhantomWalletAdapter } from "@solana/wallet-adapter-phantom";
import { SolflareWalletAdapter } from "@solana/wallet-adapter-solflare";
import { useMemo, type ReactNode } from "react";

const devnetRpcUrl = import.meta.env.VITE_SOLANA_RPC_URL?.trim() || "https://api.devnet.solana.com";

/**
 * The application's only Solana provider. WalletProvider also discovers
 * browser wallets that implement Solana Wallet Standard (including Backpack).
 */
export function SolanaWalletProvider({ children }: { children: ReactNode }) {
  const wallets = useMemo(
    () => [
      new PhantomWalletAdapter(),
      new SolflareWalletAdapter({ network: WalletAdapterNetwork.Devnet }),
    ],
    [],
  );

  return (
    <ConnectionProvider endpoint={devnetRpcUrl}>
      <WalletProvider
        autoConnect={import.meta.env.MODE !== "test"}
        localStorageKey="invoicex-wallet-adapter"
        onError={() => undefined}
        wallets={wallets}
      >
        {children}
      </WalletProvider>
    </ConnectionProvider>
  );
}
