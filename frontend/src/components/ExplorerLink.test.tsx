import { render, screen } from "@testing-library/react";
import { ExplorerLink } from "./ExplorerLink";

test("links a transaction to Solana Explorer devnet", () => {
  render(<ExplorerLink signature="5ig" />);

  expect(screen.getByRole("link", { name: "View on Solana Explorer" })).toHaveAttribute(
    "href",
    "https://explorer.solana.com/tx/5ig?cluster=devnet",
  );
});
