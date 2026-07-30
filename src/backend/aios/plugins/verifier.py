"""Plugin verifier — platform, compatibility, and package integrity."""

import hashlib
import platform
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

from aios.plugins.manifest import PluginManifest


@dataclass
class VerificationResult:
    """Represents the results of a plugin verification."""
    verified: bool = True
    messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_message(self, msg: str) -> None:
        self.messages.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_failure(self, msg: str) -> None:
        self.messages.append(msg)
        self.verified = False


class PluginVerifier:
    """
    Verifies plugin compatibility and package integrity.
    Separate from validation, verification focuses on environmental and safety checks.
    """

    def __init__(self, aios_version: str = "1.1.0", sdk_version: str = "1.1.0"):
        self._aios_version = aios_version
        self._sdk_version = sdk_version

    async def verify(self, manifest: PluginManifest, source_path: str) -> VerificationResult:
        """Perform a full verification of a plugin package."""
        result = VerificationResult()
        
        # 1. Environmental Compatibility
        self._verify_platform(manifest, result)
        self._verify_aios_compatibility(manifest, result)
        self._verify_sdk_compatibility(manifest, result)
        
        # 2. Package Integrity
        if source_path:
            self._verify_package_completeness(manifest, source_path, result)
            checksum = self.calculate_checksum(source_path)
            result.add_message(f"Package checksum: {checksum}")
            
        # 3. Security (Interface ready for future implementation)
        self._verify_trusted_publisher(manifest, result)
        
        return result

    def _verify_platform(self, manifest: PluginManifest, result: VerificationResult) -> None:
        current_system = platform.system().lower()
        # Handle common naming variations
        if current_system == "darwin": current_system = "macos"
        
        supported = [p.lower() for p in manifest.platforms]
        
        if "all" in supported:
            return
            
        if current_system not in supported:
            # Check for generic 'windows' etc.
            if current_system == "windows" and "windows" in supported: return
            if current_system == "linux" and "linux" in supported: return
            if current_system == "macos" and "macos" in supported: return
            
            result.add_failure(
                f"Platform mismatch. Current: {current_system}, Supported: {manifest.platforms}"
            )

    def _verify_aios_compatibility(self, manifest: PluginManifest, result: VerificationResult) -> None:
        if not manifest.minimum_aios_version:
            return
            
        if not self._version_gte(self._aios_version, manifest.minimum_aios_version):
            result.add_failure(
                f"Incompatible AIOS version. Required: >= {manifest.minimum_aios_version}, Installed: {self._aios_version}"
            )

    def _verify_sdk_compatibility(self, manifest: PluginManifest, result: VerificationResult) -> None:
        if not manifest.sdk_version:
            return
            
        # SDK should be backward compatible within major versions
        if not self._version_compatible(self._sdk_version, manifest.sdk_version):
            result.add_failure(
                f"Incompatible SDK version. Plugin uses: {manifest.sdk_version}, Runtime SDK: {self._sdk_version}"
            )

    def _verify_package_completeness(self, manifest: PluginManifest, source_path: str, result: VerificationResult) -> None:
        path = Path(source_path)
        
        # Check for entry point
        if not (path / manifest.entry_point).exists():
            result.add_failure(f"Missing entry point: {manifest.entry_point}")
            
        # Check for other standard files if they are in manifest
        if manifest.icon and not (path / manifest.icon).exists():
            result.add_warning(f"Plugin icon not found: {manifest.icon}")

    def _verify_trusted_publisher(self, manifest: PluginManifest, result: VerificationResult) -> None:
        # Placeholder for digital signature verification
        result.add_message("Publisher verification skipped (not implemented)")

    def calculate_checksum(self, source_path: str) -> str:
        """Calculate a SHA256 checksum of the plugin directory contents."""
        sha256 = hashlib.sha256()
        path = Path(source_path)
        
        # Walk through all files in a deterministic order
        for f in sorted(path.rglob("*")):
            if f.is_file() and "__pycache__" not in str(f) and not f.name.startswith("."):
                # Use relative path and file content for hash
                sha256.update(str(f.relative_to(path)).encode())
                sha256.update(f.read_bytes())
                
        return sha256.hexdigest()

    def _version_gte(self, v1: str, v2: str) -> bool:
        """Check if v1 >= v2."""
        try:
            p1 = [int(x) for x in v1.split(".")]
            p2 = [int(x) for x in v2.split(".")]
            while len(p1) < 3: p1.append(0)
            while len(p2) < 3: p2.append(0)
            return p1 >= p2
        except Exception:
            return True

    def _version_compatible(self, runtime_v: str, plugin_v: str) -> bool:
        """Check if runtime SDK version is compatible with plugin SDK version."""
        try:
            p_runtime = [int(x) for x in runtime_v.split(".")]
            p_plugin = [int(x) for x in plugin_v.split(".")]
            # Major versions must match, runtime minor must be >= plugin minor
            return p_runtime[0] == p_plugin[0] and p_runtime[1] >= p_plugin[1]
        except Exception:
            return True
