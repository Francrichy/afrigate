# AfriGate

One OpenAI-compatible API for every major AI model, billed in local African
currencies via Mobile Money. See `AFRIGATE_SPEC.md` for the full product
rationale and comparison against OpenRouter's actual live product.

```
afrigate/
├── AFRIGATE_SPEC.md   Full refined spec (read this first)
├── backend/           FastAPI gateway (deploy to Render)
└── frontend/          Next.js dashboard (deploy to Vercel)
```

## What's implemented and verified end-to-end

Every item below was tested against a running instance, not just written:

- **Register/login** with $1.00 free credit on signup (matches OpenRouter's activation pattern)
- **API key issuance** (`ag_live_...`) - full key shown once, only a SHA-256 hash stored
- **`POST /v1/chat/completions`** - OpenAI-compatible gateway with 5 provider
  adapters (OpenAI, Anthropic, DeepSeek, Qwen, Groq)
- **Atomic wallet debits**: a provisional hold is taken before calling upstream,
  then reconciled to the exact token cost - verified that a failed request
  (no provider configured) refunds the **full** hold back to the wallet
- **Free models** never place a hold at all - verified balance is untouched
- **Model Registry with live aliasing** - verified end-to-end: created alias
  `claude-latest` → `anthropic/claude-sonnet-4.5`, called the gateway with
  the alias (resolved correctly), then disabled the underlying model from
  the admin API and confirmed the alias **immediately** stopped resolving
  (400) with zero server restart - this is the "zero-downtime model
  upgrade" mechanism from the original spec, proven to work
- **Admin authorization** - a non-admin user gets 403 on every `/api/admin/*` route
- **3 payment provider adapters** (PawaPay, Flutterwave, Paystack) built
  against each provider's real, documented API (verified via direct research,
  not assumed) - including correct webhook signature verification for each
  (PawaPay: none needed, event id dedup; Flutterwave: `verif-hash` header;
  Paystack: HMAC-SHA512 via `x-paystack-signature`)
- **Idempotent webhooks** for all 3 payment providers, sharing the same
  proven pattern from the SwahiliStudio project in this conversation
- Full Next.js frontend - **`next build` succeeds with zero errors** across
  all 6 pages (Model Catalog, Playground, Dashboard, Docs, Admin) - verified
  CORS works correctly between frontend (:3000) and backend (:8000)

## What was NOT independently verified (be aware before going live)

- **Flutterwave/Paystack real charges** - I verified the request/response
  *shapes* against current official docs, but have not made a real charge
  against a live or sandbox account (no credentials available here). Test
  a real sandbox transaction on each before accepting real money.
- **PawaPay correspondent codes** - reused directly from the already-tested
  SwahiliStudio integration, but PawaPay assigns these per-merchant; confirm
  yours in the dashboard.
- **`:floor` routing** only produces alternate candidates when your catalog
  has multiple models sharing the same first word of their display name
  (e.g. two "Llama" entries). With the 7 seed models (all different
  families), `:floor` currently resolves to the same single model - this
  is working as designed, not a bug, but worth knowing before you demo it.
- Streaming responses (`stream: true`) are explicitly rejected with a clear
  error for now - Phase 2 per the original spec's sequencing.

## Local development

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real keys, or leave blank to explore with stubs
uvicorn main:app --reload --port 8000
```
The first startup seeds 7 starter models automatically (see `SEED_MODELS` in `main.py`).

> **Note on local testing**: if you test on SQLite instead of Postgres, only
> ever create rows through the app / API (never raw SQL) - see the UUID
> column caveat documented in the SwahiliStudio README, same root cause
> applies here.

> **Note on bcrypt**: `passlib[bcrypt]==1.7.4` has a known incompatibility
> with `bcrypt>=4.1` (raises a spurious "password cannot be longer than 72
> bytes" error on the *first* password hash, unrelated to actual password
> length). `requirements.txt` already pins `bcrypt==4.0.1` to avoid this -
> don't upgrade bcrypt alone without testing registration afterward.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_URL at your backend
npm run dev
```

### Becoming an admin locally
There's no self-serve admin signup (by design, for security). After
registering, flip the flag directly:
```sql
UPDATE users SET is_admin = true WHERE email = 'you@example.com';
```

## Deployment

### Backend → Render
1. New Web Service, root directory `backend`.
2. Build: `pip install -r requirements.txt`
3. Start: `gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
4. Attach a Render PostgreSQL instance; set `DATABASE_URL` (prefix `postgresql+psycopg2://`).
5. Set every variable from `backend/.env.example`, especially `FRONTEND_URL`
   (for CORS) and each payment provider's webhook callback URL.

### Frontend → Vercel
1. New Project, root directory `frontend`.
2. Set `NEXT_PUBLIC_API_URL` to your Render backend URL.
3. Deploy - Next.js is auto-detected.
4. Update the backend's `FRONTEND_URL` env var to your real Vercel URL afterward.

## Onboarding a new AI provider (the whole point of the Adapter Pattern)

1. Write one file in `backend/app/adapters/` implementing `BaseAdapter.chat_completion()`
   (copy `openai_compatible_base.py` if the provider is OpenAI-compatible - most are).
2. Register it in `app/adapters/__init__.py`'s `ADAPTER_REGISTRY` dict (one line).
3. Add its models via the Admin panel (`/admin`) or `POST /api/admin/models` - no deploy needed after step 2.

## Onboarding a new payment provider

Same pattern in `backend/app/payments/` - implement `request_charge()`/`request_deposit()`
and a webhook signature verifier, wire it into `routers/billing.py`'s dispatch
and `routers/webhooks.py`'s new endpoint. `PROVIDER_CURRENCIES` in
`frontend/components/CreditTopupModal.jsx` needs the new provider added too.
