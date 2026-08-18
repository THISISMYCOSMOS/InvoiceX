import { getAccessToken as getPrivyAccessToken } from "@privy-io/react-auth";
import { getDemoSession } from "./demoAccounts";

export async function getAuthorizationHeader(): Promise<HeadersInit> {
  const demoToken = getDemoSession()?.accessToken;
  if (demoToken) return { Authorization: `Bearer ${demoToken}` };

  try {
    const privyToken = await getPrivyAccessToken();
    return privyToken ? { Authorization: `Bearer ${privyToken}` } : {};
  } catch {
    // Unit tests and browser-only mock mode intentionally run without PrivyProvider.
    return {};
  }
}
