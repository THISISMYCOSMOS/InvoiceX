import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { vi } from "vitest";
import { scenarioAdapter } from "../api/client";
import { useBuyerConfirm } from "./useBuyerConfirm";

test("invalidates invoice and verification queries after buyer confirmation", async () => {
  await scenarioAdapter.reset();
  await scenarioAdapter.analyzeInvoice("INV-2026-001");
  await scenarioAdapter.requestVerification("INV-2026-001");
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  const { result } = renderHook(() => useBuyerConfirm(), { wrapper });

  await act(() => result.current.mutateAsync("VER-2026-001"));

  expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["invoice", "INV-2026-001"] });
  expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["verifications"] });
});
