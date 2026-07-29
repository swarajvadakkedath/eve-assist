"""Clipboard operations — get, set, clear, detect changes."""

from .exceptions import ClipboardError


class ClipboardService:
    def get_text(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            raise ClipboardError("pyperclip is not installed")
        except Exception as e:
            raise ClipboardError(f"Failed to read clipboard: {e}")

    def set_text(self, text: str) -> None:
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            raise ClipboardError("pyperclip is not installed")
        except Exception as e:
            raise ClipboardError(f"Failed to write clipboard: {e}")

    def clear(self) -> None:
        self.set_text("")
