import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, Minus, Plus, ScanBarcode, ShoppingCart, Trash2 } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { money } from "../lib/format";
import type { CartLine, Product, TransactionDetail } from "../types";
import { Button, Card, ErrorState, Field, Input, Modal, Select } from "../components/ui";
import { useAuth } from "../context/auth";

const TAX_RATE = 8; // percent; display mirror only — server is authority

type PayMethod = "cash" | "card" | "qr" | "ewallet";

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

export default function Pos() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const scanRef = useRef<HTMLInputElement>(null);
  const [code, setCode] = useState("");
  const [cart, setCart] = useState<CartLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [discountPct, setDiscountPct] = useState("0");
  const [method, setMethod] = useState<PayMethod>("cash");
  const [tender, setTender] = useState("");
  const [reference, setReference] = useState("");
  const [receipt, setReceipt] = useState<TransactionDetail | null>(null);

  const { data: catalog, error: catalogError } = useQuery({
    queryKey: ["products", { q: "", page: 1, page_size: 24 }],
    queryFn: () => api.products({ page: 1, page_size: 24 }),
  });

  useEffect(() => {
    scanRef.current?.focus();
  }, []);

  useEffect(() => {
    document.addEventListener("keydown", (e) => {
      if ((e.target as HTMLElement)?.tagName === "INPUT") return;
      if (e.key === "F2") {
        e.preventDefault();
        scanRef.current?.focus();
      }
    });
  }, []);

  const totals = useMemo(() => {
    const subtotal = round2(cart.reduce((acc, l) => acc + Number(l.product.unit_price) * l.quantity, 0));
    const rate = Math.max(0, Math.min(100, Number(discountPct) || 0));
    const discount = round2(subtotal * (rate / 100));
    const taxable = round2(subtotal - discount);
    const tax = round2(taxable * (TAX_RATE / 100));
    const total = round2(taxable + tax);
    return { subtotal, discount, tax, total };
  }, [cart, discountPct]);

  const lookups = useMutation({
    mutationFn: async (codeInput: string) => {
      const trimmed = codeInput.trim();
      if (!trimmed) throw new ApiError(400, "EMPTY", "Enter a barcode or SKU.");
      try {
        return await api.lookup(trimmed);
      } catch (err) {
        if (err instanceof ApiError && err.code === "NOT_FOUND") {
          throw new ApiError(404, "NOT_FOUND", `No active product found for "${trimmed}".`);
        }
        throw err;
      }
    },
    onSuccess: (product: Product) => {
      setCart((prev) => {
        const existing = prev.find((l) => l.product.id === product.id);
        if (existing) {
          return prev.map((l) =>
            l.product.id === product.id ? { ...l, quantity: l.quantity + 1 } : l,
          );
        }
        return [...prev, { product, quantity: 1 }];
      });
      setCode("");
      setError(null);
      scanRef.current?.focus();
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Lookup failed.");
      setCode("");
    },
  });

  const checkout = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.checkout(payload),
    onSuccess: (tx) => {
      setReceipt(tx);
      setCart([]);
      setDiscountPct("0");
      setTender("");
      setReference("");
      queryClient.invalidateQueries();
      setError(null);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Checkout failed.");
    },
  });

  const changeQty = useCallback((id: number, delta: number) => {
    setCart((prev) =>
      prev
        .map((l) => {
          if (l.product.id !== id) return l;
          const q = l.quantity + delta;
          return { ...l, quantity: q >= 0 ? q : 0 };
        })
        .filter((l) => l.quantity > 0),
    );
  }, []);

  const removeLine = useCallback((id: number) => {
    setCart((prev) => prev.filter((l) => l.product.id !== id));
  }, []);

  function runCheckout() {
    if (cart.length === 0) return;
    const payload = {
      items: cart.map((l) => ({ product_id: l.product.id, quantity: l.quantity })),
      discount_rate: String(Math.max(0, Math.min(100, Number(discountPct) || 0))),
      payment: {
        method,
        amount: method === "cash" && tender ? Number(tender) : Number(totals.total),
        reference: method === "cash" ? undefined : reference || undefined,
      },
    };
    // Only send a card/qr/ewallet reference if one was given (backend requires it for qr).
    checkout.mutate(payload);
  }

  if (catalogError) return <ErrorState message={"Could not load product catalog."} />;

  const stockHint = (line: CartLine): boolean => line.quantity >= line.product.stock_on_hand;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-neutral-900">POS / Checkout</h1>
          <p className="text-sm text-neutral-500">
            Signed in as {user?.username}. Press <kbd className="rounded bg-neutral-200 px-1">F2</kbd> to focus the scanner.
          </p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          <CircleAlert className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              lookups.mutate(code);
            }}
            className="mb-4 flex items-center gap-2"
          >
            <div className="relative flex-1">
              <ScanBarcode className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
              <Input
                ref={scanRef}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Scan barcode or type SKU, then Enter"
                className="pl-9"
                autoFocus
              />
            </div>
            <Button type="submit" disabled={!code.trim()}>
              Add
            </Button>
          </form>

          {cart.length === 0 ? (
            <div className="py-16 text-center">
              <ShoppingCart className="mx-auto mb-2 h-10 w-10 text-neutral-300" />
              <p className="text-sm text-neutral-400">Scan a barcode to start a sale.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-neutral-500">
                  <tr>
                    <th className="pb-2 font-medium">Product</th>
                    <th className="pb-2 text-right font-medium">Price</th>
                    <th className="pb-2 text-center font-medium">Qty</th>
                    <th className="pb-2 text-right font-medium">Line total</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody>
                  {cart.map((line) => (
                    <tr key={line.product.id} className="border-t border-neutral-100">
                      <td className="py-2 pr-2">
                        <div className="font-medium text-neutral-900">{line.product.name}</div>
                        <div className="text-xs text-neutral-400">{line.product.sku}</div>
                      </td>
                      <td className="py-2 text-right tabular-nums">{money(line.product.unit_price)}</td>
                      <td className="py-2">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => changeQty(line.product.id, -1)}
                            className="rounded-md border border-neutral-300 p-1 text-neutral-600 hover:bg-neutral-100"
                            aria-label="Decrease"
                          >
                            <Minus className="h-3 w-3" />
                          </button>
                          <span
                            className={`w-8 text-center tabular-nums ${stockHint(line) ? "font-semibold text-amber-600" : "text-neutral-900"}`}
                          >
                            {line.quantity}
                          </span>
                          <button
                            onClick={() => changeQty(line.product.id, 1)}
                            className="rounded-md border border-neutral-300 p-1 text-neutral-600 hover:bg-neutral-100"
                            aria-label="Increase"
                          >
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>
                      </td>
                      <td className="py-2 text-right font-semibold tabular-nums">
                        {money(Number(line.product.unit_price) * line.quantity)}
                      </td>
                      <td className="py-2 text-right">
                        <button onClick={() => removeLine(line.product.id)} className="text-neutral-300 hover:text-red-500" aria-label="Remove">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {catalog && (
            <div className="mt-4 border-t border-neutral-100 pt-3">
              <p className="mb-2 text-xs font-medium text-neutral-500">Quick pick</p>
              <div className="grid grid-cols-3 gap-2">
                {catalog.items.slice(0, 9).map((p) => (
                  <button
                    key={p.id}
                    onClick={() =>
                      lookups.mutate(p.barcode ?? p.sku)
                    }
                    className="truncate rounded-lg border border-neutral-200 px-2 py-1.5 text-left text-xs text-neutral-700 hover:border-neutral-400"
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card className="xl:col-span-2">
          <h2 className="mb-4 text-sm font-semibold text-neutral-900">Payment</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-500">Subtotal</span>
              <span className="font-semibold tabular-nums">{money(totals.subtotal)}</span>
            </div>
            <Field label="Discount %">
              <Input
                type="number"
                min={0}
                max={100}
                step="any"
                value={discountPct}
                onChange={(e) => setDiscountPct(e.target.value)}
              />
            </Field>
            <div className="flex items-center justify-between text-sm text-red-600">
              <span>Discount</span>
              <span className="tabular-nums">−{money(totals.discount)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-500">SST ({TAX_RATE}%)</span>
              <span className="tabular-nums">{money(totals.tax)}</span>
            </div>
            <div className="flex items-center justify-between border-t border-neutral-200 pt-3 text-base font-bold">
              <span className="text-neutral-900">Total</span>
              <span className="tabular-nums">{money(totals.total)}</span>
            </div>

            <Field label="Payment method">
              <Select value={method} onChange={(e) => setMethod(e.target.value as PayMethod)}>
                <option value="cash">Cash</option>
                <option value="card">Card</option>
                <option value="qr">QR (DuitNow / TNG)</option>
                <option value="ewallet">E-wallet</option>
              </Select>
            </Field>

            {method === "cash" && (
              <Field label="Cash tendered">
                <Input
                  type="number"
                  min={totals.total}
                  step="any"
                  value={tender}
                  placeholder={money(totals.total)}
                  onChange={(e) => setTender(e.target.value)}
                />
              </Field>
            )}
            {method !== "cash" && (
              <Field label={`${method === "qr" ? "QR" : "Card"} reference`}>
                <Input
                  value={reference}
                  placeholder={method === "qr" ? "e.g. DUITNOW-184 (required)" : "e.g. HOST4512"}
                  onChange={(e) => setReference(e.target.value)}
                  required={method === "qr"}
                />
              </Field>
            )}

            {method === "cash" && Number(tender) > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-neutral-500">Change due</span>
                <span className="font-semibold text-emerald-600 tabular-nums">
                  {money(round2(Number(tender) - totals.total))}
                </span>
              </div>
            )}

            <Button
              className="w-full py-3 text-base"
              disabled={cart.length === 0 || totals.total <= 0 || (method === "cash" && Number(tender) > 0 && Number(tender) < totals.total)}
              loading={checkout.isPending}
              onClick={runCheckout}
            >
              Charge {money(totals.total)}
            </Button>
          </div>
        </Card>
      </div>

      <ReceiptModal tx={receipt} onClose={() => setReceipt(null)} />
    </div>
  );
}

function ReceiptModal({ tx, onClose }: { tx: TransactionDetail | null; onClose: () => void }) {
  return (
    <Modal open={!!tx} onClose={onClose} title="Receipt">
      {tx && (
        <div className="space-y-4">
          <div id="receipt-print" className="rounded-lg border border-dashed border-neutral-300 p-4 text-sm">
            <div className="mb-3 text-center">
              <div className="font-bold text-neutral-900">PITSTOP POS</div>
              <div className="text-xs text-neutral-500">{tx.transaction_no}</div>
              <div className="text-xs text-neutral-400">{new Date(tx.created_at).toLocaleString()}</div>
            </div>
            <div className="space-y-1">
              {tx.items.map((it) => (
                <div key={it.id} className="flex items-baseline justify-between gap-2">
                  <span className="min-w-0 flex-1 truncate">
                    {it.quantity} × {it.product_name}
                  </span>
                  <span className="tabular-nums">{money(it.line_total)}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 space-y-1 border-t border-neutral-200 pt-2 text-xs">
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span className="tabular-nums">{money(tx.subtotal)}</span>
              </div>
              {Number(tx.discount_amount) > 0 && (
                <div className="flex justify-between text-red-600">
                  <span>Discount ({tx.discount_rate}%)</span>
                  <span className="tabular-nums">−{money(tx.discount_amount)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>SST ({tx.tax_rate}%)</span>
                <span className="tabular-nums">{money(tx.tax_amount)}</span>
              </div>
              <div className="flex justify-between border-t border-neutral-200 pt-1 font-bold text-neutral-900">
                <span>Total</span>
                <span className="tabular-nums">{money(tx.total)}</span>
              </div>
              {tx.payments.map((p) => (
                <div key={p.id} className="flex justify-between">
                  <span>Paid via {p.method}</span>
                  <span className="tabular-nums">{money(p.amount)}</span>
                </div>
              ))}
              {tx.change_amount !== null && tx.change_amount !== "0.00" && (
                <div className="flex justify-between text-emerald-600">
                  <span>Change</span>
                  <span className="tabular-nums">{money(tx.change_amount)}</span>
                </div>
              )}
            </div>
            <div className="mt-3 text-center text-xs text-neutral-400">Thank you for your business!</div>
          </div>
          <div className="flex gap-2">
            <Button
              className="flex-1"
              onClick={() => {
                window.print();
              }}
            >
              Print receipt
            </Button>
            <Button variant="secondary" className="flex-1" onClick={onClose}>
              Done
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}