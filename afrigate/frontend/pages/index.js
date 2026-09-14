import { useEffect, useMemo, useState } from "react";
import Head from "next/head";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";

export default function ModelCatalog() {
  const [models, setModels] = useState([]);
  const [query, setQuery] = useState("");
  const [activeTier, setActiveTier] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listModels()
      .then(setModels)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const TIERS = [
    { id: "all", label: "All models" },
    { id: "free", label: "Free" },
    { id: "cheap", label: "Cheap" },
    { id: "professional", label: "Professional" },
  ];

  const TIER_BADGE = {
    free: "bg-accent/15 text-accent",
    cheap: "bg-amber-500/15 text-amber-400",
    professional: "bg-indigo-500/15 text-indigo-300",
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return models
      .filter((m) => activeTier === "all" || m.tier === activeTier)
      .filter((m) => !q || m.slug.toLowerCase().includes(q) || m.display_name.toLowerCase().includes(q));
  }, [models, query, activeTier]);

  return (
    <>
      <Head>
        <title>AfriGate - One API for every AI model</title>
        <meta name="description" content="Pay for OpenAI, Anthropic, DeepSeek, Qwen, and more with Mobile Money. One API key, one wallet, built for Africa." />
      </Head>
      <Navbar />

      <main className="max-w-6xl mx-auto px-5 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-white mb-2">One API for every AI model</h1>
          <p className="text-base-200 max-w-2xl">
            Pay with M-Pesa, MTN MoMo, Airtel Money, or a card. One API key, one wallet,
            OpenAI-compatible - change your <code className="font-mono text-accent">base_url</code> and go.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-5">
          {TIERS.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTier(t.id)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                activeTier === t.id
                  ? "border-accent bg-accent/10 text-white"
                  : "border-base-700 text-base-200 hover:border-base-600"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search models..."
          className="w-full max-w-sm mb-6 px-3.5 py-2 rounded-md bg-base-850 border border-base-700 focus:border-accent outline-none text-sm text-white placeholder:text-base-400"
        />

        {loading && <p className="text-base-200 text-sm">Loading models...</p>}
        {error && <p className="text-red-400 text-sm">{error}</p>}

        {!loading && !error && (
          <div className="rounded-xl border border-base-700 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-base-850 text-left text-base-200 text-xs uppercase tracking-wide">
                  <th className="px-4 py-3 font-medium">Model</th>
                  <th className="px-4 py-3 font-medium">Context</th>
                  <th className="px-4 py-3 font-medium">Input / 1M</th>
                  <th className="px-4 py-3 font-medium">Output / 1M</th>
                  <th className="px-4 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((m) => (
                  <tr key={m.slug} className="border-t border-base-700 hover:bg-base-850/60">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{m.display_name}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${TIER_BADGE[m.tier] || ""}`}>
                          {m.tier}
                        </span>
                      </div>
                      <div className="text-base-400 font-mono text-xs">{m.slug}</div>
                    </td>
                    <td className="px-4 py-3 text-base-200 font-mono">{m.context_window.toLocaleString()}</td>
                    <td className="px-4 py-3 text-base-200 font-mono">
                      {m.is_free ? <span className="text-accent">Free</span> : `$${m.input_price_per_1m.toFixed(2)}`}
                    </td>
                    <td className="px-4 py-3 text-base-200 font-mono">
                      {m.is_free ? <span className="text-accent">Free</span> : `$${m.output_price_per_1m.toFixed(2)}`}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <a href="/playground" className="text-accent text-xs font-semibold hover:underline">
                        Try it →
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}
