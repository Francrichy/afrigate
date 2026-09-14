import { useState } from "react";

export default function CodeBlock({ code, language = "bash" }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="relative rounded-lg border border-base-700 bg-base-950 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-base-700">
        <span className="text-[11px] text-base-400 font-mono">{language}</span>
        <button onClick={copy} className="text-[11px] text-base-200 hover:text-white font-medium">
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="p-4 text-[13px] font-mono text-base-100 overflow-x-auto whitespace-pre">{code}</pre>
    </div>
  );
}
