import { useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getAuthMe, type CompanyType } from "../api/onboarding.api";
import { isMockApi } from "../api/client";
import { AppLayout } from "../components/AppLayout";
import { type CurrentPrivyAccount } from "./currentAccount";
import { CurrentAccountProvider } from "./CurrentAccountProvider";
import { getDemoSession } from "./demoAccounts";
import { useSignupAuth } from "./SignupAuthContext";

export function AuthenticatedAppLayout({ children }: { children: ReactNode }) {
  const auth = useSignupAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [account, setAccount] = useState<CurrentPrivyAccount>();
  const [checking, setChecking] = useState(!isMockApi && !getDemoSession()?.accessToken);

  useEffect(() => {
    let active = true;
    const demoSession = getDemoSession();
    if (isMockApi || demoSession?.accessToken) {
      setChecking(false);
      setAccount(undefined);
      return () => { active = false; };
    }
    if (!auth.ready) return () => { active = false; };
    if (!auth.authenticated) {
      setChecking(false);
      navigate("/login", { replace: true });
      return () => { active = false; };
    }

    setChecking(true);
    void (async () => {
      try {
        const token = await auth.getAccessToken();
        if (!token) throw new Error("Privy session is unavailable");
        const profile = await getAuthMe(token);
        if (!active) return;
        if (
          profile.onboardingStatus !== "COMPLETED"
          || !profile.company
          || !profile.embeddedWallet
        ) {
          navigate("/signup", { replace: true });
          return;
        }
        const rolePath = profile.nextPath;
        if (!location.pathname.startsWith(rolePath)) {
          navigate(rolePath, { replace: true });
        }
        setAccount({
          countryCode: profile.company.countryCode,
          registrationNumber: profile.company.registrationNumber,
          companyName: profile.company.name,
          role: profile.company.type as CompanyType,
          userEmail: profile.user.email,
          userName: profile.user.name,
          userTitle: profile.user.title,
          walletAddress: profile.embeddedWallet.address,
        });
      } catch {
        if (active) navigate("/login", { replace: true });
      } finally {
        if (active) setChecking(false);
      }
    })();
    return () => { active = false; };
  }, [auth, location.pathname, navigate]);

  if (checking) {
    return <main className="screen-stage"><p>로그인 정보를 확인하는 중입니다...</p></main>;
  }

  const logout = account
    ? async () => {
        await auth.logout();
        navigate("/login", { replace: true });
      }
    : undefined;

  return (
    <CurrentAccountProvider account={account}>
      <AppLayout currentPrivyAccount={account} onPrivyLogout={logout}>
        {children}
      </AppLayout>
    </CurrentAccountProvider>
  );
}
