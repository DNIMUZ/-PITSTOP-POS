import type { Category, Dashboard, InventoryRow, Page, Product, Refund, TransactionDetail, TransactionListItem, User } from "../types";

const TOKEN_KEY = "pitstop_token";
export const USER_KEY = "pitstop_user";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getCachedUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export class ApiError extends Error {
  status: number;
  code: string;
  requestId: string | null;

  constructor(status: number, code: string, message: string, requestId: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

type Method = "GET" | "POST" | "PATCH";

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "NETWORK", "Cannot reach the server. Is the backend running?");
  }

  let data: Record<string, unknown> | null = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!res.ok) {
    const code = (data?.error as string) || "ERROR";
    const message = (data?.message as string) || res.statusText;
    const requestId = (data?.request_id as string | null) || null;
    throw new ApiError(res.status, code, message, requestId);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),

  me: () => api.get<User>("/api/v1/auth/me"),
  login: (username: string, password: string) =>
    api.post<{ access_token: string; token_type: string }>("/api/v1/auth/login", {
      username,
      password,
    }),

  products: (params: { q?: string; page?: number; page_size?: number; category_id?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    if (params.category_id) qs.set("category_id", String(params.category_id));
    return api.get<Page<Product>>(`/api/v1/products?${qs.toString()}`);
  },
  lookup: (code: string) => api.get<Product>(`/api/v1/products/lookup/${encodeURIComponent(code)}`),
  createProduct: (body: Record<string, unknown>) =>
    api.post<Product>("/api/v1/products", body),

  categories: () => api.get<Category[]>("/api/v1/categories"),

  inventory: (params: { low_stock_only?: boolean; q?: string; page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.low_stock_only) qs.set("low_stock_only", "true");
    if (params.q) qs.set("q", params.q);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    return api.get<Page<InventoryRow>>(`/api/v1/inventory?${qs.toString()}`);
  },
  adjustStock: (body: { product_id: number; quantity_change: number; note?: string }) =>
    api.post<InventoryRow>("/api/v1/inventory/adjust", body),

  transactions: (params: { page?: number; page_size?: number; q?: string; status?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    if (params.q) qs.set("q", params.q);
    if (params.status) qs.set("status", params.status);
    return api.get<Page<TransactionListItem>>(`/api/v1/transactions?${qs.toString()}`);
  },
  transaction: (id: number) => api.get<TransactionDetail>(`/api/v1/transactions/${id}`),
  checkout: (body: Record<string, unknown>) =>
    api.post<TransactionDetail>("/api/v1/transactions", body),
  refund: (id: number, body: { transaction_id: number; items: { transaction_item_id: number; quantity: number }[]; reason?: string }) =>
    api.post<Refund>(`/api/v1/transactions/${id}/refund`, body),

  dashboard: () => api.get<Dashboard>("/api/v1/analytics/dashboard"),
};