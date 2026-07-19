"""Unit tests for PluginVerifier."""

import tempfile
import platform
from pathlib import Path

import pytest
from aios.plugins.manifest import PluginManifest
from aios.plugins.verifier import PluginVerifier, VerificationResult


def make_manifest(**overrides) -> PluginManifest:
    data = dict(
        id="test-plugin",
        name="Test Plugin",
        version="1.0.0",
        sdk_version="1.0.0",
        author="Tester",
        entry_point="plugin.py",
        platforms=["all"],
        minimum_aios_version="1.0.0",
    )
    data.update(overrides)
    return PluginManifest(**data)


class TestVerificationResult:
    def test_starts_verified(self):
        r = VerificationResult()
        assert r.verified is True
        assert r.messages == []

    def test_add_failure_marks_unverified(self):
        r = VerificationResult()
        r.add_failure("bad thing")
        assert r.verified is False
        assert "bad thing" in r.messages

    def test_add_message_stays_verified(self):
        r = VerificationResult()
        r.add_message("informational")
        assert r.verified is True


class TestPluginVerifier:
    def setup_method(self):
        self.verifier = PluginVerifier(aios_version="2.0.0", sdk_version="1.0.0")

    # --- Platform checks ---

    @pytest.mark.asyncio
    async def test_platform_all_always_passes(self):
        m = make_manifest(platforms=["all"])
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            result = await self.verifier.verify(m, tmpdir)
        assert result.verified

    @pytest.mark.asyncio
    async def test_platform_current_os_passes(self):
        current = platform.system().lower()
        if current == "darwin":
            current = "macos"
        m = make_manifest(platforms=[current])
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            result = await self.verifier.verify(m, tmpdir)
        assert result.verified

    @pytest.mark.asyncio
    async def test_platform_mismatch_fails(self):
        # Use a platform the current OS is definitely not
        current = platform.system().lower()
        if current == "darwin":
            current = "macos"
        unsupported = "haiku-os-9"  # definitely not a real platform name
        m = make_manifest(platforms=[unsupported])
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            result = await self.verifier.verify(m, tmpdir)
        assert not result.verified

    # --- AIOS version ---

    @pytest.mark.asyncio
    async def test_aios_version_compatible(self):
        m = make_manifest(minimum_aios_version="1.0.0")
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            result = await self.verifier.verify(m, tmpdir)
        assert result.verified

    @pytest.mark.asyncio
    async def test_aios_version_too_new_fails(self):
        m = make_manifest(minimum_aios_version="9.0.0")
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            result = await self.verifier.verify(m, tmpdir)
        assert not result.verified
        assert any("AIOS version" in msg for msg in result.messages)

    # --- SDK version ---

    @pytest.mark.asyncio
    async def test_sdk_version_compatible_same(self):
        m = make_manifest(sdk_version="1.0.0")
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            result = await self.verifier.verify(m, tmpdir)
        assert result.verified

    @pytest.mark.asyncio
    async def test_sdk_major_mismatch_fails(self):
        verifier = PluginVerifier(aios_version="2.0.0", sdk_version="1.0.0")
        m = make_manifest(sdk_version="2.0.0")
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            result = await verifier.verify(m, tmpdir)
        assert not result.verified

    # --- Package completeness ---

    @pytest.mark.asyncio
    async def test_missing_entry_point_fails(self):
        m = make_manifest(entry_point="plugin.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            # Don't create plugin.py
            result = await self.verifier.verify(m, tmpdir)
        assert not result.verified
        assert any("entry point" in msg.lower() or "Missing" in msg for msg in result.messages)

    @pytest.mark.asyncio
    async def test_complete_package_passes(self):
        m = make_manifest(entry_point="plugin.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            result = await self.verifier.verify(m, tmpdir)
        assert result.verified

    @pytest.mark.asyncio
    async def test_icon_missing_is_warning_not_failure(self):
        m = make_manifest(icon="icon.png")
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "plugin.py").write_text("# plugin")
            # Don't create icon.png
            result = await self.verifier.verify(m, tmpdir)
        # Icon missing is a warning, not a failure — still verified
        assert result.verified

    # --- Checksum ---

    def test_checksum_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "plugin.py").write_text("print('hello')")
            c1 = self.verifier.calculate_checksum(tmpdir)
            c2 = self.verifier.calculate_checksum(tmpdir)
            assert c1 == c2
            assert len(c1) == 64  # SHA-256 hex

    def test_checksum_changes_with_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "plugin.py"
            f.write_text("version = 1")
            c1 = self.verifier.calculate_checksum(tmpdir)
            f.write_text("version = 2")
            c2 = self.verifier.calculate_checksum(tmpdir)
            assert c1 != c2
