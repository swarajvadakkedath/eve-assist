"""Tests for updater (placeholder)."""

import pytest

from launcher.updater import Updater, UpdateInfo


def test_updater_initial_state():
    updater = Updater()
    assert updater.update_available is False


@pytest.mark.asyncio
async def test_check_for_update():
    updater = Updater()
    info = await updater.check_for_update()
    assert info.available is False


@pytest.mark.asyncio
async def test_download_update():
    updater = Updater()
    result = await updater.download_update(UpdateInfo())
    assert result is False


@pytest.mark.asyncio
async def test_apply_update():
    updater = Updater()
    result = await updater.apply_update(UpdateInfo())
    assert result is False


def test_update_info_defaults():
    info = UpdateInfo()
    assert info.available is False
    assert info.version == ""
    assert info.mandatory is False
    assert info.download_url == ""
