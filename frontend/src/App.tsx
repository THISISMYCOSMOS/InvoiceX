import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { NewInvoicePage } from "./pages/supplier/NewInvoicePage";
import { SupplierDashboardPage } from "./pages/supplier/SupplierDashboardPage";
import { SupplierInvoiceDetailPage } from "./pages/supplier/SupplierInvoiceDetailPage";
import { BuyerDashboardPage } from "./pages/buyer/BuyerDashboardPage";
import { BuyerInvoiceDetailPage } from "./pages/buyer/BuyerInvoiceDetailPage";
import { InvestorActivityPage } from "./pages/investor/InvestorActivityPage";
import { InvestorDashboardPage } from "./pages/investor/InvestorDashboardPage";
import { InvestorSetupPage } from "./pages/investor/InvestorSetupPage";
import { DemoControlPage } from "./pages/dev/DemoControlPage";
import { LoginPage } from "./pages/LoginPage";
import { LanguageProvider } from "./i18n/LanguageContext";

export function App() {
  return (
    <LanguageProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="*"
          element={(
            <AppLayout>
              <Routes>
                <Route path="/supplier" element={<SupplierDashboardPage />} />
                <Route path="/supplier/invoices/new" element={<NewInvoicePage />} />
                <Route path="/supplier/invoices/:invoiceId" element={<SupplierInvoiceDetailPage />} />
                <Route path="/buyer" element={<BuyerDashboardPage />} />
                <Route path="/buyer/invoices/:invoiceId" element={<BuyerInvoiceDetailPage />} />
                <Route path="/investor" element={<InvestorDashboardPage />} />
                <Route path="/investor/setup" element={<InvestorSetupPage />} />
                <Route path="/investor/activities/:invoiceId" element={<InvestorActivityPage />} />
                <Route path="/dev/demo" element={<DemoControlPage />} />
                <Route path="*" element={<Navigate to="/login" replace />} />
              </Routes>
            </AppLayout>
          )}
        />
      </Routes>
    </LanguageProvider>
  );
}
