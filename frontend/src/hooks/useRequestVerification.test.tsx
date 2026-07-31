import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { test } from "vitest";
import { scenarioAdapter } from "../api/client";
import { useRequestVerification } from "./useRequestVerification";

test("moves the reviewed invoice into buyer verification", async () => {
  await scenarioAdapter.reset();
  await scenarioAdapter.submitInvoiceDocuments(new FormData());
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  const { result } = renderHook(() => useRequestVerification(), { wrapper });

  await act(() => result.current.mutateAsync("INV-2026-001"));

  expect((await scenarioAdapter.getInvoice("INV-2026-001")).status).toBe("BUYER_REVIEW");
});
