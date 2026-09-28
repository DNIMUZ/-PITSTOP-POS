import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "../lib/api";
import { fmtDateTime, money } from "../lib/format";
import { Badge, Button, Card, EmptyState, ErrorState, Input, Modal, Select, Spinner, statusTone } from "../components/ui";
import type { Refund } from "../types";

export default function Transactions() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["transactions", { q, status, page }],
    queryFn: () => api.transactions({ q, status, page, page_size: 20 }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-neutral-900">Transactions</h1>
        <p className="text-sm text-neutral-500">Completed sales. Cashiers see their own; managers/admins see all.</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <form className="relative max-w-sm flex-1" onSubmit={(e) => e.preventDefault()}>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by receipt no." className="pl-9" />
        </form>
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-52">
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="partially_refunded">Partially refunded</option>
          <option value="refunded">Refunded</option>
        </Select>
      </div>

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} />}
      {data && data.items.length === 0 && <EmptyState message="No transactions found." />}

      {data && data.items.length > 0 && (
        <Card className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 text-left text-xs text-neutral-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Receipt no.</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Cashier</th>
                  <th className="px-4 py-3 font-medium">Items</th>
                  <th className="px-4 py-3 text-right font-medium">Total</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((tx) => (
                  <tr key={tx.id} className="cursor-pointer border-t border-neutral-100 hover:bg-neutral-50" onClick={() => setSelectedId(tx.id)}>
                    <td className="px-4 py-2.5 font-medium text-neutral-900">{tx.transaction_no}</td>
                    <td className="px-4 py-2.5 text-neutral-500">{fmtDateTime(tx.created_at)}</td>
                    <td className="px-4 py-2.5 text-neutral-600">{tx.cashier_name ?? `#${tx.cashier_id}`}</td>
                    <td className="px-4 py-2.5 tabular-nums">{tx.items_count}</td>
                    <td className="px-4 py-2.5 text-right font-semibold tabular-nums">{money(tx.total)}</td>
                    <td className="px-4 py-2.5">
                      <Badge tone={statusTone(tx.status)}>{tx.status.replace("_", " ")}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-neutral-100 px-4 py-3 text-sm text-neutral-500">
            <span>
              Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <Button variant="secondary" disabled={page * data.page_size >= data.total} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          </div>
        </Card>
      )}

      <TransactionDetailModal id={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  );
}

function TransactionDetailModal({ id, onClose }: { id: number | null; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["transaction", id],
    queryFn: () => api.transaction(id as number),
    enabled: id !== null,
  });

  return (
    <Modal open={id !== null} onClose={onClose} title="Transaction detail" wide>
      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} />}
      {data && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-lg font-bold text-neutral-900">{data.transaction_no}</div>
              <div className="text-sm text-neutral-500">{fmtDateTime(data.created_at)} · cashed by {data.cashier_name}</div>
            </div>
            <Badge tone={statusTone(data.status)}>{data.status.replace("_", " ")}</Badge>
          </div>

          <table className="w-full text-sm">
            <thead className="text-left text-xs text-neutral-500">
              <tr>
                <th className="pb-2 font-medium">Item</th>
                <th className="pb-2 text-right font-medium">Unit price</th>
                <th className="pb-2 text-center font-medium">Qty</th>
                <th className="pb-2 text-right font-medium">Line total</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it) => (
                <tr key={it.id} className="border-t border-neutral-100">
                  <td className="py-2">
                    <div className="font-medium text-neutral-900">{it.product_name}</div>
                    <div className="text-xs text-neutral-400">{it.sku}</div>
                  </td>
                  <td className="py-2 text-right tabular-nums">{money(it.unit_price)}</td>
                  <td className="py-2 text-center tabular-nums">{it.quantity}</td>
                  <td className="py-2 text-right font-medium tabular-nums">{money(it.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="ml-auto w-64 space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-neutral-500">Subtotal</span>
              <span className="tabular-nums">{money(data.subtotal)}</span>
            </div>
            {Number(data.discount_amount) > 0 && (
              <div className="flex justify-between text-red-600">
                <span>Discount ({data.discount_rate}%)</span>
                <span className="tabular-nums">−{money(data.discount_amount)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-neutral-500">SST ({data.tax_rate}%)</span>
              <span className="tabular-nums">{money(data.tax_amount)}</span>
            </div>
            <div className="flex justify-between border-t border-neutral-200 pt-1 font-bold text-neutral-900">
              <span>Total</span>
              <span className="tabular-nums">{money(data.total)}</span>
            </div>
            {data.payments.map((p) => (
              <div key={p.id} className="flex justify-between text-xs text-neutral-500">
                <span>
                  {p.method} {p.transaction_reference ? `· ${p.transaction_reference}` : ""}
                </span>
                <span className="tabular-nums">{money(p.amount)}</span>
              </div>
            ))}
          </div>

          <RefundBadges refunds={data.refunds} />
        </div>
      )}
    </Modal>
  );
}

function RefundBadges({ refunds }: { refunds: Refund[] }) {
  if (refunds.length === 0) return null;
  return (
    <div className="rounded-lg bg-neutral-50 p-3">
      <p className="mb-2 text-xs font-semibold text-neutral-500">Refunds on this receipt</p>
      <div className="space-y-1">
        {refunds.map((r) => (
          <div key={r.id} className="flex items-center justify-between text-sm">
            <span className="text-neutral-600">
              {r.refund_no} · {fmtDateTime(r.created_at)}
            </span>
            <span className="font-semibold tabular-nums text-red-600">−{money(r.amount)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}