import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, test } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { scenarioAdapter } from "../api/client";
import { App } from "../App";

beforeEach(async () => {
  await scenarioAdapter.reset();
});

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);
}

test.each([
  ["/supplier", "Alpha Components"],
  ["/buyer", "Prime Mobility"],
  ["/investor", "Nova Capital"],
  ["/dev/demo", "개발자 데모 제어"],
])("renders %s", async (path, expectedText) => {
  renderAt(path);

  expect(await screen.findByText(expectedText)).toBeInTheDocument();
});
