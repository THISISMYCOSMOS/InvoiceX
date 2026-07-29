import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { NewInvoicePage } from "./pages/supplier/NewInvoicePage";
import { SupplierDashboardPage } from "./pages/supplier/SupplierDashboardPage";
import { SupplierInvoiceDetailPage } from "./pages/supplier/SupplierInvoiceDetailPage";

export function App() {
  return <AppLayout><Routes><Route path="/supplier" element={<SupplierDashboardPage />} /><Route path="/supplier/invoices/new" element={<NewInvoicePage />} /><Route path="/supplier/invoices/:invoiceId" element={<SupplierInvoiceDetailPage />} /><Route path="*" element={<Navigate to="/supplier" replace />} /></Routes></AppLayout>;
}
