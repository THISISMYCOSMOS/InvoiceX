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
  const buyerTokenAccount = getAssociatedTokenAddressSync(mint, buyer);
  const transaction = new Transaction();
  for (const transfer of preparation.transfers) {
    const recipient = new PublicKey(transfer.recipientWalletAddress);
    const recipientTokenAccount = getAssociatedTokenAddressSync(mint, recipient);
    transaction.add(
      createAssociatedTokenAccountIdempotentInstruction(
        buyer,
        recipientTokenAccount,
        recipient,
        mint,
      ),
      createTransferCheckedInstruction(
        buyerTokenAccount,
        mint,
        recipientTokenAccount,
        buyer,
        BigInt(transfer.amountBaseUnits),
        preparation.decimals,
      ),
    );
  }
  return transaction;
}
