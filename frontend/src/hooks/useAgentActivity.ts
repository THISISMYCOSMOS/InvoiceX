import { useQuery } from "@tanstack/react-query";
import { isMockApi } from "../api/client";
import { rwaApi } from "../api/rwa.api";

export function useAgentActivity(invoiceId: string, role: "Supplier" | "Investor") {
  return useQuery({
    queryKey: ["agentActivity", invoiceId, role],
    queryFn: () => rwaApi.getAgentActivity(invoiceId, role),
    enabled: Boolean(invoiceId) && !isMockApi,
    refetchInterval: 3_000,
  });
}
