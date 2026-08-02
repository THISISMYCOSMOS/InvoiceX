export type WalletRole = "SUPPLIER" | "BUYER" | "INVESTOR" | null;

export function walletRoleFromPath(pathname: string): WalletRole {
  if (pathname.startsWith("/supplier")) return "SUPPLIER";
  if (pathname.startsWith("/buyer")) return "BUYER";
  if (pathname.startsWith("/investor")) return "INVESTOR";
  return null;
}
