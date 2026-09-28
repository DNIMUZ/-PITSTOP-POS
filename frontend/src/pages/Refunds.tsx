import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Undo2 } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { fmtDateTime, money } from "../lib/format";
import type { TransactionItem } from "../types";
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, Spinner, statusTone } from "../components/ui";

interface RefundsPageQuery {
  list?: { page: number; page_size: number };
  detail?: number;
  refunds?: number;
}

export default function Refunds() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<RefundsPageQuery | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: searchResults, isFetching } = useQuery({
    queryKey: ["transactions", { q }],
    queryFn: () => api.transactions({ q, page_size: 10 }),
    enabled: !!results,
    staleTime: 0,
  });

  const refund = useMutation({
    mutationFn: (args: { txId: number; body: Parameters<typeof api.refund>[1] }) =>
      api.refund(args.txId, args.body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transaction", selectedId] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setError(null);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Refund failed."),
  });

  function search(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setResults({ list: { page: 1, page_size: 10 } });
    setError(null);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-neutral-900">Refunds</h1>
        <p className="text-sm text-neutral-500">Search a receipt and refund part or all of it. Refunds restore stock.</p>
      </div>

      <form onSubmit={search} className="flex max-w-md items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by receipt no. e.g. TXN-00000123"
            className="pl-9"
          />
        </div>
        <Button type="submit" variant="secondary" loading={isFetching}>
          Search
        </Button>
      </form>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">{error}</div>
      )}

      {results && !searchResults && <Spinner label="Searching…" />}
      {results && searchResults && searchResults.items.length === 0 && (
        <EmptyState message={`No receipts match "${q}".`} />
      )}

      {results && searchResults && searchResults.items.length > 0 && (
        <Card className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 text-left text-xs text-neutral-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Receipt no.</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 text-right font-medium">Total</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 text-right font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {searchResults.items.map((tx) => (
                  <tr key={tx.id} className="border-t border-neutral-100">
                    <td className="px-4 py-2.5 font-medium text-neutral-900">{tx.transaction_no}</td>
                    <td className="px-4 py-2.5 text-neutral-500">{fmtDateTime(tx.created_at)}</td>
                    <td className="px-4 py-2.5 text-right font-semibold tabular-nums">{money(tx.total)}</td>
                    <td className="px-4 py-2.5">
                      <Badge tone={statusTone(tx.status)}>{tx.status.replace("_", " ")}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <Button
                        className="px-3 py-1.5 text-xs"
                        disabled={tx.status === "refunded"}
                        onClick={() => setSelectedId(tx.id)}
                      >
                        <Undo2 className="h-3.5 w-3.5" />
                        Refund
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <RefundForm
        txId={selectedId}
        onClose={() => setSelectedId(null)}
        submitting={refund.isPending}
        onSubmit={(items, reason) => {
          if (selectedId === null) return;
          refund.mutate({
            txId: selectedId,
            body: { transaction_id: selectedId, items, reason: reason?.trim() || undefined },
          });
        }}
      />
    </div>
  );
}

function refundable(tx: { items: TransactionItem[]; refunds: { items: { transaction_item_id: number; quantity: number }[] }[] }, itemId: number, qty: number): number {
  const refundedQty = tx.refunds.reduce(
    (acc, r) =>
      acc + r.items.filter((i) => i.transaction_item_id === itemId).reduce((a, i) => a + i.quantity, 0),
    0,
  );
  return Math.max(0, qty - refundedQty);
}

function RefundForm({
  txId,
  onClose,
  submitting,
  onSubmit,
}: {
  txId: number | null;
  onClose: () => void;
  submitting: boolean;
  onSubmit: (items: { transaction_item_id: number; quantity: number }[], reason: string) => void;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["transaction", txId],
    queryFn: () => api.transaction(txId as number),
    enabled: txId !== null,
  });
  const [qty, setQty] = useState<Record<number, string>>({});
  const [reason, setReason] = useState("");

  if (txId === null) return null;
  if (isLoading) return <div className="text-sm text-neutral-400">Loading receipt…</div>;
  if (error || !data) return <ErrorState message={error?.message ?? "Could not load receipt."} />;

  const requested = Object.entries(qty)
    .map(([itemId, value]) => ({ itemId: Number(itemId), value: Number(value) || 0 }))
    .filter((e) => e.value > 0);
  const totalRefund = requested.reduce((acc, e) => {
    const item = data.items.find((i) => i.id === e.itemId);
    return item ? acc + (Number(item.unit_price) * e.value) * 1.0 : acc;
  }, 0);

  const anyInvalid = requested.some((e) => {
    const item = data.items.find((i) => i.id === e.itemId);
    return item ? e.value > refundable(data, e.itemId, item.quantity) : true;
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (requested.length === 0 || anyInvalid) return;
    onSubmit(
      requested.map((r) => ({ transaction_item_id: r.itemId, quantity: r.value })),
      reason,
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onMouseDown={onClose}>
      <div className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-2xl bg-white p-6 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">Refund — {data.transaction_no}</h2>
            <p className="text-xs text-neutral-500">
              {fmtDateTime(data.created_at)} · {data.items.length} line(s) · total {money(data.total)}
            </p>
          </div>
          <button onClick={onClose} className="rounded px-2 py-1 text-neutral-400 hover:bg-neutral-100" aria-label="Close">
            &times;
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-neutral-500">
                <tr>
                  <th className="pb-2 font-medium">Item</th>
                  <th className="pb-2 text-right font-medium">Unit price</th>
                  <th className="pb-2 text-center font-medium">Qty</th>
                  <th className="pb-2 text-center font-medium">Refundable</th>
                  <th className="pb-2 text-center font-medium">Refund qty</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => {
                  const max = refundable(data, item.id, item.quantity);
                  return (
                    <tr key={item.id} className="border-t border-neutral-100">
                      <td className="py-2 pr-2">
                        <div className="font-medium text-neutral-900">{item.product_name}</div>
                        <div className="text-xs text-neutral-400">{item.sku}</div>
                      </td>
                      <td className="py-2 text-right tabular-nums">{money(item.unit_price)}</td>
                      <td className="py-2 text-center tabular-nums">{item.quantity}</td>
                      <td className={`py-2 text-center tabular-nums ${max === 0 ? "text-neutral-300" : "text-neutral-700"}`}>{max}</td>
                      <td className="py-2">
                        <Input
                          type="number"
                          min={0}
                          max={max}
                          value={qty[item.id] ?? ""}
                          disabled={max === 0}
                          className="mx-auto w-24 text-center"
                          placeholder="0"
                          onChange={(e) => setQty({ ...qty, [item.id]: e.target.value })}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <Field label="Reason (optional)">
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. wrong size, customer returned" />
          </Field>

          {totalRefund > 0 && (
            <p className="text-sm text-neutral-600">
              Estimated refund amount:{" "}
              <span className="font-bold text-red-600 tabular-nums">— {money(totalRefund)}</span>{" "}
              <span className="text-neutral-400">(actual amount is computed server-side incl. tax/discount and will appear in the receipt)</span>
            </p>
          )}
          {anyInvalid && <p className="text-sm text-amber-700">One or more refund quantities exceed the refundable amount.</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="danger" loading={submitting} disabled={requested.length === 0 || anyInvalid}>
              Process refund
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}