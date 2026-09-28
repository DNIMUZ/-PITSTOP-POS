import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { money } from "../lib/format";
import { can, useAuth } from "../context/auth";
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, Modal, Select, Spinner } from "../components/ui";

export default function Products() {
  const { user } = useAuth();
  const manager = can(user, ["manager", "admin"]);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["products", { q, page, page_size: 20 }],
    queryFn: () => api.products({ q, page, page_size: 20 }),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: api.categories,
    enabled: manager,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-neutral-900">Products</h1>
          <p className="text-sm text-neutral-500">{data?.total ?? 0} products in the catalog.</p>
        </div>
        {manager && (
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" />
            New product
          </Button>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
        }}
        className="flex max-w-md items-center gap-2"
      >
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or SKU" className="pl-9" />
        </div>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} />}
      {data && data.items.length === 0 && <EmptyState message="No products match." />}

      {data && data.items.length > 0 && (
        <Card className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 text-left text-xs text-neutral-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Product</th>
                  <th className="px-4 py-3 font-medium">SKU</th>
                  <th className="px-4 py-3 font-medium">Price</th>
                  <th className="px-4 py-3 font-medium">Stock</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id} className="border-t border-neutral-100">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-3">
                        <span className="grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-lg bg-neutral-100 text-[10px] font-semibold text-neutral-500">
                          {p.image_url ? (
                            <img src={p.image_url} alt="" className="h-full w-full object-cover" />
                          ) : (
                            p.sku.slice(0, 3)
                          )}
                        </span>
                        <div>
                          <div className="font-medium text-neutral-900">{p.name}</div>
                          {p.barcode && <div className="text-xs text-neutral-400">{p.barcode}</div>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-neutral-600">{p.sku}</td>
                    <td className="px-4 py-2.5 font-semibold tabular-nums">{money(p.unit_price)}</td>
                    <td className={`px-4 py-2.5 tabular-nums ${p.stock_on_hand <= p.reorder_level ? "font-semibold text-amber-600" : "text-neutral-800"}`}>
                      {p.stock_on_hand}
                    </td>
                    <td className="px-4 py-2.5 text-neutral-500">{p.category_name ?? "—"}</td>
                    <td className="px-4 py-2.5">
                      {p.is_active ? <Badge tone="green">Active</Badge> : <Badge tone="neutral">Inactive</Badge>}
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
              <Button
                variant="secondary"
                disabled={page * data.page_size >= data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </Card>
      )}

      {manager && <CreateProductModal open={showCreate} onClose={() => setShowCreate(false)} categories={categories ?? []} />}
    </div>
  );
}

function CreateProductModal({
  open,
  onClose,
  categories,
}: {
  open: boolean;
  onClose: () => void;
  categories: { id: number; name: string }[];
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    sku: "",
    name: "",
    barcode: "",
    category_id: "",
    unit_price: "",
    initial_stock: "0",
    reorder_level: "5",
  });
  const [serverError, setServerError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.createProduct(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      onClose();
      setForm({ sku: "", name: "", barcode: "", category_id: "", unit_price: "", initial_stock: "0", reorder_level: "5" });
    },
    onError: (err) => setServerError(err instanceof ApiError ? err.message : "Create failed."),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    setServerError(null);
    create.mutate({
      sku: form.sku.trim(),
      name: form.name.trim(),
      barcode: form.barcode.trim() || null,
      category_id: form.category_id ? Number(form.category_id) : null,
      unit_price: String(Number(form.unit_price || 0)),
      initial_stock: Number(form.initial_stock || 0),
      reorder_level: Number(form.reorder_level || 5),
    });
  }

  return (
    <Modal open={open} onClose={onClose} title="New product">
      {serverError && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{serverError}</div>
      )}
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="SKU *">
            <Input required value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
          </Field>
          <Field label="Barcode">
            <Input value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} />
          </Field>
        </div>
        <Field label="Product name *">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Unit price (RM) *">
            <Input
              required
              type="number"
              min="0"
              step="0.01"
              value={form.unit_price}
              onChange={(e) => setForm({ ...form, unit_price: e.target.value })}
            />
          </Field>
          <Field label="Category">
            <Select
              value={form.category_id}
              onChange={(e) => setForm({ ...form, category_id: e.target.value })}
            >
              <option value="">None</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Opening stock">
            <Input
              type="number"
              min="0"
              value={form.initial_stock}
              onChange={(e) => setForm({ ...form, initial_stock: e.target.value })}
            />
          </Field>
          <Field label="Reorder level">
            <Input
              type="number"
              min="0"
              value={form.reorder_level}
              onChange={(e) => setForm({ ...form, reorder_level: e.target.value })}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending} disabled={!form.sku.trim() || !form.name.trim() || Number(form.unit_price) < 0}>
            Create product
          </Button>
        </div>
      </form>
    </Modal>
  );
}