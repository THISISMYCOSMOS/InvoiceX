import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getAssociatedTokenAddressSync } from "@solana/spl-token";
import { PublicKey } from "@solana/web3.js";
import { investorApi } from "../api/investor.api";
import { buildInvestorDepositTransaction } from "../wallet/investorDepositTransaction";
import { queryKeys } from "./queryKeys";

export function useInvestorDeposit() {
  const { connection } = useConnection();
  const { connected, publicKey, sendTransaction } = useWallet();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ amountUsdc }: { amountUsdc: number }) => {
      if (!connected || !publicKey || !sendTransaction) {
        throw new Error("투자자 Solana 지갑을 먼저 연결해 주세요.");
      }

      const preparation = await investorApi.prepareDeposit(
        publicKey.toBase58(),
        amountUsdc,
      );
      if (preparation.investorWalletAddress !== publicKey.toBase58()) {
        throw new Error("예치 준비 주소가 현재 연결된 투자자 지갑과 다릅니다.");
      }

      const investorTokenAccount = getAssociatedTokenAddressSync(
        new PublicKey(preparation.usdcMint),
        publicKey,
      );
      const requiredRawAmount = BigInt(preparation.amountBaseUnits);

      let availableRawAmount: bigint;
      try {
        const balance = await connection.getTokenAccountBalance(
          investorTokenAccount,
          "confirmed",
        );
        availableRawAmount = BigInt(balance.value.amount);
      } catch {
        throw new Error(
          "연결된 지갑에 Devnet USDC가 없습니다. 테스트 토큰을 받은 투자자 계정으로 다시 연결해 주세요.",
        );
      }

      if (availableRawAmount < requiredRawAmount) {
        const availableUsdc = Number(availableRawAmount) / (10 ** preparation.decimals);
        throw new Error(
          `연결된 지갑의 Devnet USDC가 부족합니다(현재 ${availableUsdc} USDC). 토큰을 받은 투자자 계정으로 다시 연결해 주세요.`,
        );
      }

      const transaction = buildInvestorDepositTransaction(preparation, publicKey);
      const latestBlockhash = await connection.getLatestBlockhash("confirmed");
      transaction.feePayer = publicKey;
      transaction.recentBlockhash = latestBlockhash.blockhash;

      // Wallet Standard derives `solana:devnet` from this connection. Calling
      // signTransaction directly omits the chain context, so multichain wallets
      // can incorrectly simulate the transaction against Solana Mainnet.
      const signature = await sendTransaction(transaction, connection, {
        preflightCommitment: "confirmed",
      });
      const confirmation = await connection.confirmTransaction(
        { signature, ...latestBlockhash },
        "confirmed",
      );
      if (confirmation.value.err) {
        throw new Error("Solana Devnet 예치 트랜잭션이 실패했습니다.");
      }

      return investorApi.confirmDeposit(preparation.referenceId, signature);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.investorDashboard });
    },
  });
}
