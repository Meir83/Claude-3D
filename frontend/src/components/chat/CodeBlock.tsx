"use client";
import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface Props {
  code: string;
  language?: string;
}

export function CodeBlock({ code, language = "python" }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-3 rounded-xl overflow-hidden border border-surface-500">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-surface-900 border-b border-surface-500">
        <span className="text-xs font-mono text-surface-300">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-surface-400 hover:text-surface-100 transition-colors"
        >
          {copied ? (
            <><Check className="w-3.5 h-3.5 text-emerald-400" /><span className="text-emerald-400">Copied</span></>
          ) : (
            <><Copy className="w-3.5 h-3.5" /><span>Copy</span></>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          padding: "1rem",
          background: "#0d0f14",
          fontSize: "0.75rem",
          lineHeight: "1.6",
        }}
        showLineNumbers
        lineNumberStyle={{ color: "#3d4560", fontSize: "0.65rem" }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
