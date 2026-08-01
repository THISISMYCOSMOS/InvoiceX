import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { investorApi } from "../api/investor.api";
import { buildInvestorDepositTransaction } from "../wallet/investorDepositTransaction";
import { queryKeys } from "./queryKeys";

export function useInvestorDeposit() {
  const { connection } = useConnection();
  const { connected, publicKey, sendTransaction, signTransaction } = useWallet();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ amountUsdc }: { amountUsdc: number }) => {
      if (!connected || !publicKey || (!signTransaction && !sendTransaction)) {
        throw new Error("투자자 Solana 지갑을 먼저 연결해 주세요.");
      }

      const preparation = await investorApi.prepareDeposit(
        publicKey.toBase58(),
        amountUsdc,
      );
      if (preparation.investorWalletAddress !== publicKey.toBase58()) {
        throw new Error("예치 준비 주소가 현재 연결된 투자자 지갑과 다릅니다.");
      }

      const transaction = buildInvestorDepositTransaction(preparation, publicKey);
      const latestBlockhash = await connection.getLatestBlockhash("confirmed");
      transaction.feePayer = publicKey;
      transaction.recentBlockhash = latestBlockhash.blockhash;

      const signature = signTransaction
        ? await connection.sendRawTransaction(
            (await signTransaction(transaction)).serialize(),
          )
        : await sendTransaction!(transaction, connection);
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
