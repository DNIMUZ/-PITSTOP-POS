import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { FlagTriangleRight } from "lucide-react";
import { useAuth } from "../context/auth";
import { ApiError } from "../lib/api";
import { Button, Field, Input } from "../components/ui";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-neutral-900 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <span className="mx-auto mb-3 grid h-14 w-14 place-items-center rounded-2xl bg-white text-xl font-bold text-neutral-900">
            P
          </span>
          <h1 className="text-2xl font-bold text-white">PITSTOP POS</h1>
          <p className="mt-1 text-sm text-neutral-400">Point-of-sale for pitstop retail</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-4 rounded-2xl bg-white p-6 shadow-xl">
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              <FlagTriangleRight className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
          <Field label="Username">
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
              required
            />
          </Field>
          <Field label="Password">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </Field>
          <Button type="submit" loading={busy} className="w-full" disabled={!username || !password}>
            Sign in
          </Button>
          <p className="text-center text-xs text-neutral-400">
            Demo accounts: admin / manager / cashier (Admin@2026 · Manager@2026 · Cashier@2026)
          </p>
        </form>
      </div>
    </div>
  );
}