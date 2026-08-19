import {
  getAccessToken as getPrivyAccessToken,
  PrivyProvider,
  useLoginWithEmail,
  usePrivy,
} from "@privy-io/react-auth";
import { useSignMessage as usePrivySolanaSignMessage, useWallets as usePrivySolanaWallets } from "@privy-io/react-auth/solana";
import { createContext, useContext, type ReactNode } from "react";

type SignupAuthContextValue = {
  authenticated: boolean;
  configured: boolean;
  ready: boolean;
  getAccessToken: () => Promise<string | null>;
  logout: () => Promise<void>;
  sendCode: (email: string) => Promise<void>;
  verifyCode: (code: string) => Promise<void>;
  embeddedSolanaWalletReady: boolean;
  signEmbeddedSolanaMessage: (walletAddress: string, message: Uint8Array) => Promise<Uint8Array>;
};

const disabledContext: SignupAuthContextValue = {
  authenticated: false,
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
  signEmbeddedSolanaMessage: async () => {
    throw new Error("Privy 임베디드 지갑을 사용할 수 없습니다.");
  },
};

const SignupAuthContext = createContext<SignupAuthContextValue>(disabledContext);

function ConfiguredSignupAuthProvider({ children }: { children: ReactNode }) {
  const { authenticated, logout, ready } = usePrivy();
  const { loginWithCode, sendCode } = useLoginWithEmail();
  const { ready: embeddedSolanaWalletReady, wallets: embeddedSolanaWallets } = usePrivySolanaWallets();
  const { signMessage: signWithEmbeddedSolanaWallet } = usePrivySolanaSignMessage();

  return (
    <SignupAuthContext.Provider
      value={{
        authenticated,
        configured: true,
        ready,
        getAccessToken: getPrivyAccessToken,
        logout,
        sendCode: async (email) => sendCode({ email }),
        verifyCode: async (code) => loginWithCode({ code }),
        embeddedSolanaWalletReady,
        signEmbeddedSolanaMessage: async (walletAddress, message) => {
          const wallet = embeddedSolanaWallets.find((candidate) => candidate.address === walletAddress);
          if (!wallet) throw new Error("현재 계정의 Privy 임베디드 지갑을 찾을 수 없습니다.");
          const { signature } = await signWithEmbeddedSolanaWallet({ wallet, message });
          return signature;
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
    <PrivyProvider appId={appId} config={{ loginMethods: ["email"] }}>
      <ConfiguredSignupAuthProvider>{children}</ConfiguredSignupAuthProvider>
    </PrivyProvider>
  );
}

// Hook export intentionally shares the provider's single private context.
// eslint-disable-next-line react-refresh/only-export-components
export function useSignupAuth(): SignupAuthContextValue {
  return useContext(SignupAuthContext);
}
