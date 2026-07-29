import { useQuery } from "@tanstack/react-query";
import { investorApi } from "../api/investor.api";
import { queryKeys } from "./queryKeys";

export function useInvestorDashboard() {
  return useQuery({ queryKey: queryKeys.investorDashboard, queryFn: investorApi.getDashboard });
}
