import Head from "next/head";
import Navbar from "../components/Navbar";
import CodeBlock from "../components/CodeBlock";
import { API_BASE } from "../lib/api";

export default function Docs() {
  const exampleKey = "ag_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";

  const curlSnippet = `curl ${API_BASE}/v1/chat/completions \\
  -H "Authorization: Bearer ${exampleKey}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "anthropic/claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello"}]
  }'`;

  const pythonSnippet = `from openai import OpenAI

client = OpenAI(
    base_url="${API_BASE}/v1",
    api_key="${exampleKey}",
)

response = client.chat.completions.create(
    model="anthropic/claude-sonnet-4.5",
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.choices[0].message.content)`;

  const nodeSnippet = `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "${API_BASE}/v1",
  apiKey: "${exampleKey}",
});

const response = await client.chat.completions.create({
  model: "anthropic/claude-sonnet-4.5",
  messages: [{ role: "user", content: "Hello" }],
});
console.log(response.choices[0].message.content);`;

  const routingSnippet = `# Cheapest available provider for this model family
"model": "openai/gpt-4o-mini:floor"

# Fastest available inference (routes to Groq when available)
"model": "openai/gpt-4o-mini:nitro"

# Pinned to a specific version - never changes under you
"model": "anthropic/claude-sonnet-4.5"

# Auto-upgrading alias - admin can repoint this to a newer model any time
"model": "claude-latest"`;

  return (
    <>
      <Head><title>Docs - AfriGate</title></Head>
      <Navbar />

      <main className="max-w-3xl mx-auto px-5 py-10 space-y-10">
        <div>
          <h1 className="text-2xl font-semibold text-white mb-2">Quickstart</h1>
          <p className="text-base-200">
            AfriGate is fully OpenAI-compatible. If you already use the OpenAI SDK, change two lines
            - <code className="font-mono text-accent">base_url</code> and{" "}
            <code className="font-mono text-accent">api_key</code> - and everything else works unchanged.
          </p>
        </div>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">1. Get an API key</h2>
          <p className="text-sm text-base-200 mb-3">Sign in, then create a key on your <a href="/dashboard" className="text-accent underline">Dashboard</a>. Keys are shown once - store them securely.</p>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">2. Make a request</h2>
          <div className="space-y-4">
            <CodeBlock language="bash" code={curlSnippet} />
            <CodeBlock language="python" code={pythonSnippet} />
            <CodeBlock language="javascript" code={nodeSnippet} />
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">Routing modifiers</h2>
          <p className="text-sm text-base-200 mb-3">
            Append <code className="font-mono text-accent">:floor</code> or{" "}
            <code className="font-mono text-accent">:nitro</code> to any model slug to control routing:
          </p>
          <CodeBlock language="text" code={routingSnippet} />
        </section>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">Pricing</h2>
          <p className="text-sm text-base-200">
            Provider token costs are passed through with no per-token markup. AfriGate's fee is charged
            once, when you add credits to your wallet - see the <a href="/" className="text-accent underline">model catalog</a> for
            live per-model pricing.
          </p>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">Errors</h2>
          <ul className="text-sm text-base-200 space-y-1.5 list-disc list-inside">
            <li><code className="font-mono text-base-100">401</code> - invalid or revoked API key</li>
            <li><code className="font-mono text-base-100">400</code> - unknown model slug</li>
            <li><code className="font-mono text-base-100">402</code> - insufficient wallet balance</li>
            <li><code className="font-mono text-base-100">502</code> - all providers in the fallback chain failed (credits are refunded automatically)</li>
          </ul>
        </section>
      </main>
    </>
  );
}
