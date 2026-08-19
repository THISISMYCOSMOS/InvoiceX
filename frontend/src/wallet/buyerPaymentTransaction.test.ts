// @vitest-environment node

import {
  ASSOCIATED_TOKEN_PROGRAM_ID,
  decodeTransferCheckedInstruction,
  TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import { Keypair } from "@solana/web3.js";
import { describe, expect, test } from "vitest";
import type { BuyerPaymentPreparation } from "../types/invoice";
import { buildBuyerPaymentTransaction } from "./buyerPaymentTransaction";

describe("buyer payment transaction", () => {
  test("creates the settlement token account and transfers the exact invoice amount", () => {
    const buyer = Keypair.fromSeed(new Uint8Array(32).fill(3)).publicKey;
    const settlement = Keypair.fromSeed(new Uint8Array(32).fill(4)).publicKey;
    const preparation: BuyerPaymentPreparation = {
      invoiceId: "INV-2026-001",
      buyerWalletAddress: buyer.toBase58(),
      settlementWalletAddress: settlement.toBase58(),
      usdcMintAddress: "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
      amountUsdc: 96_000,
      amountBaseUnits: 96_000_000_000,
      decimals: 6,
      dueDate: "2026-09-18",
      demoDueDateBypass: true,
    };

    const transaction = buildBuyerPaymentTransaction(preparation, buyer);

    expect(transaction.instructions).toHaveLength(2);
    expect(transaction.instructions[0].programId.equals(ASSOCIATED_TOKEN_PROGRAM_ID)).toBe(true);
    expect(transaction.instructions[1].programId.equals(TOKEN_PROGRAM_ID)).toBe(true);
    const transfer = decodeTransferCheckedInstruction(transaction.instructions[1]);
    expect(transfer.data.amount).toBe(96_000_000_000n);
    expect(transfer.data.decimals).toBe(6);
    expect(transfer.keys.owner.pubkey.equals(buyer)).toBe(true);
  });
});
