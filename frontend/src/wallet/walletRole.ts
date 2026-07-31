export type WalletRole = "SUPPLIER" | "INVESTOR" | null;

export function walletRoleFromPath(pathname: string): WalletRole {
  if (pathname.startsWith("/supplier")) return "SUPPLIER";
  if (pathname.startsWith("/investor")) return "INVESTOR";
  return null;
}
