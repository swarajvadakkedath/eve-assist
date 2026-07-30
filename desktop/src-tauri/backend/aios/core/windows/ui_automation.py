"""UI Automation — mouse, keyboard, clicking, typing, shortcuts."""

from .exceptions import UIAutomationError
from .validation import validate_coordinates


class UIAutomationService:
    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        sx, sy = validate_coordinates(x, y)
        try:
            import pyautogui
            pyautogui.click(x=sx, y=sy, button=button, clicks=clicks)
        except ImportError:
            raise UIAutomationError("pyautogui is not installed")
        except Exception as e:
            raise UIAutomationError(f"Failed to click at ({x}, {y}): {e}")

    def double_click(self, x: int, y: int) -> None:
        self.click(x, y, clicks=2)

    def right_click(self, x: int, y: int) -> None:
        self.click(x, y, button="right")

    def type_text(self, text: str, interval: float = 0.0) -> None:
        if not isinstance(text, str):
            raise UIAutomationError("Text must be a string")
        try:
            import pyautogui
            pyautogui.write(text, interval=interval)
        except ImportError:
            raise UIAutomationError("pyautogui is not installed")
        except Exception as e:
            raise UIAutomationError(f"Failed to type text: {e}")

    def press_key(self, key: str) -> None:
        if not key or not key.strip():
            raise UIAutomationError("Key must not be empty")
        try:
            import pyautogui
            pyautogui.press(key)
        except ImportError:
            raise UIAutomationError("pyautogui is not installed")
        except Exception as e:
            raise UIAutomationError(f"Failed to press key '{key}': {e}")

    def hotkey(self, *keys: str) -> None:
        if not keys:
            raise UIAutomationError("At least one key is required for hotkey")
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
        except ImportError:
            raise UIAutomationError("pyautogui is not installed")
        except Exception as e:
            raise UIAutomationError(f"Failed to execute hotkey {keys}: {e}")

    def move_mouse(self, x: int, y: int, duration: float = 0.0) -> None:
        sx, sy = validate_coordinates(x, y)
        try:
            import pyautogui
            pyautogui.moveTo(sx, sy, duration=duration)
        except ImportError:
            raise UIAutomationError("pyautogui is not installed")
        except Exception as e:
            raise UIAutomationError(f"Failed to move mouse to ({x}, {y}): {e}")

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        try:
            import pyautogui
            pyautogui.scroll(clicks, x=x, y=y)
        except ImportError:
            raise UIAutomationError("pyautogui is not installed")
        except Exception as e:
            raise UIAutomationError(f"Failed to scroll: {e}")

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.2) -> None:
        try:
            import pyautogui
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
        except ImportError:
            raise UIAutomationError("pyautogui is not installed")
        except Exception as e:
            raise UIAutomationError(f"Failed to drag from ({start_x}, {start_y}) to ({end_x}, {end_y}): {e}")

    def get_screenshot(self, region: tuple[int, int, int, int] | None = None) -> bytes:
        try:
            import pyautogui
            screenshot = pyautogui.screenshot(region=region)
            import io
            buf = io.BytesIO()
            screenshot.save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            raise UIAutomationError("pyautogui is not installed")
        except Exception as e:
            raise UIAutomationError(f"Failed to capture screenshot: {e}")
