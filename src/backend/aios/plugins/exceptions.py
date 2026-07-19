"""Plugin-specific exceptions."""

class PluginError(Exception):
    """Base exception for all plugin-related errors."""
    def __init__(self, message: str, plugin_id: str | None = None):
        super().__init__(message)
        self.plugin_id = plugin_id


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""


class PluginManifestError(PluginError):
    """Raised when a plugin manifest is invalid or missing."""


class PluginValidationError(PluginError):
    """Raised when a plugin fails validation."""


class PluginVerificationError(PluginError):
    """Raised when a plugin fails verification."""


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies cannot be resolved."""


class PluginRuntimeError(PluginError):
    """Raised when an error occurs during plugin runtime."""


class PluginIsolationError(PluginError):
    """Raised when a plugin isolation error occurs."""


class PluginPermissionError(PluginError):
    """Raised when a plugin attempts an unauthorized action."""


class PluginConfigurationError(PluginError):
    """Raised when a plugin configuration is invalid."""


class PluginNotFoundError(PluginError):
    """Raised when a plugin is not found."""


class PluginTimeoutError(PluginError):
    """Raised when a plugin operation exceeds its allotted time."""
