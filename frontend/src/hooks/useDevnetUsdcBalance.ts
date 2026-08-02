import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { PublicKey } from "@solana/web3.js";
import { useQuery } from "@tanstack/react-query";

const defaultUsdcMint = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU";
const usdcMintAddress = import.meta.env.VITE_SOLANA_USDC_MINT?.trim() || defaultUsdcMint;
const configuredDecimals = Number(import.meta.env.VITE_SOLANA_USDC_DECIMALS ?? "6");
const usdcDecimals = Number.isInteger(configuredDecimals) && configuredDecimals >= 0 ? configuredDecimals : 6;

function rawAmountToUsdc(rawAmount: bigint): number {
  return Number(rawAmount) / 10 ** usdcDecimals;
}

/** Reads the configured Devnet USDC token accounts for the currently connected browser wallet. */
export function useDevnetUsdcBalance() {
  const { connection } = useConnection();
  const { connected, publicKey } = useWallet();
  const address = publicKey?.toBase58();

  const query = useQuery({
    queryKey: ["solana", "devnet-usdc-balance", address, usdcMintAddress],
    enabled: Boolean(connected && publicKey),
    staleTime: 10_000,
    refetchInterval: 15_000,
    retry: 1,
    queryFn: async () => {
      if (!publicKey) throw new Error("Connected wallet public key is unavailable.");

      const tokenAccounts = await connection.getParsedTokenAccountsByOwner(publicKey, {
        mint: new PublicKey(usdcMintAddress),
      });
      const rawBalance = tokenAccounts.value.reduce(
        (total, account) => total + BigInt(account.account.data.parsed.info.tokenAmount.amount),
        0n,
      );

      return rawAmountToUsdc(rawBalance);
    },
  });

  return {
    address: address ?? null,
    balanceUsdc: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    refresh: query.refetch,
  };
}
