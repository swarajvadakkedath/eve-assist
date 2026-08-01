"""Unit tests for PluginValidator."""

import tempfile
import json
from pathlib import Path

import pytest
from aios.plugins.manifest import PluginManifest
from aios.plugins.validator import PluginValidator, ValidationResult


def make_valid_manifest(**overrides) -> PluginManifest:
    data = dict(
        id="test-plugin",
        name="Test Plugin",
        version="1.0.0",
        sdk_version="1.0.0",
        author="Tester",
        entry_point="plugin.py",
    )
    data.update(overrides)
    return PluginManifest(**data)


class TestValidationResult:
    def test_starts_valid(self):
        r = ValidationResult()
        assert r.valid is True
        assert r.errors == []
        assert r.warnings == []

    def test_add_error_marks_invalid(self):
        r = ValidationResult()
        r.add_error("something wrong")
        assert r.valid is False
        assert "something wrong" in r.errors

    def test_add_warning_stays_valid(self):
        r = ValidationResult()
        r.add_warning("hmm")
        assert r.valid is True
        assert "hmm" in r.warnings

    def test_merge(self):
        r1 = ValidationResult()
        r2 = ValidationResult()
        r2.add_error("err")
        r2.add_warning("warn")
        r1.merge(r2)
        assert r1.valid is False
        assert "err" in r1.errors
        assert "warn" in r1.warnings


class TestPluginValidator:
    def setup_method(self):
        self.validator = PluginValidator()

    # --- Required fields ---

    def test_valid_manifest(self):
        m = make_valid_manifest()
        result = self.validator.validate(m)
        assert result.valid, f"Expected valid, got errors: {result.errors}"

    def test_missing_id(self):
        m = make_valid_manifest(id="")
        result = self.validator.validate(m)
        assert not result.valid
        assert any("id" in e.lower() for e in result.errors)

    def test_missing_name(self):
        m = make_valid_manifest(name="")
        result = self.validator.validate(m)
        assert not result.valid

    def test_missing_author(self):
        m = make_valid_manifest(author="")
        result = self.validator.validate(m)
        assert not result.valid

    def test_missing_entry_point(self):
        m = make_valid_manifest(entry_point="")
        result = self.validator.validate(m)
        assert not result.valid

    # --- ID format ---

    def test_invalid_id_uppercase(self):
        m = make_valid_manifest(id="MyPlugin")
        result = self.validator.validate(m)
        assert not result.valid
        assert any("ID" in e or "id" in e.lower() for e in result.errors)

    def test_invalid_id_spaces(self):
        m = make_valid_manifest(id="my plugin")
        result = self.validator.validate(m)
        assert not result.valid

    def test_valid_id_with_hyphens(self):
        m = make_valid_manifest(id="my-plugin-v2")
        result = self.validator.validate(m)
        assert result.valid, f"Errors: {result.errors}"

    def test_valid_id_with_underscores(self):
        m = make_valid_manifest(id="my_plugin")
        result = self.validator.validate(m)
        assert result.valid, f"Errors: {result.errors}"

    # --- Semver validation ---

    def test_invalid_version_format(self):
        m = make_valid_manifest(version="v1.0")
        result = self.validator.validate(m)
        assert not result.valid

    def test_valid_semver_with_prerelease(self):
        m = make_valid_manifest(version="1.0.0-alpha.1")
        result = self.validator.validate(m)
        assert result.valid, f"Errors: {result.errors}"

    # --- Platforms ---

    def test_unknown_platform_gives_warning(self):
        m = make_valid_manifest(platforms=["haiku"])
        result = self.validator.validate(m)
        assert result.valid  # warnings don't fail validation
        assert any("haiku" in w.lower() for w in result.warnings)

    def test_all_platform_is_valid(self):
        m = make_valid_manifest(platforms=["all"])
        result = self.validator.validate(m)
        assert result.valid

    # --- Entry point check with source path ---

    def test_entry_point_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # No plugin.py created → should fail
            m = make_valid_manifest(entry_point="plugin.py")
            result = self.validator.validate(m, source_path=tmpdir)
            assert not result.valid
            assert any("entry point" in e.lower() for e in result.errors)

    def test_entry_point_file_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            m = make_valid_manifest(entry_point="plugin.py")
            result = self.validator.validate(m, source_path=tmpdir)
            assert result.valid, f"Errors: {result.errors}"

    # --- Capabilities ---

    def test_capability_missing_id(self):
        m = make_valid_manifest(capabilities=[{"name": "Say Hello"}])
        result = self.validator.validate(m)
        assert not result.valid

    def test_duplicate_capability_id(self):
        m = make_valid_manifest(
            capabilities=[
                {"id": "cap1", "name": "Cap One"},
                {"id": "cap1", "name": "Cap One Again"},
            ]
        )
        result = self.validator.validate(m)
        assert not result.valid

    def test_capability_missing_name_warning(self):
        m = make_valid_manifest(capabilities=[{"id": "cap1"}])
        result = self.validator.validate(m)
        assert result.valid
        assert any("name" in w.lower() for w in result.warnings)

    # --- Permissions ---

    def test_invalid_permission_format(self):
        m = make_valid_manifest(permissions=["READ ALL FILES"])
        result = self.validator.validate(m)
        assert not result.valid

    def test_valid_permissions(self):
        m = make_valid_manifest(permissions=["filesystem.read", "network:http"])
        result = self.validator.validate(m)
        assert result.valid, f"Errors: {result.errors}"

    # --- Dependency resolution ---

    def test_dependency_satisfied(self):
        m = make_valid_manifest(dependencies={"other-plugin": ">=1.0.0"})
        result = self.validator.validate_dependencies(m, {"other-plugin": "2.0.0"})
        assert result.valid

    def test_dependency_missing(self):
        m = make_valid_manifest(dependencies={"missing-plugin": ">=1.0.0"})
        result = self.validator.validate_dependencies(m, {})
        assert not result.valid
        assert any("missing" in e.lower() for e in result.errors)

    def test_dependency_version_mismatch(self):
        m = make_valid_manifest(dependencies={"dep": ">=2.0.0"})
        result = self.validator.validate_dependencies(m, {"dep": "1.0.0"})
        assert not result.valid

    def test_no_dependencies_always_valid(self):
        m = make_valid_manifest(dependencies={})
        result = self.validator.validate_dependencies(m, {})
        assert result.valid

    # --- Version satisfaction helper ---

    def test_version_satisfies_star(self):
        result = self.validator.validate_dependencies(
            make_valid_manifest(dependencies={"dep": "*"}),
            {"dep": "99.99.99"}
        )
        assert result.valid

    def test_version_satisfies_caret(self):
        result = self.validator.validate_dependencies(
            make_valid_manifest(dependencies={"dep": "^1.0.0"}),
            {"dep": "1.5.0"}
        )
        assert result.valid

    def test_version_caret_major_mismatch(self):
        result = self.validator.validate_dependencies(
            make_valid_manifest(dependencies={"dep": "^2.0.0"}),
            {"dep": "1.9.9"}
        )
        assert not result.valid

    def test_version_tilde(self):
        result = self.validator.validate_dependencies(
            make_valid_manifest(dependencies={"dep": "~1.2.1"}),
            {"dep": "1.2.5"}
        )
        assert result.valid

    def test_version_tilde_minor_mismatch(self):
        result = self.validator.validate_dependencies(
            make_valid_manifest(dependencies={"dep": "~1.2.1"}),
            {"dep": "1.3.0"}
        )
        assert not result.valid
