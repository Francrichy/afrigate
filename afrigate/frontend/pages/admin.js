import { useEffect, useState } from "react";
import Head from "next/head";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth-context";

const EMPTY_FORM = {
  slug: "", display_name: "", adapter: "openai", upstream_model_id: "",
  input_price_per_1m: 0, output_price_per_1m: 0, context_window: 128000,
  is_free: false, tier: "cheap", is_enabled: true,
};

const ADAPTERS = ["openai", "anthropic", "deepseek", "qwen", "groq", "cerebras", "gemini", "mistral", "oxalpha"];

export default function Admin() {
  const { isAuthenticated, setAuthModalOpen } = useAuth();
  const [models, setModels] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [aliasSlug, setAliasSlug] = useState("");
  const [aliasTarget, setAliasTarget] = useState("");
  const [error, setError] = useState("");

  const [suggestions, setSuggestions] = useState([]);
  const [expandedSuggestion, setExpandedSuggestion] = useState(null);
  const [suggestionForm, setSuggestionForm] = useState({});
  const [scanning, setScanning] = useState(false);

  const [platformSettings, setPlatformSettings] = useState(null);
  const [feeInput, setFeeInput] = useState("");
  const [savingFee, setSavingFee] = useState(false);
  const [feeSaved, setFeeSaved] = useState(false);

  const [fxInputs, setFxInputs] = useState({});
  const [savingFx, setSavingFx] = useState(false);
  const [fxSaved, setFxSaved] = useState(false);
  const [syncingFx, setSyncingFx] = useState(false);

  function load() {
    api.adminListModels().then(setModels).catch((e) => setError(e.message));
    api.adminListSuggestions("new").then(setSuggestions).catch(() => {});
    api.adminGetSettings().then((s) => {
      setPlatformSettings(s);
      setFeeInput(String(s.topup_fee_percent));
      setFxInputs({
        usd_to_tzs: String(s.usd_to_tzs), usd_to_kes: String(s.usd_to_kes),
        usd_to_ngn: String(s.usd_to_ngn), usd_to_ghs: String(s.usd_to_ghs), usd_to_ugx: String(s.usd_to_ugx),
      });
    }).catch(() => {});
  }

  useEffect(() => {
    if (isAuthenticated) load();
  }, [isAuthenticated]);

  async function handleUpsert(e) {
    e.preventDefault();
    setError("");
    try {
      await api.adminUpsertModel(form);
      setForm(EMPTY_FORM);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleAlias(e) {
    e.preventDefault();
    setError("");
    try {
      await api.adminSetAlias({ alias_slug: aliasSlug, points_to_slug: aliasTarget });
      setAliasSlug("");
      setAliasTarget("");
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function toggle(slug, enabled) {
    await api.adminToggleModel(slug, enabled);
    load();
  }

  async function runScanNow() {
    setScanning(true);
    setError("");
    try {
      const res = await api.adminRunDiscoveryNow();
      load();
      if (res.new_suggestions_found === 0) {
        setError("Scan complete - no new models found right now. AfriGate already checks automatically every 24h.");
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setScanning(false);
    }
  }

  async function dismissSuggestion(id) {
    await api.adminDismissSuggestion(id);
    load();
  }

  function startPromote(s) {
    setExpandedSuggestion(s.id);
    setSuggestionForm({
      slug: `${s.adapter}/${s.upstream_model_id}`, display_name: s.upstream_model_id,
      adapter: s.adapter, upstream_model_id: s.upstream_model_id,
      input_price_per_1m: 0, output_price_per_1m: 0, context_window: 128000,
      is_free: false, tier: "cheap", is_enabled: true,
    });
  }

  async function confirmPromote(suggestionId) {
    setError("");
    try {
      await api.adminPromoteSuggestion(suggestionId, suggestionForm);
      setExpandedSuggestion(null);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function saveFee() {
    setSavingFee(true);
    setError("");
    try {
      const updated = await api.adminUpdateSettings({ topup_fee_percent: Number(feeInput) });
      setPlatformSettings(updated);
      setFeeSaved(true);
      setTimeout(() => setFeeSaved(false), 2000);
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingFee(false);
    }
  }

  async function saveFxRates() {
    setSavingFx(true);
    setError("");
    try {
      const body = Object.fromEntries(Object.entries(fxInputs).map(([k, v]) => [k, Number(v)]));
      const updated = await api.adminUpdateFxRates(body);
      setPlatformSettings(updated);
      setFxSaved(true);
      setTimeout(() => setFxSaved(false), 2000);
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingFx(false);
    }
  }

  async function syncFxNow() {
    setSyncingFx(true);
    setError("");
    try {
      const updated = await api.adminSyncFxNow();
      setPlatformSettings(updated);
      setFxInputs({
        usd_to_tzs: String(updated.usd_to_tzs), usd_to_kes: String(updated.usd_to_kes),
        usd_to_ngn: String(updated.usd_to_ngn), usd_to_ghs: String(updated.usd_to_ghs), usd_to_ugx: String(updated.usd_to_ugx),
      });
    } catch (e) {
      setError(e.message || "Could not reach the exchange rate service - your existing rates are unchanged.");
    } finally {
      setSyncingFx(false);
    }
  }

  async function toggleFxAuto() {
    try {
      const updated = await api.adminSetFxAutoUpdate(!platformSettings.fx_auto_update_enabled);
      setPlatformSettings(updated);
    } catch (e) {
      setError(e.message);
    }
  }

  if (!isAuthenticated) {
    return (
      <>
        <Navbar />
        <div className="max-w-2xl mx-auto px-5 py-20 text-center">
          <p className="text-base-200 mb-4">Admin sign-in required.</p>
          <button onClick={() => setAuthModalOpen(true)} className="px-5 py-2.5 rounded-md bg-accent text-black text-sm font-semibold">
            Sign in
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <Head><title>Model Registry - AfriGate Admin</title></Head>
      <Navbar />

      <main className="max-w-4xl mx-auto px-5 py-10 space-y-10">
        <h1 className="text-xl font-semibold text-white">Admin</h1>
        {error && <p className="text-sm text-amber-400">{error}</p>}

        {/* --- New Models Detected (the daily-cron feature) --- */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wide">
              New models detected {suggestions.length > 0 && <span className="text-accent">({suggestions.length})</span>}
            </h2>
            <button onClick={runScanNow} disabled={scanning}
              className="text-xs px-3 py-1.5 rounded-md bg-base-800 hover:bg-base-700 text-white font-semibold disabled:opacity-50">
              {scanning ? "Scanning..." : "Scan now"}
            </button>
          </div>
          <p className="text-xs text-base-400 mb-3">
            AfriGate checks every provider automatically once a day and lists anything new here,
            with a plain-language note on what it probably is. You still set the price before it goes live -
            that part can't be guessed reliably.
          </p>

          {suggestions.length === 0 ? (
            <p className="text-sm text-base-400 italic px-4 py-6 rounded-lg border border-base-700 bg-base-900 text-center">
              Nothing new right now. Come back after the next daily scan, or click "Scan now".
            </p>
          ) : (
            <div className="rounded-lg border border-base-700 divide-y divide-base-700">
              {suggestions.map((s) => (
                <div key={s.id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm text-white font-mono">{s.adapter}/{s.upstream_model_id}</p>
                      <p className="text-xs text-base-300 mt-1">{s.suggestion_note}</p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <button onClick={() => startPromote(s)}
                        className="text-xs font-semibold px-2.5 py-1 rounded-md bg-accent-soft text-accent">
                        Add to AfriGate
                      </button>
                      <button onClick={() => dismissSuggestion(s.id)}
                        className="text-xs font-semibold px-2.5 py-1 rounded-md bg-base-800 text-base-400">
                        Dismiss
                      </button>
                    </div>
                  </div>

                  {expandedSuggestion === s.id && (
                    <div className="mt-3 grid grid-cols-2 gap-2 p-3 rounded-md bg-base-850 border border-base-700">
                      <input placeholder="Display name" value={suggestionForm.display_name}
                        onChange={(e) => setSuggestionForm({ ...suggestionForm, display_name: e.target.value })}
                        className="col-span-2 px-3 py-2 rounded-md bg-base-900 border border-base-700 text-sm text-white" />
                      <input type="number" step="0.01" placeholder="Input $/1M" value={suggestionForm.input_price_per_1m}
                        onChange={(e) => setSuggestionForm({ ...suggestionForm, input_price_per_1m: Number(e.target.value) })}
                        className="px-3 py-2 rounded-md bg-base-900 border border-base-700 text-sm text-white" />
                      <input type="number" step="0.01" placeholder="Output $/1M" value={suggestionForm.output_price_per_1m}
                        onChange={(e) => setSuggestionForm({ ...suggestionForm, output_price_per_1m: Number(e.target.value) })}
                        className="px-3 py-2 rounded-md bg-base-900 border border-base-700 text-sm text-white" />
                      <select value={suggestionForm.tier} onChange={(e) => setSuggestionForm({ ...suggestionForm, tier: e.target.value })}
                        className="px-3 py-2 rounded-md bg-base-900 border border-base-700 text-sm text-white">
                        <option value="free">free</option>
                        <option value="cheap">cheap</option>
                        <option value="professional">professional</option>
                      </select>
                      <input type="number" placeholder="Context window" value={suggestionForm.context_window}
                        onChange={(e) => setSuggestionForm({ ...suggestionForm, context_window: Number(e.target.value) })}
                        className="px-3 py-2 rounded-md bg-base-900 border border-base-700 text-sm text-white" />
                      <button onClick={() => confirmPromote(s.id)}
                        className="col-span-2 px-4 py-2 rounded-md bg-accent hover:bg-accent-hover text-black text-sm font-semibold">
                        Confirm - make it live
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* --- Platform pricing settings --- */}
        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">Platform pricing</h2>
          <div className="p-4 rounded-lg border border-base-700 bg-base-900 flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs text-base-400 mb-1">
                Top-up fee (%) - charged once when a customer loads credits. Covers Mobile Money settlement float and FX risk.
              </label>
              <input type="number" step="0.5" min="0" max="50" value={feeInput} onChange={(e) => setFeeInput(e.target.value)}
                className="w-32 px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white font-mono" />
            </div>
            <button onClick={saveFee} disabled={savingFee}
              className="px-4 py-2 rounded-md bg-accent hover:bg-accent-hover text-black text-sm font-semibold disabled:opacity-50">
              {savingFee ? "Saving..." : feeSaved ? "Saved ✓" : "Save"}
            </button>
          </div>
          <p className="text-xs text-base-400 mt-2">
            Applies instantly to every top-up from this moment on - no redeploy needed.
            {platformSettings && ` Current: ${platformSettings.topup_fee_percent}%.`}
          </p>
        </section>

        {/* --- Exchange rates --- */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wide">Exchange rates</h2>
            <label className="flex items-center gap-2 text-xs text-base-300">
              <input type="checkbox" checked={platformSettings?.fx_auto_update_enabled ?? true} onChange={toggleFxAuto} />
              Auto-update daily
            </label>
          </div>

          <div className="p-4 rounded-lg border border-base-700 bg-base-900 space-y-3">
            <div className="grid grid-cols-5 gap-2">
              {["usd_to_tzs", "usd_to_kes", "usd_to_ngn", "usd_to_ghs", "usd_to_ugx"].map((key) => (
                <div key={key}>
                  <label className="block text-[10px] text-base-400 mb-1 font-mono">{key.replace("usd_to_", "").toUpperCase()}</label>
                  <input type="number" step="0.01" value={fxInputs[key] || ""}
                    onChange={(e) => setFxInputs({ ...fxInputs, [key]: e.target.value })}
                    className="w-full px-2 py-1.5 rounded-md bg-base-850 border border-base-700 text-xs text-white font-mono" />
                </div>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button onClick={saveFxRates} disabled={savingFx}
                className="px-4 py-2 rounded-md bg-accent hover:bg-accent-hover text-black text-sm font-semibold disabled:opacity-50">
                {savingFx ? "Saving..." : fxSaved ? "Saved ✓" : "Save manual rates"}
              </button>
              <button onClick={syncFxNow} disabled={syncingFx}
                className="px-4 py-2 rounded-md border border-base-700 hover:border-accent text-white text-sm font-semibold disabled:opacity-50">
                {syncingFx ? "Fetching..." : "Refresh from market now"}
              </button>
            </div>

            <p className="text-xs text-base-400">
              1 USD = local currency shown above. {platformSettings?.fx_source && `Source: ${platformSettings.fx_source}.`}
              {platformSettings?.fx_last_synced_at
                ? ` Last synced: ${new Date(platformSettings.fx_last_synced_at).toLocaleString()}.`
                : " Never auto-synced yet - click 'Refresh from market now' or wait for the daily job."}
              {" "}Auto-updates daily from open.er-api.com when enabled; manual edits above always take effect immediately either way.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">Add / update a model</h2>
          <form onSubmit={handleUpsert} className="grid grid-cols-2 gap-3 p-4 rounded-lg border border-base-700 bg-base-900">
            <input placeholder="slug (e.g. openai/gpt-5)" value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
              className="col-span-2 px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white font-mono" required />
            <input placeholder="Display name" value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              className="px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white" required />
            <select value={form.adapter} onChange={(e) => setForm({ ...form, adapter: e.target.value })}
              className="px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white">
              {ADAPTERS.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
            <input placeholder="Upstream model id" value={form.upstream_model_id}
              onChange={(e) => setForm({ ...form, upstream_model_id: e.target.value })}
              className="col-span-2 px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white font-mono" required />
            <input type="number" step="0.01" placeholder="Input $/1M" value={form.input_price_per_1m}
              onChange={(e) => setForm({ ...form, input_price_per_1m: Number(e.target.value) })}
              className="px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white" />
            <input type="number" step="0.01" placeholder="Output $/1M" value={form.output_price_per_1m}
              onChange={(e) => setForm({ ...form, output_price_per_1m: Number(e.target.value) })}
              className="px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white" />
            <select value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })}
              className="px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white">
              <option value="free">free</option>
              <option value="cheap">cheap</option>
              <option value="professional">professional</option>
            </select>
            <input type="number" placeholder="Context window" value={form.context_window}
              onChange={(e) => setForm({ ...form, context_window: Number(e.target.value) })}
              className="px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white" />
            <label className="flex items-center gap-2 text-sm text-base-200">
              <input type="checkbox" checked={form.is_free} onChange={(e) => setForm({ ...form, is_free: e.target.checked })} />
              Free model
            </label>
            <button type="submit" className="px-4 py-2 rounded-md bg-accent hover:bg-accent-hover text-black text-sm font-semibold">
              Save model
            </button>
          </form>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">Create / repoint an alias</h2>
          <form onSubmit={handleAlias} className="flex gap-2 p-4 rounded-lg border border-base-700 bg-base-900">
            <input placeholder="alias (e.g. claude-latest)" value={aliasSlug}
              onChange={(e) => setAliasSlug(e.target.value)}
              className="flex-1 px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white font-mono" required />
            <span className="text-base-400 self-center">→</span>
            <input placeholder="target slug" value={aliasTarget}
              onChange={(e) => setAliasTarget(e.target.value)}
              className="flex-1 px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white font-mono" required />
            <button type="submit" className="px-4 py-2 rounded-md bg-base-700 hover:bg-base-600 text-white text-sm font-semibold">
              Set alias
            </button>
          </form>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">All models</h2>
          <div className="rounded-lg border border-base-700 divide-y divide-base-700">
            {models.map((m) => (
              <div key={m.slug} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-sm text-white font-mono">{m.slug}</p>
                  <p className="text-xs text-base-400">{m.display_name} · {m.tier}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-base-400 font-mono">
                    ${m.input_price_per_1m}/${m.output_price_per_1m}
                  </span>
                  <button onClick={() => toggle(m.slug, !m.is_enabled)}
                    className={`text-xs font-semibold px-2.5 py-1 rounded-md ${
                      m.is_enabled ? "bg-accent-soft text-accent" : "bg-base-800 text-base-400"
                    }`}>
                    {m.is_enabled ? "Enabled" : "Disabled"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
