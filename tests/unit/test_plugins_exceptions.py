"""Unit tests for plugin exceptions."""

import pytest
from aios.plugins.exceptions import (
    PluginError,
    PluginLoadError,
    PluginManifestError,
    PluginValidationError,
    PluginVerificationError,
    PluginDependencyError,
    PluginRuntimeError,
    PluginIsolationError,
    PluginPermissionError,
    PluginConfigurationError,
    PluginNotFoundError,
    PluginTimeoutError,
)


class TestPluginExceptions:
    def test_base_plugin_error(self):
        exc = PluginError("something went wrong")
        assert str(exc) == "something went wrong"
        assert exc.plugin_id is None

    def test_plugin_error_with_plugin_id(self):
        exc = PluginError("bad plugin", plugin_id="my-plugin")
        assert exc.plugin_id == "my-plugin"

    def test_all_exceptions_inherit_plugin_error(self):
        classes = [
            PluginLoadError,
            PluginManifestError,
            PluginValidationError,
            PluginVerificationError,
            PluginDependencyError,
            PluginRuntimeError,
            PluginIsolationError,
            PluginPermissionError,
            PluginConfigurationError,
            PluginNotFoundError,
            PluginTimeoutError,
        ]
        for cls in classes:
            exc = cls("error", plugin_id="test")
            assert isinstance(exc, PluginError), f"{cls.__name__} must inherit PluginError"
            assert isinstance(exc, Exception)

    def test_plugin_load_error(self):
        exc = PluginLoadError("failed to load", plugin_id="p1")
        assert exc.plugin_id == "p1"
        assert "failed to load" in str(exc)

    def test_plugin_timeout_error(self):
        exc = PluginTimeoutError("timed out", plugin_id="slow-plugin")
        assert exc.plugin_id == "slow-plugin"
        assert isinstance(exc, PluginError)

    def test_plugin_not_found_error(self):
        exc = PluginNotFoundError("not found", plugin_id="ghost")
        assert exc.plugin_id == "ghost"

    def test_exceptions_are_catchable_as_plugin_error(self):
        with pytest.raises(PluginError):
            raise PluginRuntimeError("crash", plugin_id="p2")

    def test_exceptions_are_catchable_as_exception(self):
        with pytest.raises(Exception):
            raise PluginPermissionError("denied", plugin_id="p3")
