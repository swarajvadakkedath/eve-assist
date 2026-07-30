"""DI Container — dependency injection and module lifecycle management."""

import typing
from typing import Any, Callable


class DIContainerError(Exception):
    code: str = "DI_CONTAINER_ERROR"


class RegistrationNotFoundError(DIContainerError):
    code = "REGISTRATION_NOT_FOUND"


class CircularDependencyError(DIContainerError):
    code = "CIRCULAR_DEPENDENCY"


class _Registration:
    def __init__(self, interface: type, implementation: type, scope: str, factory: Callable | None = None):
        self.interface = interface
        self.implementation = implementation
        self.scope = scope
        self.factory = factory


class DIContainer:
    def __init__(self, parent: "DIContainer | None" = None):
        self._registry: dict[str, _Registration] = {}
        self._singletons: dict[str, Any] = {}
        self._instances: dict[str, Any] = {}
        self._parent = parent

    def register(
        self,
        interface: type,
        implementation: type | None = None,
        scope: str = "singleton",
        factory: Callable | None = None,
    ) -> None:
        if implementation is None:
            implementation = interface
        key = self._key(interface)
        self._registry[key] = _Registration(interface, implementation, scope, factory)

    def resolve(self, interface: type) -> Any:
        return self._resolve(interface, _resolving=set())

    def _resolve(self, interface: type, _resolving: set) -> Any:
        key = self._key(interface)

        if key in self._singletons:
            return self._singletons[key]

        if key in self._instances:
            return self._instances[key]

        registration = self._registry.get(key)
        if registration is None:
            if self._parent:
                return self._parent._resolve(interface, _resolving)
            raise RegistrationNotFoundError(f"No registration for {interface.__name__}")

        if key in _resolving:
            raise CircularDependencyError(
                f"Circular dependency detected: {interface.__name__}"
            )
        _resolving.add(key)

        try:
            if registration.factory:
                instance = registration.factory()
            else:
                instance = self._build_instance(registration.implementation, _resolving)
        finally:
            _resolving.discard(key)

        if registration.scope == "singleton":
            self._singletons[key] = instance

        return instance

    def _build_instance(self, implementation: type, _resolving: set) -> Any:
        init = implementation.__init__
        try:
            hints = typing.get_type_hints(init)
        except (NameError, AttributeError):
            hints = {}
        params: list[Any] = []

        for name, param_type in hints.items():
            if name == "return":
                continue
            resolved = self._resolve(param_type, _resolving)
            params.append(resolved)

        return implementation(*params)

    def create_scope(self) -> "DIContainer":
        child = DIContainer(parent=self)
        for key, reg in self._registry.items():
            child._registry[key] = reg
        return child

    def is_registered(self, interface: type) -> bool:
        key = self._key(interface)
        return key in self._registry or (self._parent is not None and self._parent.is_registered(interface))

    def clear_singletons(self) -> None:
        self._singletons.clear()

    def _key(self, interface: type) -> str:
        return f"{interface.__module__}.{interface.__name__}"


class LifecycleAware:
    async def on_init(self) -> None: ...
    async def on_start(self) -> None: ...
    async def on_stop(self) -> None: ...


async def init_container(container: DIContainer) -> None:
    for instance in container._singletons.values():
        if hasattr(instance, "on_init") and callable(instance.on_init):
            coro = instance.on_init()
            if hasattr(coro, "__await__"):
                await coro


async def start_container(container: DIContainer) -> None:
    for instance in container._singletons.values():
        if hasattr(instance, "on_start") and callable(instance.on_start):
            coro = instance.on_start()
            if hasattr(coro, "__await__"):
                await coro


async def stop_container(container: DIContainer) -> None:
    for instance in container._singletons.values():
        if hasattr(instance, "on_stop") and callable(instance.on_stop):
            coro = instance.on_stop()
            if hasattr(coro, "__await__"):
                await coro
