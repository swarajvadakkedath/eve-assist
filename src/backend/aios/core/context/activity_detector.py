"""Activity Detector — infers user activity from app name and window title."""

from .models import ActivityType


IDE_APPS = {
    "code", "code - insiders", "visual studio code", "vscode", "vscodium",
    "idea", "intellij idea", "intellij",
    "pycharm", "webstorm", "clion", "goland", "rider",
    "sublime text", "sublime_text",
    "atom", "brackets",
    "vim", "nvim", "neovim", "gvim",
    "emacs", "gnu emacs",
    "xcode",
    "android studio",
    "eclipse", "eclipse ide",
    "netbeans",
    "qt creator",
    "zed",
    "helix",
}

BROWSER_APPS = {
    "chrome", "google chrome", "chromium",
    "firefox", "mozilla firefox", "nightly",
    "edge", "microsoft edge", "msedge",
    "opera", "opera gx", "vivaldi", "brave", "arc",
}

OFFICE_APPS = {
    "winword", "microsoft word", "word",
    "excel", "microsoft excel",
    "powerpnt", "microsoft powerpoint", "powerpoint",
    "outlook", "microsoft outlook",
    "onenote", "microsoft onenote",
    "teams", "microsoft teams",
    "slack",
    "notion",
    "obsidian",
    "logseq",
    "todoist",
    "zoom",
    "discord",
}

TERMINAL_APPS = {
    "windows terminal", "wt",
    "cmd", "command prompt",
    "powershell", "windows powershell",
    "terminal",
    "mobaxterm",
    "putty",
    "hyper",
    "iterm2",
    "alacritty",
    "kitty",
    "wezterm",
    "tmux",
}


def detect_activity(app_name: str | None, window_title: str | None = None) -> ActivityType:
    if not app_name:
        return ActivityType.IDLE

    app_lower = app_name.strip().lower()
    title_lower = (window_title or "").strip().lower()

    if _is_idle(app_lower):
        return ActivityType.IDLE

    if _is_browser(app_lower):
        return ActivityType.BROWSING

    if _is_ide(app_lower, title_lower):
        return ActivityType.CODING

    if _is_terminal(app_lower, title_lower):
        return ActivityType.CODING

    if _is_office(app_lower):
        return ActivityType.OFFICE

    if _is_writing(title_lower):
        return ActivityType.WRITING

    return ActivityType.UNKNOWN


def extract_active_file(app_name: str | None, window_title: str | None) -> str | None:
    if not window_title or not app_name:
        return None
    app_lower = app_name.strip().lower()
    title = window_title.strip()

    if app_lower in IDE_APPS or app_lower in TERMINAL_APPS:
        return _extract_file_from_title(title)

    return None


def _is_idle(app: str) -> bool:
    return app in {"", "lockapp", "logonui", "screen saver"}


def _is_browser(app: str) -> bool:
    return any(b in app for b in BROWSER_APPS)


def _is_ide(app: str, title: str) -> bool:
    if any(ide in app for ide in IDE_APPS):
        return True
    return False


def _is_terminal(app: str, title: str) -> bool:
    if any(t in app for t in TERMINAL_APPS):
        return True
    return False


def _is_office(app: str) -> bool:
    return any(o in app for o in OFFICE_APPS)


def _is_writing(title: str) -> bool:
    keywords = [" - word", " - docs", " - doc", ".docx", " google docs", " - writer"]
    return any(k in title for k in keywords)


def _extract_file_from_title(title: str) -> str | None:
    import re
    patterns = [
        r"^(.+?)\s+[–—-]\s+.+$",
        r"^(.+?)\s+-\s+.+$",
    ]
    for pattern in patterns:
        match = re.match(pattern, title)
        if match:
            candidate = match.group(1).strip()
            if "." in candidate and len(candidate) < 300:
                return candidate
    return None
