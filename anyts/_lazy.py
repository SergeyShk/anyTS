import sys
from importlib import import_module
from types import ModuleType
from typing import Any


class LazyPackage(ModuleType):
    """
    Package whose names are imported from their modules on first use

    Description:
        The module of every name is in the mapping _MODULES of the package, so
        that importing one module does not load the dependencies of the others.
        A module named as one of its functions (zipf, kwic) keeps the function
        under that name in the package, as an eager import would
    """

    def __getattr__(self, name: str) -> Any:
        modules = self.__dict__["_MODULES"]
        if name not in modules:
            raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")
        value = getattr(import_module(f".{modules[name]}", self.__name__), name)
        super().__setattr__(name, value)
        return value

    def __setattr__(self, name: str, value: Any) -> None:
        if isinstance(value, ModuleType) and name in self.__dict__.get("_MODULES", ()):
            return
        super().__setattr__(name, value)

    def __dir__(self) -> list[str]:
        return sorted({*super().__dir__(), *self.__dict__["_MODULES"]})


def make_lazy(name: str) -> None:
    """Turning a package into a LazyPackage by the name of its module"""
    sys.modules[name].__class__ = LazyPackage
