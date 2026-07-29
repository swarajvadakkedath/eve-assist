import { useState } from "react";

export interface CodeBlockProps {
  language: string;
  code: string;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function CodeBlock({ language, code }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <div className="pr-code-block">
      <div className="pr-code-block-header">
        <span className="pr-code-block-lang">{language || "text"}</span>
        <button className="pr-code-block-copy" onClick={handleCopy} aria-label={copied ? "Copied" : "Copy code"}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="pr-code-block-body">
        <code>{escapeHtml(code)}</code>
      </pre>
    </div>
  );
}

export default CodeBlock;
