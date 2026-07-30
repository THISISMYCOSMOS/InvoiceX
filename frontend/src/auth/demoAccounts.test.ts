import { expect, test } from "vitest";
import { authenticateDemoAccount, DEMO_ACCOUNTS } from "./demoAccounts";

test("pre-seeds the three requested local demo accounts", () => {
  expect(DEMO_ACCOUNTS).toEqual([
    { role: "Supplier", email: "supplier@company.com", password: "supplier" },
    { role: "Buyer", email: "buyer@company.com", password: "buyer" },
    { role: "Investor", email: "invester@company.com", password: "invester" },
  ]);
});

test("requires the credential to match the selected company role", () => {
  expect(authenticateDemoAccount("Supplier", "supplier@company.com", "supplier")).toBeTruthy();
  expect(authenticateDemoAccount("Buyer", "buyer@company.com", "buyer")).toBeTruthy();
  expect(authenticateDemoAccount("Investor", "invester@company.com", "invester")).toBeTruthy();
  expect(authenticateDemoAccount("Supplier", "buyer@company.com", "buyer")).toBeUndefined();
});
