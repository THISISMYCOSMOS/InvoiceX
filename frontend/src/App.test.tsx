import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "./App";

test("renders the InvoiceX application heading", () => {
  render(<App />, { wrapper: MemoryRouter });

  expect(screen.getByRole("heading", { name: "InvoiceX" })).toBeInTheDocument();
});
