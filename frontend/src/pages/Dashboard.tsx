import { useQuery } from "@tanstack/react-query";
import { Banknote, PackageCheck, Receipt, TrendingUp } from "lucide-react";
import { api } from "../lib/api";
import { fmtDate, money } from "../lib/format";
import { Badge, Card, ErrorState, Spinner } from "../components/ui";

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
  });

  if (isLoading) return <Spinner label="Building dashboard…" />;
  if (error || !data) return <ErrorState message={error?.message ?? "Could not load dashboard."} />;

  const stats = [
    { label: "Revenue today", value: money(data.revenue_today), icon: Banknote },
    { label: "Orders today", value: String(data.orders_today), icon: Receipt },
    { label: "Avg order value", value: money(data.avg_order_value_today), icon: TrendingUp },
    { label: "Items sold today", value: String(data.items_sold_today), icon: PackageCheck },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-neutral-900">Dashboard</h1>
        <p className="text-sm text-neutral-500">Live numbers from committed transactions.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map(({ label, value, icon: Icon }) => (
          <Card key={label} className="flex items-center gap-4">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-neutral-100 text-neutral-600">
              <Icon className="h-5 w-5" />
            </span>
            <div>
              <div className="text-2xl font-bold tabular-nums text-neutral-900">{value}</div>
              <div className="text-xs text-neutral-500">{label}</div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <h2 className="mb-4 text-sm font-semibold text-neutral-900">Revenue — last 7 days</h2>
          <div className="space-y-2">
            {data.revenue_last_7_days.map((day) => (
              <div key={day.day} className="flex items-center justify-between border-b border-neutral-100 pb-2 text-sm">
                <span className="text-neutral-600">{fmtDate(day.day)}</span>
                <span className="text-neutral-400">{day.orders} order{day.orders === 1 ? "" : "s"}</span>
                <span className="font-semibold tabular-nums text-neutral-900">{money(day.revenue)}</span>
              </div>
            ))}
            {data.revenue_last_7_days.length === 0 && <p className="text-sm text-neutral-400">No sales this week.</p>}
          </div>
        </Card>

        <Card>
          <h2 className="mb-4 text-sm font-semibold text-neutral-900">Top products (30 days)</h2>
          <div className="space-y-2">
            {data.top_products.map((p, i) => (
              <div key={p.product_id} className="flex items-center justify-between gap-3 text-sm">
                <span className="flex min-w-0 items-center gap-2">
                  <span className="w-5 shrink-0 text-neutral-400">{i + 1}.</span>
                  <span className="truncate text-neutral-800">{p.name}</span>
                  <span className="shrink-0 text-xs text-neutral-400">{p.sku}</span>
                </span>
                <span className="shrink-0 tabular-nums text-neutral-500">{p.quantity} sold</span>
                <span className="w-20 shrink-0 text-right font-semibold tabular-nums text-neutral-900">
                  {money(p.revenue)}
                </span>
              </div>
            ))}
            {data.top_products.length === 0 && <p className="text-sm text-neutral-400">No sales yet.</p>}
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="mb-4 text-sm font-semibold text-neutral-900">Low stock alerts ({data.low_stock.length})</h2>
        {data.low_stock.length === 0 ? (
          <p className="text-sm text-neutral-400">All products are above their reorder level.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-neutral-500">
                  <th className="pb-2 font-medium">Product</th>
                  <th className="pb-2 font-medium">SKU</th>
                  <th className="pb-2 font-medium">On hand</th>
                  <th className="pb-2 font-medium">Reorder level</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.low_stock.map((p) => (
                  <tr key={p.product_id} className="border-t border-neutral-100">
                    <td className="py-2 text-neutral-800">{p.name}</td>
                    <td className="py-2 text-neutral-500">{p.sku}</td>
                    <td className="py-2 tabular-nums">{p.stock_on_hand}</td>
                    <td className="py-2 tabular-nums">{p.reorder_level}</td>
                    <td className="py-2">
                      <Badge tone={p.stock_on_hand === 0 ? "red" : "amber"}>
                        {p.stock_on_hand === 0 ? "Out of stock" : "Low stock"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}