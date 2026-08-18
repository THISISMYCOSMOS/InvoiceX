import {
  getAccessToken as getPrivyAccessToken,
  PrivyProvider,
  useLoginWithEmail,
  usePrivy,
} from "@privy-io/react-auth";
import { createContext, useContext, type ReactNode } from "react";

type SignupAuthContextValue = {
  authenticated: boolean;
  configured: boolean;
  ready: boolean;
  getAccessToken: () => Promise<string | null>;
  sendCode: (email: string) => Promise<void>;
  verifyCode: (code: string) => Promise<void>;
};

const disabledContext: SignupAuthContextValue = {
  authenticated: false,
  configured: false,
  ready: true,
  getAccessToken: async () => null,
  sendCode: async () => {
    throw new Error("Privy App ID가 설정되지 않았습니다.");
  },
  verifyCode: async () => {
    throw new Error("Privy App ID가 설정되지 않았습니다.");
  },
};

const SignupAuthContext = createContext<SignupAuthContextValue>(disabledContext);

function ConfiguredSignupAuthProvider({ children }: { children: ReactNode }) {
  const { authenticated, ready } = usePrivy();
  const { loginWithCode, sendCode } = useLoginWithEmail();

  return (
    <SignupAuthContext.Provider
      value={{
        authenticated,
        configured: true,
        ready,
        getAccessToken: getPrivyAccessToken,
        sendCode: async (email) => sendCode({ email }),
        verifyCode: async (code) => loginWithCode({ code }),
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
