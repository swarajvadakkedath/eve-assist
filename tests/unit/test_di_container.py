"""Unit tests for the DI Container."""

import pytest
from aios.core.di_container import (
    DIContainer,
    RegistrationNotFoundError,
    CircularDependencyError,
    init_container,
    start_container,
    stop_container,
)


class _Logger:
    def __init__(self):
        self.messages = []

    def log(self, msg: str):
        self.messages.append(msg)


class _ServiceA:
    def __init__(self, logger: _Logger):
        self.logger = logger

    def do_work(self):
        self.logger.log("A worked")


class _ServiceB:
    def __init__(self, service_a: _ServiceA, logger: _Logger):
        self.service_a = service_a
        self.logger = logger

    def do_work(self):
        self.service_a.do_work()
        self.logger.log("B worked")


class _LifecycleModule:
    def __init__(self, logger: _Logger):
        self.logger = logger
        self.init_called = False
        self.start_called = False
        self.stop_called = False

    async def on_init(self):
        self.init_called = True
        self.logger.log("init")

    async def on_start(self):
        self.start_called = True
        self.logger.log("start")

    async def on_stop(self):
        self.stop_called = True
        self.logger.log("stop")


class _CircularA:
    def __init__(self, b: "_CircularB"):
        pass


class _CircularB:
    def __init__(self, a: _CircularA):
        pass


@pytest.fixture
def container():
    return DIContainer()


def test_register_resolve(container):
    container.register(_Logger)
    logger = container.resolve(_Logger)
    assert isinstance(logger, _Logger)


def test_singleton_scope(container):
    container.register(_Logger)
    a = container.resolve(_Logger)
    b = container.resolve(_Logger)
    assert a is b


def test_factory_scope(container):
    container.register(_Logger, scope="factory")
    a = container.resolve(_Logger)
    b = container.resolve(_Logger)
    assert a is not b
    assert isinstance(a, _Logger)
    assert isinstance(b, _Logger)


@pytest.mark.asyncio
async def test_lifecycle_hooks(container):
    logger = _Logger()
    container.register(_Logger, factory=lambda: logger)
    container.register(_LifecycleModule)

    mod = container.resolve(_LifecycleModule)
    assert isinstance(mod, _LifecycleModule)
    assert not mod.init_called
    assert not mod.start_called
    assert not mod.stop_called

    await init_container(container)
    assert mod.init_called
    assert "init" in logger.messages

    await start_container(container)
    assert mod.start_called
    assert "start" in logger.messages

    await stop_container(container)
    assert mod.stop_called
    assert "stop" in logger.messages


def test_module_dependencies(container):
    container.register(_Logger)
    container.register(_ServiceA)
    container.register(_ServiceB)

    b = container.resolve(_ServiceB)
    assert isinstance(b, _ServiceB)
    assert isinstance(b.service_a, _ServiceA)
    assert b.service_a is container.resolve(_ServiceA)

    b.do_work()
    assert b.logger.messages == ["A worked", "B worked"]


def test_registration_not_found(container):
    with pytest.raises(RegistrationNotFoundError):
        container.resolve(_Logger)


def test_circular_dependency_detected(container):
    container.register(_CircularA)
    container.register(_CircularB)
    with pytest.raises(CircularDependencyError):
        container.resolve(_CircularA)


def test_is_registered(container):
    container.register(_Logger)
    assert container.is_registered(_Logger)
    assert not container.is_registered(_ServiceA)


def test_child_scope_inherits_registrations(container):
    container.register(_Logger)
    child = container.create_scope()
    assert child.is_registered(_Logger)
    logger = child.resolve(_Logger)
    assert isinstance(logger, _Logger)


def test_clear_singletons(container):
    container.register(_Logger)
    a = container.resolve(_Logger)
    container.clear_singletons()
    b = container.resolve(_Logger)
    assert a is not b


def test_factory_override(container):
    custom = _Logger()
    container.register(_Logger, factory=lambda: custom)
    result = container.resolve(_Logger)
    assert result is custom
