import { getAssociatedTokenAddressSync } from "@solana/spl-token";
import { PublicKey } from "@solana/web3.js";
import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { buildBuyerPaymentTransaction } from "../wallet/buyerPaymentTransaction";
import { queryKeys } from "./queryKeys";

export function useBuyerPaymentPreparation(invoiceId: string) {
  return useQuery({
    queryKey: [...queryKeys.invoice(invoiceId), "buyer-payment-preparation"],
    queryFn: () => invoiceApi.prepareBuyerPayment(invoiceId),
    enabled: Boolean(invoiceId),
    staleTime: 15_000,
  });
}

export function useBuyerPayment(invoiceId: string) {
  const { connection } = useConnection();
  const { connected, publicKey, sendTransaction } = useWallet();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      if (!connected || !publicKey || !sendTransaction) {
        throw new Error("구매기업 Embedded Wallet을 확인할 수 없습니다.");
      }
      const preparation = await invoiceApi.prepareBuyerPayment(invoiceId);
      if (preparation.buyerWalletAddress !== publicKey.toBase58()) {
        throw new Error("결제 준비 주소가 로그인한 구매기업 지갑과 일치하지 않습니다.");
      }
      const tokenAccount = getAssociatedTokenAddressSync(
        new PublicKey(preparation.usdcMintAddress),
        publicKey,
      );
      let available: bigint;
      try {
        available = BigInt((await connection.getTokenAccountBalance(tokenAccount, "confirmed")).value.amount);
      } catch {
        throw new Error("구매기업 지갑에 Devnet USDC 토큰 계정이 없습니다.");
      }
      if (available < BigInt(preparation.amountBaseUnits)) {
        throw new Error("구매기업 지갑의 Devnet USDC 잔액이 결제 금액보다 부족합니다.");
      }
      const transaction = buildBuyerPaymentTransaction(preparation, publicKey);
      const latestBlockhash = await connection.getLatestBlockhash("confirmed");
      transaction.feePayer = publicKey;
      transaction.recentBlockhash = latestBlockhash.blockhash;
      const signature = await sendTransaction(transaction, connection, {
        preflightCommitment: "confirmed",
      });
      const confirmation = await connection.confirmTransaction(
        { signature, ...latestBlockhash },
        "confirmed",
      );
      if (confirmation.value.err) throw new Error("Solana Devnet USDC 결제가 실패했습니다.");
      return invoiceApi.confirmBuyerPayment(invoiceId, signature);
    },
    onSuccess: async (invoice) => {
      queryClient.setQueryData(queryKeys.invoice(invoice.id), invoice);
      await queryClient.invalidateQueries({ queryKey: queryKeys.invoices });
    },
  });
}
