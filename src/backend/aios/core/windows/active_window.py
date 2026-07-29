"""Active window detection — foreground window, title, process info."""

from .exceptions import ActiveWindowError


class ActiveWindowService:
    def get_active_window(self) -> dict:
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window is None:
                return {"title": "", "app": "", "x": 0, "y": 0, "width": 0, "height": 0, "process_id": 0, "process_name": ""}
            title = window.title or ""
            app = title.split(" - ")[-1] if " - " in title else title
            result = {
                "title": title,
                "app": app,
                "x": window.left or 0,
                "y": window.top or 0,
                "width": window.width or 0,
                "height": window.height or 0,
                "process_id": 0,
                "process_name": "",
            }
            try:
                import psutil
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        if proc.info["name"] and proc.info["name"].lower() in app.lower():
                            result["process_id"] = proc.info["pid"]
                            result["process_name"] = proc.info["name"] or ""
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except ImportError:
                pass
            return result
        except ImportError:
            raise ActiveWindowError("pygetwindow is not installed")
        except Exception as e:
            raise ActiveWindowError(f"Failed to get active window: {e}")

    def get_window_by_title(self, title_substring: str) -> list[dict]:
        if not title_substring or not title_substring.strip():
            raise ActiveWindowError("Title substring must not be empty")
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_substring)
            results = []
            for w in windows:
                title = w.title or ""
                results.append({
                    "title": title,
                    "x": w.left or 0,
                    "y": w.top or 0,
                    "width": w.width or 0,
                    "height": w.height or 0,
                })
            return results
        except ImportError:
            raise ActiveWindowError("pygetwindow is not installed")
        except Exception as e:
            raise ActiveWindowError(f"Failed to search windows: {e}")

    def get_all_window_titles(self) -> list[str]:
        try:
            import pygetwindow as gw
            return [w.title for w in gw.getAllWindows() if w.title]
        except ImportError:
            raise ActiveWindowError("pygetwindow is not installed")
        except Exception as e:
            raise ActiveWindowError(f"Failed to list windows: {e}")
