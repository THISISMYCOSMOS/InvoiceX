import { Navigate, Route, Routes } from "react-router-dom";
import { NewInvoicePage } from "./pages/supplier/NewInvoicePage";
import { SupplierCompanyWalletPage } from "./pages/supplier/SupplierCompanyWalletPage";
import { SupplierFundsConversionPage } from "./pages/supplier/SupplierFundsConversionPage";
import { SupplierDashboardPage } from "./pages/supplier/SupplierDashboardPage";
import { SupplierInvoiceDetailPage } from "./pages/supplier/SupplierInvoiceDetailPage";
import { BuyerDashboardPage } from "./pages/buyer/BuyerDashboardPage";
import { BuyerInvoiceDetailPage } from "./pages/buyer/BuyerInvoiceDetailPage";
import { BuyerPaymentListPage, BuyerVerificationListPage } from "./pages/buyer/BuyerInvoiceListPage";
import { BuyerProfilePage } from "./pages/buyer/BuyerProfilePage";
import { InvestorActivityPage } from "./pages/investor/InvestorActivityPage";
import { InvestorActivityListPage } from "./pages/investor/InvestorActivityListPage";
import { InvestorDashboardPage } from "./pages/investor/InvestorDashboardPage";
import { InvestorInvestmentPolicyPage } from "./pages/investor/InvestorInvestmentPolicyPage";
import { InvestorProfilePage } from "./pages/investor/InvestorProfilePage";
import { InvestorVaultPage } from "./pages/investor/InvestorVaultPage";
import { DemoControlPage } from "./pages/dev/DemoControlPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { LanguageProvider } from "./i18n/LanguageContext";
import { SolanaWalletProvider } from "./wallet/SolanaWalletProvider";
import { WalletRoleSwitchGuard } from "./wallet/WalletRoleSwitchGuard";
import { AuthenticatedAppLayout } from "./auth/AuthenticatedAppLayout";

export function App() {
  return (
    <SolanaWalletProvider>
      <WalletRoleSwitchGuard>
        <LanguageProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route
              path="*"
              element={(
                <AuthenticatedAppLayout>
                  <Routes>
                    <Route path="/supplier" element={<SupplierDashboardPage />} />
                    <Route path="/supplier/company-wallet" element={<SupplierCompanyWalletPage />} />
                    <Route path="/supplier/funds-conversion" element={<SupplierFundsConversionPage />} />
                    <Route path="/supplier/invoices/new" element={<NewInvoicePage />} />
                    <Route path="/supplier/invoices/:invoiceId" element={<SupplierInvoiceDetailPage />} />
                    <Route path="/buyer" element={<BuyerDashboardPage />} />
                    <Route path="/buyer/verification" element={<BuyerVerificationListPage />} />
                    <Route path="/buyer/payment" element={<BuyerPaymentListPage />} />
                    <Route path="/buyer/invoices/:invoiceId" element={<BuyerInvoiceDetailPage />} />
                    <Route path="/buyer/profile" element={<BuyerProfilePage />} />
                    <Route path="/investor" element={<InvestorDashboardPage />} />
                    <Route path="/investor/activities" element={<InvestorActivityListPage />} />
                    <Route path="/investor/activities/:invoiceId" element={<InvestorActivityPage />} />
                    <Route path="/investor/investment-policy" element={<InvestorInvestmentPolicyPage />} />
                    <Route path="/investor/funds-conversion" element={<SupplierFundsConversionPage variant="investor" />} />
                    <Route path="/investor/vault" element={<InvestorVaultPage />} />
                    <Route path="/investor/profile" element={<InvestorProfilePage />} />
                    <Route path="/dev/demo" element={<DemoControlPage />} />
                    <Route path="*" element={<Navigate to="/login" replace />} />
                  </Routes>
                </AuthenticatedAppLayout>
              )}
            />
          </Routes>
        </LanguageProvider>
      </WalletRoleSwitchGuard>
    </SolanaWalletProvider>
  );
}
