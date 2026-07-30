"""Clipboard tools."""

from aios.core.tool_manager import ToolResult


async def get_clipboard(params: dict | None = None) -> ToolResult:
    try:
        import pyperclip
        text = pyperclip.paste()
        return ToolResult(success=True, data={"content": text})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def set_clipboard(params: dict) -> ToolResult:
    text = params.get("text", "")
    try:
        import pyperclip
        pyperclip.copy(text)
        return ToolResult(success=True, data={"length": len(text)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))
