import { ConnectionProvider, WalletProvider } from "@solana/wallet-adapter-react";
import { PhantomWalletAdapter } from "@solana/wallet-adapter-phantom";
import { SolflareWalletAdapter } from "@solana/wallet-adapter-solflare";
import { useMemo, type ReactNode } from "react";
import { solanaAdapterNetwork, solanaRpcEndpoint } from "./solanaNetwork";

/**
 * The application's only Solana provider. WalletProvider also discovers
 * browser wallets that implement Solana Wallet Standard (including Backpack).
 */
export function SolanaWalletProvider({ children }: { children: ReactNode }) {
  const wallets = useMemo(
    () => [
      new PhantomWalletAdapter(),
      new SolflareWalletAdapter({ network: solanaAdapterNetwork }),
    ],
    [],
  );

  return (
    <ConnectionProvider endpoint={solanaRpcEndpoint}>
      <WalletProvider
        autoConnect
        localStorageKey="invoicex-wallet-adapter"
        onError={() => undefined}
        wallets={wallets}
      >
        {children}
      </WalletProvider>
    </ConnectionProvider>
  );
}
