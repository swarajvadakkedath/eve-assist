"""Screen and monitor information — resolution, cursor position, monitor list."""

from .exceptions import MonitorError


class MonitorService:
    def get_monitors(self) -> list[dict]:
        try:
            import screeninfo
            monitors = []
            for m in screeninfo.get_monitors():
                monitors.append({
                    "name": m.name or "",
                    "is_primary": m.is_primary if hasattr(m, "is_primary") else False,
                    "x": m.x if hasattr(m, "x") else 0,
                    "y": m.y if hasattr(m, "y") else 0,
                    "width": m.width,
                    "height": m.height,
                    "width_mm": m.width_mm if hasattr(m, "width_mm") else 0,
                    "height_mm": m.height_mm if hasattr(m, "height_mm") else 0,
                })
            return monitors
        except ImportError:
            raise MonitorError("screeninfo is not installed")
        except Exception as e:
            raise MonitorError(f"Failed to get monitors: {e}")

    def get_cursor_position(self) -> dict:
        try:
            import pyautogui
            x, y = pyautogui.position()
            return {"x": x, "y": y}
        except ImportError:
            raise MonitorError("pyautogui is not installed")
        except Exception as e:
            raise MonitorError(f"Failed to get cursor position: {e}")

    def get_screen_size(self) -> dict:
        try:
            import pyautogui
            width, height = pyautogui.size()
            return {"width": width, "height": height}
        except ImportError:
            raise MonitorError("pyautogui is not installed")
        except Exception as e:
            raise MonitorError(f"Failed to get screen size: {e}")

    def get_active_monitor(self) -> dict:
        try:
            import pyautogui
            cursor_x, cursor_y = pyautogui.position()
            monitors = self.get_monitors()
            for m in monitors:
                if m["x"] <= cursor_x < m["x"] + m["width"] and m["y"] <= cursor_y < m["y"] + m["height"]:
                    return m
            if monitors:
                return monitors[0]
            return {"name": "", "is_primary": True, "x": 0, "y": 0, "width": 1920, "height": 1080, "width_mm": 0, "height_mm": 0}
        except Exception:
            return {"name": "", "is_primary": True, "x": 0, "y": 0, "width": 1920, "height": 1080, "width_mm": 0, "height_mm": 0}
