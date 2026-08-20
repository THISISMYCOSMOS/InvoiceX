import { getAssociatedTokenAddressSync } from "@solana/spl-token";
import { PublicKey } from "@solana/web3.js";
import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { useSignupAuth } from "../auth/SignupAuthContext";
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
  const { hasEmbeddedSolanaWallet, signEmbeddedSolanaTransaction } = useSignupAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const preparation = await invoiceApi.prepareBuyerPayment(invoiceId);
      const buyer = new PublicKey(preparation.buyerWalletAddress);
      const canUseExternalWallet = Boolean(
        connected
        && publicKey
        && preparation.buyerWalletAddress === publicKey.toBase58(),
      );
      const canUseEmbeddedWallet = hasEmbeddedSolanaWallet(preparation.buyerWalletAddress);
      if (!canUseExternalWallet && !canUseEmbeddedWallet) {
        throw new Error("결제 준비 주소와 일치하는 구매기업 지갑을 찾을 수 없습니다.");
      }
      const tokenAccount = getAssociatedTokenAddressSync(
        new PublicKey(preparation.usdcMintAddress),
        buyer,
      );
      let available: bigint;
      try {
        available = BigInt((await connection.getTokenAccountBalance(tokenAccount, "confirmed")).value.amount);
      } catch {
        throw new Error("구매기업 지갑에 Devnet USDC 토큰 계정이 없습니다.");
      }
      const totalAmountBaseUnits = preparation.transfers.reduce(
        (total, transfer) => total + BigInt(transfer.amountBaseUnits),
        0n,
      );
      if (available < totalAmountBaseUnits) {
        throw new Error("구매기업 지갑의 Devnet USDC 잔액이 결제 금액보다 부족합니다.");
      }
      const transaction = buildBuyerPaymentTransaction(preparation, buyer);
      const latestBlockhash = await connection.getLatestBlockhash("confirmed");
      transaction.feePayer = buyer;
      transaction.recentBlockhash = latestBlockhash.blockhash;
      const signature = canUseExternalWallet
        ? await sendTransaction(transaction, connection, { preflightCommitment: "confirmed" })
        : await connection.sendRawTransaction(
            await signEmbeddedSolanaTransaction(
              preparation.buyerWalletAddress,
              transaction.serialize({ requireAllSignatures: false, verifySignatures: false }),
            ),
            { preflightCommitment: "confirmed" },
          );
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
