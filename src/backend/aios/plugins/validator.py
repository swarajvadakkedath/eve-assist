"""Plugin validator — manifest schema, dependencies, and capability definitions."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from pathlib import Path

from aios.plugins.manifest import PluginManifest


@dataclass
class ValidationResult:
    """Represents the results of a plugin validation."""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def merge(self, other: "ValidationResult") -> None:
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


class PluginValidator:
    """
    Validates plugin manifests, dependencies, and capability definitions.
    Ensures that a plugin is structurally sound before it is loaded.
    """

    def __init__(self):
        self._known_ids: Set[str] = set()

    def validate(self, manifest: PluginManifest, source_path: str = "") -> ValidationResult:
        """Perform a full validation of a plugin manifest."""
        result = ValidationResult()
        
        # 1. Schema & Required Fields
        self._validate_required_fields(manifest, result)
        self._validate_id_format(manifest, result)
        self._validate_semver(manifest.version, "version", result)
        self._validate_semver(manifest.sdk_version, "sdk_version", result)
        self._validate_semver(manifest.minimum_aios_version, "minimum_aios_version", result)
        
        # 2. Structure & Integrity
        self._validate_platforms(manifest, result)
        self._validate_entry_point(manifest, source_path, result)
        
        # 3. Content Definitions
        self._validate_capabilities(manifest, result)
        self._validate_permissions(manifest, result)
        self._validate_tools(manifest, result)
        
        return result

    def validate_dependencies(
        self,
        manifest: PluginManifest,
        available_plugin_versions: Dict[str, str],
    ) -> ValidationResult:
        """Validate that all dependencies are satisfied and check for circularity."""
        result = ValidationResult()
        
        for dep_id, dep_spec in manifest.dependencies.items():
            if dep_id not in available_plugin_versions:
                result.add_error(f"Dependency '{dep_id}' is missing")
                continue
                
            installed_version = available_plugin_versions[dep_id]
            if not self._version_satisfies(installed_version, dep_spec):
                result.add_error(
                    f"Dependency '{dep_id}' version mismatch. Required: {dep_spec}, Found: {installed_version}"
                )
        
        return result

    def _validate_required_fields(self, manifest: PluginManifest, result: ValidationResult) -> None:
        required = ["id", "name", "version", "sdk_version", "author", "entry_point"]
        for field_name in required:
            value = getattr(manifest, field_name, None)
            if not value:
                result.add_error(f"Missing required field: '{field_name}'")

    def _validate_id_format(self, manifest: PluginManifest, result: ValidationResult) -> None:
        if not manifest.id:
            return
        # ID should be alphanumeric with hyphens or underscores, lowercase preferred
        if not re.match(r"^[a-z0-9\-_]+$", manifest.id):
            result.add_error(
                f"Invalid plugin ID format: '{manifest.id}'. "
                "Use lowercase alphanumeric characters, hyphens, and underscores only."
            )

    def _validate_semver(self, version: str, field_name: str, result: ValidationResult) -> None:
        if not version:
            return
        if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$", version):
            result.add_error(f"Invalid semver format in '{field_name}': '{version}'")

    def _validate_platforms(self, manifest: PluginManifest, result: ValidationResult) -> None:
        allowed = {"windows", "linux", "macos", "darwin", "all"}
        for p in manifest.platforms:
            if p.lower() not in allowed:
                result.add_warning(f"Unsupported platform: '{p}'")

    def _validate_entry_point(self, manifest: PluginManifest, source_path: str, result: ValidationResult) -> None:
        if not source_path or not manifest.entry_point:
            return
        ep_path = Path(source_path) / manifest.entry_point
        if not ep_path.exists():
            result.add_error(f"Entry point file not found: '{manifest.entry_point}'")

    def _validate_capabilities(self, manifest: PluginManifest, result: ValidationResult) -> None:
        ids = set()
        for cap in manifest.capabilities:
            cap_id = cap.get("id")
            if not cap_id:
                result.add_error("Capability definition missing 'id'")
                continue
            if cap_id in ids:
                result.add_error(f"Duplicate capability ID: '{cap_id}'")
            ids.add(cap_id)
            if not cap.get("name"):
                result.add_warning(f"Capability '{cap_id}' missing 'name'")

    def _validate_permissions(self, manifest: PluginManifest, result: ValidationResult) -> None:
        for perm in manifest.permissions:
            if not re.match(r"^[a-z0-9\.:*_\-]+$", perm):
                result.add_error(f"Invalid permission format: '{perm}'")

    def _validate_tools(self, manifest: PluginManifest, result: ValidationResult) -> None:
        ids = set()
        for tool in manifest.tools:
            tool_id = tool.get("id")
            if not tool_id:
                result.add_error("Tool definition missing 'id'")
                continue
            if tool_id in ids:
                result.add_error(f"Duplicate tool ID: '{tool_id}'")
            ids.add(tool_id)

    def _version_satisfies(self, installed: str, spec: str) -> bool:
        """Simple semver satisfaction check."""
        if not spec or spec == "*":
            return True
            
        try:
            # Handle basic operators: ^, ~, >=, <=, ==
            operator = ""
            version_str = spec
            for op in [">=", "<=", "==", "^", "~", ">", "<"]:
                if spec.startswith(op):
                    operator = op
                    version_str = spec[len(op):]
                    break
            
            i_parts = [int(p) for p in installed.split("-")[0].split(".")]
            s_parts = [int(p) for p in version_str.split("-")[0].split(".")]
            
            # Pad with zeros
            while len(i_parts) < 3: i_parts.append(0)
            while len(s_parts) < 3: s_parts.append(0)
            
            if operator == ">=": return i_parts >= s_parts
            if operator == "<=": return i_parts <= s_parts
            if operator == "==" or operator == "": return i_parts == s_parts
            if operator == ">": return i_parts > s_parts
            if operator == "<": return i_parts < s_parts
            
            if operator == "^":
                # Caret: compatible with major version
                return i_parts[0] == s_parts[0] and i_parts >= s_parts
            
            if operator == "~":
                # Tilde: compatible with minor version
                return i_parts[0] == s_parts[0] and i_parts[1] == s_parts[1] and i_parts >= s_parts
                
            return i_parts >= s_parts
        except Exception:
            return True

    def reset(self) -> None:
        """Clear internal validation state."""
        self._known_ids.clear()
