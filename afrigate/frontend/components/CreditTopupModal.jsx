import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth-context";

const PROVIDER_CURRENCIES = {
  pawapay: ["TZS", "UGX"],
  flutterwave: ["TZS", "KES", "NGN", "GHS", "UGX"],
  paystack: ["KES", "GHS"],
};

const PAWAPAY_NETWORKS = {
  TZS: ["MPESA", "TIGO", "AIRTEL", "HALOTEL"],
  UGX: ["MTN", "AIRTEL"],
};

const PROVIDER_LABELS = {
  pawapay: "PawaPay (Tanzania / Uganda)",
  flutterwave: "Flutterwave (multi-country)",
  paystack: "Paystack (Ghana / Kenya)",
};

const PRESET_AMOUNTS = [5000, 10000, 25000, 50000];

export default function CreditTopupModal({ open, onClose }) {
  const { refreshWallet } = useAuth();
  const [provider, setProvider] = useState("flutterwave");
  const [currency, setCurrency] = useState("KES");
  const [amount, setAmount] = useState(5000);
  const [phone, setPhone] = useState("");
  const [network, setNetwork] = useState("");
  const [step, setStep] = useState("form"); // form | pending | done | error
  const [reference, setReference] = useState(null);
  const [checkoutUrl, setCheckoutUrl] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setStep("form");
      setError("");
      setCurrency(PROVIDER_CURRENCIES[provider][0]);
    }
  }, [open, provider]);

  useEffect(() => {
    if (step !== "pending" || !reference) return;
    const interval = setInterval(async () => {
      try {
        const res = await api.depositStatus(reference);
        if (res.status === "COMPLETED") {
          clearInterval(interval);
          await refreshWallet();
          setStep("done");
        } else if (res.status === "FAILED") {
          clearInterval(interval);
          setError("Payment was not completed.");
          setStep("error");
        }
      } catch (e) {}
    }, 4000);
    return () => clearInterval(interval);
  }, [step, reference, refreshWallet]);

  if (!open) return null;

  async function handleSubmit() {
    setError("");
    try {
      const res = await api.createDeposit({
        provider,
        amount_local: amount,
        currency,
        phone_number: phone || undefined,
        network: network || undefined,
      });
      setReference(res.reference);
      setCheckoutUrl(res.checkout_url);
      setStep("pending");
    } catch (e) {
      setError(e.message);
      setStep("error");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-xl bg-base-900 border border-base-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Add credits</h2>
          <button onClick={onClose} className="text-base-200 hover:text-white">✕</button>
        </div>

        {step === "form" && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-base-200 mb-1.5">Payment provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white"
              >
                {Object.keys(PROVIDER_CURRENCIES).map((p) => (
                  <option key={p} value={p}>{PROVIDER_LABELS[p]}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-base-200 mb-1.5">Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white"
              >
                {PROVIDER_CURRENCIES[provider].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-base-200 mb-1.5">Amount ({currency})</label>
              <div className="flex gap-2 mb-2">
                {PRESET_AMOUNTS.map((a) => (
                  <button
                    key={a}
                    onClick={() => setAmount(a)}
                    className={`px-3 py-1.5 rounded-md text-xs font-semibold border ${
                      amount === a ? "border-accent bg-accent-soft text-accent" : "border-base-700 text-base-200"
                    }`}
                  >
                    {a.toLocaleString()}
                  </button>
                ))}
              </div>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-base-200 mb-1.5">Phone number</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="e.g. 0712345678"
                className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-base-200 mb-1.5">Network</label>
              {provider === "pawapay" ? (
                <select
                  value={network}
                  onChange={(e) => setNetwork(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white"
                >
                  <option value="">Select...</option>
                  {(PAWAPAY_NETWORKS[currency] || []).map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={network}
                  onChange={(e) => setNetwork(e.target.value)}
                  placeholder={provider === "flutterwave" ? "e.g. MTN, AIRTEL" : "e.g. mtn, mpesa, atl"}
                  className="w-full px-3 py-2 rounded-md bg-base-850 border border-base-700 text-sm text-white"
                />
              )}
            </div>

            {error && <p className="text-xs text-red-400">{error}</p>}

            <button
              onClick={handleSubmit}
              className="w-full py-2.5 rounded-md bg-accent hover:bg-accent-hover text-black text-sm font-semibold"
            >
              Continue
            </button>
          </div>
        )}

        {step === "pending" && (
          <div className="text-center py-6 space-y-4">
            <div className="w-12 h-12 mx-auto rounded-full border-4 border-accent-soft border-t-accent animate-spin" />
            <p className="text-white text-sm">
              {checkoutUrl
                ? "Complete the payment using the link below."
                : "Check your phone to authorize the payment."}
            </p>
            {checkoutUrl && (
              <a href={checkoutUrl} target="_blank" rel="noreferrer" className="text-accent text-sm underline">
                Open payment page →
              </a>
            )}
          </div>
        )}

        {step === "done" && (
          <div className="text-center py-6 space-y-3">
            <p className="text-accent text-2xl">✓</p>
            <p className="text-white font-medium">Credits added successfully.</p>
            <button onClick={onClose} className="px-5 py-2 rounded-md bg-accent text-black text-sm font-semibold">
              Done
            </button>
          </div>
        )}

        {step === "error" && (
          <div className="text-center py-6 space-y-3">
            <p className="text-red-400 text-sm">{error}</p>
            <button onClick={() => setStep("form")} className="px-5 py-2 rounded-md bg-base-700 text-white text-sm font-semibold">
              Try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
