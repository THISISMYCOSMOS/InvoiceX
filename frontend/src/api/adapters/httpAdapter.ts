import type { InvestorDashboard, Invoice, InvoiceStatus, VerificationRequest } from "../../types/invoice";
import type { OfferResponse, ScenarioAdapter } from "./contracts";

type FetchImplementation = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

const invoiceStatuses = new Set<InvoiceStatus>([
  "DRAFT", "DOCUMENT_UPLOADING", "DOCUMENT_ANALYZING", "DOCUMENT_REVIEW_REQUIRED",
  "BUYER_REVIEW", "BUYER_VERIFIED", "RISK_ASSESSING", "OFFER_READY", "RWA_ISSUED", "FUNDING",
  "FUNDED", "REPAYMENT_PENDING", "SETTLING", "SETTLED", "REVISION_REQUESTED",
  "DISPUTED", "BLOCKED", "ERROR",
]);

export class HttpError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "HttpError";
  }
}

export class UnsupportedApiOperation extends Error {
  constructor(operation: string) {
    super(`${operation}은(는) 현재 백엔드 API 계약에 없습니다.`);
    this.name = "UnsupportedApiOperation";
  }
}

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new HttpError(502, `${label} 응답 형식이 올바르지 않습니다.`);
  }

  return value as Record<string, unknown>;
}

function asString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new HttpError(502, `${field} 필드가 응답에 없습니다.`);
  }

  return value;
}

function unwrapInvoice(value: unknown): Invoice {
  const outer = asRecord(value, "Invoice");
  const source = outer.invoice === undefined ? outer : asRecord(outer.invoice, "Invoice");
  asString(source.id ?? source.invoiceId, "invoice.id");
  const status = asString(source.status, "invoice.status");

  if (!invoiceStatuses.has(status as InvoiceStatus)) {
    throw new HttpError(502, `invoice.status 값이 지원되지 않습니다: ${status}`);
  }

  return source as unknown as Invoice;
}

function unwrapVerification(value: unknown): VerificationRequest {
  const outer = asRecord(value, "Verification");
  const source = outer.verification === undefined ? outer : asRecord(outer.verification, "Verification");

  return {
    id: asString(source.id ?? source.verificationId, "verification.id"),
    invoiceId: asString(source.invoiceId, "verification.invoiceId"),
    status: asString(source.status, "verification.status") as VerificationRequest["status"],
  };
}

function stripTrailingSlash(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

export function createHttpAdapter(fetchImpl: FetchImplementation, baseUrl: string): ScenarioAdapter {
  const base = stripTrailingSlash(baseUrl);
  const request = async <T>(path: string, init: RequestInit): Promise<T> => {
    const response = await fetchImpl(`${base}${path}`, init);
    if (!response.ok) {
      throw new HttpError(response.status, await response.text());
    }

    return response.json() as Promise<T>;
  };

  const unavailable = (operation: string): Promise<never> => Promise.reject(new UnsupportedApiOperation(operation));

  return {
    async submitInvoiceDocuments(formData) {
      return unwrapInvoice(await request<unknown>("/invoices", { method: "POST", body: formData }));
    },
    async getInvoices() {
      const payload = await request<unknown>("/invoices", { method: "GET" });
      const data = asRecord(payload, "Invoice 목록");
      const items = Array.isArray(data.items) ? data.items : Array.isArray(payload) ? payload : undefined;
      if (items === undefined) {
        throw new HttpError(502, "Invoice 목록 응답에 items 배열이 없습니다.");
      }

      return items.map(unwrapInvoice);
    },
    async getInvoice(invoiceId) {
      return unwrapInvoice(await request<unknown>(`/invoices/${encodeURIComponent(invoiceId)}`, { method: "GET" }));
    },
    analyzeInvoice: () => unavailable("문서 분석"),
    async requestVerification(invoiceId) {
      return unwrapInvoice(await request<unknown>(`/invoices/${encodeURIComponent(invoiceId)}/verification-request`, { method: "POST" }));
    },
    async getVerifications() {
      const payload = await request<unknown>("/verifications", { method: "GET" });
      const data = asRecord(payload, "검증 목록");
      const items = Array.isArray(data.items) ? data.items : Array.isArray(payload) ? payload : undefined;
      if (items === undefined) {
        throw new HttpError(502, "검증 목록 응답에 items 배열이 없습니다.");
      }

      return items.map(unwrapVerification);
    },
    async getVerification(verificationId) {
      return unwrapVerification(await request<unknown>(`/verifications/${encodeURIComponent(verificationId)}`, { method: "GET" }));
    },
    async confirmVerification(verificationId) {
      return unwrapInvoice(await request<unknown>(`/verifications/${encodeURIComponent(verificationId)}/confirm`, { method: "POST" }));
    },
    async respondToOffer(invoiceId, response: OfferResponse) {
      return unwrapInvoice(await request<unknown>(`/invoices/${encodeURIComponent(invoiceId)}/offer-response`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ response }),
      }));
    },
    async purchaseRwa(invoiceId) {
      return unwrapInvoice(await request<unknown>(`/invoices/${encodeURIComponent(invoiceId)}/rwa-purchase`, { method: "POST" }));
    },
    runFunding: () => unavailable("Treasury Agent 투자 실행"),
    async mockPayment(invoiceId) {
      return unwrapInvoice(await request<unknown>(`/invoices/${encodeURIComponent(invoiceId)}/settlement/mock-payment`, { method: "POST" }));
    },
    runSettlement: () => unavailable("Settlement 실행"),
    async getInvestorDashboard() {
      return (await request<unknown>("/investor/dashboard", { method: "GET" })) as InvestorDashboard;
    },
    reset: () => unavailable("데모 초기화"),
  };
}
