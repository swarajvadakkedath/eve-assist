import { useMemo } from "react";
import CodeBlock from "./CodeBlock";
import StreamingCursor from "./StreamingCursor";

export interface MarkdownRendererProps {
  content: string;
  streaming?: boolean;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

interface CodeBlockData {
  language: string;
  code: string;
}

function parseCodeBlocks(content: string): (string | CodeBlockData)[] {
  const parts: (string | CodeBlockData)[] = [];
  const regex = /```(\w*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }
    parts.push({ language: match[1] || "text", code: match[2] });
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts;
}

function renderInlineMarkdown(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/~~(.+?)~~/g, "<del>$1</del>")
    .replace(/\[(.+?)\]\((.+?)\)/g, (match, text, url) => {
      const scheme = url.split(':')[0].toLowerCase();
      if (['javascript', 'data', 'file', 'vbscript'].includes(scheme)) {
        return text;
      }
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`;
    });
}

function MarkdownRenderer({ content, streaming }: MarkdownRendererProps) {
  const parts = useMemo(() => parseCodeBlocks(content), [content]);

  if (!content) return null;

  return (
    <div className={`pr-md ${streaming ? "pr-md-streaming" : ""}`}>
      {parts.map((part, i) => {
        if (typeof part === "string") {
          const paragraphs = part.split("\n\n").filter(Boolean);
          return (
            <div key={i}>
              {paragraphs.map((para, j) => {
                const trimmed = para.trim();
                if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
                  const items = trimmed.split("\n").filter((l) => l.trim().startsWith("- ") || l.trim().startsWith("* "));
                  return (
                    <ul key={j}>
                      {items.map((item, k) => (
                        <li key={k} dangerouslySetInnerHTML={{ __html: renderInlineMarkdown(item.replace(/^[-*]\s+/, "")) }} />
                      ))}
                    </ul>
                  );
                }
                if (/^\d+\.\s/.test(trimmed)) {
                  const items = trimmed.split("\n").filter((l) => /^\d+\.\s/.test(l.trim()));
                  return (
                    <ol key={j}>
                      {items.map((item, k) => (
                        <li key={k} dangerouslySetInnerHTML={{ __html: renderInlineMarkdown(item.replace(/^\d+\.\s+/, "")) }} />
                      ))}
                    </ol>
                  );
                }
                return <p key={j} dangerouslySetInnerHTML={{ __html: renderInlineMarkdown(trimmed) }} />;
              })}
            </div>
          );
        }
        return <CodeBlock key={i} language={part.language} code={part.code} />;
      })}
      {streaming && <StreamingCursor />}
    </div>
  );
}

export default MarkdownRenderer;
