import { createMockAdapter } from "./adapters/mockAdapter";
import { createHttpAdapter } from "./adapters/httpAdapter";

export const isMockApi = import.meta.env.VITE_USE_MOCK_API !== "false";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

export const scenarioAdapter = isMockApi
  ? createMockAdapter()
  : createHttpAdapter(fetch, `${apiBaseUrl.replace(/\/$/, "")}/api/v1`);
