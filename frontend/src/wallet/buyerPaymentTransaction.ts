import {
  createAssociatedTokenAccountIdempotentInstruction,
  createTransferCheckedInstruction,
  getAssociatedTokenAddressSync,
} from "@solana/spl-token";
import { PublicKey, Transaction } from "@solana/web3.js";
import type { BuyerPaymentPreparation } from "../types/invoice";

export function buildBuyerPaymentTransaction(
  preparation: BuyerPaymentPreparation,
  buyer: PublicKey,
): Transaction {
  const mint = new PublicKey(preparation.usdcMintAddress);
  const settlement = new PublicKey(preparation.settlementWalletAddress);
  const buyerTokenAccount = getAssociatedTokenAddressSync(mint, buyer);
  const settlementTokenAccount = getAssociatedTokenAddressSync(mint, settlement);
  return new Transaction().add(
    createAssociatedTokenAccountIdempotentInstruction(
      buyer,
      settlementTokenAccount,
      settlement,
      mint,
    ),
    createTransferCheckedInstruction(
      buyerTokenAccount,
      mint,
      settlementTokenAccount,
      buyer,
      BigInt(preparation.amountBaseUnits),
      preparation.decimals,
    ),
  );
}
