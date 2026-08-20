import { getAssociatedTokenAddressSync } from "@solana/spl-token";
import { PublicKey, TransactionMessage, VersionedTransaction } from "@solana/web3.js";
import { useConnection } from "@solana/wallet-adapter-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { linkEmbeddedWallet, withPrivyAccessTokenRetry } from "../api/onboarding.api";
import { useCurrentPrivyAccount, useUpdateCurrentPrivyAccount } from "../auth/currentAccount";
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
  const currentAccount = useCurrentPrivyAccount();
  const updateCurrentAccount = useUpdateCurrentPrivyAccount();
  const {
    authenticated,
    authenticatedEmail,
    embeddedSolanaWalletReady,
    ensureEmbeddedSolanaWallet,
    getAccessToken,
    hasEmbeddedSolanaWallet,
    signEmbeddedSolanaTransaction,
  } = useSignupAuth();
  const queryClient = useQueryClient();
  const requiresPrivyVerification = Boolean(
    currentAccount
    && (!authenticated || authenticatedEmail !== currentAccount.userEmail.trim().toLowerCase()),
  );

  const mutation = useMutation({
    mutationFn: async () => {
      if (!currentAccount) {
        throw new Error("로그인한 구매기업 정보를 확인할 수 없습니다.");
      }
      if (requiresPrivyVerification) {
        throw new Error("결제하려면 로그인한 이메일로 Privy 인증을 완료해 주세요.");
      }
      if (!embeddedSolanaWalletReady) {
        throw new Error("Privy Solana 지갑을 확인하는 중입니다. 잠시 후 다시 시도해 주세요.");
      }

      let buyerWalletAddress = currentAccount.walletAddress;
      if (!hasEmbeddedSolanaWallet(buyerWalletAddress)) {
        const wallet = await ensureEmbeddedSolanaWallet();
        buyerWalletAddress = wallet.address;
      }

      const accessToken = await withPrivyAccessTokenRetry(
        getAccessToken,
        async (token) => {
          if (buyerWalletAddress !== currentAccount.walletAddress) {
            const profile = await linkEmbeddedWallet(token, buyerWalletAddress);
            if (!profile.embeddedWallet || profile.embeddedWallet.address !== buyerWalletAddress) {
              throw new Error("구매기업 Embedded Wallet 연결을 갱신하지 못했습니다.");
            }
            updateCurrentAccount({ walletAddress: profile.embeddedWallet.address });
          }
          return token;
        },
      );

      const buyer = new PublicKey(buyerWalletAddress);
      const preparation = await invoiceApi.prepareBuyerPayment(invoiceId, accessToken);
      if (preparation.buyerWalletAddress !== buyerWalletAddress) {
        throw new Error("결제 준비 주소가 로그인한 구매기업 지갑과 일치하지 않습니다.");
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
      // Reuse the tested instruction builder, then wrap them in a v0 message so
      // the Privy embedded wallet signs the exact VersionedTransaction shape it
      // supports (mirrors the investor deposit flow).
      const { instructions } = buildBuyerPaymentTransaction(preparation, buyer);
      const latestBlockhash = await connection.getLatestBlockhash("confirmed");
      const message = new TransactionMessage({
        payerKey: buyer,
        recentBlockhash: latestBlockhash.blockhash,
        instructions,
      }).compileToV0Message();
      const transaction = new VersionedTransaction(message);
      const signedTransaction = await signEmbeddedSolanaTransaction(buyerWalletAddress, transaction.serialize());
      const signature = await connection.sendRawTransaction(signedTransaction, {
        preflightCommitment: "confirmed",
      });
      const confirmation = await connection.confirmTransaction(
        { signature, ...latestBlockhash },
        "confirmed",
      );
      if (confirmation.value.err) throw new Error("Solana Devnet USDC 결제가 실패했습니다.");
      return invoiceApi.confirmBuyerPayment(invoiceId, signature, accessToken);
    },
    onSuccess: async (invoice) => {
      queryClient.setQueryData(queryKeys.invoice(invoice.id), invoice);
      await queryClient.invalidateQueries({ queryKey: queryKeys.invoices });
    },
  });

  return { ...mutation, requiresPrivyVerification };
}
