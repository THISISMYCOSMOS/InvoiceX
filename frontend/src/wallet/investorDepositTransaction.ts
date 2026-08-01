import {
  createAssociatedTokenAccountIdempotentInstruction,
  createTransferCheckedInstruction,
  getAssociatedTokenAddressSync,
} from "@solana/spl-token";
import { PublicKey, Transaction } from "@solana/web3.js";
import type { InvestorDepositPreparation } from "../types/invoice";

export function buildInvestorDepositTransaction(
  preparation: InvestorDepositPreparation,
  investor: PublicKey,
): Transaction {
  const mint = new PublicKey(preparation.usdcMint);
  const treasury = new PublicKey(preparation.treasuryWalletAddress);
  const investorTokenAccount = getAssociatedTokenAddressSync(mint, investor);
  const treasuryTokenAccount = getAssociatedTokenAddressSync(mint, treasury);
  const rawAmount = BigInt(preparation.amountUsdc)
    * (10n ** BigInt(preparation.decimals));

  return new Transaction().add(
    createAssociatedTokenAccountIdempotentInstruction(
      investor,
      treasuryTokenAccount,
      treasury,
      mint,
    ),
    createTransferCheckedInstruction(
      investorTokenAccount,
      mint,
      treasuryTokenAccount,
      investor,
      rawAmount,
      preparation.decimals,
    ),
  );
}
