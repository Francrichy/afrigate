import { useEffect, useState } from "react";
import Head from "next/head";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth-context";

export default function Playground() {
  const { isAuthenticated, setAuthModalOpen } = useAuth();
  const [models, setModels] = useState([]);
  const [model, setModel] = useState("");
  const [apiKeys, setApiKeys] = useState([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [prompt, setPrompt] = useState("Explain what AfriGate does in one sentence.");
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listModels().then((data) => {
      setModels(data);
      if (data.length) setModel(data[0].slug);
    });
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    api.listKeys().then(setApiKeys).catch(() => {});
  }, [isAuthenticated]);

  async function handleRun() {
    if (!isAuthenticated) {
      setAuthModalOpen(true);
      return;
    }
    if (!selectedKey) {
      setError("Create an API key on the Dashboard first, or paste one below.");
      return;
    }
    setError("");
    setLoading(true);
    setReply("");
    try {
      const res = await api.chatCompletion(selectedKey, {
        model,
        messages: [{ role: "user", content: prompt }],
      });
      setReply(res.choices[0].message.content);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head><title>Playground - AfriGate</title></Head>
      <Navbar />

      <main className="max-w-3xl mx-auto px-5 py-10">
        <h1 className="text-xl font-semibold text-white mb-6">Playground</h1>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-base-200 mb-1.5">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white font-mono"
            >
              {models.map((m) => (
                <option key={m.slug} value={m.slug}>{m.display_name} ({m.slug})</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-base-200 mb-1.5">API key</label>
            {isAuthenticated && apiKeys.length > 0 ? (
              <p className="text-xs text-base-400 mb-1.5">
                Using a key requires the raw key value - paste it below (keys aren't retrievable after creation).
              </p>
            ) : null}
            <input
              type="text"
              value={selectedKey}
              onChange={(e) => setSelectedKey(e.target.value)}
              placeholder="ag_live_..."
              className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white font-mono placeholder:text-base-400"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-base-200 mb-1.5">Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white resize-none"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            onClick={handleRun}
            disabled={loading}
            className="px-5 py-2.5 rounded-md bg-accent hover:bg-accent-hover disabled:opacity-60 text-black text-sm font-semibold"
          >
            {loading ? "Running..." : "Run"}
          </button>

          {reply && (
            <div className="mt-4 p-4 rounded-lg bg-base-850 border border-base-700 text-sm text-white whitespace-pre-wrap">
              {reply}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
