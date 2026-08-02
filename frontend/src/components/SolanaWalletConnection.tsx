import { Copy, LinkSimple, Plug, Wallet as WalletIcon } from "@phosphor-icons/react";
import { useWallet, type Wallet as AdapterWallet } from "@solana/wallet-adapter-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useConnectedSolanaWallet } from "../hooks/useConnectedSolanaWallet";
import { useDevnetUsdcBalance } from "../hooks/useDevnetUsdcBalance";
import { useLanguage } from "../i18n/LanguageContext";
import { shortenWalletAddress, walletErrorMessage, type WalletConnectionStatus } from "../wallet/walletConnectionUtils";

interface SolanaWalletConnectionProps {
  title: string;
  description: string;
  onWalletConnected?: (address: string) => void | Promise<void>;
  onWalletDisconnected?: () => void;
}

const supportedWalletNames = ["Phantom", "Solflare", "Backpack"] as const;

function walletByName(wallets: AdapterWallet[], walletName: string): AdapterWallet | undefined {
  return wallets.find(({ adapter }) => adapter.name === walletName);
}

export function SolanaWalletConnection({
  title,
  description,
  onWalletConnected,
  onWalletDisconnected,
}: SolanaWalletConnectionProps) {
  const { connect, disconnect, select, wallet, wallets } = useWallet();
  const { connected, publicKey, walletName } = useConnectedSolanaWallet();
  const walletUsdcBalance = useDevnetUsdcBalance();
  const { t } = useLanguage();
  const [isChooserOpen, setIsChooserOpen] = useState(false);
  const [pendingWalletName, setPendingWalletName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const connectedAddressRef = useRef<string | null>(null);
  const isManualDisconnectRef = useRef(false);
  const reconnectAttemptedWalletRef = useRef<string | null>(null);

  const supportedWallets = useMemo(() => {
    const knownWallets = supportedWalletNames.map((name) => ({ name, wallet: walletByName(wallets, name) }));
    const additionalWallets = wallets
      .filter(({ adapter }) => !supportedWalletNames.includes(adapter.name as (typeof supportedWalletNames)[number]))
      .map((availableWallet) => ({ name: availableWallet.adapter.name, wallet: availableWallet }));

    return [...knownWallets, ...additionalWallets];
  }, [wallets]);

  const status: WalletConnectionStatus = error
    ? "ERROR"
    : connected && publicKey
      ? "CONNECTED"
      : pendingWalletName
        ? "CONNECTING"
        : "DISCONNECTED";
  const displayedUsdcBalance = walletUsdcBalance.balanceUsdc?.toLocaleString(undefined, {
    maximumFractionDigits: 6,
  });

  useEffect(() => {
    if (!wallet || connected) {
      return;
    }

    const selectedWalletName = wallet.adapter.name;
    const isExplicitConnection = pendingWalletName === selectedWalletName;
    if (!isExplicitConnection && reconnectAttemptedWalletRef.current === selectedWalletName) {
      return;
    }

    let isCurrent = true;
    reconnectAttemptedWalletRef.current = selectedWalletName;
    void connect()
      .catch((connectionError: unknown) => {
        if (isCurrent) {
          setError(walletErrorMessage(connectionError));
          select(null);
        }
      })
      .finally(() => {
        if (isCurrent) {
          setPendingWalletName(null);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [connect, connected, pendingWalletName, select, wallet]);

  useEffect(() => {
    if (connected && publicKey && connectedAddressRef.current !== publicKey) {
      connectedAddressRef.current = publicKey;
      setError(null);
      void Promise.resolve(onWalletConnected?.(publicKey)).catch(() => {
        setError("지갑 연결 정보를 저장하지 못했습니다. 다시 연결해 주세요.");
      });
      return;
    }

    if (!connected && connectedAddressRef.current) {
      const wasManualDisconnect = isManualDisconnectRef.current;
      connectedAddressRef.current = null;
      onWalletDisconnected?.();
      if (!wasManualDisconnect) {
        setError("지갑 연결이 해제되었습니다. 다시 연결해 주세요.");
      }
      isManualDisconnectRef.current = false;
    }
  }, [connected, onWalletConnected, onWalletDisconnected, publicKey]);

  const chooseWallet = (name: string, availableWallet?: AdapterWallet) => {
    setError(null);
    setCopied(false);

    if (!availableWallet) {
      setIsChooserOpen(false);
      setError("지원하는 Solana 지갑을 설치한 뒤 다시 시도해 주세요.");
      return;
    }

    setPendingWalletName(name);
    reconnectAttemptedWalletRef.current = null;
    select(availableWallet.adapter.name);
    setIsChooserOpen(false);
  };

  const copyWalletAddress = async () => {
    if (!publicKey) return;

    try {
      if (!window.navigator.clipboard?.writeText) throw new Error("Clipboard is unavailable");
      await window.navigator.clipboard.writeText(publicKey);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setError("지갑 주소를 복사하지 못했습니다. 다시 시도해 주세요.");
    }
  };

  const disconnectWallet = async () => {
    isManualDisconnectRef.current = true;
    setPendingWalletName(null);
    setIsChooserOpen(false);
    try {
      await disconnect();
    } catch {
      isManualDisconnectRef.current = false;
      setError("지갑 연결을 해제하지 못했습니다. 다시 시도해 주세요.");
    } finally {
      select(null);
    }
  };

  return (
    <article className="wallet-card solana-wallet-connection">
      <header className="settings-card__header">
        <span className="settings-card__icon settings-card__icon--navy" aria-hidden="true">
          <WalletIcon size={18} weight="fill" />
        </span>
        <div>
          <h2>{title}</h2>
          <p>Solana Devnet</p>
        </div>
        <span className={`wallet-status ${status === "CONNECTED" ? "is-connected" : status === "ERROR" ? "is-error" : ""}`}>
          <span aria-hidden="true" />
          {status === "CONNECTED"
            ? t("Connected", "연결됨")
            : status === "CONNECTING"
              ? t("Connecting", "연결 중")
              : status === "ERROR"
                ? t("Connection error", "연결 오류")
              : t("Not connected", "연결 안 됨")}
        </span>
      </header>

      {status === "CONNECTED" && publicKey ? (
        <>
          <p className="wallet-connection-description">{description}</p>
          <div className="wallet-address-panel">
            <div>
              <span>{t("Connected wallet", "연결된 지갑")}</span>
              <strong>{walletName ?? t("Solana wallet", "Solana 지갑")}</strong>
              <span className="wallet-address-value" title={publicKey}>{shortenWalletAddress(publicKey)}</span>
            </div>
            <button type="button" className="wallet-copy-button" onClick={copyWalletAddress}>
              <Copy size={14} weight="bold" aria-hidden="true" />
              {copied ? t("Copied", "복사됨") : t("Copy address", "주소 복사")}
            </button>
          </div>

          <div className="wallet-metrics">
            <div>
              <span>{t("Available balance", "사용 가능 잔액")}</span>
              <strong>
                {walletUsdcBalance.isLoading
                  ? t("Loading", "조회 중")
                  : walletUsdcBalance.isError
                    ? t("Unavailable", "조회 실패")
                    : displayedUsdcBalance ?? "—"} <small>USDC</small>
              </strong>
            </div>
            <div>
              <span>{t("Network", "네트워크")}</span>
              <strong>Solana Devnet</strong>
            </div>
            <div>
              <span>{t("Connection status", "연결 상태")}</span>
              <strong>{t("Connected", "연결됨")}</strong>
            </div>
          </div>

          <div className="wallet-card__footer">
            <p>{walletUsdcBalance.isError
              ? t("Unable to load the Devnet USDC balance. Try again shortly.", "Devnet USDC 잔액을 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.")
              : t("Displays the Devnet USDC balance of the connected external wallet.", "연결된 외부 지갑의 Devnet USDC 잔액을 표시합니다.")}</p>
            <button type="button" className="secondary-button wallet-action" onClick={disconnectWallet}>
              <Plug size={14} weight="bold" aria-hidden="true" />
              {t("Disconnect wallet", "지갑 연결 해제")}
            </button>
          </div>
        </>
      ) : (
        <div className="wallet-empty-state">
          <span aria-hidden="true">
            <LinkSimple size={25} weight="bold" />
          </span>
          <h3>{t("No wallet connected", "연결된 지갑 없음")}</h3>
          <p>{description}</p>
          <button
            type="button"
            className="primary-button wallet-connect-button"
            disabled={status === "CONNECTING"}
            onClick={() => { setError(null); setIsChooserOpen(true); }}
          >
            <WalletIcon size={15} weight="fill" aria-hidden="true" />
            {status === "CONNECTING" ? t("Connecting wallet...", "지갑 연결 중...") : t("Connect Solana wallet", "Solana 지갑 연결")}
          </button>
        </div>
      )}

      {error && <p className="wallet-error" role="alert">{error}</p>}

      {isChooserOpen && (
        <section className="wallet-chooser" aria-label={t("Choose a Solana wallet", "Solana 지갑 선택")} role="dialog">
          <div>
            <strong>{t("Choose a wallet", "지갑 선택")}</strong>
            <button type="button" aria-label={t("Cancel wallet connection", "지갑 연결 취소")} onClick={() => setIsChooserOpen(false)}>×</button>
          </div>
          <p>{t("Select an installed wallet to continue.", "설치된 지갑을 선택해 연결을 계속하세요.")}</p>
          <ul>
            {supportedWallets.map(({ name, wallet: availableWallet }) => (
              <li key={name}>
                <button type="button" onClick={() => chooseWallet(name, availableWallet)}>
                  <span>{name}</span>
                  <small>{availableWallet ? t("Connect", "연결") : t("Install required", "설치 필요")}</small>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
