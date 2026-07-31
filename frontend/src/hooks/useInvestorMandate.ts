import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { investorApi } from "../api/investor.api";
import type { InvestorMandate } from "../types/invoice";
import { queryKeys } from "./queryKeys";

export function useInvestorMandate() {
  const queryClient = useQueryClient();
  const mandate = useQuery({
    queryKey: queryKeys.investorMandate,
    queryFn: investorApi.getMandate,
  });
  const save = useMutation({
    mutationFn: (value: InvestorMandate) => investorApi.saveMandate(value),
    onSuccess: async (saved) => {
      queryClient.setQueryData(queryKeys.investorMandate, saved);
      await queryClient.invalidateQueries({ queryKey: queryKeys.investorDashboard });
    },
  });

  return { mandate, save };
}
