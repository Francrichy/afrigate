import { useEffect, useState } from "react";
import Head from "next/head";
import Navbar from "../components/Navbar";
import CreditTopupModal from "../components/CreditTopupModal";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth-context";

export default function Dashboard() {
  const { isAuthenticated, user, setAuthModalOpen, refreshWallet } = useAuth();
  const [keys, setKeys] = useState([]);
  const [usage, setUsage] = useState([]);
  const [newKey, setNewKey] = useState(null);
  const [label, setLabel] = useState("");
  const [topupOpen, setTopupOpen] = useState(false);
  const [error, setError] = useState("");

  function load() {
    api.listKeys().then(setKeys).catch(() => {});
    api.getUsage().then(setUsage).catch(() => {});
  }

  useEffect(() => {
    if (isAuthenticated) load();
  }, [isAuthenticated]);

  async function handleCreateKey() {
    try {
      const res = await api.createKey(label || "default");
      setNewKey(res.full_key);
      setLabel("");
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleRevoke(id) {
    await api.revokeKey(id);
    load();
  }

  if (!isAuthenticated) {
    return (
      <>
        <Navbar />
        <div className="max-w-2xl mx-auto px-5 py-20 text-center">
          <p className="text-base-200 mb-4">Sign in to view your dashboard.</p>
          <button onClick={() => setAuthModalOpen(true)} className="px-5 py-2.5 rounded-md bg-accent text-black text-sm font-semibold">
            Sign in
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <Head><title>Dashboard - AfriGate</title></Head>
      <Navbar />

      <main className="max-w-4xl mx-auto px-5 py-10 space-y-10">
        <section>
          <div className="flex items-center justify-between p-5 rounded-xl border border-base-700 bg-base-900">
            <div>
              <p className="text-xs text-base-200 mb-1">Wallet balance</p>
              <p className="text-2xl font-mono font-semibold text-white">
                ${(user.credit_balance / 100000).toFixed(4)}
              </p>
            </div>
            <button
              onClick={() => setTopupOpen(true)}
              className="px-4 py-2 rounded-md bg-accent hover:bg-accent-hover text-black text-sm font-semibold"
            >
              Add credits
            </button>
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">API keys</h2>

          {newKey && (
            <div className="mb-4 p-4 rounded-lg bg-accent-soft border border-accent/40">
              <p className="text-xs text-white mb-1">Copy this key now - it won't be shown again:</p>
              <code className="text-accent font-mono text-sm break-all">{newKey}</code>
            </div>
          )}

          <div className="flex gap-2 mb-4">
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Key label (e.g. production)"
              className="flex-1 px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white placeholder:text-base-400"
            />
            <button onClick={handleCreateKey} className="px-4 py-2 rounded-md bg-base-700 hover:bg-base-600 text-white text-sm font-semibold">
              Create key
            </button>
          </div>

          <div className="rounded-lg border border-base-700 divide-y divide-base-700">
            {keys.length === 0 && <p className="p-4 text-sm text-base-400">No API keys yet.</p>}
            {keys.map((k) => (
              <div key={k.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-sm text-white font-mono">{k.key_prefix}...</p>
                  <p className="text-xs text-base-400">{k.label} - created {new Date(k.created_at).toLocaleDateString()}</p>
                </div>
                {k.is_active ? (
                  <button onClick={() => handleRevoke(k.id)} className="text-xs text-red-400 hover:text-red-300 font-medium">
                    Revoke
                  </button>
                ) : (
                  <span className="text-xs text-base-400">Revoked</span>
                )}
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">Recent usage</h2>
          <div className="rounded-lg border border-base-700 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-base-850 text-left text-base-200 text-xs uppercase">
                  <th className="px-4 py-2 font-medium">Model</th>
                  <th className="px-4 py-2 font-medium">Tokens</th>
                  <th className="px-4 py-2 font-medium">Cost</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">When</th>
                </tr>
              </thead>
              <tbody>
                {usage.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-6 text-center text-base-400">No requests yet.</td></tr>
                )}
                {usage.map((u, i) => (
                  <tr key={i} className="border-t border-base-700">
                    <td className="px-4 py-2 font-mono text-base-100 text-xs">{u.resolved_slug}</td>
                    <td className="px-4 py-2 font-mono text-base-200 text-xs">{u.prompt_tokens + u.completion_tokens}</td>
                    <td className="px-4 py-2 font-mono text-base-200 text-xs">${u.cost_usd.toFixed(5)}</td>
                    <td className="px-4 py-2 text-xs">
                      <span className={u.status === "success" ? "text-accent" : "text-red-400"}>{u.status}</span>
                    </td>
                    <td className="px-4 py-2 text-xs text-base-400">{new Date(u.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <CreditTopupModal open={topupOpen} onClose={() => setTopupOpen(false)} />
    </>
  );
}
