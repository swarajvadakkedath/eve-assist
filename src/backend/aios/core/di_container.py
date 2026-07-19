"""Dependency Injection container for AIOS module wiring."""

from typing import Any, Callable


class DIContainer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = {}
            cls._instance._singletons = {}
        return cls._instance

    def register(
        self,
        interface: type,
        implementation: Callable[..., Any] | type,
        scope: str = "singleton",
    ):
        self._registry[interface] = {
            "implementation": implementation,
            "scope": scope,
        }

    def resolve(self, interface: type) -> Any:
        if interface not in self._registry:
            raise KeyError(f"No registration found for {interface.__name__}")

        entry = self._registry[interface]

        if entry["scope"] == "singleton":
            if interface not in self._singletons:
                self._singletons[interface] = entry["implementation"]()
            return self._singletons[interface]

        return entry["implementation"]()

    def create_scope(self) -> "DIContainer":
        scope = DIContainer()
        scope._registry = self._registry.copy()
        scope._singletons = {}
        return scope

    def has(self, interface: type) -> bool:
        return interface in self._registry

    def clear(self):
        self._registry.clear()
        self._singletons.clear()
