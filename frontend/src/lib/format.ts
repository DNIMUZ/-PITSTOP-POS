const nf = new Intl.NumberFormat("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "0.00";
  return nf.format(Number(value));
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-MY", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtDate(day: string): string {
  const d = new Date(`${day}T00:00:00`);
  return d.toLocaleDateString("en-MY", { day: "2-digit", month: "short" });
}

export function titleCase(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1);
}