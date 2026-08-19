import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getAuthMe, type CompanyType } from "../api/onboarding.api";
import { isMockApi } from "../api/client";
import { AppLayout } from "../components/AppLayout";
import { type CurrentPrivyAccount, type CurrentPrivyAccountUpdate } from "./currentAccount";
import { CurrentAccountProvider } from "./CurrentAccountProvider";
import { clearDemoSession, getDemoSession } from "./demoAccounts";
import { useSignupAuth } from "./SignupAuthContext";

export function AuthenticatedAppLayout({ children }: { children: ReactNode }) {
  const { authenticated, getAccessToken, ready } = useSignupAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const [account, setAccount] = useState<CurrentPrivyAccount>();
  const [rolePath, setRolePath] = useState<string>();
  const [checking, setChecking] = useState(() => {
    const session = getDemoSession();
    return !isMockApi && (!session?.accessToken || session.authMode === "MEMBER");
  });
  const updateAccount = useCallback((update: CurrentPrivyAccountUpdate) => {
    setAccount((current) => current ? { ...current, ...update } : current);
  }, []);

  useEffect(() => {
    let active = true;
    const demoSession = getDemoSession();
    if (isMockApi || (demoSession?.accessToken && demoSession.authMode !== "MEMBER")) {
      setChecking(false);
      setAccount(undefined);
      setRolePath(undefined);
      return () => { active = false; };
    }
    if (demoSession?.accessToken && demoSession.authMode === "MEMBER") {
      setChecking(true);
      void (async () => {
        try {
          const profile = await getAuthMe(demoSession.accessToken!);
          if (!active) return;
          if (
            profile.onboardingStatus !== "COMPLETED"
            || !profile.company
            || !profile.embeddedWallet
          ) {
            clearDemoSession();
            navigateRef.current("/login", { replace: true });
            return;
          }
          setAccount({
            countryCode: profile.company.countryCode,
            registrationNumber: profile.company.registrationNumber,
            companyName: profile.company.name,
            role: profile.company.type as CompanyType,
            userEmail: profile.user.email,
            userName: profile.user.name,
            userPhone: profile.user.phone,
            userTitle: profile.user.title,
            walletAddress: profile.embeddedWallet.address,
          });
          setRolePath(profile.nextPath);
        } catch {
          if (active) {
            clearDemoSession();
            navigate("/login", { replace: true });
          }
        } finally {
          if (active) setChecking(false);
        }
      })();
      return () => { active = false; };
    }
    if (!ready) return () => { active = false; };
    if (!authenticated) {
      setChecking(false);
      navigateRef.current("/login", { replace: true });
      return () => { active = false; };
    }

    setChecking(true);
    void (async () => {
      try {
        const token = await getAccessToken();
        if (!token) throw new Error("Privy session is unavailable");
        const profile = await getAuthMe(token);
        if (!active) return;
        if (
          profile.onboardingStatus !== "COMPLETED"
          || !profile.company
          || !profile.embeddedWallet
        ) {
          navigateRef.current("/signup", { replace: true });
          return;
        }
        setAccount({
          countryCode: profile.company.countryCode,
          registrationNumber: profile.company.registrationNumber,
          companyName: profile.company.name,
          role: profile.company.type as CompanyType,
          userEmail: profile.user.email,
          userName: profile.user.name,
          userPhone: profile.user.phone,
          userTitle: profile.user.title,
          walletAddress: profile.embeddedWallet.address,
        });
        setRolePath(profile.nextPath);
      } catch {
        if (active) navigateRef.current("/login", { replace: true });
      } finally {
        if (active) setChecking(false);
      }
    })();
    return () => { active = false; };
  }, [authenticated, getAccessToken, ready]);

  useEffect(() => {
    if (checking || !rolePath || location.pathname.startsWith(rolePath)) return;
    navigate(rolePath, { replace: true });
  }, [checking, location.pathname, navigate, rolePath]);

  if (checking) {
    return <main className="screen-stage"><p>로그인 정보를 확인하는 중입니다...</p></main>;
  }

  return (
    <CurrentAccountProvider account={account} onAccountChange={updateAccount}>
      <AppLayout currentPrivyAccount={account}>
        {children}
      </AppLayout>
    </CurrentAccountProvider>
  );
}
