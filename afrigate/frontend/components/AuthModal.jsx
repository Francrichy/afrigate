import { useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth-context";

export default function AuthModal() {
  const { authModalOpen, setAuthModalOpen, login } = useAuth();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!authModalOpen) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res =
        mode === "login"
          ? await api.login({ email, password })
          : await api.register({ email, password, company_name: companyName || null });
      login(res);
    } catch (e) {
      setError(e.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/70" onClick={() => setAuthModalOpen(false)} />
      <div className="relative w-full max-w-sm rounded-xl bg-base-900 border border-base-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-1">
          {mode === "login" ? "Sign in" : "Create your account"}
        </h2>
        <p className="text-sm text-base-200 mb-5">
          {mode === "login" ? "Access your dashboard and API keys." : "Get $1.00 in free credits to start."}
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-base-200 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 focus:border-accent outline-none text-sm text-white"
            />
          </div>

          {mode === "register" && (
            <div>
              <label className="block text-xs font-medium text-base-200 mb-1">Company (optional)</label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 focus:border-accent outline-none text-sm text-white"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-base-200 mb-1">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 focus:border-accent outline-none text-sm text-white"
            />
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-md bg-accent hover:bg-accent-hover disabled:opacity-60 text-black text-sm font-semibold transition-colors"
          >
            {loading ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <button
          onClick={() => setMode(mode === "login" ? "register" : "login")}
          className="w-full text-center mt-4 text-xs text-base-200 hover:text-white"
        >
          {mode === "login" ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}
