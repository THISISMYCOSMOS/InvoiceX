import { Link } from "react-router-dom";
import { useLanguage } from "../i18n/LanguageContext";

export function RoleSwitcher() {
  const { t } = useLanguage();
  if (!import.meta.env.DEV) {
    return null;
  }

  return (
    <nav aria-label={t("Development role switcher", "개발 역할 전환")}>
      <Link to="/supplier">{t("Supplier", "공급기업")}</Link>{" "}
      <Link to="/buyer">{t("Buyer", "구매기업")}</Link>{" "}
      <Link to="/investor">{t("Investor", "투자기관")}</Link>{" "}
      <Link to="/dev/demo">{t("Demo controls", "데모 제어")}</Link>
    </nav>
  );
}
