// @vitest-environment node

import {
  ASSOCIATED_TOKEN_PROGRAM_ID,
  decodeTransferCheckedInstruction,
  TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import { Keypair } from "@solana/web3.js";
import { describe, expect, test } from "vitest";
import type { InvestorDepositPreparation } from "../types/invoice";
import { buildInvestorDepositTransaction } from "./investorDepositTransaction";

describe("investor deposit transaction", () => {
  test("creates the vault token account idempotently and transfers exact Devnet USDC", () => {
    const investor = Keypair.fromSeed(new Uint8Array(32).fill(1)).publicKey;
    const treasury = Keypair.fromSeed(new Uint8Array(32).fill(2)).publicKey;
    const preparation: InvestorDepositPreparation = {
      referenceId: "DEP-2026-001",
      investorWalletAddress: investor.toBase58(),
      treasuryWalletAddress: treasury.toBase58(),
      usdcMint: "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
      amountUsdc: 20,
      amountBaseUnits: "20000000",
      decimals: 6,
      network: "SOLANA_DEVNET",
    };

    const transaction = buildInvestorDepositTransaction(preparation, investor);

    expect(transaction.instructions).toHaveLength(2);
    expect(transaction.instructions[0].programId.equals(ASSOCIATED_TOKEN_PROGRAM_ID)).toBe(true);
    expect(transaction.instructions[1].programId.equals(TOKEN_PROGRAM_ID)).toBe(true);
    const transfer = decodeTransferCheckedInstruction(transaction.instructions[1]);
    expect(transfer.data.amount).toBe(20_000_000n);
    expect(transfer.data.decimals).toBe(6);
    expect(transfer.keys.owner.pubkey.equals(investor)).toBe(true);
  });
});
