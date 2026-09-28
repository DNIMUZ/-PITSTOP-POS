import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, SlidersHorizontal } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { can, useAuth } from "../context/auth";
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, Modal, Spinner } from "../components/ui";

export default function Inventory() {
  const { user } = useAuth();
  const manager = can(user, ["manager", "admin"]);
  const [q, setQ] = useState("");
  const [lowOnly, setLowOnly] = useState(false);
  const [adjustFor, setAdjustFor] = useState<number | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["inventory", { q, lowOnly }],
    queryFn: () => api.inventory({ q, low_stock_only: lowOnly, page_size: 100 }),
  });

  const row = adjustFor !== null ? data?.items.find((r) => r.product_id === adjustFor) : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-neutral-900">Inventory</h1>
        <p className="text-sm text-neutral-500">Stock levels per product. Adjustments are manager-only.</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
          }}
          className="relative max-w-sm flex-1"
        >
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by product" className="pl-9" />
        </form>
        <Button variant={lowOnly ? "primary" : "secondary"} onClick={() => setLowOnly((v) => !v)}>
          <SlidersHorizontal className="h-4 w-4" />
          Low stock only
        </Button>
      </div>

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} />}
      {data && data.items.length === 0 && <EmptyState message="No inventory rows match." />}

      {data && data.items.length > 0 && (
        <Card className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 text-left text-xs text-neutral-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Product</th>
                  <th className="px-4 py-3 font-medium">SKU</th>
                  <th className="px-4 py-3 font-medium">On hand</th>
                  <th className="px-4 py-3 font-medium">Reorder level</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  {manager && <th className="px-4 py-3 text-right font-medium">Action</th>}
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => {
                  const low = r.stock_on_hand <= r.reorder_level;
                  return (
                    <tr key={r.product_id} className="border-t border-neutral-100">
                      <td className="px-4 py-2.5 font-medium text-neutral-900">{r.product_name}</td>
                      <td className="px-4 py-2.5 text-neutral-500">{r.sku}</td>
                      <td className={`px-4 py-2.5 tabular-nums ${low ? "font-bold text-amber-600" : "text-neutral-800"}`}>
                        {r.stock_on_hand}
                      </td>
                      <td className="px-4 py-2.5 tabular-nums text-neutral-500">{r.reorder_level}</td>
                      <td className="px-4 py-2.5">
                        <Badge tone={r.stock_on_hand === 0 ? "red" : low ? "amber" : "green"}>
                          {r.stock_on_hand === 0 ? "Out" : low ? "Low" : "OK"}
                        </Badge>
                      </td>
                      {manager && (
                        <td className="px-4 py-2.5 text-right">
                          <Button variant="secondary" className="px-3 py-1 text-xs" onClick={() => setAdjustFor(r.product_id)}>
                            Adjust
                          </Button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {manager && (
        <AdjustModal
          open={adjustFor !== null}
          onClose={() => setAdjustFor(null)}
          productId={adjustFor ?? 0}
          productName={row?.product_name ?? ""}
          sku={row?.sku ?? ""}
        />
      )}
    </div>
  );
}

function AdjustModal({
  open,
  onClose,
  productId,
  productName,
  sku,
}: {
  open: boolean;
  onClose: () => void;
  productId: number;
  productName: string;
  sku: string;
}) {
  const queryClient = useQueryClient();
  const [delta, setDelta] = useState("");
  const [note, setNote] = useState("");
  const [serverError, setServerError] = useState<string | null>(null);

  const adjust = useMutation({
    mutationFn: (b: { product_id: number; quantity_change: number; note?: string }) => api.adjustStock(b),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      onClose();
      setDelta("");
      setNote("");
      setServerError(null);
    },
    onError: (err) => setServerError(err instanceof ApiError ? err.message : "Adjustment failed."),
  });

  const amount = Math.round(Number(delta) || 0);

  return (
    <Modal open={open} onClose={onClose} title="Adjust stock">
      {serverError && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{serverError}</div>
      )}
      <div className="mb-4 text-sm text-neutral-600">
        <span className="font-medium text-neutral-900">{productName}</span> · {sku}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (amount === 0) return;
          adjust.mutate({ product_id: productId, quantity_change: amount, note: note.trim() || undefined });
        }}
        className="space-y-3"
      >
        <Field label={`Quantity change (positive = restock, negative = remove) — current: ${delta}`}>
          <Input
            type="number"
            required
            value={delta}
            placeholder="e.g. +10 or -3"
            onChange={(e) => setDelta(e.target.value)}
          />
        </Field>
        <Field label="Note">
          <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. stocktake / supplier delivery" />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={adjust.isPending} disabled={amount === 0}>
            Apply adjustment
          </Button>
        </div>
      </form>
    </Modal>
  );
}