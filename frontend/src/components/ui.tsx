import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { forwardRef } from "react";
import { Loader2 } from "lucide-react";

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export function Button({
  variant = "primary",
  className,
  loading,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; loading?: boolean }) {
  const styles: Record<ButtonVariant, string> = {
    primary:
      "bg-neutral-900 text-white hover:bg-neutral-700 disabled:bg-neutral-400",
    secondary:
      "bg-white text-neutral-900 border border-neutral-300 hover:bg-neutral-100",
    danger: "bg-red-600 text-white hover:bg-red-500",
    ghost: "bg-transparent text-neutral-600 hover:bg-neutral-100",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed",
        styles[variant],
        className,
      )}
      disabled={loading || rest.disabled}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200",
          className,
        )}
        {...rest}
      />
    );
  },
);

export function Select({ className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-neutral-500",
        className,
      )}
      {...rest}
    >
      {children}
    </select>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("rounded-xl border border-neutral-200 bg-white p-5 shadow-sm", className)}>
      {children}
    </div>
  );
}

type BadgeTone = "green" | "red" | "amber" | "neutral" | "blue";

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: ReactNode }) {
  const tones: Record<BadgeTone, string> = {
    green: "bg-emerald-50 text-emerald-700 border-emerald-200",
    red: "bg-red-50 text-red-700 border-red-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
    neutral: "bg-neutral-100 text-neutral-700 border-neutral-200",
    blue: "bg-sky-50 text-sky-700 border-sky-200",
  };
  return (
    <span className={cn("inline-block rounded-full border px-2 py-0.5 text-xs font-medium", tones[tone])}>
      {children}
    </span>
  );
}

export function statusTone(status: string): BadgeTone {
  switch (status) {
    case "completed":
      return "green";
    case "refunded":
      return "red";
    case "partially_refunded":
      return "amber";
    default:
      return "neutral";
  }
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-neutral-500">
      <Loader2 className="h-5 w-5 animate-spin" />
      <span className="text-sm">{label ?? "Loading…"}</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      {message}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="py-14 text-center text-sm text-neutral-400">{message}</div>;
}

export function Modal({
  open,
  onClose,
  title,
  children,
  wide,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onMouseDown={onClose}>
      <div
        className={cn(
          "max-h-[90vh] w-full overflow-auto rounded-2xl bg-white p-6 shadow-2xl",
          wide ? "max-w-3xl" : "max-w-lg",
        )}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-900">{title}</h2>
          <button onClick={onClose} className="rounded-lg px-2 py-1 text-neutral-400 hover:bg-neutral-100" aria-label="Close">
            &times;
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-neutral-600">{label}</span>
      {children}
    </label>
  );
}