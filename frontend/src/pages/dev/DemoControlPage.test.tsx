import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { scenarioAdapter } from "../../api/client";
import { DemoControlPage } from "./DemoControlPage";

test("enables buyer confirmation after document analysis succeeds", async () => {
  await scenarioAdapter.reset();
  const user = userEvent.setup();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={queryClient}><DemoControlPage /></QueryClientProvider>);

  expect(await screen.findByRole("button", { name: "Buyer Confirm" })).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Document Agent 분석 실행" }));

  expect(await screen.findByRole("button", { name: "Buyer Confirm" })).toBeEnabled();
});
