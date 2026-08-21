import {
  getAccessToken as getPrivyAccessToken,
  PrivyProvider,
  useLoginWithEmail,
  usePrivy,
} from "@privy-io/react-auth";
import {
  defaultSolanaRpcsPlugin,
  useCreateWallet as useCreatePrivySolanaWallet,
  useSignMessage as usePrivySolanaSignMessage,
  useSignTransaction as usePrivySolanaSignTransaction,
  useWallets as usePrivySolanaWallets,
} from "@privy-io/react-auth/solana";
import { createContext, useContext, type ReactNode } from "react";

type SignupAuthContextValue = {
  authenticated: boolean;
  authenticatedEmail: string | null;
  configured: boolean;
  ready: boolean;
  getAccessToken: () => Promise<string | null>;
  logout: () => Promise<void>;
  sendCode: (email: string, options?: { disableSignup?: boolean }) => Promise<void>;
  verifyCode: (code: string) => Promise<void>;
  embeddedSolanaWalletReady: boolean;
  ensureEmbeddedSolanaWallet: () => Promise<{ address: string; created: boolean }>;
  hasEmbeddedSolanaWallet: (walletAddress: string) => boolean;
  signEmbeddedSolanaMessage: (walletAddress: string, message: Uint8Array) => Promise<Uint8Array>;
  signEmbeddedSolanaTransaction: (walletAddress: string, transaction: Uint8Array) => Promise<Uint8Array>;
};

const disabledContext: SignupAuthContextValue = {
  authenticated: false,
  authenticatedEmail: null,
  configured: false,
  ready: true,
  getAccessToken: async () => null,
  logout: async () => undefined,
  sendCode: async () => {
    throw new Error("Privy App ID가 설정되지 않았습니다.");
  },
  verifyCode: async () => {
    throw new Error("Privy App ID가 설정되지 않았습니다.");
  },
  embeddedSolanaWalletReady: false,
  ensureEmbeddedSolanaWallet: async () => {
    throw new Error("Privy 임베디드 지갑을 사용할 수 없습니다.");
  },
  hasEmbeddedSolanaWallet: () => false,
  signEmbeddedSolanaMessage: async () => {
    throw new Error("Privy 임베디드 지갑을 사용할 수 없습니다.");
  },
  signEmbeddedSolanaTransaction: async () => {
    throw new Error("Privy 임베디드 지갑을 사용할 수 없습니다.");
  },
};

const SignupAuthContext = createContext<SignupAuthContextValue>(disabledContext);

function ConfiguredSignupAuthProvider({ children }: { children: ReactNode }) {
  const { authenticated, logout, ready, user } = usePrivy();
  const { loginWithCode, sendCode } = useLoginWithEmail();
  const { ready: embeddedSolanaWalletReady, wallets: embeddedSolanaWallets } = usePrivySolanaWallets();
  const { createWallet: createEmbeddedSolanaWallet } = useCreatePrivySolanaWallet();
  const { signMessage: signWithEmbeddedSolanaWallet } = usePrivySolanaSignMessage();
  const { signTransaction: signTransactionWithEmbeddedSolanaWallet } = usePrivySolanaSignTransaction();

  return (
    <SignupAuthContext.Provider
      value={{
        authenticated,
        authenticatedEmail: user?.email?.address?.trim().toLowerCase() ?? null,
        configured: true,
        ready,
        getAccessToken: getPrivyAccessToken,
        logout,
        sendCode: async (email, options) => sendCode({
          email,
          disableSignup: options?.disableSignup,
        }),
        verifyCode: async (code) => loginWithCode({ code }),
        embeddedSolanaWalletReady,
        ensureEmbeddedSolanaWallet: async () => {
          if (!embeddedSolanaWalletReady) {
            throw new Error("Privy 임베디드 지갑을 확인하는 중입니다. 잠시 후 다시 시도해 주세요.");
          }
          const existing = embeddedSolanaWallets[0];
          if (existing) return { address: existing.address, created: false };
          const { wallet } = await createEmbeddedSolanaWallet();
          return { address: wallet.address, created: true };
        },
        hasEmbeddedSolanaWallet: (walletAddress) => (
          embeddedSolanaWallets.some((candidate) => candidate.address === walletAddress)
        ),
        signEmbeddedSolanaMessage: async (walletAddress, message) => {
          const wallet = embeddedSolanaWallets.find((candidate) => candidate.address === walletAddress);
          if (!wallet) throw new Error("현재 계정의 Privy 임베디드 지갑을 찾을 수 없습니다.");
          const { signature } = await signWithEmbeddedSolanaWallet({ wallet, message });
          return signature;
        },
        signEmbeddedSolanaTransaction: async (walletAddress, transaction) => {
          const wallet = embeddedSolanaWallets.find((candidate) => candidate.address === walletAddress);
          if (!wallet) throw new Error("현재 계정의 Privy 임베디드 지갑을 찾을 수 없습니다.");
          const { signedTransaction } = await signTransactionWithEmbeddedSolanaWallet({
            wallet,
            transaction,
            chain: "solana:devnet",
          });
          return signedTransaction;
        },
      }}
    >
      {children}
    </SignupAuthContext.Provider>
  );
}

export function SignupAuthProvider({ children }: { children: ReactNode }) {
  const appId = import.meta.env.VITE_PRIVY_APP_ID?.trim();
  if (!appId) {
    return (
      <SignupAuthContext.Provider value={disabledContext}>
        {children}
      </SignupAuthContext.Provider>
    );
  }

  return (
    <PrivyProvider
      appId={appId}
      config={{
        loginMethods: ["email"],
        plugins: [defaultSolanaRpcsPlugin()],
      }}
    >
      <ConfiguredSignupAuthProvider>{children}</ConfiguredSignupAuthProvider>
    </PrivyProvider>
  );
}

// Hook export intentionally shares the provider's single private context.
// eslint-disable-next-line react-refresh/only-export-components
export function useSignupAuth(): SignupAuthContextValue {
  return useContext(SignupAuthContext);
}
