"""Conversation export — Markdown, HTML, JSON formats."""

import json
from datetime import datetime, timezone
from typing import Any

from aios.conversation.models import Conversation, Message, MessageRole, ToolCall


class ConversationExporter:
    async def export_markdown(self, conversation: Conversation, messages: list[Message]) -> str:
        lines = [
            f"# {conversation.title}",
            f"",
            f"**Date:** {conversation.created_at.isoformat() if conversation.created_at else 'N/A'}",
            f"**Participants:** User, Eve (AIOS)",
            f"**Messages:** {len([m for m in messages if m.role != MessageRole.SYSTEM])}",
            f"",
            f"---",
            f"",
        ]
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                continue
            role_label = "You" if msg.role == MessageRole.USER else "Eve"
            lines.append(f"### {role_label}")
            lines.append(f"*{msg.timestamp.isoformat() if msg.timestamp else 'N/A'}*")
            lines.append(f"")
            lines.append(msg.content)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    lines.append(f"")
                    lines.append(f"> **Tool:** {tc.tool_name} | **Status:** {tc.status.value if hasattr(tc.status, 'value') else tc.status}")
                    if tc.execution_time:
                        lines.append(f"> **Duration:** {tc.execution_time:.2f}s")
            if msg.tokens_used:
                lines.append(f"")
                lines.append(f"*({msg.tokens_used} tokens)*")
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")

        return "\n".join(lines)

    async def export_html(self, conversation: Conversation, messages: list[Message]) -> str:
        parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{conversation.title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; max-width: 800px; margin: 0 auto; padding: 24px; background: #1a1a2e; color: #e0e0e0; }}
h1 {{ color: #7c73ff; }}
.message {{ margin: 16px 0; padding: 12px 16px; border-radius: 8px; }}
.user {{ background: #7c73ff; color: white; margin-left: 40px; }}
.assistant {{ background: #16213e; border: 1px solid #2a2a4a; }}
.system {{ display: none; }}
.timestamp {{ font-size: 11px; color: #a0a0a0; }}
.tool-call {{ font-size: 12px; color: #a0a0a0; margin-top: 4px; }}
.meta {{ font-size: 12px; color: #a0a0a0; text-align: center; margin: 24px 0; }}
pre {{ background: #0f3460; padding: 12px; border-radius: 8px; overflow-x: auto; }}
code {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; }}
</style>
</head>
<body>
<h1>{conversation.title}</h1>
<div class="meta">
<p>Date: {conversation.created_at.isoformat() if conversation.created_at else 'N/A'}</p>
<p>Messages: {len([m for m in messages if m.role != MessageRole.SYSTEM])}</p>
</div>
"""]

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                continue
            role_label = "You" if msg.role == MessageRole.USER else "Eve"
            ts = msg.timestamp.isoformat() if msg.timestamp else ""
            parts.append(f'<div class="message {msg.role.value}">')
            parts.append(f'<strong>{role_label}</strong>')
            parts.append(f'<div class="timestamp">{ts}</div>')
            parts.append(f'<div>{msg.content}</div>')
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    status = tc.status.value if hasattr(tc.status, "value") else tc.status
                    duration = f" | {tc.execution_time:.2f}s" if tc.execution_time else ""
                    parts.append(f'<div class="tool-call">🔧 {tc.tool_name} — {status}{duration}</div>')
            if msg.tokens_used:
                parts.append(f'<div class="tool-call">{msg.tokens_used} tokens</div>')
            parts.append("</div>")

        parts.append("</body></html>")
        return "\n".join(parts)

    async def export_json(self, conversation: Conversation, messages: list[Message]) -> str:
        def msg_to_dict(m: Message) -> dict:
            return {
                "id": m.id,
                "role": m.role.value if hasattr(m.role, "value") else m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "tokens_used": m.tokens_used,
                "tool_calls": [
                    {
                        "tool_name": tc.tool_name,
                        "capability": tc.capability,
                        "parameters": tc.parameters,
                        "status": tc.status.value if hasattr(tc.status, "value") else tc.status,
                        "execution_time": tc.execution_time,
                    }
                    for tc in (m.tool_calls or [])
                ],
                "attachments": m.attachments,
            }

        data = {
            "export_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
                "active_project": conversation.active_project,
                "message_count": len([m for m in messages if m.role != MessageRole.SYSTEM]),
                "metadata": conversation.metadata,
            },
            "messages": [msg_to_dict(m) for m in messages if m.role != MessageRole.SYSTEM],
        }
        return json.dumps(data, indent=2, default=str)
