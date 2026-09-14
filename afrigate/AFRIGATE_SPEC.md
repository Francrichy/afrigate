# AfriGate — Refined Product & Technical Specification
### (African AI Gateway — OpenRouter-model, Mobile-Money-native)

*Refined against OpenRouter's actual live product (verified Sept 2026), with gaps/improvements marked.*

---

## 1. Reality Check: What OpenRouter Actually Does Today

Your draft assumed a few things about OpenRouter that are worth correcting, because they change your pricing and architecture decisions:

| Assumption in draft | What OpenRouter actually does (verified) | Implication for AfriGate |
|---|---|---|
| "5–10% markup on tokens" | **No token markup.** Provider price passes through unchanged. Instead: a flat **5.5% fee on credit top-ups** (card/crypto), and $0 fee if a user brings their own provider key (BYOK, up to $25k/mo before a 5% fee) | Charge your margin **once, at top-up** (in TZS/KES/NGN), not per-token. Simpler to explain, simpler to reconcile, and matches what developers already expect from OpenRouter. |
| Generic "intelligent routing" | Concrete, named routing modifiers: **`:floor`** (cheapest available provider for a model), **`:nitro`** (fastest), automatic fallback on provider outage | Copy this exact pattern — it's a proven, developer-legible UX. Don't invent new terminology. |
| No mention of catalog trust signals | Public **rankings/leaderboard page** (usage by model, by app), model cards showing context window + $/1M tokens, **zero-data-retention** policy toggle per provider | These are trust-builders specifically for a *new* gateway with no track record yet — copy them from day one. |
| Static credits | Credits **never expire**, no minimum purchase, deducted per-token in real time | Matches your "lifetime credits" instinct from the SwahiliBot/SwahiliStudio work already done — keep that positioning, it's proven to work well for African prepaid mental models. |

**Bottom line:** your architecture instincts (Adapter Pattern, Model Registry, aliasing) are *sound and match how OpenRouter is actually built internally* — the main correction is the **pricing mechanic** (top-up fee, not token markup) and borrowing their exact routing-modifier UX.

---

## 2. Refined Pricing Model

**Recommended: Pass-through + flat top-up fee** (not per-token markup)

```
User loads TZS 20,000 → converted to credits at fixed internal USD peg
                       → platform fee (e.g. 6-8%, higher than OpenRouter's
                         5.5% to cover Mobile Money settlement float + FX risk)
                       → remainder becomes spendable credit balance
Per-request: credit deducted = provider's real token cost (no markup)
```

Why higher than OpenRouter's 5.5%: you're carrying **Mobile Money settlement risk** (PawaPay/Flutterwave T+1 to T+3 settlement) that OpenRouter doesn't have with cards. This is your Model C (Hybrid Reserve + Overflow) from the original doc — correct instinct, keep it, and price the fee to cover it explicitly rather than absorbing it silently.

**BYOK tier**: let verified businesses plug in their own OpenAI/Anthropic keys and pay AfriGate a small flat monthly fee for routing/analytics only — this is what unlocks the "$500+/mo" segment without you carrying their inference cost at all.

---

## 3. Architecture (refined from your draft — confirmed sound)

```
┌─────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│  Developer  │───▶│  AfriGate Gateway     │───▶│ Provider Adapters    │
│  (OpenAI-   │    │  /v1/chat/completions │    │ openai.py            │
│  compatible │    │  - auth (API key)     │    │ anthropic.py         │
│  SDK, no    │    │  - wallet debit       │    │ deepseek.py          │
│  code       │    │  - model registry     │    │ qwen.py              │
│  changes)   │    │    lookup + alias     │    │ groq.py (fast Llama) │
└─────────────┘    │  - routing (:floor/   │    │ together.py          │
                    │    :nitro/fallback)  │    └─────────────────────┘
                    └──────────────────────┘
                            │
                    ┌───────┴────────┐
                    │  PostgreSQL     │  users, api_keys, wallets,
                    │  + Redis        │  model_registry, usage_log,
                    │                 │  webhook_events (idempotent)
                    └────────────────┘
                            │
                    ┌───────┴────────┐
                    │  Payments        │  Flutterwave (primary — already
                    │                 │  supports M-Pesa/MTN MoMo/Airtel/
                    │                 │  Orange across your Phase-1
                    │                 │  countries in ONE integration)
                    └────────────────┘
```

This directly reuses patterns already **built and tested** in this conversation for SwahiliBot/SwahiliStudio: idempotent webhook table, `SELECT ... FOR UPDATE` atomic wallet debits, provider-adapter isolation, alias-based model routing. Nothing here is unproven.

**One correction to your doc**: you listed Paystack *or* Flutterwave as alternatives. Recommend **Flutterwave only for Phase 1** — it already covers M-Pesa (KE/TZ), MTN MoMo (multiple countries), Airtel Money, and cards in one integration, so you avoid maintaining two payment adapters before you have revenue to justify it. Add Paystack later specifically if Nigeria volume demands their better local reconciliation.

---

## 4. Design Direction ("beautiful, developer-first")

Lesson already learned earlier in this project: heavy gradients/glass reads as unprofessional for a *developer tool* specifically (different audience than a consumer app). Developer tools that are considered beautiful (OpenRouter, Stripe, Vercel, Resend) share:

- **Near-black or pure-white flat surfaces**, one accent color only, generous whitespace
- **Monospace for anything technical** (API keys, code snippets, model IDs) — Inter/Sora is right for prose, but code needs `JetBrains Mono` or `IBM Plex Mono`
- **The model catalog IS the homepage** — a searchable/filterable table (provider, price, context, speed), not a marketing hero
- One tasteful, restrained African identity signal (e.g. a thin accent-stripe, or naming models' regional routing after cities — "Lagos edge", "Nairobi edge") rather than decorative background imagery
- Every screen assumes the visitor is a developer mid-integration, not a consumer being sold to — code snippet with **their real API key already filled in** should be visible within one click of signup (OpenRouter and Stripe both do this; it's the single biggest activation-time reducer)

Core screens: **Model Catalog** (home) → **Playground** (test before you code) → **Dashboard** (wallet, usage graph, API keys) → **Docs** (OpenAI-compatible, so mostly "here's what's different") → **Admin Model Registry** (internal only, per your Phase-2 spec).

---

## 5. Phase 1 MVP — concretely scoped

- Backend: **FastAPI** (Python) — matches the two production backends already built and tested in this conversation, so patterns (auth, wallet locking, webhook idempotency) carry over directly instead of being reinvented in Node.
- 8 models at launch across 4 adapters: OpenAI (gpt-4o-mini, gpt-4o), Anthropic (Claude Haiku, Sonnet), DeepSeek (V3), Qwen (Plus), Groq-hosted Llama 3.1 70B (for speed-sensitive `:nitro` demos), one free model for signup activation.
- Flutterwave only, KES + TZS + NGN display currencies, USD-pegged credits internally.
- Manual model toggling in admin (no auto-sync scraper yet — that's Phase 2 as your original doc correctly sequenced it).

---

## Open decisions before I start building

I can start on the actual codebase next — confirming a few concrete choices first will save a rebuild later, same as it did on SwahiliStudio:
