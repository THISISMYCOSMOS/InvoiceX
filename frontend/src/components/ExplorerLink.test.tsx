import { render, screen } from "@testing-library/react";
import { ExplorerLink } from "./ExplorerLink";

test("links a transaction to the explorer URL the backend produced", () => {
  render(<ExplorerLink explorerUrl="https://explorer.solana.com/tx/5ig?cluster=testnet" />);

  expect(screen.getByRole("link", { name: "View on Solana Explorer" })).toHaveAttribute(
    "href",
    "https://explorer.solana.com/tx/5ig?cluster=testnet",
  );
});
